"""Copyright (C) 2021-2025 Katelynn Cadwallader.

This file is part of Moogle's Intuition.

Moogle's Intuition is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3, or (at your option)
any later version.

Moogle's Intuition is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public
License for more details.

You should have received a copy of the GNU General Public License
along with Moogle's Intuition; see the file COPYING.  If not, write to the Free
Software Foundation, 51 Franklin Street - Fifth Floor, Boston, MA
02110-1301, USA.
"""

from __future__ import annotations

import base64
import csv
import json
import logging
import statistics
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    ForwardRef,
    Literal,
    NamedTuple,
    Optional,
    ParamSpec,
    Self,
    TypeVar,
    Union,
    Unpack,
    overload,
)

import aiohttp
from aiohttp_client_cache.session import CachedSession
from async_garlandtools import GarlandToolsAsync, IconType, Object as GTObject
from async_garlandtools._types import Item as GTItem, ItemResponse, PartialTypeIDObj
from async_garlandtools.errors import GarlandToolsKeyError, GarlandToolsRequestError
from async_universalis import CurrentData, CurrentDataEntries, DataCenter, HistoryData, MultiPart, UniversalisAPI, World
from async_universalis.errors import UniversalisError
from thefuzz import fuzz  # type: ignore[reportMissingStubFile]

from moogle_intuition._types import CurrencySpender, ShoppingItem, Vendor
from moogle_intuition.errors import MoogleLookupError
from moogle_intuition.ff14angler._types import FishingData

from ._enums import CraftType, Currency, EquipSlotCategory, Expansion, FishingSpotCategory, ItemUICategory
from ._types import ItemData
from .ff14angler import Angler, AnglerBaits, AnglerFish

if TYPE_CHECKING:
    from collections.abc import Iterator
    from types import TracebackType

    from aiohttp import ClientResponse
    from aiohttp.client import _RequestOptions as AiohttpRequestOptions  # pyright: ignore[reportPrivateUsage]
    from async_garlandtools._types import IDCount, Item as GTItem, ItemResponse, Node, NodeResponse, PartialTypeIDObj, TradeShops
    from async_universalis import CurrentDataEntries, HistoryDataEntries

    from moogle_intuition.ff14angler._types import FishingData

    D = TypeVar("D", bound="Moogle")
    T = ParamSpec("T")
    F = TypeVar("F")
    from ._types import (
        CSVParseParams,
        CurMarketBoardParams,
        CurrencySpender,
        FishingSpotData,
        FishParameterData,
        GatheringData,
        GatheringItemLevelData,
        GatheringNodeData,
        HistMarketBoardParams,
        HTMLKeys,
        ItemLevelData,
        ObjectParams,
        PartialItemData,
        PlaceNameData,
        RecipeData,
        RecipeLevelData,
        RecipeLookUpData,
        ShoppingItem,
        SpearFishingItemData,
        SpearFishingNotebookData,
        Vendor,
    )

    DataTypeAliases = Union[
        ItemData,
        GatheringData,
        GatheringItemLevelData,
        FishingSpotData,
        RecipeLookUpData,
        RecipeData,
        RecipeLevelData,
        FishParameterData,
        PlaceNameData,
        SpearFishingItemData,
        SpearFishingNotebookData,
        GatheringNodeData,
        Node,
    ]


__all__ = (
    "IGNORED_KEYS",
    "PRE_FORMATTED_KEYS",
    "URLS",
    "Builder",
    "Fishing",
    "FishingSpot",
    "Gathering",
    "GatheringNode",
    "Item",
    "Moogle",
    "Recipe",
    "SpearFishing",
    "SpearFishingSpot",
)

LOGGER = logging.getLogger(__name__)
DATA_PATH: Path = Path(__file__).parent.joinpath("xiv_datamining")


PRE_FORMATTED_KEYS: dict[str, str] = {
    "ItemID": "item_id",
    "IsPvP": "is_pvp",
    "ItemUICategory": "item_ui_category",
    "EXPBonus": "exp_bonus",
    "PvPActionSortRow": "pvp_action_sort_row",
    "UIPriority": "ui_priority",
    "OH_percent": "oh_percent",
}
IGNORED_KEYS: list[str] = [
    "CRP",
    "BSM",
    "ARM",
    "GSM",
    "LTW",
    "WVR",
    "ALC",
    "CUL",
    "HP",
    "MP",
    "TP",
    "GP",
    "CP",
    "ADV",
    "GLA",
    "PGL",
    "MRD",
    "LNC",
    "ARC",
    "CNJ",
    "THM",
    "MIN",
    "BTN",
    "FSH",
    "PLD",
    "MNK",
    "WAR",
    "DRG",
    "BRD",
    "WHM",
    "BLM",
    "ACN",
    "SMN",
    "SCH",
    "ROG",
    "NIN",
    "MCH",
    "DRK",
    "AST",
    "SAM",
    "RDM",
    "BLU",
    "GNB",
    "DNC",
    "RPR",
    "SGE",
    "VPR",
    "PCT",
]

SANITIZED_VALUES: list[str] = ["<Emphasis>", "</Emphasis>"]


SANITIZED_HTML: dict[str, HTMLKeys] = {
    "uiforeground": {"replace": ""},
    "uiglow": {"replace": ""},
}


# The order of these keys matter as the occurence of the data in the arrays can vary.
SANITIZED_KEYS: dict[str, str] = {
    ":": "",
    "(": "",
    ")": "",
    "{": "",
    "}": "",
    "][": "_",  # this needs to happen first as it deals with `[0][1]`
    "[": "",
    "]": "",
    "<ms>": "",
    "<s>": "",
    "<%>": "_percent",
    "%": "_percent",
    "'": "",
    " ": "_",
    "-": "_",
    "–": "_",
}


# https://github.com/xivapi/ffxiv-datamining/tree/master/csv
# Used when getting files and using `Moogle.data_building()`
# Simply adding the `file_name` key and the remaining fields, the data will be fetched and converted automatically.
# file_name | convert_pound(bool) | url
URLS: dict[str, tuple[bool, str]] = {
    "item": (True, "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/Item.csv"),
    # Used as a dict for FFXIVItem.level_item
    "item_level": (
        True,
        "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/ItemLevel.csv",
    ),
    "item_search_category": (
        True,
        "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/ItemSearchCategory.csv",
    ),
    "base_params": (True, "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/BaseParam.csv"),
    "recipe": (True, "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/Recipe.csv"),
    "recipe_lookup": (True, "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/RecipeLookup.csv"),
    "gathering_item": (True, "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/GatheringItem.csv"),
    "gathering_item_level": (
        False,
        "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/GatheringItemLevelConvertTable.csv",
    ),
    "fish_parameter": (True, "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/FishParameter.csv"),
    "fishing_spot": (True, "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/FishingSpot.csv"),
    "spearfishing_item": (True, "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/SpearfishingItem.csv"),
    "spearfishing_notebook": (
        True,
        "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/SpearfishingNotebook.csv",
    ),
    "class_job": (True, "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/ClassJob.csv"),
    "class_job_category": (True, "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/ClassJobCategory.csv"),
    "place_name": (True, "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/PlaceName.csv"),
}

DATA_URLS: dict[str, tuple[str, str]] = {
    "item_special_bonus": ("name", "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/ItemSpecialBonus.csv"),
    "item_repair_resource": (
        "item",
        "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/ItemRepairResource.csv",
    ),
    "item_ui_category": ("name", "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/ItemUICategory.csv"),
    "item_series": ("name", "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/ItemSeries.csv"),
}


class Object:
    """Our Base object class for FFXIV related object handling."""

    _raw: DataTypeAliases
    _repr_keys: list[str]
    _moogle: Moogle
    # _universalis: Optional[UniversalisAPI]
    # _angler: Optional[Angler]

    # A simple ref dict to map the repair Item to the Key.
    _item_repair: ClassVar[dict[int, int]] = {
        1: 5594,
        2: 5595,
        3: 5596,
        4: 5597,
        5: 5598,
        6: 10386,
        7: 17837,
        8: 33916,
    }
    id: int

    def __init__(self, data: DataTypeAliases, *, moogle: Moogle) -> None:
        """Handles setting our `_raw` attribute and setting our `Moogle` class.

        Parameters
        ----------
        data: :class:`DataTypeAliases`
            Generic typed as the data structure being passed in is typically a dict.
        moogle: :class:`Moogle`
            The :class:`Moogle` object that created this class.

        """
        self._moogle = moogle
        self._raw = data
        LOGGER.debug("<%s.__init__()> | ID: %s | data: %s", __class__.__name__, id(self), data)

    def __str__(self) -> str:
        return self.__repr__()

    def to_json(self) -> dict[str, DataTypeAliases]:
        """Returns the `Object` in JSON format."""
        if hasattr(self, "id"):
            return {f"{self.id}": self._raw}
        return {"0": self._raw}

    def __repr__(self) -> str:
        try:
            res: str = f"\n\n__{self.__class__.__name__}__\n"
            for entry in self._repr_keys:
                if entry.startswith("_"):
                    continue
                try:
                    value = getattr(self, entry)
                    res += f"{entry}: {value}\n"
                except AttributeError:
                    continue

            return res  # noqa: TRY300 # I want to continue generating our str return.
        # This is to catch any objects without a `_repr_keys` defined.
        except AttributeError:
            return f"\n\n__{self.__class__.__name__}__\n" + "\n".join([
                f"{e}: {getattr(self, e)}" for e in sorted(self.__dict__) if e.startswith("_") is False
            ])


class Generic:
    """A Generic object to house attributes and data that `<Moogle>` and `<Builder>` will share and populate."""

    _session: Optional[aiohttp.ClientSession | CachedSession]
    session: Optional[aiohttp.ClientSession | CachedSession]

    # Item Handling.
    _items: dict[str, DataTypeAliases]
    "Structure -> `item_id[str]` : `item_data`"
    _items_ref: dict[str | int, str | int]
    "Useful for Item Name -> Item ID lookups.  `item_name[str]` : `item_id[int]`"

    # Recipe Handling.
    _recipes: dict[str, DataTypeAliases]
    _recipes_ref: dict[str | int, str | int]
    "Useful for Recipe ID -> Item Result lookups. `recipe_id[str]` : `item_result[int]`"

    # Job Recipe Table
    _recipe_lookups: dict[str, DataTypeAliases]

    # Recipe Level Table
    _recipe_levels: dict[str, DataTypeAliases]

    # Gatherable Items Handling.
    _gathering_items: dict[str, DataTypeAliases]
    # Using flipped keys in the item_dict for faster lookup of an item.
    _gathering_items_ref: dict[str | int, str | int]
    "Useful for Gathering ID -> Item ID lookups. `gathering_id[str]` : `item_id[int]`"
    _gathering_item_levels: dict[str, DataTypeAliases]

    # Fishing Related
    _fish_params: dict[str, DataTypeAliases]
    # This is stored with FLIPPED key to values ("Item ID" : "Dict Index")
    _fish_params_ref: dict[str | int, str | int]
    "Useful for Item ID -> Fishing Info ID. `item_id[int]` : `fish_parameter_id[str]`"
    _fishing_spot: dict[str, DataTypeAliases]

    # Spearfishing Related
    _spearfishing_items: dict[str, DataTypeAliases]
    # This is stored with FLIPPED key to values ("item id" : "Dict Index")
    _spearfishing_items_ref: dict[str | int, str | int]
    "Useful for Item ID -> SpearFishing Info ID. `item_id[int]` : `spearfishing_item_id[str]`"
    _spearfishing_notebook: dict[str, DataTypeAliases]

    # Location Information
    _place_names: dict[str, DataTypeAliases]

    def teamcraft_list(self, items: Optional[list[Item]] = None) -> Optional[str]:
        """Create a Teamcraft Import URL from a list of :class:`Item` or if called from a :class:`Item` object will use `Self`.

        If multiple of the :class:`Item`'s are in supplied list; this function will
        increment the quantity needed to craft the item by `X` entries of the Item in the data set.

        .. note::
            https://wiki.ffxivteamcraft.com/dev-stuff/import-a-list-from-another-tool


        .. note::
            Handles :class:`Item`'s that may not have Crafting Recipes; they will still be added to your list.



        Parameters
        ----------
        items: :class:`Optional[list[Item]]`
            A list of :class:`Item`'s needed to be turned into a Teamcraft List.
            - If `None` will check object type and process accordingly.

        Returns
        -------
        :class:`str`
            The list of items converted into a FFXIV TeamCraft import list url.

        """
        # Item ID | Recipe ID | Quantity
        # ; is the seperator between each item
        # payload = ["10373", "null", "1"]
        # payload = ["17962", "32308", "1"]
        struct: dict[int, ShoppingItem] = {}
        payload: str = ""
        # Allows easier access to this function when it's attached to multiple objects through inheritance.
        if items is None and isinstance(self, Item):
            items = [self]
        elif items is None:
            return None

        for entry in items:
            value = struct.get(entry.id, None)
            if value is None:
                struct[entry.id] = {"count": 1, "item": entry}
            else:
                value["count"] += 1

        for item in struct:
            value: ShoppingItem | None = struct.get(item)
            if value is None:
                continue
            payload += ",".join([
                str(value["item"].id),
                str("null" if value["item"].recipe is None else value["item"].recipe.recipe_id),
                str(value["count"]) + ";",
            ])

        payload = payload[:-1]  # truncate the last semicolon
        base_url = "https://ffxivteamcraft.com/import/"
        LOGGER.debug("<%s.teamcraft_list> | Payload: %s", __class__.__name__, payload)
        encoded = base64.b64encode(payload.encode("utf-8"))
        LOGGER.debug("<%s.teamcraft_list> | Encoding: %s | Encoded: %s", __class__.__name__, "utf-8", encoded)
        return f"{base_url}{encoded.decode('utf-8')}"


