# type:ignore
# ruff: noqa
import argparse
import asyncio
import base64
import copy
import datetime
import json
import logging
import operator
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
from async_garlandtools import GarlandToolsAsync as GarlandTools
from async_garlandtools._types import ItemResponse, TradeShops
from async_universalis import CurrentData, CurrentDataEntries, DataCenter, HistoryData, MultiPart, UniversalisAPI, World

from moogle_intuition import Currency, Item, Moogle, Expansion
from moogle_intuition._enums import InventoryLocation
from moogle_intuition._types import Crafting, CurMarketBoardParams, ShoppingCurrency, Vendor

if TYPE_CHECKING:
    from async_garlandtools._types import ItemResponse

    from moogle_intuition._types import MakePlaceData
    from moogle_intuition.ff14angler import AnglerFish
    from moogle_intuition.modules import InventoryItem


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


async def local_test() -> None:
    """Co-routine to run local tests."""
    moogle: Moogle = await Moogle().build()
    stime = time()  # don't remove this line.
    # item: Item = moogle.get_item(item="10373", limit_results=1) # Magitek Repair Mats
    item = moogle.get_item(item="Square Maple Shield", limit_results=1)
    print("Item Obj:\n", item)
    print("Recipe Obj:\n", item.recipe)
    pprint(await item.recipe.get_crafting_cost())
    LOGGER.info("Completed local_test() in %s seconds...", format(time() - stime, ".3f"))
    await moogle.clean_up()


async def currency(moogle: Moogle) -> None:
    res: dict[int, ShoppingCurrency] | None = await moogle.currency_spender(
        Currency.Serpent_Seal, patch=Expansion.Endwalker, world_or_dc=World.Zalera
    )
    # print(res)
    if res is not None:
        write_data_to_file(file_name="seals_crystal.txt", data=parse_shopping_data(res), path=Path().joinpath("local_data/dumps"))


def parse_shopping_data(data: dict[int, ShoppingCurrency]) -> list[str]:
    """I was using this to parse currency_spender return data."""
    output: list[str] = []
    entries: list[ShoppingCurrency] = []
    for entry in data:
        res: ShoppingCurrency | None = data.get(entry, None)
        # print(entry, res)
        if res is None:
            continue
        # if res["marketboard"] is None:
        #     print("No MB", entry)
        entries.append(res)
    # entries: list[ShoppingCurrency] = [data.get(entry) for entry in data if data.get(entry) is not None]
    for item in sorted(entries, key=lambda x: x["marketboard"].regular_sale_velocity):
        if item is None:
            continue
        # print("Got Shopping Data", type(shopping))
        mb: CurrentData | HistoryData | None = item["marketboard"]
        if mb is None:
            continue
        timestamp: str | int = (
            mb.last_upload_time.strftime("%d/%m | %H:%M(%Z)") if isinstance(mb.last_upload_time, datetime.datetime) else mb.last_upload_time
        )
        temp: str = (
            f"Name: {mb.name}[{mb.item_id}] | Timestamp: {timestamp} | Sale Velocity: {mb.regular_sale_velocity} | "
            f"Avg Price Cur({mb.current_average_price}) | Hist({mb.average_price}) | Min({mb.min_price}) | Currency Cost: {item['cost']} | "
            f"PPU/Currency: {mb.min_price / item['cost']:2f}"
        )
        # print("Appending Data")
        output.append(temp)

    return output


# def sorted_dict(entries: dict[int, ShoppingCurrency]):
#     for item_id, data in entries.items():


async def dev_test() -> None:
    moogle: Moogle = await Moogle().build()
    await makeplace_housing(moogle)
    await moogle.clean_up()
    pass


