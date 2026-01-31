# pyright: ignore[reportUnusedImport]  # noqa: D100
from __future__ import annotations

import argparse
import asyncio
import base64
import copy
import csv
import datetime
import json
import logging
import operator
import pickle
import subprocess
import sys
from argparse import Namespace
from configparser import ConfigParser
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from pprint import pprint
from time import time
from typing import TYPE_CHECKING, Any, ClassVar, Optional, TypedDict, Unpack

import aiohttp
import aiohttp.web
from aiohttp import FormData
from async_garlandtools import GarlandToolsAsync as GarlandTools, IconType
from async_garlandtools._types import ItemResponse, NodeResponse, TradeShops
from async_universalis import CurrentData, CurrentDataEntries, DataCenter, HistoryData, MultiPart, UniversalisAPI, World
from bs4 import BeautifulSoup
from bs4.element import Tag

from moogle_intuition import Angler, Currency, Expansion, GatheringNode, Item, Moogle
from moogle_intuition._types import CurrencySpender, ShoppingItem, Vendor
from moogle_intuition.ext.allagan_tools._types import RecipeCrafting
from moogle_intuition.ext.converters import Converter

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine  # pyright: ignore[reportUnusedImport]

    from moogle_intuition._types import CurrencySpender


local_data_path: Path = Path(__file__).parent.joinpath("moogle_intuition")
LOGGER: logging.Logger = logging.getLogger(__name__)

missing = []
timestamp_format = "%d/%m | %H:%M(%Z)"

a = [
    "White Pepper",
    "Royal Maple Sap",
    "Raw Black Star",
    "Ra'Kaznar Ore",
    "Mountain Rock Salt",
    "Magnesia Powder",
    "Ginseng Log",
    "Claro Walnut Log",
    "Ceiba Log",
]




b = """<UIForeground>F201F8</UIForeground><UIGlow>F201F9</UIGlow>EXP Bonus:<UIGlow>01</UIGlow><UIForeground>01</UIForeground> +3% <UIForeground>F201F8</UIForeground><UIGlow>F201F9</UIGlow>Duration:<UIGlow>01</UIGlow><UIForeground>01</UIForeground> 30m
(Duration can be extended to 60m by consuming multiple)"""


async def local_test() -> None:
    """Co-routine to run local tests."""
    moogle = await Moogle().build(use_v2= True)
    item = moogle.get_item("Flying Chair", limit_results=1)
    print(item)
    await moogle.clean_up()



async def tradeshop_testing(moogle: Moogle) -> None:  # noqa: D103
    item = moogle.get_item("15855", limit_results=1)
    print(item.name)
    gt_data: ItemResponse | None = await item.get_garlandtools_data()
    if gt_data is not None:
        pprint(gt_data["item"].get("tradeShops"))
    print(item.get_tradeshops())
    return


def parse_test(data: dict[int, ShoppingItem], indent: int = 0):  # noqa: ANN201, D103
    for key in data:
        # print("Key", key)
        value = data.get(key)
        if value is None:
            continue

        tabs = "\t" * indent
        if value.get("ingredients", None) is not None:
            print(tabs, value["item"].name, value["item"].id, value["count"], "-> Ingredients:")
            parse_test(data=value["ingredients"], indent=indent + 1)
        else:
            print(tabs, value["item"].name, value["item"].id, value["count"], "-> No Ingredients")


async def currency(moogle: Moogle) -> None:  # noqa: D103
    currency = Currency.serpent_seal
    world_or_dc = World.Zalera
    res: dict[int, CurrencySpender] | None = await moogle.currency_spender(
        currency,
        patch=Expansion.shadowbringers,
        world_or_dc=world_or_dc,
    )

    if res is not None:
        write_data_to_file(
            file_name=f"{currency.name}_{world_or_dc.name}.txt",
            data=Converter.parse_shopping_data(res),
            path=Path().joinpath("local_data/dumps"),
        )


async def dev_test() -> None:  # noqa: D103
    stime = time()
    moogle: Moogle = await Moogle().build(ignore_validation=True)
    item = moogle.get_item("Flying Chair", limit_results=1)
    pprint(item._raw)
    LOGGER.info("Completed dev_test() in %s seconds...", format(time() - stime, ".3f"))
    await moogle.clean_up()