class Builder(Generic):
    """Our class to handle :class:`Moogle` data building and parsing."""

    def __init__(self, session: Optional[aiohttp.ClientSession | CachedSession] = None) -> None:
        """Create a :class:`Builder` Instance.

        Parameters
        ----------
        session: :class:`Optional[aiohttp.ClientSession | CachedSession]`, optional
            A pre-existing `<aiohttp.ClientSession>` object if applicable, by default None.

        """
        self.session = session
        self._session = None

    async def clean_up(self) -> None:
        """Cleans up any resources."""
        LOGGER.debug("<%s._clean_up> | Closing open `aiohttp.ClientSession` %s", __class__.__name__, self._session)
        if self._session is not None:
            await self._session.close()

    @staticmethod
    def convert_values(value: str) -> int | bool | str | list[int] | None:
        """Converts CSV values from strings into something Python can understand.

        Parameters
        ----------
        value: :class:`str`
            The string value to be converted.

        Returns
        -------
        :class:`int | bool | str | list[int] | None`
            The converted value.

        """
        if len(value) == 0:
            return None

        if value.isdigit():
            return int(value)

        if value.lower() in ["false", "true"]:
            return value.lower() == "true"

        if value.find(",") != -1:
            test: str = value.replace(",", "")
            if test.isdigit():
                return [int(entry) for entry in value.split(",")]
            return value
        return value

    def csv_parse(
        self,
        path: Path,
        *,
        convert_pound: bool = True,
        format_keys: bool = True,
    ) -> tuple[dict[str, dict[str, int | str | list[int] | bool | None]], list[str], list[str]]:
        """Parse a CSV file, breaking out the Keys and Types to be return as a tuple for turning into Typed Dicts.

        - Purely for XIV Data Mining CSV structure.

        .. note::
            All keys, values and types are sanitized via `<Builder.sanitize_key_name()`,
            `<Builder.convert_values()>` and `<Builder.sanitized_type_name()`.

        Parameters
        ----------
        path: :class:`Path`
            The Path to the CSV file.
        convert_pound: :class:`bool`, optional
            If the initial key value in the CSV should be changed to `id`.
        format_keys: :class:`bool`, optional
            If the keys should be formatted via `<Builder.from_camel_case()>`, by default True.

        Returns
        -------
        :class:`tuple`
            The Sanatized Data from the CSV file, along with the Keys and Types related to those Keys.

        """
        with path.open(mode="r", encoding="utf-8") as file:
            # so first off we need the key/type pairing, read those, skipping the first line
            # that is useless
            data = file.readline()
            keys: list[str] = file.readline()[0:-1].split(",")
            types: list[str] = file.readline()[0:-1].split(",")

            # This line appears to be "ItemID" 0 which has no value based upon the CSV inspection.
            data = file.readline()

            # Take our data and turn it into a dict, using the second line of the CSV file as the Keys.
            data = csv.DictReader(file, fieldnames=keys)
            outdata: dict[str, dict[str, str]] = {}

            for entry in data:
                outdata[entry["#"]] = entry
            file.close()

            reject_keys: list[str] = ["#", "", "Model{Sub}", "Model{Main}"]
            sanitized_data: dict[str, dict[str, int | str | list[int] | bool | None]] = {}
            for item, value in outdata.items():
                sanitized_data[item] = {}
                for k, v in value.items():
                    _k = k
                    # The Pound symbol from item.csv is the Item ID.
                    if k == "#" and convert_pound:
                        _k = "id"

                    # Removes the unused keys.
                    elif k in reject_keys:
                        continue

                    # ? Suggestion
                    # Pep 8 all "keys" as they will be used as attributes for the TypedDict/Class objects.
                    if format_keys is True:
                        _k: str = self.from_camel_case(key_name=self.sanitize_key_name(key_name=_k))
                    else:
                        _k: str = self.sanitize_key_name(key_name=k)
                    _v: str = self.sanitize_values(value=v)
                    sanitized_data[item][_k] = self.convert_values(value=_v)

            if format_keys is True:
                return (
                    sanitized_data,
                    [self.from_camel_case(key_name=self.sanitize_key_name(key_name=i)) for i in keys],
                    [self.sanitize_type_name(type_name=i) for i in types],
                )
            return (
                sanitized_data,
                [self.sanitize_key_name(key_name=i) for i in keys],
                [self.sanitize_type_name(type_name=i) for i in types],
            )

    async def csv_to_json(
        self,
        csv_name: str,
        *,
        typed_dict: bool = False,
        typed_file_name: Optional[str] = None,
        **csv_args: Unpack[CSVParseParams],
    ) -> None:
        """Parses a local `xiv_datamining` csv file into a JSON file.

        .. note::
            - If the `.csv` files are no longer present, it will get the csv file, save it and parse that.
            - This assumes the csv file is located in `DATA_PATH`.


        Parameters
        ----------
        csv_name: :class:`str`
            The name of the csv file to parse located in `DATA_PATH`.
        typed_dict: :class:`bool`, optional
            If we want to generate a Typed Dict and write the data out to a file, by default False.
            - File location will be `DATA_PATH`.
        typed_file_name: :class:`Optional[str]`, optional
            The file name to write out the Typed Dict data to, by default None.
                - If `None`, Defaults to `csv_name_typed.py`.
        **csv_args: :class:`Unpack[CSVParseParams]`
            Any additional args to supply to `<Builder.csv_parse()>`.

        """
        f_name = "convert_csv_to_json"

        json_name: str = csv_name.split(".", maxsplit=1)[0] + ".json"
        if typed_file_name is None:
            typed_file_name = csv_name.split(".", maxsplit=1)[0] + "_typed.py"
        typed_class_name = "XIV" + typed_file_name[:-3]

        if DATA_PATH.joinpath(csv_name).exists():
            LOGGER.debug("<%s.%s> | Found the local CSV file. | Name: %s", __class__.__name__, f_name, csv_name)
            res, keys, types = self.csv_parse(path=DATA_PATH.joinpath(csv_name), **csv_args)

            # ? Suggestion
            # This will make the JSON file regardless if it exists or not.
            # Could possible have a flag to prevent overwrite.. unsure.
            self.write_data_to_file(path=DATA_PATH, file_name=json_name, data=res)

            if typed_dict:
                res = self.to_typed_dict(class_name=typed_class_name, keys=keys, key_types=types)
                self.write_data_to_file(path=DATA_PATH, file_name=typed_file_name, data=res)

        else:
            # In case we cannot find the local file we can use our pre-built URLS dict to
            # get the CSV file from the `xivapi` Github repo else prompt for a url.
            url_key = csv_name.split(".", maxsplit=1)[0]
            key_data: tuple[bool, str] | None = URLS.get(url_key)
            if key_data is None:
                url: str = input(f"Please provide a url for {csv_name}")
            else:
                url = key_data[1]

            data: bytes = await self._request(url=url)
            self.write_data_to_file(path=DATA_PATH, file_name=csv_name, data=data)
            await self.csv_to_json(csv_name=csv_name, typed_dict=typed_dict, **csv_args)

        # Remove the CSV files since we don't need them after they have been converted.
        LOGGER.debug("<%s.%s> | Removing CSV file. | Name: %s", __class__.__name__, f_name, csv_name)
        DATA_PATH.joinpath(csv_name).unlink()

    async def file_validation(self) -> None:
        """Validate's the required files for Moogle to operate.

        - Files are located in `xiv_datamining`.
        """
        LOGGER.info("<%s.%s> | Validating json files... | Path: %s", __class__.__name__, "file_validation", DATA_PATH)
        for key, data in URLS.items():
            # lets check for the json file, which is all we care about to build our data structures.
            f_path: Path = Path(DATA_PATH).joinpath(key + ".json")
            LOGGER.debug(
                "<%s.%s> | Validating file... %s. | Exists: %s | Path: %s",
                __class__.__name__,
                "file_validation",
                key,
                f_path.exists(),
                f_path,
            )
            if f_path.exists() is False:
                if DATA_PATH.exists() is False:
                    DATA_PATH.mkdir()
                file_name = key + ".csv"

                res: bytes = await self._request(url=data[1])
                self.write_data_to_file(path=DATA_PATH, file_name=file_name, data=res)
                await self.csv_to_json(csv_name=file_name, convert_pound=data[0], format_keys=True)
                LOGGER.debug(
                    "<%s.%s> | Finished retrieving and building data for file.| File: %s",
                    __class__.__name__,
                    "file_validation",
                    key,
                )

    @staticmethod
    def from_camel_case(
        key_name: str,
        *,
        ignored_keys: Optional[list[str]] = None,
        pre_formatted_keys: Optional[dict[str, str]] = None,
    ) -> str:
        """Resolve a camelCase string to snake_case.

        .. note::
            Adds a `_` before any uppercase char in the `key_name` and then calls `.lower()` on the remaining string.


        .. note::
            The parameter `pre_formatted_keys` the dict structure is `key` = "what to replace" and `value` = "replacement".
            - Example: `ItemID` with `item_id`. Structure would be `{"ItemID": "item_id"}`".


        Parameters
        ----------
        key_name: :class:`str`
            The string to format.
        ignored_keys: :class:`Optional[list[str]]`, optional
            An array of strings that if the `key_name` is in the array it will be ignored and instantly returned unformatted.
            - You may provide your own, or use the constant `IGNORED_KEYS`
        pre_formatted_keys: :class:`Optional[dict[str, str]]`, optional
            An dictionary with keys consisting of values to compare against and the value of the keys to be the replacement string.
            - You may provide your own, or use the constant `PRE_FORMATTED_KEYS`

        Returns
        -------
        :class:`str`
            The formatted string.

        """
        if ignored_keys is None:
            ignored_keys = IGNORED_KEYS
        if pre_formatted_keys is None:
            pre_formatted_keys = PRE_FORMATTED_KEYS

        # We have keys we don't want to format/change during generation so add them to the ignored_keys list.
        if key_name in ignored_keys:
            return key_name

        for k, v in pre_formatted_keys.items():
            if key_name == k:
                LOGGER.debug("<%s.%s> | Replaced `key` and `value` | Key: %s | Value: %s", __class__.__name__, "from_camel_case", k, v)
                return v

        temp: str = key_name[:1].lower()
        for e in key_name[1:]:
            if e.isupper():
                temp += f"_{e.lower()}"
                continue
            temp += e
        LOGGER.debug("<%s.from_camel_case> | key_name: %s | Converted: %s", __class__.__name__, key_name, temp)
        return temp

    def generate_enum(self, class_name: str, keys: list[int], values: list[str] | list[int]) -> str:
        """Takes in keys and values to generate an basic Enum.

        - Structing the Enum in the way of `values = keys` (my_attribute = 0)

        Parameters
        ----------
        class_name: :class:`str`
            The name of the Enum placed into `{class_name}(Enum):`.
        keys: :class:`list[int]`
            The int value for the Enum values to equal `(values = keys)`.
        values: :class:`list[str | int]`
            The attributes to be used for the Enum.

        Returns
        -------
        :class:`str`
            A :class:`Enum` as a string.

        """
        temp: list[str] = []
        temp.append(f"class {class_name}(Enum):")
        for key, key_value in zip(keys, values, strict=False):
            temp.append(f"    {key_value} = {key}")
        return "\n".join(temp)

    def _rebuild_files(self) -> Optional[Literal[True]]:
        """Currently used for relocating all local JSON files inside `xiv_dataminig`.

        No file validation in terms of size, keys, etc. Moves the existing library files to `xiv_datamining_old` directory.

        .. note::
            Typical usage would be for new content being added to XIV.


        """
        if DATA_PATH.exists() is False:
            msg = "<%s.%s> | Failed to find existing JSON directory. | Path: %s"
            raise FileNotFoundError(msg, __class__.__name__, "_rebuild_files", DATA_PATH)

        old_cache: Path = Path(__file__).parent.joinpath("xiv_datamining_old")
        # Removing old files.
        if old_cache.exists() is True:
            for file in old_cache.iterdir():
                try:
                    file.unlink(missing_ok=True)
                except OSError:
                    LOGGER.warning("<%s.%s> | Failed to remove file. | %s", __class__.__name__, "_rebuild_files", file.name)
                    continue

        if old_cache.exists() is False:
            old_cache.mkdir()

        DATA_PATH.rename(old_cache)
        LOGGER.info("<%s.%s> | Moved XIV JSON files to backup directory. | Path: %s", __class__.__name__, "_rebuild_files", old_cache)
        return True

    async def _request(self, url: str, **request_options: Unpack[AiohttpRequestOptions]) -> bytes:
        if self.session is None:
            if self._session is None:
                session: aiohttp.ClientSession = aiohttp.ClientSession()
                self._session = session
                LOGGER.debug("<%s._request> | Creating local `aiohttp.ClientSession()` | session: %s", __class__.__name__, session)
            else:
                session = self._session
        else:
            session = self.session

        res: ClientResponse = await session.get(url=url, **request_options)
        if res.status != 200:
            msg = "Unable to access the URL provided: %s"
            raise ConnectionError(msg, url)

        if res.content_type == "application/json":
            return await res.json()
        return await res.content.read()

    @classmethod
    def sanitize_html(
        cls,
        data: str,
        *,
        keys: dict[str, HTMLKeys] = SANITIZED_HTML,
        keep_tag_contents: bool = False,
        count: int = -1,
    ) -> str:
        """Removes HTML tags with the option to keep tag contents or not.

        If you wanted to target the starting tag `<UIForeground>` and the closing tag `</UIForeground>` see the below data struct.
        - The tags are not case sensitive as we are calling `str.lower()`
        on the entire data struct for parsing purposes the returned data will be unaffected.

        ```
        SANITIZED_HTML = {"uiforeground": {"replace": "..."},
                            "uiglow": {"replace": ""}}
        ```

        .. note::
            Will recursively parse the data until the start tag and end tag are no longer found.


        Parameters
        ----------
        data: :class:`str`
            The data to remove HTML tags.
        keys: :class:`dict[str, HTMLKeys]`, optional
            The HTML tags to be replaced with their replacement value, by default SANITIZED_HTML.
        count: :class:`int`, optional
            The count parameter for :class:`str`.replace(), by default -1.
        keep_tag_contents: :class:`bool`, optional
            If you want to keep the content between HTML tags.

        Returns
        -------
        :class:`str`
            The parsed data set.

        """
        for key, value in keys.items():
            start_key: str = f"<{key}>"
            start_idx: int = data.lower().find(start_key)
            end_key: str = f"</{key}>"
            end_idx: int = data.lower().find(end_key)
            if start_idx == -1 and end_idx == -1:
                LOGGER.debug(
                    "<%s.%s> | No Keys found in dataset. | Start Index: %s | End Index: %s",
                    __class__.__name__,
                    "sanitize_html",
                    start_idx,
                    end_idx,
                )
                return data

            if start_idx != -1 and end_idx != -1:
                LOGGER.debug(
                    "<%s.%s> | Found keys with proper index. | Start Index: %s | End Index: %s | Offset: %s",
                    __class__.__name__,
                    "sanitize_html",
                    start_idx,
                    end_idx,
                    len(end_key),
                )
                end_idx += len(end_key)
                LOGGER.debug(
                    "<%s.%s> | Replacing sectioned data. | Data: %s | Replacement: %s",
                    __class__.__name__,
                    "sanitize_html",
                    data[start_idx:end_idx],
                    value["replace"],
                )
                if keep_tag_contents is True:
                    data = data.replace(start_key, value["replace"], count)
                    data = data.replace(end_key, value["replace"], count)
                else:
                    data = data.replace(data[start_idx:end_idx], value["replace"], count)

                data = cls.sanitize_html(data=data)
        return data

    @staticmethod
    def sanitize_key_name(key_name: str, keys: dict[str, str] = SANITIZED_KEYS) -> str:
        """Uses `.replace()` to remove unwanted characters based upon a supplied array.

        .. note::
            The order of the dict array `keys` matters as it is an iterator `keys.items()`.


        Parameters
        ----------
        key_name: :class:`str`
            The Key name to sanitize.
        keys: :class:`dict[str, str]`, optional
            The `key: value` dict to replace characters with.
            - Uses the global `SANITIZED_KEYS`, otherwise supply your own `key : value` combo.
            - `key_name.replace(key, value)`

        Returns
        -------
        :class:`str`
            The sanizted key_name value.

        """
        # some fields have {} and other symbols that must be sanitized
        if len(key_name) > 1 and key_name[0].isnumeric():
            key_name = key_name.replace("1", "one").replace("2", "two")
        for key, value in keys.items():
            key_name = key_name.replace(key, value)
        # key_name = key_name.replace(":", "")
        # key_name = key_name.replace("(", "").replace(")", "")
        # key_name = key_name.replace("{", "").replace("}", "")
        # key_name = key_name.replace("][", "_")  # do this first for [0][1] as an example
        # key_name = key_name.replace("[", "").replace("]", "")
        # key_name = key_name.replace("<ms>", "").replace("<s>", "")
        # key_name = key_name.replace("<%>", "_percent")
        # key_name = key_name.replace("%", "_percent")
        # key_name = key_name.replace("'", "").replace(" ", "_").replace("-", "_").replace("–", "_")
        return key_name

    @staticmethod
    def sanitize_type_name(type_name: str) -> str:
        """Replaces the C/C# type names with Python related types.

        .. note::
            Similar to `<Builder.sanitize_key_name>`, but this is type name conversion with a static list.

        Parameters
        ----------
        type_name: :class:`str`
            The Type name from the CSV to replace.

        Returns
        -------
        :class:`str`
            The replaced type_name as a string.

        """
        # These values are considered `int` types for the purpose of data parsing/mapping references.
        int_type: list[str] = [
            "int32",
            "sbyte",
            "uint16",
            "uint32",
            "bit&10",
            "byte",
            "int64",
            "int16",
            "Image",
        ]
        bool_type: list[str] = ["bit&", "bool"]
        if type_name.startswith(tuple(int_type)):
            return "int"
        if type_name.startswith(tuple(bool_type)):
            return "bool"
        if type_name.startswith("str"):
            return "str"
        LOGGER.warning("<%s.%s> | UNK value type. | Type name: %s", __class__.__name__, "sanitize_type_name", type_name)
        return f"Any #{type_name}"

    @staticmethod
    def sanitize_values(value: str, _sanitize_values: Optional[list[str]] = None) -> str:
        """Using `.find()` to locate the entry from `_sanitize_values` will use `.replace()` of an empty str `""`.

        Parameters
        ----------
        value: :class:`str`
            The value to sanitize.
        _sanitize_values: :class:`list[str]`, optional
            The list of strings to search for and replace with `""`, by default ["<Emphasis>", "</Emphasis>"].

        Returns
        -------
        :class:`str`
            The sanitized string.

        """
        sanitize = SANITIZED_VALUES if _sanitize_values is None else _sanitize_values
        for entry in sanitize:
            if value.find(entry):
                value = value.replace(entry, "")
        return value

    async def to_enum(
        self,
        value_get: str,
        file_name: str,
        class_name: str,
        url: Optional[str] = None,
        data_url_key: Optional[str] = None,
    ) -> None:
        """Parses bytes and converts into a block of Enum code.

        Using the string of an Enum as Python code written to a file.

        .. note::
            - The `file_name` parameter is used to name the file; replacing the  extension with `Enum.py`.

        Parameters
        ----------
        value_get: :class:`str`
            The string value to retrieve from the CSV dictionary as a key for the data structure in the Enum.
        file_name: :class:`str`
            The file name for the CSV file.
        class_name: :class:`str`
            The name of class to house the Enum, it will automatically append `Enum` to the end of the class name parameter.
        url: :class:`Optional[str]`, optional
            The URL to fetch the CSV data from, by default None.
        data_url_key: :class:`Optional[str]`, optional
            The dictionary key value to fetch from `DATA_URLS` global, by default None.

        Raises
        ------
        ValueError
            If you do not provide a `url` or `data_url_key` parameter.

        """
        if url is None and data_url_key is None:
            msg = "You must provide either a `url` or `data_url_key` parameter. | url: %s | data_url_key: %s"
            raise ValueError(msg, url, data_url_key)

        if data_url_key is not None:
            value_get, url = DATA_URLS.get(data_url_key, ("", None))
            if url is None:
                LOGGER.error(
                    "<%s.%s> | Failed to get url from `DATA_URLS`. | data_url_key: %s",
                    __class__.__name__,
                    "generate_enum_build",
                    data_url_key,
                )
                return
        elif url is not None:
            res: bytes = await self._request(url=url)
            self.write_data_to_file(path=DATA_PATH, file_name=file_name, data=res)
            data = self.csv_parse(path=DATA_PATH.joinpath(file_name), convert_pound=False)
            keys: list[int] = []
            values: list[str] = []
            # typically the first row is the keys of the CSV.
            for key, value in data[0].items():
                temp = value.get(value_get, None)
                if isinstance(temp, str):
                    temp = self.sanitize_key_name(key_name=temp)
                    values.append(temp)
                    keys.append(int(key))

            enum_str: str = self.generate_enum(class_name=class_name, keys=keys, values=values)
            file_name = file_name.split(".", maxsplit=1)[0]
            self.write_data_to_file(
                file_name=f"{file_name}Enum.py",
                data=enum_str,
            )

    def to_typed_dict(self, class_name: str, keys: list[str], key_types: list[str]) -> str:
        """Generate a :class:`TypedDict` as a string.

        Takes our sanitized keys and key types from our CSV file parsing and generates code as a string.

        Parameters
        ----------
        class_name: :class:`str`
            The name of the :class:`TypedDict` written out as `{class_name}(TypedDict):`.
        keys: :class:`list[str]`
            The keys for the :class:`TypedDict`.
        key_types: :class:`list[str]`
            The type values for the :class:`TypedDict`.

        Raises
        ------
        ValueError
            If the length of keys and key_types are not equal.

        Returns
        -------
        :class:`str`
            A :class:`TypedDict` as a string.

        """
        if len(keys) != len(key_types):
            msg = "The length of keys is not the same as key_types. | keys: %s | key_types: %s"
            raise ValueError(msg, len(keys), len(key_types))
        temp: list[str] = []
        temp.append(f"class {class_name}(TypedDict):")
        for key, k_type in zip(keys, key_types, strict=False):
            if len(key) == 0:
                continue
            # This only works on Item.csv as the `#` in the file is the actual item id.
            _key = "id" if key == "#" else key
            temp.append(f"    {_key}: {k_type}")

        return "\n".join(temp)

    def write_data_to_file(
        self,
        file_name: str,
        data: bytes | dict[Any, Any] | str,
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
        data: :class:`bytes | dict | str`
            The data to write out to the path and file_name provided.
        mode: :class:`str`, optional
            The mode to open the provided file path with using `<Path.open()>`.
        **kwargs: :class:`Any`
            Any additional kwargs to be supplied to `<json.dumps()>`, if applicable.

        """
        file_name = file_name.lower()
        with path.joinpath(file_name).open(mode=mode) as file:
            LOGGER.debug("<%s.%s> | Wrote data to file %s located at: %s", __class__.__name__, "write_data_to_file", path, file_name)
            if isinstance(data, bytes):
                file.write(data.decode(encoding="utf-8"))
            elif isinstance(data, dict):
                file.write(json.dumps(data, indent=4, **kwargs))
            else:
                file.write(data)
        LOGGER.info(
            "<%s.%s> | File write successful to path: %s ",
            __class__.__name__,
            "write_data_to_file",
            path.joinpath(file_name).as_posix(),
        )

    def _load_json(self, path: Path, **json_args: Any) -> dict[str, DataTypeAliases]:
        if path.exists() is False:
            msg = "<%s.%s> | The Path provided does not exist. | Path: %s"
            raise FileNotFoundError(msg, __class__.__name__, "_load_json", path)
        if path.is_dir() is True:
            msg = "<%s.%s> | The Path provided is a directory. | Path: %s"
            raise TypeError(msg, __class__.__name__, path)

        data: dict[str, DataTypeAliases] = json.loads(path.read_bytes(), **json_args)
        return data

    def _reference_dict(
        self,
        data: dict[str, DataTypeAliases],
        value_get: str,
        *,
        flip_key_value: bool = False,
    ) -> dict[str | int, str | int]:
        item_dict: dict[str | int, str | int] = {}
        for key, value in data.items():
            temp: Optional[str | int] = value.get(value_get, None)

            if isinstance(temp, str):
                temp = temp.lower()

            if temp is None:
                continue

            if flip_key_value is True:
                item_dict[temp] = key

            else:
                item_dict[key] = temp

        LOGGER.debug(
            "<%s.%s> | Value Get: %s | Number of Items: %s | Flip Key Value: %s",
            __class__.__name__,
            "_reference_dict",
            value_get,
            len(item_dict.keys()),
            flip_key_value,
        )
        return item_dict


class Moogle(Generic):
    """Our handler type class for interacting with FFXIV Items, Recipes and other Data structures from XIV Datamining."""

    _builder: Builder

    # This will eventually act like our cache to help reduce web requests for similar data.
    _angler_spot_cache: dict[str, AnglerFish]
    _universalis: UniversalisAPI
    _angler: Angler

    # FF14 Angler Integration
    _angler_loc_map: Optional[dict[str, int]]
    _angler_invert_loc_map: Optional[dict[int, str]]
    _angler_fish_map: Optional[dict[str, int]]
    "Data structure is `fish_name : fish_id`."

    _garlandtools: GarlandToolsAsync

    _items_cache: dict[str, Item]
    "Local cache to our Moogle object for faster data lookup."

    @property
    def garlandtools(self) -> GarlandToolsAsync:
        """Returns the internal :class:`GarlandToolsAsync` object.

        Returns
        -------
        :class:`GarlandToolsAsync`
            An async version of GarlandTools-PIP.

        """
        return self._garlandtools

    def __init__(
        self,
        session: Optional[aiohttp.ClientSession | CachedSession] = None,
        universalis: Optional[UniversalisAPI] = None,
        angler: Optional[Angler] = None,
        garlandtools: Optional[GarlandToolsAsync] = None,
    ) -> None:
        """Build your Moogle Intuition~.

        Parameters
        ----------
        session: :class:`Optional[aiohttp.ClientSession]`, optional
            A pre-existing `<aiohttp.ClientSession>` object if applicable, by default None.
        universalis: :class:`Optional[UniversalisAPI]`, optional
            A pre-existing `<universalis.UniversalisAPI>` object if applicable, by default None.
        angler: :class:`Optional[Angler]`, optional
            A pre-existing `<ff14angler.Angler>` object if applicable, by default None.
        garlandtools: :class:`Optional[GarlandToolsAsync]`, optional
            A pre-existing `<async_garlandtools.GarlandToolsAsync>` object if applicable, by default None.

        """
        if garlandtools is None:
            if isinstance(session, CachedSession):
                self._garlandtools = GarlandToolsAsync(session=session)
            else:
                self._garlandtools = GarlandToolsAsync(cache_location=Path(__file__).parent)
                # This forces us to swap to a CachedSession object for all other usage.
                session = self._garlandtools.session
        else:
            self._garlandtools = garlandtools

        if universalis is None:
            self._universalis = UniversalisAPI(session=session)
        else:
            self._universalis = universalis

        if angler is None:
            self._angler = Angler(session=session)
        else:
            self._angler = angler

        self._builder = Builder(session=session)
        # Create our empty itemcache.
        self._items_cache = {}

    async def __aenter__(self) -> Self:  # noqa: D105
        try:
            await self.build()
        except (FileNotFoundError, FileExistsError) as e:
            LOGGER.error("<%s.%s> | Failed to Build, rebuilding data. | Exception: %s", __class__.__name__, "build", e)
            await self.build(relocate_data=True)
            return self
        except ConnectionError as e:
            LOGGER.error("<%s.%s> | Failed to Build. | Exception: %s", __class__.__name__, "build", e)
        return self

    async def __aexit__(  # noqa: D105
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        await self.clean_up()

    async def clean_up(self) -> None:
        """Handles deconstruction of :class:`Moogle`."""
        LOGGER.debug("<%s._clean_up> | Closing any open `aiohttp.ClientSession`", __class__.__name__)
        await self._universalis.clean_up()
        await self._builder.clean_up()
        await self._angler.clean_up()
        await self._garlandtools.close()

    def create_generic_item(self, **kwargs: Unpack[PartialItemData]) -> ItemData | None:
        """Create a default value filled :class:`ItemData` TypedDict to be supplied to a :class:`Item` object.

        .. note::
            This was built to handle items from GarlandTools that may not have an ID value.


        .. warning::
            There is no validation of the ID provided; so if you clash with an existing Item ID... well, you're on your own.


        Returns
        -------
        :class:`ItemData | None`
            Item data to build an :class:`Item` object.

        """
        # Credits for the enrichment of an Eorzean free company.
        item_data: ItemData = {}  # pyright: ignore[reportAssignmentType]
        if kwargs.get("icon") is None:
            item_data["icon"] = 0
        if kwargs.get("description") is None:
            item_data["description"] = kwargs["name"] + "generic description."
        for key, value in kwargs.items():
            if key not in item_data:
                item_data[key] = value

        for key, value in ItemData.__annotations__.items():
            if key not in kwargs and isinstance(value, ForwardRef):
                if value.__forward_arg__ == "int":
                    item_data[key] = 0
                elif value.__forward_arg__ == "bool":
                    item_data[key] = False
                elif value.__forward_arg__ == "str":
                    item_data[key] = ""
        # This is just in case, checking a random but
        # specific key if it exists to invalidate our "spoofing" default data.
        if "singular" not in item_data:
            return None
        return item_data

    async def build(self, *, ignore_validation: bool = False, relocate_data: bool = False) -> Self:
        """Builds the required arrays and library's for :class:`Moogle` to function.

        Parameters
        ----------
        relocate_data: :class:`bool`
            Relocates current local JSON files, fetches new files and builds new local JSON files, default is False.
        ignore_validation: :class:`bool`
            Allows bypassing local JSON/CSV file validation, default is False.

        Returns
        -------
        :class:`Self`:
            A :class:`Moogle` object.

        """
        if relocate_data is True:
            self._builder._rebuild_files()

        if ignore_validation is False:
            await self._builder.file_validation()

        # Item related dict/JSON
        self._items = self._builder._load_json(path=DATA_PATH.joinpath("item.json"))
        self._items_ref = self._builder._reference_dict(data=self._items, value_get="name", flip_key_value=True)
        # This is to handle the Custom Item "fccredit"
        # See -> https://www.garlandtools.org/db/#item/fccredit
        fc_credit: ItemData | None = self.create_generic_item(
            id=0,
            name="Company Credit",
            singular="fccredit",
            description="Credits for the enrichment of an Eorzean free company.",
            level_item=1,
            is_untradeable=True,
            stack_size=999999,
            item_ui_category=63,  # other
        )
        if fc_credit is not None:
            self._items["0"] = fc_credit
            # This has to match the `id` value from the `item.json`; which we supplied as `0` for `fccredit`.
            self._items_ref["fccredit"] = 0

        # Recipe related dict/JSON
        self._recipes = self._builder._load_json(path=DATA_PATH.joinpath("recipe.json"))
        self._recipes_ref = self._builder._reference_dict(data=self._recipes, value_get="item_result")
        self._recipe_lookups = self._builder._load_json(path=DATA_PATH.joinpath("recipe_lookup.json"))
        # self._recipe_levels = self._load_json(path=DATA_PATH.joinpath("recipe_level.json"))

        # Fishing related dict/JSON
        self._fish_params = self._builder._load_json(path=DATA_PATH.joinpath("fish_parameter.json"))
        self._fish_params_ref = self._builder._reference_dict(
            data=self._fish_params,
            value_get="item",
            flip_key_value=True,
        )
        self._fishing_spot = self._builder._load_json(path=DATA_PATH.joinpath("fishing_spot.json"))

        # Spearfishing related dict/JSON
        self._spearfishing_items = self._builder._load_json(path=DATA_PATH.joinpath("spearfishing_item.json"))
        self._spearfishing_items_ref = self._builder._reference_dict(
            data=self._spearfishing_items,
            value_get="item",
            flip_key_value=True,
        )
        self._spearfishing_notebook = self._builder._load_json(path=DATA_PATH.joinpath("spearfishing_notebook.json"))

        # Gathering related dict/JSON.
        self._gathering_items = self._builder._load_json(path=DATA_PATH.joinpath("gathering_item.json"))
        self._gathering_items_ref = self._builder._reference_dict(
            data=self._gathering_items,
            value_get="item",
            flip_key_value=True,
        )
        self._gathering_item_levels = self._builder._load_json(path=DATA_PATH.joinpath("gathering_item_level.json"))

        # Location related JSON
        self._place_names = self._builder._load_json(path=DATA_PATH.joinpath("place_name.json"))

        # FF14 Angler related dict.
        locs: tuple[dict[str, int], dict[int, str]] | None = await self._angler.get_location_id_mapping(include_inverted_map=True)
        if locs is not None:
            self._angler_loc_map = locs[0]
            self._angler_invert_loc_map = locs[1]
        self._angler_fish_map = await self._angler.get_fish_id_mapping()

        return self

    @overload
    def get_item(self, item: str, *, limit_results: Literal[1], match: int = ...) -> Item: ...

    @overload
    def get_item(self, item: str, *, limit_results: int = ...) -> list[Item]: ...

    def get_item(self, item: str, *, limit_results: int = 10, match: int = 80) -> Item | list[Item]:
        """Retrieves a possible match to the `item_name` or `item_id` parameter as an FFXIV Item.

        Parameters
        ----------
        item: :class:`str`
            Search for a Final Fantasy 14 Item, by name or item id.
        match: :class:`int`, optional
            The percentage required for the Fuzzy match comparison, by default 80.
        limit_results: :class:`int`, optional
            You can limit the number of results if needed; otherwise it will return the only 10 entries by default.

        Returns
        -------
        :class:`Item | list[Item]`
            A list or single entry of an Item.

        Raises
        ------
        :class:`MoogleLookupError`
            If we are unable to find the item parameter provided for any reason.

        """
        LOGGER.debug("<%s.%s> | Searching... query: %s |", __class__.__name__, "get_item", item)
        results: list[Item] = []

        # Numeric Item lookup.
        # item: 10373 # magitek repair materials.
        if item.isnumeric():
            # So let's try to check the cache first for a matching item assuming we have an `id` value.
            LOGGER.debug("<%s.%s> | Checking item cache.. | item: %s", __class__.__name__, "get_item", item)
            cache: Optional[Item] = self._items_cache.get(item, None)

            if isinstance(cache, Item):
                LOGGER.debug("<%s.%s> | Found item in cache.. | item: %s", __class__.__name__, "get_item", cache.id)
                return cache if limit_results == 1 else [cache]

            res: DataTypeAliases | None = self._items.get(item, None)
            if res is not None and "level_item" in res:
                cache = Item(data=res, moogle=self, universalis=self._universalis)
                self._items_cache[str(cache.id)] = cache
                LOGGER.debug("<%s.%s> | Built Item and placed in cache.. | item: %s", __class__.__name__, "get_item", cache.id)
                return cache if limit_results == 1 else [cache]

            raise MoogleLookupError(item, "item", "get_item", self)

        # item_name's we have to get a reference since we are supporting partial string matching.
        # This handles the edge case of a perfect match, albeit unlikely.
        ref: Optional[str | int] = self._items_ref.get(item.lower(), None)
        if ref is not None:
            res = self._items.get(str(ref), None)
            if res is not None and "level_item" in res:
                cache = self._items_cache.get(str(res["id"]))
                if cache is None:
                    cache = Item(data=res, moogle=self, universalis=self._universalis)
                    self._items_cache[str(cache.id)] = cache
                    LOGGER.debug("<%s.%s> | Built Item and placed in cache.. | item: %s", __class__.__name__, "get_item", cache.id)
                return cache if limit_results == 1 else [cache]

        # if the item_name wasn't in the ref list we would do our partial matching below.
        # we take our list of item_ids that partially matched and get our data/objects.
        matches: list[tuple[str, int]] = self._partial_match(item, match=match)
        LOGGER.debug("<%s.%s> | Searching... %s partial matches.", __class__.__name__, "get_item", len(matches))
        for entry in sorted(matches, key=lambda x: x[1], reverse=True):
            # Let's try to find our partial matches in our cache too.
            cache = self._items_cache.get(entry[0], None)
            LOGGER.debug("<%s.%s> | Checking item cache.. | item: %s", __class__.__name__, "get_item", entry)
            if cache is not None:
                LOGGER.debug("<%s.%s> | Found item in cache.. | item: %s", __class__.__name__, "get_item", entry)
                results.append(cache)
                continue
            # Not in cache; so let's get them from our array of data.
            # If we don't find it, we will skip it.. :shrug:

            res = self._items.get(entry[0], None)
            if res is not None and "level_item" in res:
                LOGGER.debug("<%s.%s> | Found item, building data. | item: %s", __class__.__name__, "get_item", entry)
                cache = Item(data=res, moogle=self, universalis=self._universalis)
                self._items_cache[str(cache.id)] = cache
                results.append(cache)

        if len(results) == 0:
            raise MoogleLookupError(item, "item", "get_item", self)

        return results[0] if limit_results == 1 else results[:limit_results]

    def _partial_match(self, query: str, match: int = 80) -> list[tuple[str, int]]:
        """Partial string matching using `fuzzy` logic.

        Parameters
        ----------
        query: :class:`str`
            The item ID or name to search for.
        match: :class:`int`, optional
            The `fuzz.partial_ratio` value threshold to be above to consider a result, by default 80.

        Returns
        -------
        :class:`list[dict[str, int]]`
            A list of viable Item IDs to lookup with their associated weight values.

        Raises
        ------
        :class:`MoogleLookupError`
            Failure to find any matching :class:`Item` names to the `query` parameter.

        """
        # This section assumes we are using `item_name` given the above if check for `item_id`.
        # matches will be a list of dict "item_id's" and their weight value that matched our query string.
        matches: list[tuple[str, int]] = []
        # self._items_ref = { item_name : item_id }
        for item_name, item_id in self._items_ref.items():
            LOGGER.debug(
                "Searching... item_name: %s | item_id: %s | query: %s",
                item_name,
                item_id,
                query,
            )

            _value = str(item_name) if isinstance(item_name, int) else item_name

            # Simple in check for `str` comparsion.
            if query.lower() in _value.lower():
                matches.append((str(item_id), 100))
                continue

            # We have a partial match, but not exact. So we can either
            # look the item up and see if we can find it, or return the key.
            ratio: int = fuzz.partial_ratio(s1=_value.lower(), s2=query.lower())  # pyright: ignore[reportUnknownMemberType]
            if ratio >= match:
                LOGGER.debug(
                    "<%s.%s> | Searching... | item_name: %s | item_id: %s | ratio: %s | query: %s ",
                    __class__.__name__,
                    "_partial_match",
                    item_name,
                    _value,
                    ratio,
                    query,
                )
                matches.append((str(item_id), ratio))
                continue

        if len(matches) == 0:
            raise MoogleLookupError(query, "query", "_partial_match", self)
        LOGGER.debug("<%s.%s> | Returning %s partial matches", __class__.__name__, "_partial_match", len(matches))
        return matches

    def _get_gathering_level(self, level_id: int) -> GatheringLevel:
        LOGGER.debug(
            "<%s.%s> | Searching... gathering_level_id: %s | entries: %s",
            __class__.__name__,
            "_get_gathering_level",
            level_id,
            len(self._gathering_item_levels),
        )

        data: Optional[DataTypeAliases] = self._gathering_item_levels.get(str(level_id), None)
        if data is None or ("stars" not in data or "gathering_item_level" not in data):
            raise MoogleLookupError(str(level_id), "level_id", "_get_gathering_level", self)
        return GatheringLevel(data=data, moogle=self)

    def _get_place_name(self, place_id: int) -> PlaceName:
        LOGGER.debug(
            "<%s.%s> | Searching... place_id: %s | entries: %s",
            __class__.__name__,
            "_get_place_name",
            place_id,
            len(self._place_names),
        )
        data: Optional[DataTypeAliases] = self._place_names.get(str(place_id), None)
        if data is None or "name_no_article" not in data:
            raise MoogleLookupError(str(place_id), "place_id", "_get_place_name", self)
        return PlaceName(data=data, moogle=self)

    def _parse_multipart(self, items: list[Item], data: MultiPart) -> list[Item]:
        """Takes an array of :class:`Item` objects and updates their Universalis data with the supplied data.

        .. note::
            Supports :class:`CurrentData` and :class:`HistoryData`.

        Parameters
        ----------
        items: :class:`list[Item]`
            The list of :class:`Item`'s to update.
        data: :class:`MultiPart`
            The Universalis data to update the :class:`Item`'s with.

        Returns
        -------
        :class:`list[Item]`
            The update :class:`Item` objects.

        """
        results: list[Item] = []
        for item in items:
            for entry in data.items:
                if isinstance(entry, CurrentData) and entry.item_id == item.id:
                    item._mb_current = entry
                elif isinstance(entry, HistoryData) and entry.item_id == item.id:
                    item._mb_history = entry

        return results

    @overload
    async def get_current_marketboard_bulk(self, items: str, **kwargs: Unpack[CurMarketBoardParams]) -> CurrentData | None: ...

    @overload
    async def get_current_marketboard_bulk(
        self,
        items: list[Item] | list[str],
        **kwargs: Unpack[CurMarketBoardParams],
    ) -> list[Item] | None: ...

    async def get_current_marketboard_bulk(
        self,
        items: str | list[Item] | list[str],
        **kwargs: Unpack[CurMarketBoardParams],
    ) -> CurrentData | list[Item] | None:
        """Get Universalis current marketboard data and return updated :class:`Item` objects.

        .. note::
            If an invalid entry in `items` is found, `<UniversalisAPI>` will omit those entries.

        Parameters
        ----------
        items: :class:`str | list[Item | str]`
            An array of either :class:`Item` objects, Item ids or Item names as strings.
        **kwargs: :class:`Unpack[CurMarketBoardParams]`
            Any additional params to pass to `<UniversalisAPI.get_bulk_current_data()>`.

        Returns
        -------
        :class:`CurrentData | list[Item] | None`
            The Universalis JSON data represented as a class, or an array of :class:`Item` objects with updated Marketboard data.
            - See :class:`Item.mb_current` for data.

        """
        query: list[str] = []
        item_obj: list[Item] = []
        # If we have a single entry, get the item object and fetch the results that way.
        if isinstance(items, str):
            try:
                item: Item = self.get_item(items, limit_results=1)
                LOGGER.debug(
                    "<%s.%s> | Universalis market search. | items: %s",
                    __class__.__name__,
                    "get_current_marketboard",
                    items,
                )
                return await item.get_current_marketboard(**kwargs)
            except MoogleLookupError:
                LOGGER.error("<%s.%s> | Failed item lookup. | Item: %s", __class__.__name__, "get_current_marketboard_bulk", items)
                return None

        else:
            for entry in items:
                # Just in case we fail to find the item.
                if isinstance(entry, Item):
                    if entry.is_untradable is True:
                        continue

                    if entry not in item_obj:
                        item_obj.append(entry)
                        query.append(str(entry.id))
                        continue
                else:
                    try:
                        item: Item = self.get_item(entry, limit_results=1)

                        if item.is_untradable is True:
                            continue

                        if item not in item_obj:
                            item_obj.append(item)
                            query.append(str(item.id))

                    except MoogleLookupError:
                        LOGGER.error("<%s.%s> | Failed item lookup. | Item: %s", __class__.__name__, "get_current_marketboard_bulk", items)
                        continue

            LOGGER.debug(
                "<%s.%s> | Universalis market search. | items: %s | entries: %s",
                __class__.__name__,
                "get_current_marketboard",
                items,
                len(query),
            )
            res: CurrentData | MultiPart | None = await self._universalis.get_bulk_current_data(items=query, **kwargs)
            if isinstance(res, MultiPart):
                return self._parse_multipart(items=item_obj, data=res)
            return res

    @overload
    async def get_history_marketboard_bulk(self, items: str, **kwargs: Unpack[HistMarketBoardParams]) -> HistoryData | None: ...

    @overload
    async def get_history_marketboard_bulk(
        self,
        items: list[Item] | list[str],
        **kwargs: Unpack[HistMarketBoardParams],
    ) -> list[Item] | None: ...

    async def get_history_marketboard_bulk(
        self,
        items: str | list[Item] | list[str],
        **kwargs: Unpack[HistMarketBoardParams],
    ) -> HistoryData | list[Item] | None:
        """Get Universalis history marketboard data and return updated :class:`Item` objects.

        .. note::
            If an invalid entry in `items` is found, `<UniversalisAPI>` will omit those entries.

        Parameters
        ----------
        items: :class:`str | list[Item | str]`
            An array of either :class:`Item` objects, Item ids or Item names as strings.
        **kwargs: :class:`Unpack[MarketBoardParams]`
            Any additional params to pass to `<UniversalisAPI.get_bulk_current_data()>`.

        Returns
        -------
         :class:`HistoryData | list[Item] | None`
            The Universalis JSON data represented as a class, or an array of :class:`Item` objects with updated Marketboard data.
            - See :class:`Item.mb_history` for data.

        """
        query: list[str] = []
        item_obj: list[Item] = []
        # If we have a single entry, get the item object and fetch the results that way.
        if isinstance(items, str):
            try:
                item: Item = self.get_item(items, limit_results=1)
                LOGGER.debug(
                    "<%s.%s> | Universalis market search. | items: %s",
                    __class__.__name__,
                    "get_current_marketboard",
                    items,
                )
                return await item.get_history_marketboard(**kwargs)
            except MoogleLookupError:
                LOGGER.error("<%s.%s> | Failed item lookup. | Item: %s", __class__.__name__, "get_history_marketboard_bulk", items)
                return None

        else:
            for entry in items:
                # Just in case we fail to find the item.
                if isinstance(entry, Item):
                    if entry.is_untradable is True:
                        continue

                    if entry not in item_obj:
                        item_obj.append(entry)
                        query.append(str(entry.id))
                        continue
                else:
                    try:
                        item: Item = self.get_item(entry, limit_results=1)

                        if item.is_untradable is True:
                            continue

                        if item not in item_obj:
                            item_obj.append(item)
                            query.append(str(item.id))

                    except MoogleLookupError:
                        LOGGER.error("<%s.%s> | Failed item lookup. | Item: %s", __class__.__name__, "get_history_marketboard_bulk", items)
                        continue

            LOGGER.debug(
                "<%s.%s> | Universalis market search. | items: %s | entries: %s",
                __class__.__name__,
                "get_history_marketboard_bulk",
                items,
                len(query),
            )
            res: HistoryData | MultiPart | None = await self._universalis.get_bulk_history_data(items=query, **kwargs)
            if isinstance(res, MultiPart):
                return self._parse_multipart(items=item_obj, data=res)
            return res

    async def get_suggested_price(
        self,
        item: int | str,
        *,
        filter_results: bool = True,
        **kwargs: Unpack[CurMarketBoardParams],
    ) -> SuggestedPrice:
        """Use current listings and recent history listings to give a "suggestive" price and stack size to sell the item.

        .. note::
            The information is purely based on the sample size.
            - So increasing or decreasing the `num_of_listings` parameter can skew the results.


        .. note::
            You can change the default DataCenter by setting the `<UniversalisAPI>.datacenter` property.


        Parameters
        ----------
        item: :class:`int | str`
            A Final Fantasy 14 item id of int or str type.
        filter_results: :class:`bool`, optional
            If we should omit too high of price per unit entries from Current listings.
        **kwargs: :class:`Unpack[CurMarketBoardParams]`
            Any additional params to pass to :class:`UniversalisAPI.get_bulk_current_data()`.

        Returns
        -------
        :class:`str`
            A string including the item name, quality, world, sample size, current highest price and lowest price,
            mean price diff for current and recent history and suggested stack sizing.

        """
        if isinstance(item, str):
            item = int(item)

        # Get a bulk of data to check average price/stack and other information to make a suggested price.
        res: CurrentData = await self._universalis.get_current_data(item=item, **kwargs)

        stacksize: int = 0
        optimal_stacksize: str = "UNK"
        for key, value in res.stack_size_histogram.items():
            if value > stacksize:
                stacksize = value
                optimal_stacksize = key

        cur_stacksize_mode: float = statistics.mode(data=[entry.quantity for entry in res.listings])
        history_stacksize_mode: float = statistics.mode(data=[entry.quantity for entry in res.recent_history])
        # Let's sort our listings by highest price first.
        sorted_cur_listings: list[CurrentDataEntries] = sorted(res.listings, key=lambda x: x.price_per_unit, reverse=True)
        sorted_history_listings: list[HistoryDataEntries] = sorted(res.recent_history, key=lambda x: x.price_per_unit, reverse=True)

        cur_listings: list[CurrentDataEntries] = []
        history_listings: list[HistoryDataEntries] = []
        if filter_results:
            cur_listings.extend(entry for entry in sorted_cur_listings if entry.price_per_unit < (res.current_average_price * 2))
            history_listings.extend(entry for entry in sorted_history_listings if entry.price_per_unit < (res.average_price * 2))
        else:
            cur_listings = sorted_cur_listings
            history_listings = sorted_history_listings

        # Let's get the middle price point
        cur_price_mean: float = statistics.mean(data=[entry.price_per_unit for entry in cur_listings])
        history_price_mean: float = statistics.mean(data=[entry.price_per_unit for entry in history_listings])
        # So we have the MEAN values for price and stacksize in terms of current listings and history listings.
        # Current highest price = sorted_cur_listings[0]
        # History highest price = sorted_history_listings[0]
        cur_mean_diff = int(cur_listings[0].price_per_unit - cur_price_mean)
        hist_mean_diff = int(history_listings[0].price_per_unit - history_price_mean)
        cur_metrics = SuggestedPriceMetrics(
            cur_listings[0].price_per_unit,
            cur_listings[-1].price_per_unit,
            cur_price_mean,
            cur_mean_diff,
            str(cur_stacksize_mode),
        )
        history_metrics = SuggestedPriceMetrics(
            history_listings[0].price_per_unit,
            history_listings[-1].price_per_unit,
            history_price_mean,
            hist_mean_diff,
            str(history_stacksize_mode),
        )
        try:
            name: str = self.get_item(item=str(res.item_id), limit_results=1).name
        except MoogleLookupError:
            name = "UNK"

        world_or_dc = World.UNK
        if kwargs.get("world_or_dc") is None:
            if res.world_name is not None:
                world_or_dc = res.world_name
            elif res.dc_name is not None:
                world_or_dc = res.dc_name

        item_quality = "NQ"
        if kwargs.get("item_quality") is None and res.listings[0].hq is True:
            item_quality = "HQ"

        if kwargs.get("num_listings") is None:  # noqa: SIM108
            num_of_listings = res.listings_count
        else:
            num_of_listings = kwargs.get("num_listings", 0)

        return SuggestedPrice(
            name=name,
            item_id=res.item_id,
            item_quality=item_quality,
            world_or_dc=world_or_dc,
            num_of_listings=num_of_listings,
            current_metrics=cur_metrics,
            history_metrics=history_metrics,
            stacksize=optimal_stacksize,
        )

    async def currency_spender(
        self,
        currency: Currency = Currency.allagan_tomestone_of_poetics,
        patch: Expansion = Expansion.dawntrail,
        **kwargs: Unpack[CurMarketBoardParams],
    ) -> dict[int, CurrencySpender] | None:
        """Returns a list of items with the highest sale velocity per World/Datacenter purchased with the specified currency.

        .. warning::
            This function can take a while to process, especially if filtering results with a patch.

        .. note::
            There is built in functionality to parse the results via :class:`Converter.parse_currency_spender` in an easy to read format.

        Parameters
        ----------
        currency: :class:`Currency`, optional
            The currency to look up for potential spending, by default :class:`Currency.allagan_tomestone_of_poetics`.
        patch: :class:`Patch`, optional
            The patch at which to filter results "up to", so :class:`Patch.dawntrail`
        **kwargs: :class:`Unpack[CurMarketBoardParams]`
            Any additional params to pass to :class:`UniversalisAPI.get_bulk_current_data()`.


        Returns
        -------
        :class:`list[CurrencySpender] | None`
            A simple :class:`TypedDict` housing relevant information regarding the currency such as the cost and Universalis data.

        """
        results: dict[int, CurrencySpender] = {}
        currency_response: ItemResponse = await self._garlandtools.item(item_id=currency.value)
        trade_data: list[TradeShops] | None = currency_response["item"].get("tradeCurrency", None)
        if trade_data is None:
            return None

        # items: list[int] = []
        cost: int = 0
        item_obj: list[Item] = []
        for entry in trade_data:
            for i in entry["listings"]:
                cost = i["currency"][0]["amount"]
                # items.extend([e["id"] for e in i["item"] if e["id"] not in items])
                for e in i["item"]:
                    if e["id"] not in results:
                        item: Item = self.get_item(str(e["id"]), limit_results=1)
                        if item.garlandtools_data is None:
                            itemres: ItemResponse | None = await item.get_garlandtools_data()
                        else:
                            itemres = item.garlandtools_data

                        if item.is_untradable is False and itemres is not None and itemres["item"]["patch"] < patch.value + 1:
                            item_obj.append(item)
                            results[int(e["id"])] = {"item": item, "cost": cost, "currency": currency}

        res: MultiPart | CurrentData | None = await self._universalis.get_bulk_current_data(items=list(results), **kwargs)
        if isinstance(res, MultiPart):
            self._parse_multipart(items=item_obj, data=res)
        return results


class Item(Object):
    """Represents an FFXIV Item per XIV Datamining CSV.

    .. note::
        Inherits attributes and functions from :class:`Object`.

    Attributes
    ----------
    id: :class:`int`
        The item ID.
    description: :class:`Optional[str]`
        The description about the item, if applicable..
    name: :class:`str`
        The name of the Final Fantasy 14 item.
    level_item: :class:`ItemLevelData`
        The attributes and other characteristics related to the item such as HP, MP and damage.
    equip_slot_category: :class:`EquipSlotCategory`
        The equipment slot the item belongs to, if applicable.
    stack_size: :class:`int`
        The max stack size of the item.
    is_unique: :class:`bool`
        If the item is unique or not.
    is_untradable: :class:`bool`
        If the item is un-tradeable or not.
    is_indisposable: :class:`bool`
        If the item is in-disposable or not.
    item_ui_category: :class:`ItemUICategory`
        The UI slot this item belongs to.
    can_be_hq: :class:`int`
        If the item can be high-quality or not.
    dye_count: :obj:`int`
        The number of dye slots.
    is_collectable: :class:`bool`
        If the item is collectable or not.
    always_collectable: :class:`bool`
        If the item is always collectable or not.
    materia_slot_count: :class:`int`
        The number of materia slots.
    is_advanced_melding_permitted: :class:`bool`
        If the item supports advanced melding or not.
    is_glamourous: :class:`bool`
        If the item can be used in glamour or not.
    recipe: :class:`Optional[JobRecipe]`
        Any recipe information related to the item, if applicable.
    fishing: :class:`Optional[Fishing]`
        Any fishing information related to the item, if applicable.
    spear_fishing: :class:`Optional[SpearFishing]`
        Any spearfishing information related to the item, if applicable.
    gathering: :class:`Optional[GatheringItem]`
        Any gathering information related to the item, if applicable.
    garland_tools_url: :class:`str`
        A url link to the item on Garland Tools.
    ffxivconsolegames_wiki_url: :class:`str`
        A url link to the `FFXIV Console Games Wiki` of the item.
    mb_current: :class:`Optional[CurrentData]`
        Cached current :class:`UniversalisAPI` marketboard data, if applicable.
    mb_history: :class:`Optional[HistoryData]`
        Cached history :class:`UniversalisAPI` marketboard data, if applicable.
    garlandtools_data: :class:`Optional[ItemResponse]`
        Cached :class:`GarlandToolsAsync` API data, if applicable.

    """

    _ff14angler_data: Any
    _recipe: Optional[JobRecipe]
    _fishing: Optional[Fishing]
    _spear_fishing: Optional[SpearFishing]
    _gathering: Optional[Gathering]

    _garlandtools_data: Optional[ItemResponse]
    "For GarlandToolsAsync API data"
    _vendors: Optional[list[Vendor]]
    _tradeshops: Optional[list[Vendor]]
    _icon_data: Optional[GTObject]

    _mb_current: Optional[CurrentData]
    _mb_history: Optional[HistoryData]

    id: int
    icon: int
    "Icon ID, can be used in place for :class:`GarlandToolsAsync.icon()`"
    description: Optional[str]
    name: str
    level_item: ItemLevelData
    equip_slot_category: EquipSlotCategory
    stack_size: int
    is_unique: bool
    is_untradable: bool
    is_indisposable: bool
    item_ui_category: ItemUICategory
    can_be_hq: int
    dye_count: int
    is_collectable: bool
    always_collectable: bool
    materia_slot_count: int
    is_advanced_melding_permitted: bool
    is_glamourous: bool

    __slots__ = (
        "always_collectable",
        "can_be_hq",
        "description",
        "dye_count",
        "equip_slot_category",
        "icon",
        "id",
        "is_advanced_melding_permitted",
        "is_collectable",
        "is_glamourous",
        "is_indisposable",
        "is_unique",
        "is_untradable",
        "item_ui_category",
        "level_item",
        "materia_slot_count",
        "name",
        "stack_size",
    )

    def __init__(self, data: ItemData, **kwargs: Unpack[ObjectParams]) -> None:
        """Build your Final Fantasy 14 Item.

        Parameters
        ----------
        data: :class:`ItemData`
            The JSON data.
        **kwargs: :class:`Unpack[ObjectParams]`
            Any additional functionality such as a :class:`Angler` object or :class:`UniversalisAPI` object.
            - By default the :class:`Moogle` object is required for functionality.

        """
        super().__init__(data=data, moogle=kwargs["moogle"])
        # This list to control the amount of information we return via `__str__()` and `__repr__()` dunder methods.
        self._repr_keys = ["id", "name"]
        self.description = None

        self._icon_data = None

        for key in self.__slots__:
            value: Optional[int | bool | str] = data.get(key, None)
            if value is None:
                continue
            if key == "equip_slot_category" and isinstance(value, int):
                try:
                    self.equip_slot_category = EquipSlotCategory(value=value)
                except ValueError:
                    LOGGER.warning(
                        "<%s> | Failed to find value in %s. | value: %s ",
                        __class__.__name__,
                        "EquipSlotCategory",
                        value,
                    )
                    self.equip_slot_category = EquipSlotCategory.unk

            if key == "item_ui_category" and isinstance(value, int):
                try:
                    self.item_ui_category = ItemUICategory(value=value)
                except ValueError:
                    LOGGER.warning(
                        "<%s> | Failed to find value in %s. | value: %s ",
                        __class__.__name__,
                        "ItemUICategory",
                        value,
                    )
                    self.item_ui_category = ItemUICategory.unkown

            else:
                setattr(self, key, value)
        try:
            self._gathering = self._is_gatherable()
        except MoogleLookupError:
            LOGGER.debug("<%s.%s> | _is_gatherable <MoogleLookupError> | Item ID: %s", __class__.__name__, "__init__", self.id)
            self._gathering = None
        try:
            self._recipe = self._get_item_job_recipes(self.id)
        except MoogleLookupError:
            LOGGER.debug("<%s.%s> | _get_item_job_recipes <MoogleLookupError> | Item ID: %s", __class__.__name__, "__init__", self.id)
            self._recipe = None
        try:
            # self._fishing = self._moogle._is_fishable(self.id)
            self._fishing = self._is_fishable()
        except MoogleLookupError:
            LOGGER.debug("<%s.%s> | _is_fishable <MoogleLookupError> | Item ID: %s", __class__.__name__, "__init__", self.id)
            self._fishing = None
        try:
            self._spear_fishing = self._is_spearfishing()
        except MoogleLookupError:
            LOGGER.debug("<%s.%s> | _is_spearfishing <MoogleLookupError> | Item ID: %s", __class__.__name__, "__init__", self.id)
            self._spear_fishing = None

    def __len__(self) -> int:  # noqa: D105
        return len(str(self.id))

    def __eq__(self, other: object) -> bool:  # noqa: D105
        return isinstance(other, self.__class__) and self.id == other.id

    def __hash__(self) -> int:  # noqa: D105
        return hash(self.id)

    def __lt__(self, other: object) -> bool:  # noqa: D105
        return isinstance(other, self.__class__) and self.id < other.id

    @property
    def recipe(self) -> Optional[JobRecipe]:
        """Any recipe information stored in seperately attached attributes related to the :class:`Item`, if applicable.

        Returns
        -------
        :class:`Optional[JobRecipe]`
            Returns any related recipe information as an object representing the data from the recipe.json.

        """
        return self._recipe

    @property
    def fishing(self) -> Optional[Fishing]:
        """Any fishing information related to the item, if applicable.

        Returns
        -------
        :class:`Optional[Fishing]`
            Returns any related fishing information as an object representing the data from the fishing_spot.json.

        """
        return self._fishing

    @property
    def spear_fishing(self) -> Optional[SpearFishing]:
        """Any spearfishing information related to the item, if applicable.

        Returns
        -------
        :class:`Optional[SpearFishing]`
            Returns any related spear fishing information as an object representing the data from the spearfishing_item.json.

        """
        return self._spear_fishing

    @property
    def gathering(self) -> Optional[Gathering]:
        """Any gathering information related to the item, if applicable.

        Returns
        -------
        :class:`Optional[GatheringItem]`
            Returns any related gathering information as an object representing the data from the gathering_item.json.

        """
        return self._gathering

    @property
    def garland_tools_url(self) -> str:
        """A url link to the item on Garland Tools."""
        return f"https://www.garlandtools.org/db/#item/{self.id}"

    @property
    def ffxivconsolegames_wiki_url(self) -> Any:
        """A url link to the `FFXIV Console Games Wiki` of the item."""
        return f"https://ffxiv.consolegameswiki.com/wiki/{self.name.replace(' ', '_')}"

    @property
    def universalis_url(self) -> str:
        """A url link to the item on Universalis.app, if applicable.

        .. note::
            May fail to resolve on items that are not marketable.
        """
        return f"https://universalis.app/market/{self.id}"

    @property
    def mb_current(self) -> Optional[CurrentData]:
        """Cached current marketboard data, if applicable."""
        try:
            return self._mb_current
        except AttributeError:
            return None

    @property
    def mb_history(self) -> Optional[HistoryData]:
        """Cached history marketboard data, if applicable."""
        try:
            return self._mb_history
        except AttributeError:
            return None

    def _is_fishable(self) -> Fishing | None:
        LOGGER.debug(
            "<%s.%s> | Searching... item_id: %s | entries: %s ",
            __class__.__name__,
            "_is_fishable",
            self.id,
            len(self._moogle._fish_params_ref),
        )

        key: Optional[str | int] = self._moogle._fish_params_ref.get(self.id, None)
        if key is None:
            return None

        data: Optional[DataTypeAliases] = self._moogle._fish_params.get(str(key), None)
        if data is None or "fishing_spot" not in data:
            raise MoogleLookupError(str(key), "item_id", "_is_fishable", self)
        return Fishing(data=data, item=self, angler=self._moogle._angler, moogle=self._moogle)

    def _is_spearfishing(self) -> SpearFishing | None:
        LOGGER.debug(
            "<%s.%s> | Searching... item_id: %s | entries: %s ",
            __class__.__name__,
            "_is_spearfishing",
            self.id,
            len(self._moogle._spearfishing_items_ref),
        )
        key: Optional[str | int] = self._moogle._spearfishing_items_ref.get(self.id, None)
        if key is None:
            return None

        data: Optional[DataTypeAliases] = self._moogle._spearfishing_items.get(str(key), None)
        if data is None or "is_visible" not in data:
            raise MoogleLookupError(str(key), "item_id", "_is_spearfishing", self)
        return SpearFishing(data=data, item=self, angler=self._moogle._angler, moogle=self._moogle)

    def _is_gatherable(self) -> Gathering | None:
        LOGGER.debug(
            "<%s.%s> | Searching... item_id: %s | entries: %s ",
            __class__.__name__,
            "_is_gatherable",
            self.id,
            len(self._moogle._gathering_items_ref),
        )
        key: Optional[str | int] = self._moogle._gathering_items_ref.get(self.id, None)
        if key is None:
            return None

        data: Optional[DataTypeAliases] = self._moogle._gathering_items.get(str(key), None)
        if data is None or ("gathering_item_level" not in data or "quest" not in data or "is_hidden" not in data):
            raise MoogleLookupError(str(key), "item_id", "_is_gatherable", self)
        return Gathering(data=data, item=self, moogle=self._moogle)

    def _get_item_job_recipes(self, item_id: int) -> JobRecipe | None:
        LOGGER.debug(
            "<%s.%s> | Searching... Job Recipe by Item ID: %s | Entries: %s",
            __class__.__name__,
            "_get_item_job_recipes",
            item_id,
            len(self._moogle._recipe_lookups),
        )

        data: Optional[DataTypeAliases] = self._moogle._recipe_lookups.get(str(item_id), None)
        if data is None or "CRP" not in data:
            return None

        return JobRecipe(data=data, item=self, moogle=self._moogle)

    async def get_current_marketboard(self, **kwargs: Unpack[CurMarketBoardParams]) -> Optional[CurrentData]:
        """Retrieve the current Marketboard data for this item, while also setting the `<Item.mb_current>` property.

        Parameters
        ----------
        **kwargs: :class:`Unpack[CurMarketBoardParams]`
            Any additional params to pass to `<UniversalisAPI.get_bulk_current_data()>`.

        Returns
        -------
        :class:`CurrentData`
            The JSON response converted into a :class:`CurrentData` object if applicable.

        """
        try:
            self._mb_current = await self._moogle._universalis.get_current_data(item=self.id, **kwargs)
        except UniversalisError:
            LOGGER.error(
                "<%s.%S> | Failed to get Universalis Current Marketboard data | Item: %s",
                __class__.__name__,
                "get_current_martketboard",
                self.id,
            )
            return None
        return self._mb_current

    async def get_history_marketboard(self, **kwargs: Unpack[HistMarketBoardParams]) -> Optional[HistoryData]:
        """Retrieve the Marketboard History data for this item, while also setting the `<Item.mb_history>` property.

        Parameters
        ----------
        **kwargs: :class:`Unpack[MarketBoardParams]`
            Any additional parameters to change the results of the data.

        Returns
        -------
        :class:`CurrentData`
            The JSON response converted into a :class:`HistoryData` object if applicable.

        """
        try:
            self._mb_history = await self._moogle._universalis.get_history_data(item=self.id, **kwargs)
        except UniversalisError:
            LOGGER.error(
                "<%s.%S> | Failed to get Universalis History Marketboard data | Item: %s",
                __class__.__name__,
                "get_history_marketboard",
                self.id,
            )
            return None
        return self._mb_history

    @property
    def garlandtools_data(self) -> Optional[ItemResponse]:
        """Cached GarlandTools API data, if applicable.

        .. warning::
            The Garlandtools data must first be fetched/cached via :class:`Item.get_garlandtools_data()`.

        Returns
        -------
        :class:`Optional[ItemResponse]`
            Cached GarlandTools dict data if applicable.

        """
        try:
            return self._garlandtools_data
        except AttributeError:
            return None

    async def get_garlandtools_data(self) -> Optional[ItemResponse]:
        """Retrieve GarlandTools API data for this item, while also setting the :class:`Item.garlandtools_data` property.

        Returns
        -------
        :class:`ItemResponse`
            A JSON response structred as :class:`ItemResponse`.

        """
        try:
            self._garlandtools_data = await self._moogle._garlandtools.item(item_id=self.id)
        except GarlandToolsKeyError:
            LOGGER.warning("<%s.%s> | Failed to get GarlandTools Data. | Item: %s", __class__.__name__, "get_garlandtools_data", self.id)
            return None
        return self._garlandtools_data

    async def get_icon(self) -> Optional[GTObject]:
        """Fetches GarlandTools Icon data, if applicable.

        Returns
        -------
        :class:`Optional[GTObject]`
            A GarlandTools API Object.

        """
        if self._icon_data is not None:
            return self._icon_data

        try:
            res: GTObject = await self._moogle._garlandtools.icon(icon_id=self.icon, icon_type=IconType.item)
            self._icon_data = res
        except GarlandToolsRequestError:
            LOGGER.warning("<%s.%s> | Failed to get GarlandTools Icon data. | Item: %s", __class__.__name__, "get_icon", self.id)
            return None
        return res

    @property
    def vendors(self) -> Optional[list[Vendor]]:
        """Item vendor information, if applicable.

        .. warning::
            The Garlandtools data must first be fetched/cached via :class:`Item.get_garlandtools_data()` and
            then parsed via :class:`Item.get_vendors()`.

        Returns
        -------
        :class:`Optional[list[Vendor]]`
            A list of parsed GarlandTools data regarding Vendors.

        """
        if self.garlandtools_data is None:
            return None

        try:
            return self._vendors
        except AttributeError:
            return None

    def get_vendors(self) -> list[Vendor] | None:
        """Parse GarlandTools Data and retrieve Vendor information, if applicable.

        .. note::
            Will set results to our :class:`Item.vendors` property.


        .. warning::
            The Garlandtools data must first be fetched/cached via :class:`Item.get_garlandtools_data()`.


        Returns
        -------
        :class:`list[Vendor] | None`
            A list of :class:`Vendor` to access information related to the vendor,
            otherwise will return `None` if :class:`Item.garlandtools_data` is `None`.

        """
        if self.garlandtools_data is None:
            return None

        vendors_ids: list[int] | None = self.garlandtools_data["item"].get("vendors", None)
        if vendors_ids is None:
            return None

        partials: list[PartialTypeIDObj] | None = self.garlandtools_data.get("partials", None)
        if partials is None:
            return None

        item: GTItem = self.garlandtools_data["item"]
        self._vendors = []
        for value in partials:
            if int(value["id"]) in vendors_ids:
                self._vendors.append({
                    "name": value["obj"].get("n", "N/A"),
                    "id": value["id"],
                    "price": item["price"],
                    "shop_name": str(value["obj"].get("t", "N/A")),
                    "url": f"https://www.garlandtools.org/db/#npc/{value['id']}",
                })
        return self._vendors

    @property
    def tradeshops(self) -> Optional[list[Vendor]]:
        """Tradeshop information, if applicable.

        .. warning::
            The Garlandtools data must first be fetched/cached via :class:`Item.get_garlandtools_data()` and
            then parsed via :class:`Item.get_vendors()`.

        Returns
        -------
        :class:`Optional[list[Vendor]]`
            A list of parsed GarlandTools data regarding Tradeshops.

        """
        if self.garlandtools_data is None:
            return None

        try:
            return self._tradeshops
        except AttributeError:
            return None

    def get_tradeshops(self) -> list[Vendor] | None:
        """Parse GarlandTools data and retrieve Trade shop information, if applicable.

        .. note::
            Will set results to our :class:`Item.tradeshops` property.


        .. warning::
            The Garlandtools data must first be fetched/cached via :class:`Item.get_garlandtools_data()`.


        Returns
        -------
        :class:`list[Vendor] | None`
             A list of :class:`Vendor` to access information related to the vendor,
            otherwise will return `None` if :class:`Item.garlandtools_data` is `None`.

        """
        if self.garlandtools_data is None:
            return None

        trade_shops: list[TradeShops] | None = self.garlandtools_data["item"].get("tradeShops", None)
        if trade_shops is None:
            return None

        partials: list[PartialTypeIDObj] | None = self.garlandtools_data.get("partials", None)
        if partials is None:
            return None

        self._tradeshops = []
        for entry in trade_shops:
            for shop_info in partials:
                if shop_info["id"].isnumeric() is False:
                    continue

                if int(shop_info["id"]) in entry["npcs"]:
                    try:
                        currency: Item = self._moogle.get_item(item=str(entry["listings"][0]["currency"][0]["id"]), limit_results=1)
                    except MoogleLookupError:
                        LOGGER.warning(
                            "<%s.%s> | Failed to find Currency Item | Item: %s",
                            __class__.__name__,
                            "get_tradeshops",
                            entry["listings"][0]["currency"][0]["id"],
                        )
                        continue

                    self._tradeshops.append({
                        "name": shop_info["obj"].get("n", "N/A"),
                        "id": shop_info["id"],
                        "price": entry["listings"][0]["currency"][0]["amount"],
                        "currency": currency,
                        "shop_name": str(shop_info["obj"].get("t", "N/A")),
                        "url": f"https://www.garlandtools.org/db/#npc/{shop_info['id']}",
                    })
        return self._tradeshops


class JobRecipe(Object):
    """A represensation of Job specific information related to a Final Fantasy 14 Item.

    .. note::
        Each Disciple of Hand has an attribute and related :class:`Recipe` information, if applicable.
        - Supports iteration to access Job specific :class:`Recipe` objects.


    .. note::
        Inherits attributes and functions from :class:`Object`.


    Attributes
    ----------
    CRP: :class:`Optional[Recipe]`
        Carpenter related Job Recipe, if applicable.
    BSM: :class:`Optional[Recipe]`
        Blacksmith related Job Recipe, if applicable.
    ARM: :class:`Optional[Recipe]`
        Armorsmith related Job Recipe, if applicable.
    GSM: :class:`Optional[Recipe]`
        Goldsmith related Job Recipe, if applicable.
    LTW: :class:`Optional[Recipe]`
        Leatherworker related Job Recipe, if applicable.
    WVR: :class:`Optional[Recipe]`
        Weaver related Job Recipe, if applicable.
    ALC: :class:`Optional[Recipe]`
        Alchemist related Job Recipe, if applicable.
    CUL: :class:`Optional[Recipe]`
        Culinarian related Job Recipe, if applicable.

    """

    CRP: Optional[Recipe]
    BSM: Optional[Recipe]
    ARM: Optional[Recipe]
    GSM: Optional[Recipe]
    LTW: Optional[Recipe]
    WVR: Optional[Recipe]
    ALC: Optional[Recipe]
    CUL: Optional[Recipe]
    _id: Optional[int]
    _item: Item

    __slots__ = ("ALC", "ARM", "BSM", "CRP", "CUL", "GSM", "LTW", "WVR")

    @property
    def recipe_id(self) -> Optional[int]:
        """The first occurence of a :class:`Recipe` ID during class initialization, if applicable."""
        return self._id

    @recipe_id.setter
    def recipe_id(self, value: int) -> None:
        self._id = value

    def __init__(self, data: RecipeLookUpData, item: Item, **kwargs: Unpack[ObjectParams]) -> None:
        """Build your Job Recipe object.

        Parameters
        ----------
        data: :class:`RecipeLookUpData`
            The JSON data.
        item: :class:`Item`
            The Final Fantasy :class:`Item` object associated to the :class:`Recipe` data.
        **kwargs: :class:`Unpack[ObjectParams]`
            Any additional functionality such as a :class:`Angler` object or :class:`UniversalisAPI` object.
            - By default the :class:`Moogle` object is required for functionality sake.

        """
        super().__init__(data=data, moogle=kwargs["moogle"])
        # self._items: list[Recipe] = []
        self._id = None
        self._repr_keys = ["recipe_id"]

        self._item = item

        for key in self.__slots__:
            value: Optional[str | int | bool] = data.get(key, None)
            if value is None:
                continue
            if isinstance(value, int) and value != 0:
                if self.recipe_id is None:
                    self.recipe_id = value
                # This takes the value data and builds our FFXIVRecipe class from the raw JSON stored on our Moogle class.
                try:
                    recipe = self._get_recipe(str(value))
                    setattr(self, key, recipe)
                except MoogleLookupError:
                    LOGGER.warning("<%s> | Failed to Recipe ID. | Recipe: %s", __class__.__name__, value)
                    setattr(self, key, value)
            else:
                setattr(self, key, None)

    def __iter__(self) -> Iterator[Recipe]:
        _iter = 0
        while _iter < len(self.__slots__):
            try:
                attr = self.__slots__[_iter]
                data = getattr(self, attr)
                # We don't want to return any `int` or `None` values when during our loops.
                if isinstance(data, int) or data is None:
                    _iter += 1
                    continue
            except IndexError:
                raise StopIteration from IndexError

            _iter += 1
            yield data

    def __len__(self) -> int:
        return len([entry for entry in self])  # noqa: C416

    def __getitem__(self, job: int) -> Recipe:
        return list(self)[job]

    def _get_recipe(self, recipe_id: str) -> Recipe:
        """Lookup a Final Fantasy 14 Recipe by ID.

        Parameters
        ----------
        recipe_id: :class:`str`
            The recipe ID.

        Returns
        -------
        :class:`Recipe`
            The :class:`Recipe` class object.

        Raises
        ------
        MoogleLookupError
            If the Recipe ID doesn't have the proper dict key.

        """
        # I am storing str "Recipe ID" : int "Item Result ID"
        LOGGER.debug(
            "<%s.%s> | Searching... recipe_id: %s | entries: %s",
            __class__.__name__,
            "_get_recipe",
            recipe_id,
            len(self._moogle._recipes),
        )

        data: Optional[DataTypeAliases] = self._moogle._recipes.get(recipe_id, None)
        if data is None or "item_result" not in data:
            raise MoogleLookupError(recipe_id, "recipe_id", "_get_recipe", self)

        return Recipe(recipe_id=recipe_id, data=data, item=self._item, moogle=self._moogle)

    async def get_crafting_cost(
        self,
        *,
        count: int = 1,
        **kwargs: Unpack[CurMarketBoardParams],
    ) -> Optional[dict[int, ShoppingItem]]:
        """Fetches purchasing information related to the Recipe and it's ingredients.

        .. note::
            This uses the `self.id` attribute to fetch information.
            Consider using this funciton at the :class:`Recipe` level for recipe specific information.

        Retrieve Item, Marketboard, Vendor and Tradeshop information and returns the data in a useful structure.

        Parameters
        ----------
        count: :class:`int`, optional.
            Number of "ingredients" times number of Items to craft, default is 1.
        **kwargs: :class:`Unpack[CurMarketBoardParams]`
            Any additional params to pass to `<UniversalisAPI.get_bulk_current_data()>`.

        Returns
        -------
        :class:`Optional[dict[int, CraftingCost]]`
            Information about every Item needed to craft this Recipe.

        """
        # We are getting all the items and ingredients to craft the item.
        try:
            recipe: Recipe = self._get_recipe(recipe_id=str(self.recipe_id))
        except MoogleLookupError:
            LOGGER.warning("<%s> | Failed to Recipe ID. | Recipe: %s", __class__.__name__, self.recipe_id)
            return None

        return await recipe.get_crafting_cost(count=count, **kwargs)


class Recipe(Object):
    """A representation of a Final Fantasy 14 Recipe.

    .. note::
        Inherits attributes and functions from :class:`Object`.

    Attributes
    ----------
    id: :class:`int`
        The Final Fantasy 14 Recipe ID.
    craft_type: :class:`Optional[CraftType]`, optional
        The Job this recipe belongs too, if applicable.
    recipe_level_table: :class:`RecipeLevelData`
        The characteristics and details about the recipe, such as difficulty and craftsmanship required.
    item_result: :class:`Item`
        The resulting Final Fantasy 14 Item object.
    amount_result: :class:`int`
        The number of items recieved after completing the crafting recipe.
    item_ingredient0: :class:`Item`
        The Final Fantasy 14 item for the ingredient of the recipe, if applicable.
    amount_ingredient0: :class:`int`
        The quantity required for the ingredient of the recipe, if applicable.
    item_ingredient1: :class:`Item`
        The Final Fantasy 14 item for the ingredient of the recipe, if applicable.
    amount_ingredient1: :class:`int`
        The quantity required for the ingredient of the recipe, if applicable.
    item_ingredient2: :class:`Item`
        The Final Fantasy 14 item for the ingredient of the recipe, if applicable.
    amount_ingredient2: :class:`int`
        The quantity required for the ingredient of the recipe, if applicable.
    item_ingredient3: :class:`Item`
        The Final Fantasy 14 item for the ingredient of the recipe, if applicable.
    amount_ingredient3: :class:`int`
        The quantity required for the ingredient of the recipe, if applicable.
    item_ingredient4: :class:`Item`
        The Final Fantasy 14 item for the ingredient of the recipe, if applicable.
    amount_ingredient4: :class:`int`
        The quantity required for the ingredient of the recip, if applicablee.
    item_ingredient5: :class:`Item`
        The Final Fantasy 14 item for the ingredient of the recipe, if applicable.
    amount_ingredient5: :class:`int`
        The quantity required for the ingredient of the recipe, if applicable.
    item_ingredient6: :class:`Item`
        The Final Fantasy 14 item for the ingredient of the recipe, if applicable.
    amount_ingredient6: :class:`int`
        The quantity required for the ingredient of the recipe, if applicable.
    item_ingredient7: :class:`Item`
        The Final Fantasy 14 item for the ingredient of the recipe, if applicable.
    amount_ingredient7: :class:`int`
        The quantity required for the ingredient of the recipe, if applicable.
    can_quick_synth: :class:`bool`
        If the recipe supports quick sythesis or not.
    can_hq: :class:`bool`
        If the recipe can be high-quality or not.
    status_required: :class:`int`
        If the recipe requires a buff or status effect to craft. (Think Ixali daily quests.)
    item_required: :class:`int`
        If the recipe requires a specific item to be equiped. (Think Ixali daily quests.)
    is_specialization_required: :class:`int`
        If the recipe requires a "book" or similar to be acquired first.
    is_expert: :class:`bool`
        If the recipe is an expert craft or not.

    """

    id: int
    craft_type: Optional[CraftType]
    recipe_level_table: RecipeLevelData
    item_result: Item
    amount_result: int
    item_ingredient0: Optional[Item | int]
    amount_ingredient0: Optional[int]
    item_ingredient1: Optional[Item | int]
    amount_ingredient1: Optional[int]
    item_ingredient2: Optional[Item | int]
    amount_ingredient2: Optional[int]
    item_ingredient3: Optional[Item | int]
    amount_ingredient3: Optional[int]
    item_ingredient4: Optional[Item | int]
    amount_ingredient4: Optional[int]
    item_ingredient5: Optional[Item | int]
    amount_ingredient5: Optional[int]
    item_ingredient6: Optional[Item | int]
    amount_ingredient6: Optional[int]
    item_ingredient7: Optional[Item | int]
    amount_ingredient7: Optional[int]
    can_quick_synth: bool
    can_hq: bool
    status_required: int
    item_required: int
    is_specialization_required: int
    is_expert: bool

    # _ingredients: list[Item]
    _iter = 0

    __slots__ = (
        "amount_ingredient0",
        "amount_ingredient1",
        "amount_ingredient2",
        "amount_ingredient3",
        "amount_ingredient4",
        "amount_ingredient5",
        "amount_ingredient6",
        "amount_ingredient7",
        "amount_result",
        "can_hq",
        "can_quick_synth",
        "craft_type",
        "id",
        "is_expert",
        "is_specialization_required",
        "item_ingredient0",
        "item_ingredient1",
        "item_ingredient2",
        "item_ingredient3",
        "item_ingredient4",
        "item_ingredient5",
        "item_ingredient6",
        "item_ingredient7",
        "item_required",
        "item_result",
        "recipe_level_table",
        "status_required",
    )

    def __init__(self, recipe_id: str, data: RecipeData, item: Item, **kwargs: Unpack[ObjectParams]) -> None:
        """Build your Recipe object.

        Parameters
        ----------
        recipe_id: :class:`int`
            The Final Fantasy 14 recipe id.
        data: :class:`RecipeData`
            The JSON data.
        item: :class:`Item`
            The Final Fantasy :class:`Item` object associated to this :class:`Recipe`.
        **kwargs: :class:`Unpack[ObjectParams]`
            Any additional functionality such as a :class:`Angler` object or :class:`UniversalisAPI` object.
            - By default the :class:`Moogle` object is required for functionality sake.

        """
        super().__init__(data=data, moogle=kwargs["moogle"])
        self.id = int(recipe_id)
        # This list to control the amount of information we return via `__str__()` and `__repr__()` dunder methods.
        self._repr_keys = ["id", "craft_type", "item_result", "is_expert", "item_required", "amount_result"]
        self._repr_keys.extend([f"item_ingredient{idx}" for idx in range(8)])
        self._repr_keys.extend([f"amount_ingredient{idx}" for idx in range(8)])
        for key in self.__slots__:
            value: Optional[int | bool | str] = data.get(key, None)
            if value is None:
                continue
            if isinstance(value, int):
                if key == "item_result":
                    self.item_result = item

                # Essentially we are looking up all our Ingredients and setting our item objects.
                elif key in ["is_specialization_required", "item_required"] or key.startswith("item_ingredient"):
                    if value not in [0, -1]:
                        try:
                            setattr(self, key, self._moogle.get_item(item=str(value), limit_results=1))
                        except MoogleLookupError:
                            LOGGER.warning("<%s> | Failed to find item. | item: %s", __class__.__name__, value)
                            setattr(self, key, value)

                    else:
                        setattr(self, key, None)

                elif key.startswith("amount_ingredient"):
                    if value == 0:
                        setattr(self, key, None)
                    setattr(self, key, value)

                elif key == "craft_type":
                    try:
                        self.craft_type = CraftType(value=value)
                    except ValueError:
                        LOGGER.warning(
                            "<%s> | Failed to find value in %s. | value: %s ",
                            __class__.__name__,
                            "CraftType",
                            value,
                        )
                        self.craft_type = None

                elif key in ["is_expert", "can_hq", "can_quick_synth"]:
                    setattr(self, key, bool(value))
                else:
                    setattr(self, key, value)

            else:
                # Some recipe's have a `-1` value set for `item_ingredient` key.
                if value == "-1":
                    setattr(self, key, None)
                    continue
                setattr(self, key, value)

    def __iter__(self) -> Iterator[tuple[Item, int]]:
        """Yields a tuple containing :class:`Item` and item count:class:`int`."""
        _iter = 0
        while _iter < 8:
            try:
                ingredient: Optional[Item] = getattr(self, f"item_ingredient{_iter}")
                count: Optional[int] = getattr(self, f"amount_ingredient{_iter}")
                if isinstance(ingredient, int) or (ingredient is None or count is None):
                    _iter += 1
                    continue

            except IndexError:
                raise StopIteration from IndexError

            _iter += 1
            yield ingredient, count

    def __len__(self) -> int:  # noqa: D105
        return len([entry for entry in self])  # noqa: C416

    async def get_crafting_cost(
        self,
        *,
        count: int = 1,
        **kwargs: Unpack[CurMarketBoardParams],
    ) -> Optional[dict[int, ShoppingItem]]:
        """Fetches purchasing information related to the Recipe and it's ingredients.

        Retrieve Item, Marketboard, Vendor and Tradeshop information and returns the data in a useful structure.

        Parameters
        ----------
        count: :class:`int`, optional.
            Number of "ingredients" times number of Items to craft, default is 1.
        **kwargs: :class:`Unpack[CurMarketBoardParams]`
            Any additional params to pass to `<UniversalisAPI.get_bulk_current_data()>`.

        Returns
        -------
        :class:`Optional[dict[int, ShoppingItem]]`
            Information about every Item needed to craft this Recipe.

        """
        # First iteration; set's the data structure up.
        # if results is None:
        results: dict[int, ShoppingItem] = {}

        # We are getting all the items and ingredients to craft the item.
        for ingredient in self:
            item: Item | int = ingredient[0]
            if isinstance(item, int):
                continue

            if results.get(item.id, None) is None:
                results[item.id] = {"item": item, "count": ingredient[1] * count}
            else:
                results[item.id]["count"] += ingredient[1] * count

            if item.garlandtools_data is None:
                await item.get_garlandtools_data()
                item.get_vendors()
                item.get_tradeshops()

            if item.mb_current is None:
                await item.get_current_marketboard(**kwargs)

            # This is for the item if it has it's own recipe
            if item.recipe is not None:
                res: dict[int, ShoppingItem] | None = await item.recipe.get_crafting_cost(count=ingredient[1] * count, **kwargs)
                if res is not None:
                    results[item.id]["ingredients"] = res

        return results


class Fish(Object):
    """Generic base object for handling FF14 Angler data and FFXIV item information.

    . note::
        Inherits attributes and functions from :class:`Object`.


    Attributes
    ----------
    item_id: :class:`int`
        The item ID.
    name: :class:`Optional[str]`
        The name of the Fish.
    angler_id: :class:`Optional[int]`
        The ID of the fish.

    Properties
    -----------
    angler_data: :class:`Optional[list[AnglerFish]]`
        Houses the FF14Angler information retrieved from `<ItemFish.get_angler_data>`.
    angler_url: :class:`str`
        The FF14Angler website url for the Fish.

    """

    item_id: int
    name: Optional[str]
    fishing_record_type: int

    # FF14 Angler website lookup information.
    # This value comes from `<Angler.fish_map>` array.
    angler_id: Optional[int]
    _angler_data: Optional[list[AnglerFish]]
    _angler: Angler

    def __init__(self, data: DataTypeAliases, angler: Angler, moogle: Moogle) -> None:
        """Generic object for bridging FF14Angler and XIV data.

        Parameters
        ----------
        data: :class:`DataTypeAliases`
            Generic typed as the data structure being passed in is typically a dict.
        angler: :class:`Angler`
            The :class:`Angler` object to handle data lookup.
        moogle: :class:`Moogle`
            The :class:`Moogle` object that created this class.

        """
        self._angler = angler
        super().__init__(data=data, moogle=moogle)

        self.item_id = data.get("item", 0)
        if self._moogle._angler_fish_map is not None:
            try:
                item_data: DataTypeAliases | None = self._moogle._items.get(str(self.item_id))
                if item_data is not None:
                    name = item_data.get("name", "")
                    self.angler_id = self._moogle._angler_fish_map.get(name)
                    self.name = name
            except MoogleLookupError:
                LOGGER.error("<%s.%s> | Failed to lookup Item ID | Item ID: %s", __class__.__name__, "__init__", self.item_id)
                return

    @overload
    async def get_angler_data(self, *, best_chance: Literal[True]) -> Optional[AnglerFish]: ...

    @overload
    async def get_angler_data(self, *, best_chance: bool = ...) -> Optional[list[AnglerFish] | AnglerFish]: ...

    async def get_angler_data(self, *, best_chance: bool = False) -> Optional[list[AnglerFish] | AnglerFish]:
        """Retrieve FF14 Fishing Angler data from their website and return it in a manageable form.

        .. note:
            - This will populate the :class:`Self.angler_data` property.


        Parameters
        ----------
        best_chance: :class:`bool`, optional
            Returns the highest percent catch chance by bait and location only, by default False.
            - The first entry of :class:`AnglerFish.baits` would be the "best percent catch".

        Returns
        -------
        :class:`Optional[list[AnglerFish] | AnglerFish]`
            Returns a list of Fishing locations and Baits by default, if using `best_chance` parameter you will get a single entry back.

        """
        LOGGER.debug("<%s.%s> | Best Chance: %s", __class__.__name__, "get_angler_data", best_chance)
        LOGGER.debug(
            "<%s.%s> | Angler Fish Map: %s | Name: %s",
            __class__.__name__,
            "get_angler_data",
            self._moogle._angler_fish_map,
            self.name,
        )
        if self._moogle._angler_fish_map is None:
            return None

        if self.name is None:
            return None

        # Most of the data is static; so no need to re-fetch it.
        if self.angler_data is not None:
            return self.angler_data

        fish_id: Optional[int] = self._moogle._angler_fish_map.get(self.name, None)
        if fish_id is None:
            LOGGER.debug("<%s.%s> | Fish ID: %s", __class__.__name__, "get_angler_data", fish_id)
            return None

        fish_locs: Optional[list[int]] = await self._angler.get_fish_locations(fish_id=fish_id)
        if fish_locs is None:
            LOGGER.debug("<%s.%s> | Fish Locs: %s", __class__.__name__, "get_angler_data", fish_locs)
            return None

        data: list[AnglerFish] = []
        chance = 0
        best: Optional[AnglerFish] = None
        LOGGER.debug("Checking Best Chance: %s | Type: %s | Entries: %s", best_chance, type(self), len(data))
        for entry in fish_locs:
            res: Optional[FishingData] = await self._angler.get_location_fish_data(location_id=entry, fish_id=fish_id)
            if res is None:
                continue

            # We use our inverted location mapping to get a location name.
            # if self._moogle._angler_invert_loc_map is not None:
            #     location_name = self._moogle._angler_invert_loc_map.get(entry)
            spot = None
            if self._moogle._angler.area_mapping is not None:
                spot = self._angler.resolve_area_from_loc_id(location_id=entry)

            fish = AnglerFish(item_id=fish_id, data=res, spot=spot)

            data.append(fish)

            # This is to handle retrieving the best location, lure and chance to catch the fish.
            if best_chance is True and isinstance(self, Fishing):
                temp: AnglerBaits | None = fish.best_bait()
                if temp is not None and temp.hook_percent > chance:
                    chance = temp.hook_percent
                    best = fish

        if best_chance is True:
            self._angler_data = data
            return best

        self._angler_data = data
        return data

    @property
    def angler_data(self) -> Optional[list[AnglerFish]]:
        """Houses the FF14Angler information retrieved from :class:`Self.get_angler_data()`."""
        try:
            return self._angler_data
        except AttributeError:
            return None

    @property
    def angler_url(self) -> str:
        """The FF14Angler website url for the Fish."""
        if self.angler_id is None:
            return "https://en.ff14angler.com/"
        return f"https://en.ff14angler.com/fish/{self.angler_id}"


class Fishing(Fish):
    """Represents the data for a Final Fantasy 14 Fish related to :class:`Item`.

    .. note::
        Inherits attributes from :class:`Fish`.


    Attributes
    ----------
    item: :class:`Item`
        The associated :class:`Item` object.
    name: :class:`Optional[str]`
        The name of the Fish.
    angler_id: :class:`Optional[int]`
        The ID of the fish.
    text: :class:`str`
        Any description or text if applicable.
    ocean_stars: :class:`int`
        The number of stars.
    is_hidden: :class:`bool`
        If the location is hidden or not.


    Properties
    -----------
    angler_data: :class:`Optional[list[AnglerFish]]`
        Houses the FF14Angler data retrieved by :class:`Self.get_angler_data()`.
    angler_url: :class:`str`
        The FF14Angler website url for the Fish.
    fishing_spot: :class:`Optional[FishingSpot]`, optional
        The fishing spot the fish belongs to, if applicable.

    """

    text: Optional[str]
    "Any description or text if applicable."
    ocean_stars: int
    is_hidden: bool
    fishing_spot_id: int
    _fishing_spot: Optional[FishingSpot]

    __slots__ = (
        # "fishing_spot",
        "is_hidden",
        "item",
        "ocean_stars",
        "text",
    )

    def __init__(self, data: FishParameterData, item: Item, angler: Angler, moogle: Moogle) -> None:
        """Build your :class:`Fishing` object.

        Parameters
        ----------
        data: :class:`FishParameterData`
            Generic typed as the data structure being passed in is typically a dict.
        angler: :class:`Angler`
            The :class:`Angler` object to handle data lookup.
        item: :class:`Item`
            The Final Fantasy :class:`Item` object associated to the Fishing data.
        moogle: :class:`Moogle`
            The :class:`Moogle` object that created this class.

        """
        super().__init__(data=data, angler=angler, moogle=moogle)

        self._repr_keys = ["text", "is_hidden", "fishing_spot", "item"]
        self.fishing_spot_id = data["fishing_spot"]
        for key in self.__slots__:
            value: Optional[int | bool | str] = data.get(key, None)
            if value is None:
                continue
            if isinstance(value, int):
                if key == "is_hidden":
                    setattr(self, key, bool(value))
                else:
                    setattr(self, key, value)
            else:
                setattr(self, key, value)

        self.item: Item = item

    def _get_fishing_spot(self, spot_id: int) -> FishingSpot:
        LOGGER.debug(
            "<%s.%s> | Searching... spot_id: %s | entries: %s",
            __class__.__name__,
            "_get_fishing_spot",
            spot_id,
            len(self._moogle._fishing_spot),
        )

        data: Optional[DataTypeAliases] = self._moogle._fishing_spot.get(str(spot_id), None)
        if data is None or "fishing_spot_category" not in data:
            raise MoogleLookupError(str(spot_id), "spot_id", "_get_fishing_spot", self)
        return FishingSpot(data=data, item=self.item, moogle=self._moogle)

    @property
    def fishing_spot(self) -> Optional[FishingSpot]:
        """The fishing spot the :class:`Fishing` belongs to."""
        try:
            self._fishing_spot = self._get_fishing_spot(self.fishing_spot_id)
        except MoogleLookupError:
            LOGGER.warning("<%s> | Failed to find Fishing spot id. | ID: %s", __class__.__name__, self.fishing_spot_id)
            self._fishing_spot = None
        return self._fishing_spot


class SpearFishing(Fish):
    """Represents an Final Fantasy Fish that is acquired via Spear Fishing.

    .. note::
        Inherits attributes from :class:`Fish`.


    Attributes
    ----------
    description: :class:`str`
        The description related to the Fish.
    territory_type: :class:`SpearFishingSpot`
        Similar to :class:`FishingSpot` but specifically for spear fishing locations.
    is_visible: :class:`bool`
        If the fish is visible.
    item: :class:`Item`
        The associated :class:`Item` object.
    name: :class:`Optional[str]`
        The name of the Fish.
    angler_id: :class:`Optional[int]`
        The ID of the fish.

    Properties
    -----------
    angler_data: :class:`Optional[list[AnglerFish]]`
        Houses the FF14Angler data retrieved by :class:`Self.get_angler_data()`.
    angler_url: :class:`str`
        The FF14Angler website url for the Fish.


    """

    description: str
    "The description related to the Fish."
    territory_type: SpearFishingSpot
    "Similar to :class:`FishingSpot` but specifically for spear fishing locations."
    is_visible: bool

    __slots__ = (
        "description",
        "is_visible",
        "item",
        "territory_type",
    )

    def __init__(self, data: SpearFishingItemData, item: Item, angler: Angler, moogle: Moogle) -> None:
        """Build your :class:`SpearFishing` object.

        Parameters
        ----------
        data: :class:`SpearFishingItemData`
            Generic typed as the data structure being passed in is typically a dict.
        item: :class:`Item`
            The Final Fantasy :class:`Item` object associated to the SpearFishing data.
        angler: :class:`Angler`
            The :class:`Angler` object to handle data lookup.
        moogle: :class:`Moogle`
            The :class:`Moogle` object that created this class.

        """
        super().__init__(data=data, angler=angler, moogle=moogle)
        self._repr_keys = ["item", "is_visible", "description"]

        for key in self.__slots__:
            value: Optional[int | bool | str] = data.get(key, None)
            if value is None:
                continue
            if isinstance(value, int):
                if key.lower() == "item" and value != 0:
                    self.item_id = value
                    # try:
                    #     self.item = self._moogle.get_item(item=str(value), limit_results=1)
                    # except MoogleLookupError:
                    #     LOGGER.warning("<%s> | Failed to find item. | item: %s", __class__.__name__, value)
                    #     self.item = value
                elif key.lower() == "territory_type" and value != 0:
                    try:
                        self.territory_type = self._get_spearfishing_spot(record_type=value)
                    except MoogleLookupError:
                        LOGGER.warning("<%s> | Failed to find Spearfishing spot id. | ID: %s", __class__.__name__, value)
                        raise

                elif key.lower() == "is_visible":
                    setattr(self, key, bool(value))
                else:
                    setattr(self, key, value)
            else:
                setattr(self, key, value)

        self.item: Item = item

    def _get_spearfishing_spot(self, record_type: int) -> SpearFishingSpot:
        LOGGER.debug(
            "<%s.%s> | Searching... record_type: %s | entries: %s",
            __class__.__name__,
            "_get_spearfishing_spot",
            record_type,
            len(self._moogle._spearfishing_notebook),
        )
        data: Optional[DataTypeAliases] = self._moogle._spearfishing_notebook.get(str(record_type), None)
        if data is None or "territory_type" not in data:
            raise MoogleLookupError(str(record_type), "record_type", "_get_spearfishing_spot", self)
        return SpearFishingSpot(data=data, angler=self._angler, moogle=self._moogle)


class SpearFishingSpot(Object):
    """A represensation of a Spearfishing Node.

    Attributes
    ----------
    gathering_level: :class:`GatheringItemLevel`
        The characteristics and attributes related to the Spearfishing node location.
    is_shadow_node: :class:`bool`
        If the node is a shadow node or not.
    x: :class:`int`
        In game `X` coordinate.
    y: :class:`int`
        In game `Y` coordinate.
    place_name: :class:`PlaceName`
        The Final Fantasy 14 place the Spearfishing spot is located.

    Properties
    ----------
    angler_url: :class:`str`
        The FF14Angler website url for the Spot.

    """

    gathering_level: GatheringLevel
    is_shadow_node: bool
    x: int
    y: int
    place_name: PlaceName

    __slots__ = (
        "gathering_level",
        "is_shadow_node",
        "place_name",
        "x",
        "y",
    )

    def __init__(self, data: DataTypeAliases, angler: Angler, moogle: Moogle) -> None:
        """Build your :class:`SpearFishingSpot` object.

        Parameters
        ----------
        data: :class:`DataTypeAliases`
            Generic typed as the data structure being passed in is typically a dict.
        angler: :class:`Angler`
            The :class:`Angler` object to handle data lookup.
        moogle: :class:`Moogle`
            The :class:`Moogle` object that created this class.

        """
        super().__init__(data=data, moogle=moogle)
        self._angler = angler
        self._repr_keys = ["place_name", "x", "y", "gathering_level", "is_shadow_node"]

        for key in self.__slots__:
            value: Optional[int | bool | str] = data.get(key, None)
            if value is None:
                continue
            if isinstance(value, int):
                if key.lower() == "gathering_level":
                    try:
                        self.gathering_level = self._moogle._get_gathering_level(level_id=value)
                    except MoogleLookupError:
                        LOGGER.warning("<%s> | Failed to find Gathering level id. | ID: %s", __class__.__name__, value)
                        raise

                elif key.lower() == "place_name":
                    try:
                        self.place_name = self._moogle._get_place_name(place_id=value)
                    except MoogleLookupError:
                        LOGGER.warning("<%s> | Failed to find Place Name id. | ID: %s", __class__.__name__, value)
                        raise
                    if self._moogle._angler_loc_map is not None:
                        self.spot_id = self._moogle._angler_loc_map.get(self.place_name.name)
                    else:
                        self.spot_id = None

                elif key.lower() == "is_shadow_node":
                    self.is_shadow_node = bool(value)
                else:
                    setattr(self, key, value)
            else:
                setattr(self, key, value)

    @property
    def angler_url(self) -> str:
        """The FF14Angler website url for the Spot."""
        if self.spot_id is None:
            return "https://en.ff14angler.com"

        return f"https://en.ff14angler.com/spot/{self.spot_id}"


class FishingSpot(Object):
    """A represensation of a Fishing spot.

    Attributes
    ----------
    gathering_level: :class:`int`
        The gathering job level required.
    fishing_spot_category: :class:`FishingSpotCategory`
        The type of Fishing spot. eg. Ocean, Lava, etc...
    rare: :class:`bool`
        If the Fishing spot is rare or not.
    x: :class:`int`
        In game `X` coordinate.
    z: :class:`int`
        In game `Z` coordinate.
    item0: :class:`int` | :class:`Item`
        The Final Fantasy 14 item of what Fish can be caught in this spot, if applicable.
    item1: :class:`int` | :class:`Item`
        The Final Fantasy 14 item of what Fish can be caught in this spot, if applicable.
    item2: :class:`int` | :class:`Item`
        The Final Fantasy 14 item of what Fish can be caught in this spot, if applicable.
    item3: :class:`int` | :class:`Item`
        The Final Fantasy 14 item of what Fish can be caught in this spot, if applicable.
    item4: :class:`int` | :class:`Item`
        The Final Fantasy 14 item of what Fish can be caught in this spot, if applicable.
    item5: :class:`int` | :class:`Item`
        The Final Fantasy 14 item of what Fish can be caught in this spot, if applicable.
    item6: :class:`int` | :class:`Item`
        The Final Fantasy 14 item of what Fish can be caught in this spot, if applicable.
    item7: :class:`int` | :class:`Item`
        The Final Fantasy 14 item of what Fish can be caught in this spot, if applicable.
    item8: :class:`int` | :class:`Item`
        The Final Fantasy 14 item of what Fish can be caught in this spot, if applicable.
    item9: :class:`int` | :class:`Item`
        The Final Fantasy 14 item of what Fish can be caught in this spot, if applicable.
    place_name: :class:`PlaceName`
        The Final Fantasy 14 place the Fishing spot is located.

    Properties
    ----------
    angler_url: :class:`str`
        The FF14Angler website url for the Spot.

    """

    gathering_level: int
    fishing_spot_category: FishingSpotCategory
    rare: bool
    x: int
    z: int
    item0: Item | int
    item1: Item | int
    item2: Item | int
    item3: Item | int
    item4: Item | int
    item5: Item | int
    item6: Item | int
    item7: Item | int
    item8: Item | int
    item9: Item | int
    place_name: PlaceName | int

    # FF14 Angler website lookup information.
    _angler_loc_id: Optional[int]  # This value comes from `Moogle.ff14angler_loc_map` dict.

    __slots__ = (
        "fishing_spot_category",
        "gathering_level",
        "item0",
        "item1",
        "item2",
        "item3",
        "item4",
        "item5",
        "item6",
        "item7",
        "item8",
        "item9",
        "place_name",
        "rare",
        "x",
        "z",
    )

    def __init__(self, data: FishingSpotData, *, item: Item, **kwargs: Unpack[ObjectParams]) -> None:
        """Build your Fishing spot object.

        Parameters
        ----------
        data: :class:`FishingSpotData`
            The JSON data.
        item: :class:`Item`
            The Final Fantasy :class:`Item` object associated to the :class:`Fishing` data.
        **kwargs: :class:`Unpack[ObjectParams]`
            Any additional functionality such as a :class:`Angler` object or :class:`UniversalisAPI` object.
            - By default the :class:`Moogle` object is required for functionality sake.

        """
        super().__init__(data=data, moogle=kwargs["moogle"])
        self._item: Item = item
        self._repr_keys = [
            "gathering_level",
            "fishing_spot_category",
            "place_name",
        ]
        self._repr_keys.extend([f"item{idx}" for idx in range(10)])
        for key in self.__slots__:
            value: Optional[int | bool | str] = data.get(key, None)
            if value is None:
                continue
            if isinstance(value, int):
                if key.startswith("item") and value != 0:
                    # If any of our Fishing Items are the original Fish,
                    # We set the key accordingly.
                    if value == self._item.id:
                        setattr(self, key, self._item)
                        continue

                    try:
                        temp: Item = self._moogle.get_item(item=str(value), limit_results=1)
                        setattr(self, key, temp)
                    except MoogleLookupError:
                        LOGGER.warning("<%s.%s> | Failed to find item id. | ID: %s", __class__.__name__, "__init__", value)
                        setattr(self, key, value)
                        continue

                elif key.lower() == "place_name" and value != 0:
                    try:
                        self.place_name = self._moogle._get_place_name(place_id=value)
                        if self._moogle._angler_loc_map is not None:
                            self._angler_loc_id = self._moogle._angler_loc_map.get(self.place_name.name)
                    except MoogleLookupError:
                        LOGGER.warning("<%s.%s> | Failed to find Place ID. | ID: %s", __class__.__name__, "__init__", value)
                        self.place_name = value
                        self._angler_loc_id = None

                elif key.lower() == "fishing_spot_category":
                    self.fishing_spot_category = FishingSpotCategory(value)

                elif key == "rare":
                    self.rare = bool(value)
                else:
                    setattr(self, key, value)
            else:
                setattr(self, key, value)

    def __iter__(self) -> Iterator[Item]:
        """Yields a tuple containing :class:`Item`."""
        _iter = 0
        while _iter < 10:
            try:
                item: Optional[Item | int] = getattr(self, f"item{_iter}")
                if isinstance(item, int) or item is None:
                    _iter += 1
                    continue

            except IndexError:
                raise StopIteration from IndexError

            _iter += 1
            yield item

    def __len__(self) -> int:  # noqa: D105
        return len([entry for entry in self])  # noqa: C416

    @property
    def angler_url(self) -> str:
        """The FF14Angler website url for the Spot."""
        if self._angler_loc_id is None:
            return "https://en.ff14angler.com"
        return f"https://en.ff14angler.com/spot/{self._angler_loc_id}"


class Gathering(Object):
    """A represensation of an Final Fantasy 14 Item as Gatherable.

    Attributes
    ----------
    gathering_item_level: :class:`GatheringLevel`
        The item level of the Item and the Stars required if any.
    quest: :class:`bool`
        If the item is from a quest or not.
    is_hidden: :class:`bool`
        If the item is hidden or not.
    item: :class:`Item`
        The associated :class:`Item` object.

    """

    gathering_item_level: GatheringLevel
    quest: bool
    is_hidden: bool
    item: Item
    _nodes: list[GatheringNode]
    __slots__ = (
        "gathering_item_level",
        "is_hidden",
        "quest",
    )

    @property
    def nodes(self) -> Optional[list[GatheringNode]]:
        """A list of Final Fantasy 14 Node information such as zone name, level and area name.

        .. warning::
            The data must first be parsed via :class:`Gathering.get_gathering_nodes()`, which assumes the
            Garlandtools data has been fetched/cached via :class:`Item.get_garlandtools_data()`.


        """
        try:
            return sorted(self._nodes, reverse=True)
        except AttributeError:
            return None

    def __init__(self, data: GatheringData, item: Item, **kwargs: Unpack[ObjectParams]) -> None:
        """Build your Gathering Item object.

        Parameters
        ----------
        data: :class:`GatheringData`
            The JSON data.
        item: :class:`Item`
            The Final Fantasy :class:`Item` object associated to the Gathering data.
        **kwargs: :class:`Unpack[ObjectParams]`
            Any additional functionality such as a :class:`Angler` object or :class:`UniversalisAPI` object.
            - By default the :class:`Moogle` object is required for functionality sake.

        """
        super().__init__(data=data, moogle=kwargs["moogle"])
        self._repr_keys = ["quest", "is_hidden", "gathering_item_level"]
        self.item = item

        for key in self.__slots__:
            value: Optional[int | bool | str] = data.get(key, None)
            if value is None:
                continue
            if key == "gathering_item_level" and isinstance(value, int):
                try:
                    self.gathering_item_level = self._moogle._get_gathering_level(level_id=value)
                except MoogleLookupError:
                    LOGGER.warning("<%s> | Failed to get gathering level. | level id: %s", __class__.__name__, value)
                    continue

            elif key in ["is_hidden", "quest"] and isinstance(value, int):
                setattr(self, key, bool(value))

    async def get_gathering_nodes(self, *, count: int = 5, fetch_data: bool = False) -> Optional[list[GatheringNode]]:
        """Parses GarlandTools data and retrieves Gathering Node information, if applicable.

        This function also sets :class:`Gathering.nodes` attribute.

        .. warning::
            The Garlandtools data must first be fetched/cached via :class:`Item.get_garlandtools_data()`.
            - You can forse fetch new data by setting `fetch_data` to True.

        Parameters
        ----------
        count: :class:`int`, optional
            The number of "nodes" to lookup, by default 5.
        fetch_data: :class:`bool`, optional
            Force fetch GarlandTools Data for parsing, by default False.

        Returns
        -------
        :class:`list[GatheringNode] | None`
            A list of :class:`GatheringNode` to access information related to the gathering node location,
            otherwise will return `None` if :class:`Item.garlandtools_data` is `None`.

        """
        # Force re-fetching of data
        if fetch_data is True:
            await self.item.get_garlandtools_data()

        # In case our data-fetching fails or we haven't fetched data at all.
        if self.item.garlandtools_data is None:
            LOGGER.warning("<%s.%s> | GarlandTools data hasn't been fetched yet.")
            return None

        # Early exit to prevent re-fetching data.
        if fetch_data is False and self.nodes is not None:
            return self.nodes

        nodes: list[int] | None = self.item.garlandtools_data["item"].get("nodes", None)
        if nodes is None:
            return None

        self._nodes = []
        for idx, node in enumerate(nodes):
            if idx > count:
                return self._nodes
            try:
                res: NodeResponse = await self._moogle._garlandtools.node(node_id=node)
            except GarlandToolsKeyError:
                LOGGER.warning("<%s.%s> | Unable to get GarlandTools Node Info. | ID: %s", __class__.__name__, "get_Gathering_nodes", node)
                return None
            self._nodes.append(GatheringNode(data=res["node"], gathering=self, moogle=self._moogle))

        return self._nodes


class GatheringLevel(Object):
    """A represensation of the gatherable items characteristics and attributes.

    Attributes
    ----------
    gathering_item_level: :class:`int`
        The item level of the item.
    stars: :class:`int`
        The number of stars the item has.

    """

    gathering_item_level: int
    stars: int

    __slots__ = ("gathering_item_level", "stars")

    def __init__(self, data: GatheringItemLevelData, **kwargs: Unpack[ObjectParams]) -> None:
        """Build your Gathering Item Level object.

        Parameters
        ----------
        data: :class:`GatheringItemLevelData`
            The JSON data.
        **kwargs: :class:`Unpack[ObjectParams]`
            Any additional functionality such as a :class:`Angler` object or :class:`UniversalisAPI` object.
            - By default the :class:`Moogle` object is required for functionality sake.

        """
        super().__init__(data=data, moogle=kwargs["moogle"])
        self._repr_keys = ["gathering_item_level", "stars"]
        for key in self.__slots__:
            value: Optional[int | bool | str] = data.get(key, None)
            if value is None:
                continue
            setattr(self, key, value)


class GatheringNode(Object):
    """Gathering Node location information related to an :class:`Gathering`.

    .. note::
        If any Item IDs fail lookup will not be in the :class:`GatheringNode.items` array.

    Attributes
    ----------
    areaid: :class:`int`
        The Garlandtools Data area ID.
    patch: :class:`Expansion`
        The Final Fantasy Expansion the Node is located in.
    type: :class:`int`
        The Type of Node, Logging, Harvesting, Mining and Quarrying.
    points: :class:`list[IDCount]`
        UNK...
    items: :class:`list[Item]`
        A list of available items from the Node.
    bonus: :class:`list[int]`
        Any bonus "buffs" from the node.
    zoneid: :class:`int`
        The Zone ID.
    radius: :class:`int`
        How large of a spawn area around the coords the Node can spawn.
    coords: :class:`list[float]`
        The centerpoint for the spawn area of Nodes.
    lvl: :class:`int`
        The level of the Node.
    zone_name: :class:`Optional[PlaceName]`
        The name of the Zone as :class:`PlaceName`.
    area_name: :class:`str`
        The name of the Sub Area of the Zone, aka `Node['name']`
    node_id: :class:`int`
        The original `Node['id']` value.

    """

    areaid: int
    patch: Expansion
    type: int
    points: list[IDCount]
    items: list[Item]
    bonus: list[int]
    zoneid: int
    radius: int
    coords: list[float]
    lvl: int

    zone_name: PlaceName | str
    area_name: str
    "The name of the Map/Zone aka `Node['name']`"
    node_id: int
    "The original `Node['id']` value."
    _parent: Gathering

    __slots__ = ("areaid", "bonus", "coords", "id", "items", "lvl", "name", "patch", "points", "radius", "type", "zoneid")

    def __lt__(self, other: object) -> bool:  # noqa: D105
        return isinstance(other, self.__class__) and self.patch == other.patch and self.lvl < other.lvl

    def __eq__(self, other: object) -> bool:  # noqa: D105
        return isinstance(other, self.__class__) and self.patch == other.patch and self.lvl == other.lvl

    def __hash__(self) -> int:  # noqa: D105
        return hash(self)

    def __init__(self, data: Node, *, gathering: Gathering, **kwargs: Unpack[ObjectParams]) -> None:
        """Build your :class:`GatheringNode` object.

        Parameters
        ----------
        data: :class:`Node`
            The GarlandTools Node information as a JSON dict.
        gathering: :class:`Gathering`
            The :class:`Gathering` object or Item the Node information belongs to.
        **kwargs: :class:`Unpack[ObjectParams]`
            Any additional functionality such as a :class:`Angler` object or :class:`UniversalisAPI` object.
            - By default the :class:`Moogle` object is required for functionality sake.

        """
        super().__init__(data=data, moogle=kwargs["moogle"])
        self._repr_keys = ["zone_name", "area_name", "lvl", "coords", "garland_tools_url"]
        self._parent = gathering
        self.items = []

        for key in self.__slots__:
            value: Optional[int | str | float | list[float] | list[int] | list[dict[str, int]]] = data.get(key, None)
            if value is None:
                continue
            if key == "zoneid" and isinstance(value, int):
                try:
                    self.zone_name = self._moogle._get_place_name(place_id=value)
                except MoogleLookupError:
                    LOGGER.warning("<%s> | Failed to find place name. | ID: %s", __class__.__name__, value)
                    self.zone_name = str(value)
                    continue
            elif key == "id" and isinstance(value, int):
                self.node_id = value
            elif key == "name" and isinstance(value, str):
                self.area_name = value
            elif key == "items" and isinstance(value, list):
                items: list[dict[str, int]] = data.get("items", [])
                for entry in items:
                    item_id: int | None = entry.get("id", None)
                    if item_id is None:
                        continue

                    try:
                        temp: Item = self._moogle.get_item(item=str(item_id), limit_results=1)
                        self.items.append(temp)
                    except MoogleLookupError:
                        LOGGER.warning("<%s> | Failed to find item. | item: %s", __class__.__name__, value)
                        continue

            elif key == "patch" and isinstance(value, (float, int)):
                if int(value) == 0:
                    self.patch = Expansion(2)
                else:
                    self.patch = Expansion(value=int(value))

            else:
                setattr(self, key, value)

    @property
    def garland_tools_url(self) -> str:
        """A url link to the Node on Garland Tools."""
        return f"https://www.garlandtools.org/db/#node/{self.node_id}"


class PlaceName(Object):
    """A represensation of a Final Fantasy 14 location.

    Attributes
    ----------
    name: :class:`str`
        The name of the Final Fantasy 14 place.

    """

    name: str

    __slots__ = ("name",)

    def __init__(self, data: PlaceNameData, **kwargs: Unpack[ObjectParams]) -> None:
        """Build your Place Name object.

        Parameters
        ----------
        data: :class:`PlaceNameData`
            The JSON data.
        **kwargs: :class:`Unpack[ObjectParams]`
            Any additional functionality such as a :class:`Angler` object or :class:`UniversalisAPI` object.
            - By default the :class:`Moogle` object is required for functionality sake.

        """
        super().__init__(data=data, moogle=kwargs["moogle"])
        self._repr_keys = ["name"]
        self.name = data.get("name", None)


class SuggestedPrice:
    """A represensation of the data from `get_suggested_price`.

    Attributes
    ----------
    name: :class:`str`
        The
    item_id: :class:`int`
        The Final Fantasy 14 item ID.
    item_quality: :class:`ItemQuality`, optional
            The quality of the Item to query, by default `<ItemQuality>.NQ`.
    world_or_dc: :class:`DataCenter | World`, optional
        The Final Fantasy 14 World or Datacenter to query your results for, by default `<UniversalisAPI>.datacenter`.
        - The default is a datacenter for the library, `<DataCenter>.Crystal`.
    num_listings: :class:`int`, optional
        The number of listing results for the query, by default 10.
    current_metrics: :class:`SuggestedPriceMetrics`
        The metrics information based upon `CurrentDataEntries`.
    history_metrics: :class:`SuggestedPriceMetrics`
        The metrics information based upon the `HistoryDataEntries`.
    stacksize: :class:`str`
        The Optimal stacksize calculated.

    """

    name: str
    item_id: int
    item_quality: Literal["HQ", "NQ"]
    world_or_dc: str
    num_of_listings: int
    current_metrics: SuggestedPriceMetrics
    history_metrics: SuggestedPriceMetrics
    stacksize: str

    def __init__(
        self,
        name: str,
        item_id: int,
        item_quality: Literal["HQ", "NQ"],
        world_or_dc: DataCenter | World | str,
        num_of_listings: int,
        current_metrics: SuggestedPriceMetrics,
        history_metrics: SuggestedPriceMetrics,
        stacksize: str,
    ) -> None:
        self.name = name
        self.item_id = item_id
        self.item_quality = item_quality
        if isinstance(world_or_dc, (DataCenter, World)):
            self.world_or_dc = world_or_dc.name
        else:
            self.world_or_dc = world_or_dc
        self.num_of_listings = num_of_listings
        self.current_metrics = current_metrics
        self.history_metrics = history_metrics
        self.stacksize = stacksize

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        temp: list[str] = []
        temp.extend((
            f"Price Insight for: {self.name} ({self.item_id}) | Item Quality: {self.item_quality} | World: {self.world_or_dc} | Sample Size: {self.num_of_listings}",  # noqa: E501
            f"- Current Highest Price/Unit: {self.current_metrics.highest_price} | Lowest Price/Unit: {self.current_metrics.lowest_price}",
            f"- Current Mean Price/Unit: {self.current_metrics.mean_price} | Price/Unit diff over Mean: {self.current_metrics.diff_price} | {self.current_metrics.diff_price / self.current_metrics.highest_price % 2 * 100:.2f}%",  # noqa: E501
            f"- History Highest Price/Unit: {self.history_metrics.highest_price} | Lowest Price/Unit: {self.history_metrics.lowest_price}",
            f"- History Mean Price/Unit: {self.history_metrics.mean_price} | Price/Unit diff over Mean: {self.history_metrics.diff_price} | {self.history_metrics.diff_price / self.history_metrics.highest_price % 2 * 100:.2f}%",  # noqa: E501
            f"- Common stack sizes (Optimal | Current Mode | History Mode): {self.stacksize} | {self.current_metrics.stacksize} | {self.history_metrics.stacksize}",  # noqa: E501
        ))
        return "\n".join(temp)


class SuggestedPriceMetrics(NamedTuple):
    """The metrics related to `CurrentDataEntries` or `HistoryDataEntries`.

    Attributes
    ----------
    highest_price: :class:`int`
        The highest price in the listings.
    lowest_price: :class:`int`
        The lowest price in the listings.
    mean_price: :class:`float`
        Also known as the "average".
    diff_price: :class:`float`
        The price difference between the current highest and the `mean_price` or average.
    stacksize: :class:`str`
        The most frequent stacksize in the listings.

    """

    highest_price: int
    lowest_price: int
    mean_price: float
    diff_price: float
    stacksize: str

    # def __init__(self, highest_price: int, lowest_price: int, mean_price: float, diff_price: float, stacksize: str) -> None:
    #     self.highest_price = highest_price
    #     self.lowest_price = lowest_price
    #     self.mean_price = mean_price
    #     self.diff_price = diff_price
    #     self.stacksize = stacksize