# Attempting to create a full list of items to finish a "MakePlace" build.
async def makeplace_housing(moogle: Moogle) -> None:
    """Co-routine to run development tests."""
    # moogle: Moogle = await Moogle().build()
    stime = time()  # don't remove this line.
    mp_data: MakePlaceData = load_data_from_file(Path("./local_data/Kat House.json"), is_json=True)  # pyright: ignore[reportAssignmentType]
    atools_data: str = load_data_from_file(Path("./local_data/8.25.2025.csv"), encoding="utf-8-sig")  # pyright: ignore[reportAssignmentType]

    res: list[Item] = await moogle.makeplace_create_itemlist(makeplace_data=mp_data, atools_data=atools_data)

    output: list[str] = []
    # TODO: Maybe count all currency's?
    # Marketboard Gil will by default have an ID of 0.
    # Non-MB Gil will be ID of 1
    currencies: dict[int, int] = {0: 0, 1: 0}
    output.append(f"# MakePlace Shopping List:")
    output.append("*Note*: Marketboard Total includes Tax. *(mb listing count * price per unit + tax)*\n")
    output.append(f"__[TeamCraft List URL]({moogle.teamcraft_list(res)})__")
    output.append((f"\n- Total # of Items: {len(res)}\n----"))
    for item in res:
        # This is the finished item section..
        output.append(f"## __[{item.name}]({item.garland_tools_url})__ [{item.id}]")
        # TODO(@k8thekat): Handle items not craftable; but still tradeable or purchasable from a Vendor/etc.
        # See "A Knight to Remember [13289] as an example."
        if item.recipe is not None:
            data: dict[int, Crafting] | None = await item.recipe.get_crafting_cost()
            output.append(f"- Total # of Ingredients: {len(data)}")
            # These are all the ingredients; so we should see a count.
            for entry in data:
                value: Crafting | None = data.get(entry, None)
                data_item = value.get("item")

                # Ingredient Information, Name, URL, ID and Count
                output.append(f"### __[{data_item.name}]({data_item.garland_tools_url})__ [{data_item.id}] ")
                output.append(f"> Count: {value.get('count')}\n")
                # Ingredient info cont...
                # Marketboard/Universalis Info.
                marketboard: CurrentData | None = value.get("marketboard", None)
                if marketboard is None:
                    output.append("#### **Marketboard**: N/A")
                else:
                    market_listing: CurrentDataEntries = sorted(marketboard.listings, key=lambda x: x.price_per_unit)[0]
                    currencies[0] += market_listing.tax + market_listing.total
                    # TODO(@k8thekat): Improve timestamp display, show date and time as UTC.
                    output.append(f"#### **Marketboard**: [{market_listing.last_review_time.date()}]")
                    output.append(
                        f"> World/DC: {market_listing.world_name}/{market_listing.dc_name} | PPU | Listing Count: {market_listing.price_per_unit} | [{market_listing.quantity}] | Total: {market_listing.tax + market_listing.total}"
                    )

                # Vendors info...
                vendors: list[Vendor] | None = value.get("vendors", None)
                if vendors is None:
                    output.append("#### **Vendors**: N/A")
                else:
                    vendor_cur_flag = True
                    for cur_vendor in vendors:
                        output.append(
                            f"#### **Vendor**: [{cur_vendor.get('name')} | {cur_vendor.get('shop_name')}]({cur_vendor.get('url', 'N/A')})"
                        )
                        currency: Item | None = cur_vendor.get("currency")
                        price = cur_vendor.get("price", 0)
                        if currency is not None:
                            output.append(f"> Currency: {currency.name} | Cost: {price} | ")
                            if vendor_cur_flag is True:
                                currencies[currency.id] += price
                                vendor_cur_flag = False
                        else:
                            output.append(f"> Currency: Gil | Cost: {price}")
                            if vendor_cur_flag is True:
                                currencies[1] += price
                                vendor_cur_flag = False

                # Tradeshop Info...
                tradeshops: list[Vendor] | None = value.get("tradeshops", None)
                if tradeshops is None:
                    output.append("#### **TradeShops**: N/A")
                else:
                    shop_cur_flag = True
                    for cur_shop in tradeshops:
                        output.append(
                            f"#### **TradeShop**: [{cur_vendor.get('name')} | {cur_vendor.get('shop_name')}]({cur_vendor.get('url', 'N/A')})"
                        )
                        currency: Item | None = cur_shop.get("currency")
                        price = cur_shop.get("price", 0)
                        if currency is not None:
                            output.append(f"> Currency: {currency.name} | Cost: {price} | ")
                            if shop_cur_flag is True:
                                currencies[currency.id] += price
                                shop_cur_flag = False
                        else:
                            output.append(f"> Currency: Gil | Cost: {price}")
                            if shop_cur_flag is True:
                                currencies[1] += price
                                shop_cur_flag = False
        output.append("\n")
    output.append("---")
    for entry in currencies:
        val = currencies.get(entry)
        if entry == 0:
            output.append(f"**Total Marketboard Gil**: {val:,d}\n")
        elif entry == 1 and val > 0:
            output.append(f"**Total Vendor Gil**: {val:,d}\n")
        else:
            output.append(f"Currency: {entry} | Count: {val:,d}")

    write_data_to_file(file_name="shopping_list.md", data="\n".join(output))
    LOGGER.info("Completed local_test() in %s seconds...", format(time() - stime, ".3f"))


async def build_test() -> None:
    """|CORO|

    Tests the FFXIVBuilder class.

    Testing the build function,
    also making sure it can get Fish/Fishing related items, Recipe and gatherable items properly.

    """
    item_handler: Moogle = await Moogle().build()
    # Item lookup test.
    item: Item = item_handler.get_item(item="Angelfish", limit_results=1)  # Angelfish
    item.level_item
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
    """Co-routine"""
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

if _parsed_args.dev:
    LOGGER.info("Running dev_test()...")
    asyncio.run(dev_test())
    LOGGER.info("Completed in %s seconds...", format(time() - stime, ".3f"))
