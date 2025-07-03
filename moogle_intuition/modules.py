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

import csv
import json
import logging
from io import TextIOWrapper
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Literal, Optional, Self, Union, Unpack, overload

import aiohttp
from thefuzz import fuzz  # type: ignore[reportMissingStubFile]
from universalis import CurrentData, HistoryData, ItemQuality, UniversalisAPI

from moogle_intuition.errors import MoogleLookupError
from moogle_intuition.ff14angler._types import FishingData

from ._enums import CraftType, EquipSlotCategory, FishingSpotCategory, InventoryLocation
from .ff14angler import Angler, AnglerBaits, AnglerFish

if TYPE_CHECKING:
    from collections.abc import Iterator
    from types import TracebackType

    from aiohttp import ClientResponse
    from aiohttp.client import _RequestOptions as AiohttpRequestOptions  # pyright: ignore[reportPrivateUsage]

    from moogle_intuition.ff14angler._types import FishingData

    from ._types import (
        AllagonToolsInventoryCSV,
        CSVParseParams,
        CurMarketBoardParams,
        FishingSpotData,
        FishParameterData,
        GatheringItemData,
        GatheringItemLevelData,
        HistMarketBoardParams,
        ItemData,
        ItemLevelData,
        ObjectParams,
        PlaceNameData,
        RecipeData,
        RecipeLevelData,
        RecipeLookUpData,
        SpearFishingItemData,
        SpearFishingNotebookData,
    )

    DataTypeAliases = Union[
        ItemData,
        GatheringItemData,
        GatheringItemLevelData,
        FishingSpotData,
        RecipeLookUpData,
        RecipeData,
        RecipeLevelData,
        FishParameterData,
        PlaceNameData,
        SpearFishingItemData,
        SpearFishingNotebookData,
    ]


__all__ = ("ATOOLS_OMIT_INV_LOCS", "IGNORED_KEYS", "PRE_FORMATTED_KEYS", "URLS", "Builder", "Item", "Moogle")

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

ATOOLS_OMIT_INV_LOCS: list[InventoryLocation] = [
    InventoryLocation.free_company,
    InventoryLocation.currency,
    InventoryLocation.crystals,
    InventoryLocation.glamour_chest,
    InventoryLocation.market,
    InventoryLocation.armoire,
    InventoryLocation.armory,
    InventoryLocation.equipped_gear,
]

ATOOLS_OMIT_ITEM_NAMES: list[str] = []


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
        LOGGER.debug("<%s.__init__()> data: %s", __class__.__name__, data)

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        try:
            return f"\n\n__{self.__class__.__name__}__\n" + "\n".join([
                f"{e}: {getattr(self, e)}" for e in self._repr_keys if e.startswith("_") is False
            ])
        except AttributeError:
            return f"\n\n__{self.__class__.__name__}__\n" + "\n".join([
                f"{e}: {getattr(self, e)}" for e in sorted(self.__dict__) if e.startswith("_") is False
            ])


class Generic:
    """A Generic object to house attributes and data that `<Moogle>` and `<Builder>` will share and populate."""

    _session: Optional[aiohttp.ClientSession]
    session: Optional[aiohttp.ClientSession]

    # Item Handling.
    _items: dict[str, DataTypeAliases]
    # I am storing "item id" : "name"
    _items_ref: dict[str | int, str | int]
    # Recipe Handling.
    # I am storing "Recipe ID" : "Item Result ID"
    # recipe_dict: dict[str, int]  # ? Unsure why this was commented out, need to validate usage.
    _recipes: dict[str, DataTypeAliases]
    _recipes_ref: dict[str | int, str | int]

    # Job Recipe Table
    _recipe_lookups: dict[str, DataTypeAliases]

    # Recipe Level Table
    _recipe_levels: dict[str, DataTypeAliases]

    # Gatherable Items Handling.
    # Using flipped keys in the item_dict for faster lookup of an item.
    _gathering_items: dict[str, DataTypeAliases]
    _gathering_items_ref: dict[str | int, str | int]
    _gathering_item_levels: dict[str, DataTypeAliases]

    # Fishing Related
    _fish_params: dict[str, DataTypeAliases]
    # This is stored with FLIPPED key to values ("Item ID" : "Dict Index")
    _fish_params_ref: dict[str | int, str | int]
    _fishing_spot: dict[str, DataTypeAliases]

    # Spearfishing Related
    _spearfishing_items: dict[str, DataTypeAliases]
    # This is stored with FLIPPED key to values ("item id" : "Dict Index")
    _spearfishing_items_ref: dict[str | int, str | int]
    _spearfishing_notebook: dict[str, DataTypeAliases]

    # Location Information
    _place_names: dict[str, DataTypeAliases]