async def request(  # noqa: D103
    url: str,
    session: Optional[aiohttp.ClientSession] = None,
    auto_close: bool = True,
    raw_bytes: bool = False,
) -> Optional[bytes | dict[Any, Any]]:  # pyright: ignore[reportUnusedFunction]
    if session is None:
        session = aiohttp.ClientSession()

    res: aiohttp.ClientResponse = await session.get(url=url)
    if res.status != 200:
        LOGGER.error("<%s._request> failed to access the url. | Status Code: %s | URL: %s", __file__, res.status, url)
        return None
        # raise ConnectionError("Unable to access the url: %s", url)
    if raw_bytes:
        data = await res.content.read()
    else:
        data = await res.json()
    if auto_close:
        await session.close()
    return data


def csv_parse(file: Path) -> Any:  # noqa: D103
    with file.open(mode="r", encoding="utf-8") as csv_file:
        column_keys = csv_file.readline()[0:-1].split(",")
        data = csv.DictReader(csv_file, fieldnames=column_keys)
        res = {}
        for row in data:
            # print(row)
            # if row["Color"] == "":
            #     continue
            res[row["##"]] = row["Name"]
            # print(f'{row["##"]} = "{row["Name"].replace(" ", "_")}"')
            print(f'{row["Name"].replace(" ", "_")} = "{row["##"][:-2]}"')


async def time_validation(func: Callable[..., Coroutine[Any, Any, Any]]) -> Any:  # noqa: D103
    stime = time()
    if asyncio.iscoroutinefunction(func):
        var = await func()
    else:
        var = func()

    LOGGER.info("Completed local_test() in %s seconds...", format(time() - stime, ".3f"))
    return var


def ini_load(file: Path, section: str, options: list[str]) -> list[str | None]:
    """Parse an ini file.

    Parameters
    ----------
    file: :class:`Path`
        The file path.
    section: :class:`str`
        The name of the section. `[section_name]`.
    options: :class:`list[str]`
        The options to load as a list.

    Returns
    -------
        The list of options loaded in the same order.

    """
    if file.is_file():
        settings = ConfigParser(converters={"list": lambda setting: [value.strip() for value in setting.split(",")]})
        settings.read(filenames=file)
        res: list[str | None] = []
        for entry in options:
            res.append(settings.get(section=section, option=entry, fallback=None))
        return res
    raise FileNotFoundError("<%s> | Failed to load file. | Path: %s", "local.ini_load", file.as_posix())


def flatten(data: list[Any], new_list: list[Any]) -> list:
    """Flatten a list."""
    for i in data:
        if isinstance(i, list):
            flatten(i, new_list)
        else:
            new_list.append(i)
    return new_list


def load_data_from_file(
    path: Path,
    size: Optional[int] = None,
    is_json: bool = False,
    encoding: str = "utf-8",
) -> str | dict[str, dict[str, Any]] | dict[str, Any]:
    """Basic file read.

    Parameters
    ----------
    path: :class:`Path`
        The Path to load the data from.
    size: :class:`Optional[int]`, optional
        The amount of data to read if needed, by default None will read until EOF.
    is_json: :class:`bool`, optional
        If the file is a json file, by default False.
    encoding: :class:`str`, optional
        The encoding to use, by default "utf-8".

    Returns
    -------
    :class:`str`
        The file data.

    Raises
    ------
    FileNotFoundError
        If the file path doesn't exist.

    """
    if path.exists() is False:
        msg = "<%s.%s> | The Path provided does not exist. | Path: %s"
        raise FileNotFoundError(msg, __name__, "load_data_from_file", path)

    with path.open(mode="r", encoding=encoding) as file:
        if is_json is True:
            return json.loads(file.read(size))

        return file.read(size)


