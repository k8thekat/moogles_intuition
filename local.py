# ruff : noqa
# type: ignore
import argparse
import asyncio
import datetime
import json
import logging
import subprocess
import sys
from argparse import Namespace
from configparser import ConfigParser
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from time import time
from typing import TYPE_CHECKING, Any, ClassVar, Optional

import aiohttp
from async_garlandtools import GarlandToolsAsync as GarlandTools
from async_garlandtools._types import TradeShops
from universalis import CurrentData, UniversalisAPI, World


from moogle_intuition import Moogle, Currency, Item


if TYPE_CHECKING:
    from async_garlandtools._types import ItemResponse

    from moogle_intuition.ff14angler import AnglerFish


local_data_path: Path = Path(__file__).parent.joinpath("moogle_intuition")
LOGGER: logging.Logger = logging.getLogger(__name__)


async def local_test() -> None:
    moogle: Moogle = await Moogle().build()
    stime = time()  # don't remove this line.
    res = await moogle.currency_spender(currency=Currency.Allagan_Tomestone_of_Poetics)
    print(res)
    LOGGER.info("Completed local_test() in %s seconds...", format(time() - stime, ".3f"))
    await moogle.clean_up()


async def build_test() -> None:
    """Tests the FFXIVBuilder class.

    Testing the build function,
    also making sure it can get Fish/Fishing related items, Recipe and gatherable items properly.

    """
    item_handler: Moogle = await Moogle().build()
    # Item lookup test.
    item: Item = item_handler.get_item(item="Angelfish", limit_results=1)  # Angelfish
    print(item)  # noqa:

    # Fishing Item test
    # This is to check the types of Fish vs SpearFishing
    print(type(item.fishing))
    print(item.fishing)

    # FF14 Angler Test...
    data: Optional[AnglerFish] = await item.fishing.get_angler_data()
    print(data)
    print(data.best_bait())

    # Recipe Item Test
    item: Item = item_handler.get_item(item="27300")  # Titania Shadow Box
    print(item)
    print(item.recipe)

    # Gathering Item Test
    item: Item = item_handler.get_item(item="36164")  # Bismuth Ore
    print(item)
    print(item.gathering)

    # Marketboard Test
    await item_mb_test(item="27300")


async def item_mb_test(item: str) -> Item | list[Item]:
    item_handler = await Moogle().build()
    stime = time()
    items: list[Item] = item_handler.get_item(item=item)

    print(len(items))
    if isinstance(items, list):
        for entry in items:
            print(entry.name, entry.id)
            print(entry.recipe)
            print(entry.get_current_marketboard())
    LOGGER.info("Completed item_name search in %s seconds...", format(time() - stime, ".3f"))
    return items


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
    info: bool
    debug: bool
    upgrade: Optional[str]


_parser = argparse.ArgumentParser(description="Local arg parse for Python Package development")
_parser.add_argument("-local", help="Run our local_test() function", default=False, required=False, action="store_true")
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
    subprocess.run([f"uv sync -n --upgrade-package {_parsed_args.upgrade}"], check=False, shell=True)  # noqa: S602
    LOGGER.info("Completed in %s seconds...", format(time() - stime, ".3f"))

if _parsed_args.local:
    LOGGER.info("Running local_test()...")
    asyncio.run(local_test())
    LOGGER.info("Completed in %s seconds...", format(time() - stime, ".3f"))

if _parsed_args.build:
    LOGGER.info("Build...")
    # subprocess.call("./build.bash")
    LOGGER.info("Completed in %s seconds...", format(time() - stime, ".3f"))