class Builder(Generic):
    """Basic class to handle `<Moogle>` data building and parsing."""

    def __init__(self, session: Optional[aiohttp.ClientSession] = None) -> None:
        """Create the `<Builder>` class.

        Parameters
        ----------
        session: :class:`Optional[aiohttp.ClientSession]`, optional
            A pre-existing `<aiohttp.ClientSession>` object if applicable, by default None.

        """
        self.session = session
        self._session = None

    async def clean_up(self) -> None:
        """Cleans up any open resources."""
        LOGGER.debug("<%s._clean_up> | Closing open `aiohttp.ClientSession` %s", __class__.__name__, self._session)
        if self._session is not None:
            await self._session.close()

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

    def csv_parse(
        self,
        path: Path,
        *,
        convert_pound: bool = True,
        format_keys: bool = True,
    ) -> tuple[dict[str, dict[str, int | str | list[int] | bool | None]], list[str], list[str]]:
        """Parse a CSV file, breaking out the Keys and Types to be return as a tuple for turning into Typed Dicts.

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

    # TODO(@k8thekat): - Better docstring.. explaniation is.. bad.
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

    _items_cache: dict[str, Item]

    def __init__(
        self,
        session: Optional[aiohttp.ClientSession] = None,
        universalis: Optional[UniversalisAPI] = None,
        angler: Optional[Angler] = None,
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

        """
        self._builder = Builder(session=session)

        if universalis is None:
            self._universalis = UniversalisAPI(session=session)

        if angler is None:
            self._angler = Angler(session=session)

        # Create our empty itemcache.
        self._items_cache = {}

    async def __aenter__(self) -> Self:  # noqa: D105
        try:
            await self.build()
        # TODO(@k8thekat): - See what possible Exceptions could be raised and handle properly.
        # ConnectionError
        # FileNotFoundError or Exists
        except Exception as e:  # noqa: BLE001
            LOGGER.error("<%s.%s> | Failed to Build. | Exception: %s", __class__.__name__, "build", e)  # noqa: TRY400
        return self

    async def __aexit__(  # noqa: D105
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        await self.clean_up()

    async def clean_up(self) -> None:
        """Handles deconstruction of `<Moogle>`."""
        LOGGER.debug("<%s._clean_up> | Closing any open `aiohttp.ClientSession`", __class__.__name__)
        await self._universalis.clean_up()
        await self._builder.clean_up()
        await self._angler.clean_up()

    async def build(self) -> Self:
        """Builds the required arrays and library's for `<Moogle>` to function.

        Returns
        -------
        :class:`Self`:
            A :class:`Moogle` object.

        """
        await self._builder.file_validation()
        self._items: dict[str, DataTypeAliases] = self._load_json(path=DATA_PATH.joinpath("item.json"))

        self._items_ref: dict[str | int, str | int] = self._reference_dict(data=self._items, value_get="name")

        # Recipe related dict/JSON
        self._recipes = self._load_json(path=DATA_PATH.joinpath("recipe.json"))
        self._recipes_ref = self._reference_dict(data=self._recipes, value_get="item_result")
        self._recipe_lookups = self._load_json(path=DATA_PATH.joinpath("recipe_lookup.json"))
        # self._recipe_levels = self._load_json(path=DATA_PATH.joinpath("recipe_level.json"))

        # Fishing related dict/JSON
        self._fish_params: dict[str, DataTypeAliases] = self._load_json(path=DATA_PATH.joinpath("fish_parameter.json"))
        # { item_id : dict ref id for `fish_parameter.json`}
        self._fish_params_ref: dict[str | int, str | int] = self._reference_dict(
            data=self._fish_params,
            value_get="item",
            flip_key_value=True,
        )
        self._fishing_spot: dict[str, DataTypeAliases] = self._load_json(path=DATA_PATH.joinpath("fishing_spot.json"))

        # Spearfishing related dict/JSON
        self._spearfishing_items: dict[str, DataTypeAliases] = self._load_json(path=DATA_PATH.joinpath("spearfishing_item.json"))
        self._spearfishing_items_ref: dict[str | int, str | int] = self._reference_dict(
            data=self._spearfishing_items,
            value_get="item",
            flip_key_value=True,
        )
        self._spearfishing_notebook: dict[str, DataTypeAliases] = self._load_json(path=DATA_PATH.joinpath("spearfishing_notebook.json"))

        # Gathering related dict/JSON.
        self._gathering_items: dict[str, DataTypeAliases] = self._load_json(path=DATA_PATH.joinpath("gathering_item.json"))
        self._gathering_items_ref: dict[str | int, str | int] = self._reference_dict(
            data=self._gathering_items,
            value_get="item",
            flip_key_value=True,
        )
        self._gathering_item_levels: dict[str, DataTypeAliases] = self._load_json(path=DATA_PATH.joinpath("gathering_item_level.json"))

        # Location related JSON
        self._place_names: dict[str, DataTypeAliases] = self._load_json(path=DATA_PATH.joinpath("place_name.json"))

        # FF14 Angler related dict.
        locs: tuple[dict[str, int], dict[int, str]] | None = await self._angler.get_location_id_mapping(include_inverted_map=True)
        if locs is not None:
            self._angler_loc_map = locs[0]
            self._angler_invert_loc_map = locs[1]
        self._angler_fish_map = await self._angler.get_fish_id_mapping()

        return self

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

    def _update_cache(self, item: Item) -> None:
        self._items_cache.update({str(item.id): item})

    @overload
    def get_item(self, *, item: str, limit_results: Literal[1], match: int = ...) -> Item: ...

    @overload
    def get_item(self, *, item: str, limit_results: int = ...) -> list[Item]: ...

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
        MoogleLookupError
            If we are unable to find the item parameter provided for any reason.

        """
        LOGGER.debug("<%s.%s> | Searching... query: %s |", __class__.__name__, "get_item", item)
        results: list[Item] = []

        # item: 10373 # magitek repair materials.
        if item.isnumeric():
            # So let's try to check the cache first for a matching item assuming we have an `id` value.
            cache: Optional[Item] = self._items_cache.get(item, None)
            if isinstance(cache, Item):
                return cache
            # TODO(@k8thekat): If I type hint `res`, parts of the code become unreachable and I need to understand why.
            res = self._items.get(item, None)
            if res is not None and "level_item" in res:
                cache = Item(data=res, moogle=self, universalis=self._universalis)
                self._items_cache[item] = cache
                return cache
            raise MoogleLookupError(item, "item", "get_item", self)

        # item_name's we have to get a reference since we are supporting partial string matching.
        # This handles the edge case of a perfect match, albeit unlikely.
        ref: Optional[str | int] = self._items_ref.get(item, None)
        if ref is not None:
            res = self._items.get(str(ref), None)
            if res is not None and "item_level" in res:
                cache = Item(data=res, moogle=self, universalis=self._universalis)
                self._items_cache[item] = cache
                return cache

        # if the item_name wasn't in the ref list we would do our partial matching below.
        # we take our list of item_ids that partially matched and get our data/objects.
        matches = self._partial_match(item, match=match)
        LOGGER.debug("<%s.%s> | Searching... %s partial matches.", __class__.__name__, "get_item", len(matches))
        for entry in matches:
            # Let's try to find our partial matches in our cache too.
            cache = self._items_cache.get(entry, None)
            LOGGER.debug("<%s.%s> | Checking item cache.. | item: %s", __class__.__name__, "get_item", entry)
            if cache is not None:
                LOGGER.debug("<%s.%s> | Found item in cache.. | item: %s", __class__.__name__, "get_item", entry)
                results.append(cache)
                continue
            # Not in cache; so let's get them from our array of data.
            # If we don't find it, we will skip it.. :shrug:

            res = self._items.get(entry, None)
            if res is not None and "level_item" in res:
                LOGGER.debug("<%s.%s> | Found item, building data. | item: %s", __class__.__name__, "get_item", entry)
                cache = Item(data=res, moogle=self, universalis=self._universalis)
                self._items_cache[item] = cache
                results.append(cache)

        if len(results) == 0:
            raise MoogleLookupError(item, "item", "get_item", self)

        return results[0] if limit_results == 1 else results[:limit_results]

    def _partial_match(self, query: str, match: int = 80) -> list[str]:
        # This section assumes we are using `item_name` given the above if check for `item_id`.
        # matches will be a list of "item_id's" that matched our query string.
        matches: list[str] = []
        for key, value in self._items_ref.items():  # { item_id : item_name }
            LOGGER.debug(
                "Searching... key: %s | value: %s | query: %s",
                key,
                value,
                query,
            )

            _value = str(value) if isinstance(value, int) else value

            ratio: int = fuzz.partial_ratio(s1=_value.lower(), s2=query.lower())  # pyright: ignore[reportUnknownMemberType]

            # We have a partial match, but not exact. So we can either
            # look the item up and see if we can find it, or return the key.
            if ratio >= match:
                LOGGER.debug(
                    "<%s.%s> | Searching... | key: %s | value: %s | ratio: %s | query: %s ",
                    __class__.__name__,
                    "_partial_match",
                    key,
                    _value,
                    ratio,
                    query,
                )
                matches.append(str(key))
                continue

        if len(matches) == 0:
            raise MoogleLookupError(query, "query", "_partial_match", self)
        LOGGER.debug("<%s.%s> | Returning %s partial matches", __class__.__name__, "_partial_match", len(matches))
        return matches

    def _get_item_job_recipes(self, item_id: int) -> JobRecipe:
        LOGGER.debug(
            "<%s.%s> | Searching... Job Recipe by Item ID: %s | Entries: %s",
            __class__.__name__,
            "get_item_job_recipes",
            item_id,
            len(self._recipe_lookups),
        )
        data: Optional[DataTypeAliases] = self._recipe_lookups.get(str(item_id), None)
        if data is None or "CRP" not in data:
            raise MoogleLookupError(str(item_id), "item_id", "get_item_job_recipes", self)

        return JobRecipe(data=data, moogle=self)

    def _get_recipe(self, recipe_id: str) -> Recipe:
        # I am storing str "Recipe ID" : int "Item Result ID"
        LOGGER.debug("<%s.%s> | Searching... recipe_id: %s | entries: %s", __class__.__name__, "_get_recipe", recipe_id, len(self._recipes))
        data: Optional[DataTypeAliases] = self._recipes.get(recipe_id, None)
        if data is None or "item_result" not in data:
            raise MoogleLookupError(recipe_id, "recipe_id", "_get_recipe", self)
        return Recipe(data=data, moogle=self)

    def _get_gathering_level(self, level_id: int) -> GatheringItemLevel:
        LOGGER.debug(
            "<%s.%s> | Searching... gathering_level_id: %s | entries: %s",
            __class__.__name__,
            "_get_gathering_level",
            level_id,
            len(self._gathering_item_levels),
        )
        data: Optional[DataTypeAliases] = self._gathering_item_levels.get(str(level_id), None)
        # TODO(@k8thekat): - In theory all 3 dict key values are present to build GatheringItemLevel object.
        # so I am unsure WHAT or Why it's complaining.
        if data is None or ("id" not in data and "stars" not in data and "gathering_item_level" not in data):
            raise MoogleLookupError(str(level_id), "level_id", "_get_gathering_level", self)
        return GatheringItemLevel(data=data, moogle=self)

    def _get_fishing_spot(self, spot_id: int) -> FishingSpot:
        LOGGER.debug(
            "<%s.%s> | Searching... spot_id: %s | entries: %s",
            __class__.__name__,
            "_get_fishing_spot",
            spot_id,
            len(self._fishing_spot),
        )
        data: Optional[DataTypeAliases] = self._fishing_spot.get(str(spot_id), None)
        if data is None or "fishing_spot_category" not in data:
            raise MoogleLookupError(str(spot_id), "spot_id", "_get_fishing_spot", self)
        return FishingSpot(data=data, moogle=self)

    def _get_spearfishing_spot(self, record_type: int) -> SpearFishingNotebook:
        LOGGER.debug(
            "<%s.%s> | Searching... record_type: %s | entries: %s",
            __class__.__name__,
            "_get_spearfishing_spot",
            record_type,
            len(self._spearfishing_notebook),
        )
        data: Optional[DataTypeAliases] = self._spearfishing_notebook.get(str(record_type), None)
        if data is None or "territory_type" not in data:
            raise MoogleLookupError(str(record_type), "record_type", "_get_spearfishing_spot", self)
        return SpearFishingNotebook(data=data, angler=self._angler, moogle=self)

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

    def _is_fishable(self, item_id: int) -> Fishing:
        LOGGER.debug(
            "<%s.%s> | Searching... item_id: %s | entries: %s ",
            __class__.__name__,
            "_is_fishable",
            item_id,
            len(self._fish_params_ref),
        )

        key: Optional[str | int] = self._fish_params_ref.get(item_id, None)
        if key is None:
            raise MoogleLookupError(str(item_id), "item_id", "_is_fishable", self)

        data: Optional[DataTypeAliases] = self._fish_params.get(str(key), None)
        if data is None or "fishing_spot" not in data:
            raise MoogleLookupError(str(key), "item_id", "_is_fishable", self)
        return Fishing(data=data, angler=self._angler, moogle=self)

    def _is_spearfishing(self, item_id: int) -> SpearFishing:
        LOGGER.debug(
            "<%s.%s> | Searching... item_id: %s | entries: %s ",
            __class__.__name__,
            "_is_spearfishing",
            item_id,
            len(self._spearfishing_items_ref),
        )
        key: Optional[str | int] = self._spearfishing_items_ref.get(item_id, None)
        if key is None:
            raise MoogleLookupError(str(item_id), "item_id", "_is_spearfishing", self)
        data: Optional[DataTypeAliases] = self._spearfishing_items.get(str(key), None)
        if data is None or "is_visible" not in data:
            raise MoogleLookupError(str(key), "item_id", "_is_spearfishing", self)
        return SpearFishing(data=data, angler=self._angler, moogle=self)

    def _is_gatherable(self, item_id: int) -> GatheringItem:
        LOGGER.debug(
            "<%s.%s> | Searching... item_id: %s | entries: %s ",
            __class__.__name__,
            "_is_gatherable",
            item_id,
            len(self._gathering_items_ref),
        )
        key: Optional[str | int] = self._gathering_items_ref.get(item_id, None)
        if key is None:
            raise MoogleLookupError(str(item_id), "item_id", "_is_gatherable", self)
        data: Optional[DataTypeAliases] = self._gathering_items.get(str(key), None)

        # TODO(@k8thekat): - In theory the key values are present to build GatheringItem object.
        # so I am unsure WHAT or Why it's complaining.
        # Only FishParameter has the key `achievement_credit`; so checking FOR that key should validate the data.
        if data is None or ("achievement_credit" in data and "quest" in data):
            raise MoogleLookupError(str(key), "item_id", "_is_gatherable", self)
        return GatheringItem(data=data, moogle=self)

    async def get_current_marketboard(
        self,
        items: str | list[Item | str],
        **kwargs: Unpack[CurMarketBoardParams],
    ) -> list[CurrentData] | CurrentData:
        """Get Universalis current marketboard data.

        .. note::
            If an invalid entry in `items` is found, `<UniversalisAPI>` will omit those entries.

        Parameters
        ----------
        items: :class:`Optional[list[str | int] | list[FFXIVItem]]`, optional
            A list of item_names, by default None.
        **kwargs: :class:`Unpack[MarketBoardParams]`
            Any additional params to pass to `<UniversalisAPI.get_bulk_current_data()>`.

        Returns
        -------
        :class:`list[CurrentData] | CurrentData | None`
            The Universalis JSON data represented as a class.

        """
        query: list[str] = []
        # Allow handling of Item names dynamically.
        if isinstance(items, str):
            query.append(items)
        else:
            for entry in items:
                # Just in case we fail to find the item.
                if isinstance(entry, Item):
                    query.append(str(entry.id))
                    continue
                query.append(entry)

        LOGGER.debug(
            "<%s.%s> | Universalis market search. | items: %s | entries: %s",
            __class__.__name__,
            "get_current_marketboard",
            items,
            len(query),
        )
        return await self._universalis.get_bulk_current_data(items=query, **kwargs)

    async def get_history_marketboard(
        self,
        items: str | list[Item | str],
        **kwargs: Unpack[HistMarketBoardParams],
    ) -> list[HistoryData] | HistoryData:
        """Get Universalis history marketboard data.

        .. note::
            If an invalid entry in `items` is found, `<UniversalisAPI>` will omit those entries.

        Parameters
        ----------
        items: :class:`Optional[list[str | int] | list[FFXIVItem]]`, optional
            A list of item_names, by default None.
        **kwargs: :class:`Unpack[MarketBoardParams]`
            Any additional params to pass to `<UniversalisAPI.get_bulk_current_data()>`.

        Returns
        -------
        :class:`list[HistoryData] | HistoryData | None`
            The Universalis JSON data represented as a class.

        """
        query: list[str] = []
        # Allow handling of Item names dynamically.
        if isinstance(items, str):
            query.append(items)
        else:
            for entry in items:
                # Just in case we fail to find the item.
                if isinstance(entry, Item):
                    query.append(str(entry.id))
                    continue
                query.append(entry)

        LOGGER.debug(
            "<%s.%s> | Universalis market search. | items: %s | entries: %s",
            __class__.__name__,
            "get_current_marketboard",
            items,
            len(query),
        )
        return await self._universalis.get_bulk_history_data(items=query, **kwargs)

    def _parse_atools_csv(
        self,
        data: bytes | str,
        *,
        omit_item_names: Optional[list[str]] = None,
        omit_inv_locs: Optional[list[InventoryLocation]] = None,
    ) -> list[InventoryItem]:
        r"""Parse a Allagon Tools Inventory CSV.

        Take's the `bytes` or `str` array and returns a list of :class:`FFXIVInventoryItem`.
        - These objects are a smaller reference of :class:`FFXIVItem` as they contain character specific information.

        Parameters
        ----------
        data: :class:`bytes | str `
            The source of the CSV file data. This assumes the data structure of the CSV file is using `\n` as a seperator for rows.
        omit_inv_locs: :class:`Optional[list[InventoryLocationEnum]]`, optional
            The inventory location of the item to omit from our returned list, by default is None.
            - If `None`, will use the global `ATOOLS_OMIT_INV_LOCS`.
        omit_item_names: :class:`Optional[list[str]]`, optional
            Any item names to omit such as `Free Company Credits` as it's not apart of the XIV Item.json, by default [].
            - If `None`, will use the global `ATOOLS_OMIT_ITEM_NAMES`.

        Returns
        -------
        :class:`list[FFXIVInventoryItem]`
            Returns a list of converted CSV data into FFXIVInventoryItem.

        """
        if isinstance(data, bytes):
            data = data.decode(encoding="utf-8")
        keys = data.split("\n")[0]
        file = data

        if omit_inv_locs is None:
            omit_inv_locs = ATOOLS_OMIT_INV_LOCS

        if omit_item_names is None:
            omit_item_names = ATOOLS_OMIT_ITEM_NAMES

        # Keys= "Favorite?", "Icon", "Name", "Type", "Total Quantity Available", "Source", "Inventory Location"
        # We know the structure of res to be Iterator[AllagonToolsInventoryCSV].
        _keys: list[str] = keys.strip().replace("?", "").lower().replace(" ", "_").split(",")
        res: Iterator[AllagonToolsInventoryCSV] = csv.DictReader(file, fieldnames=_keys)  # type: ignore[reportAssignmentType]
        LOGGER.debug(
            "<%s.%s> | Reading CSV data. | keys: %s | data size: %s",
            __class__.__name__,
            "_parse_atools_csv",
            _keys,
            len(file),
        )
        inventory: list[InventoryItem] = []
        for entry in res:
            if entry["name"].lower().startswith("free company credits") or entry["name"].lower() in omit_item_names:
                LOGGER.debug("<%s.%s> | Skipping entry. | entry: %s", __class__.__name__, "_parse_atools_csv", entry["name"])
                continue
            # Given we are using item names; there is a "small" chance it will return incorrect items
            # but it should find everything as it's directly from the game.
            try:
                item_id: Item = self.get_item(item=entry["name"], limit_results=1, match=95)
            except MoogleLookupError:
                LOGGER.warning("<%s.%s> | Failed to lookup item name. | item: %s", __class__.__name__, "_parse_atools_csv", entry["name"])
                continue

            item = InventoryItem(item_id=item_id.id, data=entry)
            # If we have inventory locations to omit and our item is NOT in that list of locations, lets add it to our results.
            if item.location not in omit_inv_locs:
                inventory.append(item)

        if isinstance(file, TextIOWrapper):
            file.close()
        return inventory


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
    equip_slot_category: :class:`Optional[EquipSlotCategory]`
        The equipment slot the item belongs to, if applicable.
    stack_size: :class:`int`
        The max stack size of the item.
    is_unique: :class:`bool`
        If the item is unique or not.
    is_untradable: :class:`bool`
        If the item is un-tradeable or not.
    is_indisposable: :class:`bool`
        If the item is in-disposable or not.
    can_be_hq: :class:`int`
        If the item can be high-quality or not.
    dye_count: :class:`int`
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

    Properties
    ----------
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
        Cached current marketboard data, if applicable.
    mb_history: :class:`Optional[HistoryData]`
        Cached history marketboard data, if applicable.

    """

    _ff14angler_data: Any
    _recipe: Optional[JobRecipe]
    _fishing: Optional[Fishing]
    _spear_fishing: Optional[SpearFishing]
    _gathering: Optional[GatheringItem]

    _mb_current: Optional[CurrentData]
    _mb_history: Optional[HistoryData]

    id: int
    description: Optional[str]
    name: str
    level_item: ItemLevelData
    equip_slot_category: Optional[EquipSlotCategory]
    stack_size: int
    is_unique: bool
    is_untradable: bool
    is_indisposable: bool
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
        "id",
        "is_advanced_melding_permitted",
        "is_collectable",
        "is_glamourous",
        "is_indisposable",
        "is_unique",
        "is_untradable",
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
            - By default the :class:`Moogle` object is required for functionality sake.

        """
        super().__init__(data=data, moogle=kwargs["moogle"])
        # This list to control the amount of information we return via `__str__()` and `__repr__()` dunder methods.
        self._repr_keys = ["id", "name"]
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
                    self.equip_slot_category = None

            else:
                setattr(self, key, value)
        try:
            self._gathering = self._moogle._is_gatherable(self.id)
        except MoogleLookupError:
            self._gathering = None
        try:
            self._recipe = self._moogle._get_item_job_recipes(self.id)
        except MoogleLookupError:
            self._recipe = None
        try:
            self._fishing = self._moogle._is_fishable(self.id)
        except MoogleLookupError:
            self._fishing = None
        try:
            self._spear_fishing = self._moogle._is_spearfishing(self.id)
        except MoogleLookupError:
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
        """Any recipe information related to the item, if applicable.

        Returns
        -------
        :class:`Optional[FFXIVJobRecipe]`
            Returns any related recipe information as an object representing the data from recipe.json.

        """
        return self._recipe

    @property
    def fishing(self) -> Optional[Fishing]:
        """Any fishing information related to the item, if applicable.

        Returns
        -------
        :class:`Optional[Fishing]`
            Returns any related fishing information as an object representing the data from fishing_spot.json.

        """
        return self._fishing

    @property
    def spear_fishing(self) -> Optional[SpearFishing]:
        """Any spearfishing information related to the item, if applicable.

        Returns
        -------
        :class:`Optional[SpearFishing]`
            Returns any related spear fishing information as an object representing the data from spearfishing_item.json.

        """
        return self._spear_fishing

    @property
    def gathering(self) -> Optional[GatheringItem]:
        """Any gathering information related to the item, if applicable.

        Returns
        -------
        :class:`Optional[GatheringItem]`
            Returns any related gathering information as an object representing the data from gathering_item.json.

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

    async def get_current_marketboard(self, **kwargs: Unpack[CurMarketBoardParams]) -> CurrentData:
        """Retrieve the current Marketboard data for this item, while also setting the `<Item.mb_current>` property.

        Parameters
        ----------
        **kwargs: :class:`Unpack[MarketBoardParams]`
            Any additional parameters to change the results of the data.

        Returns
        -------
        :class:`CurrentData`
            The JSON response converted into a :class:`CurrentData` object.

        """
        self._mb_current = await self._moogle._universalis.get_current_data(item=self.id, **kwargs)
        return self._mb_current

    async def get_history_marketboard(self, **kwargs: Unpack[HistMarketBoardParams]) -> HistoryData:
        """Retrieve the Marketboard History data for this item, while also setting the `<Item.mb_history>` property.

        Parameters
        ----------
        **kwargs: :class:`Unpack[MarketBoardParams]`
            Any additional parameters to change the results of the data.

        Returns
        -------
        :class:`CurrentData`
            The JSON response converted into a :class:`HistoryData` object.

        """
        self._mb_history = await self._moogle._universalis.get_history_data(item=self.id, **kwargs)
        return self._mb_history


class JobRecipe(Object):
    """A represensation of Job specific information related to a Final Fantasy 14 Item.

    .. note::
        Each Disciple of Hand has an attribute and related :class:`Recipe` information, if applicable.


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

    __slots__ = ("ALC", "ARM", "BSM", "CRP", "CUL", "GSM", "LTW", "WVR")

    def __init__(self, data: RecipeLookUpData, **kwargs: Unpack[ObjectParams]) -> None:
        """Build your Job Recipe object.

        Parameters
        ----------
        data: :class:`RecipeLookUpData`
            The JSON data.
        **kwargs: :class:`Unpack[ObjectParams]`
            Any additional functionality such as a :class:`Angler` object or :class:`UniversalisAPI` object.
            - By default the :class:`Moogle` object is required for functionality sake.

        """
        super().__init__(data=data, moogle=kwargs["moogle"])
        for key in self.__slots__:
            value: Optional[str | int | bool] = data.get(key, None)
            if value is None:
                continue
            if isinstance(value, int) and value != 0:
                # This takes the value data and builds our FFXIVRecipe class from the raw JSON stored on our Moogle class.
                setattr(self, key, self._moogle._get_recipe(str(value)))


class Recipe(Object):
    """A representation of a Final Fantasy 14 Recipe.

    .. note::
        Inherits attributes and functions from :class:`Object`.


    Attributes
    ----------
    craft_type: :class:`Optional[CraftType]`, optional
        The Job this recipe belongs too, if applicable.
    recipe_level_table: :class:`RecipeLevelData`
        The characteristics and details about the recipe, such as difficulty and craftsmanship required.
    item_result: :class:`int`
        The item ID.
    amount_result: :class:`int`
        The number of items recieved after completing the crafting recipe.
    item_ingredient0: :class:`int`
        The Final Fantasy 14 item id for the ingredient of the recipe, if applicable.
    amount_ingredient0: :class:`int`
        The quantity required for the ingredient of the recipe, if applicable.
    item_ingredient1: :class:`int`
        The Final Fantasy 14 item id for the ingredient of the recipe, if applicable.
    amount_ingredient1: :class:`int`
        The quantity required for the ingredient of the recipe, if applicable.
    item_ingredient2: :class:`int`
        The Final Fantasy 14 item id for the ingredient of the recipe, if applicable.
    amount_ingredient2: :class:`int`
        The quantity required for the ingredient of the recipe, if applicable.
    item_ingredient3: :class:`int`
        The Final Fantasy 14 item id for the ingredient of the recipe, if applicable.
    amount_ingredient3: :class:`int`
        The quantity required for the ingredient of the recipe, if applicable.
    item_ingredient4: :class:`int`
        The Final Fantasy 14 item id for the ingredient of the recipe, if applicable.
    amount_ingredient4: :class:`int`
        The quantity required for the ingredient of the recip, if applicablee.
    item_ingredient5: :class:`int`
        The Final Fantasy 14 item id for the ingredient of the recipe, if applicable.
    amount_ingredient5: :class:`int`
        The quantity required for the ingredient of the recipe, if applicable.
    item_ingredient6: :class:`int`
        The Final Fantasy 14 item id for the ingredient of the recipe, if applicable.
    amount_ingredient6: :class:`int`
        The quantity required for the ingredient of the recipe, if applicable.
    item_ingredient7: :class:`int`
        The Final Fantasy 14 item id for the ingredient of the recipe, if applicable.
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

    craft_type: Optional[CraftType]
    recipe_level_table: RecipeLevelData
    item_result: int
    amount_result: int
    item_ingredient0: int
    amount_ingredient0: int
    item_ingredient1: int
    amount_ingredient1: int
    item_ingredient2: int
    amount_ingredient2: int
    item_ingredient3: int
    amount_ingredient3: int
    item_ingredient4: int
    amount_ingredient4: int
    item_ingredient5: int
    amount_ingredient5: int
    item_ingredient6: int
    amount_ingredient6: int
    item_ingredient7: int
    amount_ingredient7: int
    can_quick_synth: bool
    can_hq: bool
    status_required: int
    item_required: int
    is_specialization_required: int
    is_expert: bool

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

    def __init__(self, data: RecipeData, **kwargs: Unpack[ObjectParams]) -> None:
        """Build your Recipe object.

        Parameters
        ----------
        data: :class:`RecipeData`
            The JSON data.
        **kwargs: :class:`Unpack[ObjectParams]`
            Any additional functionality such as a :class:`Angler` object or :class:`UniversalisAPI` object.
            - By default the :class:`Moogle` object is required for functionality sake.

        """
        super().__init__(data=data, moogle=kwargs["moogle"])
        # This list to control the amount of information we return via `__str__()` and `__repr__()` dunder methods.
        self._repr_keys = ["craft_type", "item_result", "is_expert", "item_required", "amount_result"]
        self._repr_keys.extend([f"item_ingredient{idx}" for idx in range(8)])
        self._repr_keys.extend([f"amount_ingredient{idx}" for idx in range(8)])
        for key in self.__slots__:
            value: Optional[int | bool | str] = data.get(key, None)
            if value is None:
                continue
            if isinstance(value, int):
                if (
                    key in ["is_specialization_required", "item_result", "item_required"] or key.startswith("item_ingredient")
                ) and value != 0:
                    setattr(self, key, value)
                    # try:
                    #     setattr(self, key, self._moogle.get_item(item=str(value), limit_results=1))
                    # except MoogleLookupError:
                    #     LOGGER.warning("<%s> | Failed to find item. | item: %s", __class__.__name__, value)
                    #     setattr(self, key, value)

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
                setattr(self, key, value)


class ItemFish(Object):
    """Generic base object for handling FF14 Angler data and FFXIV item fish information.

    . note::
        Inherits attributes and functions from :class:`Object`.


    Attributes
    ----------
    item: :class:`int`
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

    item: int
    name: Optional[str]
    fishing_record_type: int

    # FF14 Angler website lookup information.
    # This value comes from `<Angler.fish_map>` array.
    angler_id: Optional[int]
    _angler_data: Optional[list[AnglerFish]]
    _angler: Angler

    def __init__(self, data: DataTypeAliases, angler: Angler, moogle: Moogle) -> None:
        """Generic object for bridging FF14Angler and Moogle.

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

        item_id = data.get("item")
        if self._moogle._angler_fish_map is not None and item_id is not None:
            name = self._moogle._items_ref.get(str(item_id), None)
            if name is None or isinstance(name, int):
                self.angler_id = None
                self.name = None
            else:
                self.name = name
                self.angler_id = self._moogle._angler_fish_map.get(name)

    @overload
    async def get_angler_data(self, *, best_chance: Literal[True]) -> Optional[AnglerFish]: ...

    @overload
    async def get_angler_data(self, *, best_chance: ...) -> Optional[list[AnglerFish] | AnglerFish]: ...

    async def get_angler_data(self, *, best_chance: bool = False) -> Optional[list[AnglerFish] | AnglerFish]:
        """Retrieve FF14 Fishing Angler data from their website and return it in a manageable form.

        .. note:
            - This will populate the `<ItemFish.ff14angler_data>` property.

        Parameters
        ----------
        best_chance: :class:`bool`, optional
            If you want the highest percent catch chance plus the bait and location only, by default False.

        Returns
        -------
        :class:`Optional[list[AnglerFish] | AnglerFish]`
            Returns a list of Fishing locations and Baits by default, if using `best_chance` parameter you will get a single entry back.

        """
        LOGGER.debug("<%s.%s> | Best Chance: %s", __class__.__name__, "get_angler_data", best_chance)
        if self._moogle._angler_fish_map is None:
            return None

        if self.name is None:
            return None

        fish_id: Optional[int] = self._moogle._angler_fish_map.get(self.name, None)
        if fish_id is None:
            return None

        fish_locs: Optional[list[int]] = await self._angler.get_fish_locations(fish_id=fish_id)
        if fish_locs is None:
            return None

        data: list[AnglerFish] = []
        location_name: Optional[str] = None
        chance = 0
        best: Optional[AnglerFish] = None
        LOGGER.debug("Checking Best Chance: %s | Type: %s | Entries: %s", best_chance, type(self), len(data))
        for entry in fish_locs:
            res: Optional[FishingData] = await self._angler.get_location_fish_data(location_id=entry, fish_id=fish_id)
            if res is None:
                continue

            # We use our inverted location mapping to get a location name.
            if self._moogle._angler_invert_loc_map is not None:
                location_name = self._moogle._angler_invert_loc_map.get(entry)
            fish = AnglerFish(item_id=fish_id, data=res, location_name=location_name)
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
        """Houses the FF14Angler information retrieved from `<ItemFish.get_ff14angler_data>`."""
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


class Fishing(ItemFish):
    """Represents an Final Fantasy 14 Fish.

    .. note::
        Inherits attributes from :class:`ItemFish`.


    Attributes
    ----------
    item: :class:`int`
        The item ID.
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
    fishing_spot: :class:`FishingSpot`
        The fishing spot the fish belongs to.

    Properties
    -----------
    angler_data: :class:`Optional[list[AnglerFish]]`
        Houses the FF14Angler information retrieved from `<ItemFish.get_angler_data>`.
    angler_url: :class:`str`
        The FF14Angler website url for the Fish.

    """

    text: Optional[str]
    ocean_stars: int
    is_hidden: bool
    fishing_spot: FishingSpot

    __slots__ = (
        "fishing_spot",
        "is_hidden",
        "item",
        "ocean_stars",
        "text",
    )

    def __init__(self, data: FishParameterData, angler: Angler, moogle: Moogle) -> None:
        """Build your :class:`Fishing` object.

        Parameters
        ----------
        data: :class:`DataTypeAliases`
            Generic typed as the data structure being passed in is typically a dict.
        angler: :class:`Angler`
            The :class:`Angler` object to handle data lookup.
        moogle: :class:`Moogle`
            The :class:`Moogle` object that created this class.

        """
        super().__init__(data=data, angler=angler, moogle=moogle)
        self._repr_keys = ["text", "is_hidden", "fishing_spot", "item"]
        for key in self.__slots__:
            value: Optional[int | bool | str] = data.get(key, None)
            if value is None:
                continue
            if isinstance(value, int):
                if key == "fishing_spot" and value != 0:
                    self.fishing_spot = self._moogle._get_fishing_spot(spot_id=value)
                elif key == "is_hidden":
                    setattr(self, key, bool(value))
                else:
                    setattr(self, key, value)
            else:
                setattr(self, key, value)


class SpearFishing(ItemFish):
    """Represents an Final Fantasy Fish that is acquired via Spear Fishing.

    .. note::
        Inherits attributes from :class:`ItemFish`.


    Attributes
    ----------
    description: :class:`str`
        The description related to the Fish.
    territory_type: :class:`SpearFishingNotebook`
        Similar to :class:`FishingSpot` but specifically for spear fishing locations.
    is_visible: :class:`bool`
        If the fish is visible.
    item: :class:`int`
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

    description: str
    territory_type: SpearFishingNotebook
    is_visible: bool

    __slots__ = (
        "description",
        "is_visible",
        "item",
        "territory_type",
    )

    def __init__(self, data: SpearFishingItemData, angler: Angler, moogle: Moogle) -> None:
        """Build your :class:`SpearFishing` object.

        Parameters
        ----------
        data: :class:`DataTypeAliases`
            Generic typed as the data structure being passed in is typically a dict.
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
                    self.item = value
                    # try:
                    #     self.item = self._moogle.get_item(item=str(value), limit_results=1)
                    # except MoogleLookupError:
                    #     LOGGER.warning("<%s> | Failed to find item. | item: %s", __class__.__name__, value)
                    #     self.item = value
                elif key.lower() == "territory_type" and value != 0:
                    self.territory_type = self._moogle._get_spearfishing_spot(record_type=value)
                elif key.lower() == "is_visible":
                    setattr(self, key, bool(value))
                else:
                    setattr(self, key, value)
            else:
                setattr(self, key, value)


class SpearFishingNotebook(Object):
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
        The Final Fantasy 14 place the Spearfishing node is located.

    Properties
    ----------
    angler_url: :class:`str`
        The FF14Angler website url for the Fish.

    """

    gathering_level: GatheringItemLevel
    is_shadow_node: bool
    # territory_type: int
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
        """Build your :class:`SpearFishingNotebook` object.

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
                    self.gathering_level = self._moogle._get_gathering_level(level_id=value)

                elif key.lower() == "place_name":
                    self.place_name = self._moogle._get_place_name(place_id=value)
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
    item0: :class:`int`
        The Final Fantasy 14 item of what Fish can be caught in this spot, if applicable.
    item1: :class:`int`
        The Final Fantasy 14 item of what Fish can be caught in this spot, if applicable.
    item2: :class:`int`
        The Final Fantasy 14 item of what Fish can be caught in this spot, if applicable.
    item3: :class:`int`
        The Final Fantasy 14 item of what Fish can be caught in this spot, if applicable.
    item4: :class:`int`
        The Final Fantasy 14 item of what Fish can be caught in this spot, if applicable.
    item5: :class:`int`
        The Final Fantasy 14 item of what Fish can be caught in this spot, if applicable.
    item6: :class:`int`
        The Final Fantasy 14 item of what Fish can be caught in this spot, if applicable.
    item7: :class:`int`
        The Final Fantasy 14 item of what Fish can be caught in this spot, if applicable.
    item8: :class:`int`
        The Final Fantasy 14 item of what Fish can be caught in this spot, if applicable.
    item9: :class:`int`
        The Final Fantasy 14 item of what Fish can be caught in this spot, if applicable.
    place_name: :class:`PlaceName`
        The Final Fantasy 14 place the Fishing spot is located.

    Properties
    ----------
    angler_url: :class:`str`
        The FF14Angler website url for the Fish.

    """

    gathering_level: int
    fishing_spot_category: FishingSpotCategory
    rare: bool
    x: int
    z: int
    item0: int
    item1: int
    item2: int
    item3: int
    item4: int
    item5: int
    item6: int
    item7: int
    item8: int
    item9: int
    place_name: PlaceName

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

    def __init__(self, data: FishingSpotData, **kwargs: Unpack[ObjectParams]) -> None:
        """Build your Fishing spot object.

        Parameters
        ----------
        data: :class:`FishingSpotData`
            The JSON data.
        **kwargs: :class:`Unpack[ObjectParams]`
            Any additional functionality such as a :class:`Angler` object or :class:`UniversalisAPI` object.
            - By default the :class:`Moogle` object is required for functionality sake.

        """
        super().__init__(data=data, moogle=kwargs["moogle"])
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
                    setattr(self, key, value)

                elif key.lower() == "place_name" and value != 0:
                    self.place_name = self._moogle._get_place_name(place_id=value)

                    if self._moogle._angler_loc_map is not None:
                        self._angler_loc_id = self._moogle._angler_loc_map.get(self.place_name.name)

                elif key.lower() == "fishing_spot_category":
                    self.fishing_spot_category = FishingSpotCategory(value)

                elif key == "rare":
                    self.rare = bool(value)
                else:
                    setattr(self, key, value)
            else:
                setattr(self, key, value)

    @property
    def angler_url(self) -> str:
        if self._angler_loc_id is None:
            return "https://en.ff14angler.com"
        return f"https://en.ff14angler.com/spot/{self._angler_loc_id}"


class GatheringItem(Object):
    """A represensation of an Final Fantasy 14 Item as Gatherable.

    Attributes
    ----------
    gathering_item_level: :class:`GatheringItemLevel`
        The item level of the Item and the Stars required if any.
    quest: :class:`bool`
        If the item is from a quest or not.
    is_hidden: :class:`bool`
        If the item is hidden or not.

    """

    # item: Item | int
    gathering_item_level: GatheringItemLevel
    quest: bool
    is_hidden: bool

    __slots__ = (
        "gathering_item_level",
        "is_hidden",
        "quest",
    )

    def __init__(self, data: GatheringItemData, **kwargs: Unpack[ObjectParams]) -> None:
        """Build your Gathering Item object.

        Parameters
        ----------
        data: :class:`GatheringItemData`
            The JSON data.
        **kwargs: :class:`Unpack[ObjectParams]`
            Any additional functionality such as a :class:`Angler` object or :class:`UniversalisAPI` object.
            - By default the :class:`Moogle` object is required for functionality sake.

        """
        super().__init__(data=data, moogle=kwargs["moogle"])
        self._repr_keys = ["quest", "is_hidden", "gathering_item_level"]
        for key in self.__slots__:
            value: Optional[int | bool | str] = data.get(key, None)
            if value is None:
                continue
            if key == "gathering_item_level" and isinstance(value, int):
                self.gathering_item_level = self._moogle._get_gathering_level(level_id=value)
            elif key in ["is_hidden", "quest"] and isinstance(value, int):
                setattr(self, key, bool(value))


class GatheringItemLevel(Object):
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


class InventoryItem(Object):
    """Represents an item from a parsed Allagon Tools Inventory CSV file.

    Attributes
    ----------
    name: :class:`str`
        The name of the item.
    id: :class:`int`
        The item ID.
    quality: :class:`ItemQuality`
        The quality of the item, either HQ or NQ.
    quantity: :class:`int`
        The number of said item from the CSV data.
    source: :class:`str`
        Who has the item, typically a character, retainer or FC name.
    location: :class:`InventoryLocationEnum`
        What type of inventory the item is located, such as Bag, Saddlebag, Glamour chest...

    """

    name: str
    id: int
    quality: ItemQuality
    quantity: int
    source: str
    location: InventoryLocation

    __slots__ = (
        "id",
        "location",
        "name",
        "quality",
        "quantity",
        "source",
    )

    def __init__(self, item_id: int, data: AllagonToolsInventoryCSV) -> None:
        """Build your Partial Item object.

        Parameters
        ----------
        item_id: :class:`int`
            The Final Fantasy 14 item id.
        data: :class:`AllagonToolsInventoryCSV`
            The JSON data.

        """
        self.id = item_id
        self._repr_keys = ["name", "id", "location", "quantity", "source"]
        for key in self.__slots__:
            value: Optional[int | bool | str] = data.get(key, None)
            if value is None:
                continue
            if key.lower() == "type":
                if isinstance(value, str) and value.lower() == "nq":
                    self.quality = ItemQuality.NQ
                elif isinstance(value, str) and value.lower() == "hq":
                    self.quality = ItemQuality.HQ
            elif key.lower().startswith("total_quantity") and isinstance(value, int):
                self.quantity = value
            elif key.lower() == "inventory_location" and isinstance(value, str):
                self.location = self._convert_inv_loc_to_enum(location=value)
            else:
                setattr(self, key, value)

    @staticmethod
    def _convert_inv_loc_to_enum(location: str) -> InventoryLocation:
        """Convert a provided location string from the Allagon Tools CSV into a :class:`InventoryLocationEnum`.

        Parameters
        ----------
        location: :class:`str`
            The inventory location string.

        Returns
        -------
        :class:`InventoryLocationEnum`
            The converted inventory location as an Enum.

        """
        if location.lower().startswith("bag"):
            return InventoryLocation.bag
        if location.lower().startswith("glamour"):
            return InventoryLocation.armoire
        if location.lower().startswith("saddlebag"):
            if location.lower().startswith("premium"):
                if "left" in location.lower():
                    return InventoryLocation.premium_saddlebag_left
                return InventoryLocation.premium_saddlebag_right
            if "left" in location.lower():
                return InventoryLocation.saddlebag_left
            return InventoryLocation.saddlebag_right
        if location.lower().startswith("armory"):
            return InventoryLocation.armory
        if location.lower().startswith("market"):
            return InventoryLocation.market
        if location.lower().startswith("free"):
            return InventoryLocation.free_company
        if location.lower().startswith("currency"):
            return InventoryLocation.currency
        if location.lower().startswith("equipped"):
            return InventoryLocation.equipped_gear
        if location.lower().startswith("crystals"):
            return InventoryLocation.crystals
        return InventoryLocation.null