def write_data_to_file(
    file_name: str,
    data: bytes | dict[Any, Any] | str | list[str],
    path: Path = Path(__file__).parent,
    *,
    mode: str = "w+",
    **kwargs: Any,
) -> None:
    """Basic file dump with json handling. If the data parameter is of type `dict`, `json.dumps()` will be used with an indent of 4.

    Parameters
    ----------
    path: :class:`Path`, optional
        The Path to write the data, default's to `Path(__file__).parent`.
    file_name: :class:`str`
        The name of the file, include the file extension.
    data: :class:`bytes | dict | str | list`
        The data to write out to the path and file_name provided.
    mode: :class:`str`, optional
        The mode to open the provided file path with using `<Path.open()>`.
    **kwargs: :class:`Any`
        Any additional kwargs to be supplied to `<json.dumps()>`, if applicable.

    """
    with path.joinpath(file_name).open(mode=mode) as file:
        LOGGER.debug("<%s.%s> | Wrote data to file %s located at: %s", __name__, "write_data_to_file", path, file_name)
        if isinstance(data, bytes):
            file.write(data.decode(encoding="utf-8"))
        elif isinstance(data, dict):
            file.write(json.dumps(data, indent=4, **kwargs))
        elif isinstance(data, list):
            file.write("\n".join(data))
        else:
            file.write(data)
    LOGGER.info(
        "<%s.%s> | File write successful to path: %s ",
        __name__,
        "write_data_to_file",
        path.joinpath(file_name).as_posix(),
    )


class LogHandler:
    """Loggy~.

    Discord Multi-line code block formats:
    - https://github.com/highlightjs/highlight.js/blob/main/SUPPORTED_LANGUAGES.md

    """

    cur_log: Path
    code_formats: ClassVar[list[str]] = ["excel", "nc", "ml", " nim", " ps", " prolog", "thor"]
    default_code_format: str = "ps"

    def __init__(self, level: int = logging.INFO) -> None:
        self.path: Path = Path(__file__).parent.joinpath("logs")
        if self.path.exists() is False:
            self.path.mkdir()

        self.cur_log: Path = Path(__file__).parent.joinpath("logs/log.log")

        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(threadName)s] [%(levelname)s]  %(message)s",
            datefmt="%m/%d/%Y %I:%M:%S %p",
            handlers=[
                logging.StreamHandler(stream=sys.stdout),
                TimedRotatingFileHandler(
                    filename=Path.as_posix(self=self.path) + "/log.log",
                    when="midnight",
                    atTime=datetime.datetime.min.time(),
                    backupCount=4,
                    encoding="utf-8",
                    utc=True,
                ),
            ],
        )


class Launcher(Namespace):
    local: bool
    build: bool
    dev: bool
    info: bool
    debug: bool
    upgrade: Optional[str]


_parser = argparse.ArgumentParser(description="Local arg parse for Python Package development")
_parser.add_argument("-local", help="Run our local_test() function", default=False, required=False, action="store_true")
_parser.add_argument("-dev", help="Run our dev_test() function", default=False, required=False, action="store_true")
_parser.add_argument("-build", help="Run our development_text() function", default=False, required=False, action="store_true")
# uv sync -n --upgrade-package foo
_parser.add_argument("--upgrade", help="Run `uv sync -n --upgrade-package package_name`")
# If I want to add a group, this is what I use.
# group: argparse._MutuallyExclusiveGroup = _parser.add_mutually_exclusive_group(required=False)
_parser.add_argument("-info", help="Set the logging level to `INFO`.", default=False, required=False, action="store_true")
_parser.add_argument("-debug", help="Set the logging level to `INFO`.", default=False, required=False, action="store_true")
_parsed_args: Launcher = _parser.parse_known_args()[0]

# Logging section.
LOGGER.name = "Local Logging - "
if _parsed_args.info:
    LogHandler(level=logging.INFO)
elif _parsed_args.debug:
    LogHandler(level=logging.DEBUG)


# Any specific handling of launch args.
# Update `Launcher` class with new args and type def.
stime: float = time()
if _parsed_args.upgrade:
    LOGGER.info("Running uv sync upgrade. | Package: %s", _parsed_args.upgrade)
    # subprocess.run(["uv" , "sync", "-n" ,"--upgrade-package",_parsed_args.upgrade], check=False)
    subprocess.run([f"uv sync -n -P {_parsed_args.upgrade}"], check=False, shell=True)  # noqa: S602
    LOGGER.info("Completed in %s seconds...", format(time() - stime, ".3f"))

if _parsed_args.local:
    LOGGER.info("Running local_test()...")
    asyncio.run(local_test())
    LOGGER.info("Completed in %s seconds...", format(time() - stime, ".3f"))

if _parsed_args.build:
    LOGGER.info("Build...")
    # subprocess.call("./build.bash")
    LOGGER.info("Completed in %s seconds...", format(time() - stime, ".3f"))

if _parsed_args.dev:
    LOGGER.info("Running dev_test()...")
    asyncio.run(dev_test())
    LOGGER.info("Completed in %s seconds...", format(time() - stime, ".3f"))
