from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Literal, Optional, Unpack, overload

import aiohttp
from thefuzz import fuzz

from moogle_intuition._types import (
    XIVFishParameterTyped,
    XIVGatheringItemLevelTyped,
    XIVGatheringItemTyped,
    XIVItemTyped,
    XIVRecipeLevelTyped,
    XIVRecipeLookUpTyped,
)

from ._enums import (
    XIVCraftTypeEnum,
    XIVEquipSlotCategoryEnum,
    XIVGrandCompanyEnum,
    XIVItemSeriesEnum,
    XIVItemSpecialBonus,
    XIVItemUICategoryEnum,
)
from .garland_tools import GarlandAPI
from .universalis import UniversalisAPI

if TYPE_CHECKING:
    from aiohttp import ClientResponse
    from aiohttp.client import _RequestOptions

    from moogle_intuition.universalis import CurrentData

    from ._types import (
        ConvertCSVtoJsonParams,
        XIVBaseParamTyped,
        XIVClassJobCategoryTyped,
        XIVClassJobTyped,
        XIVFishingSpotTyped,
        XIVFishParameterTyped,
        XIVGatheringItemLevelTyped,
        XIVGatheringItemTyped,
        XIVItemLevelTyped,
        XIVItemTyped,
        XIVPlaceNameTyped,
        XIVRecipeLevelTyped,
        XIVRecipeLookUpTyped,
        XIVRecipeTyped,
    )
    from .universalis._types import MarketBoardParams


__all__ = (
    "FFXIVHandler",
    "FFXIVItem",
)


# https://github.com/xivapi/ffxiv-datamining/tree/master/csv
# Used when getting files and using `FFXIVHandler.data_building()`
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
    "recipe_level": (True, "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/RecipeLevelTable.csv"),
    "recipe": (True, "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/Recipe.csv"),
    "recipe_lookup": (True, "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/RecipeLookup.csv"),
    "gathering_item": (True, "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/GatheringItem.csv"),
    "gathering_item_level": (
        False,
        "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/GatheringItemLevelConvertTable.csv",
    ),
    "fish_parameter": (True, "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/FishParameter.csv"),
    "fishing_spot": (True, "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/FishingSpot.csv"),
    "class_job": (True, "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/ClassJob.csv"),
    "class_job_category": (True, "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/ClassJobCategory.csv"),
    "place_name": (True, "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/PlaceName.csv"),
}


class FFXIVHandler(UniversalisAPI):
    """
    Our handler type class for interacting with FFXIV Items, Recipes and other Data structures inside of FFXIV.

    """

    logger: ClassVar[logging.Logger] = logging.getLogger(__name__)
    _initialized: bool = False

    # File Paths
    data_path: ClassVar[Path] = Path(__file__).parent.joinpath("xiv_datamining")
    data_urls: dict[str, tuple[bool, str]]

    # CSV Parsing
    pre_formatted_keys: ClassVar[dict[str, str]] = {
        "ItemID": "item_id",
        "IsPvP": "is_pvp",
        "ItemUICategory": "item_ui_category",
        "EXPBonus": "exp_bonus",
        "PvPActionSortRow": "pvp_action_sort_row",
        "UIPriority": "ui_priority",
        "OH_percent": "oh_percent",
    }
    ignored_keys: ClassVar[list[str]] = [
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

    # Item Handling.
    # I am storing "Item ID" : "Item Name"
    item_dict: dict[str, str | FFXIVItem]
    item_json: dict[str, XIVItemTyped]
    # A simple ref dict to map the repair Item to the Key.
    item_repair_dict: ClassVar[dict[int, int]] = {
        1: 5594,
        2: 5595,
        3: 5596,
        4: 5597,
        5: 5598,
        6: 10386,
        7: 17837,
        8: 33916,
    }

    # Recipe Handling.
    # I am storing "Recipe ID" : "Item Result ID"
    # recipe_dict: dict[str, int]
    recipe_json: dict[str, XIVRecipeTyped]
    # Job Recipe Table
    recipelookup_json: dict[str, XIVRecipeLookUpTyped]
    # Recipe Level Table
    recipelevel_json: dict[str, XIVRecipeLevelTyped]
    # Gatherable Items Handling.
    gatheringitem_dict: dict[str, int]
    gatheringitem_json: dict[str, XIVGatheringItemTyped]
    gatheringitemlevel_json: dict[str, XIVGatheringItemLevelTyped]
    # Fishing Related
    fishparameter_json: dict[str, XIVFishParameterTyped]
    # This is stored with FLIPPED key to values ("Item ID" : "Dict Index")
    fishparameter_dict: dict[int, str]
    fishingspot_json: dict[str, XIVFishingSpotTyped]
    # Location Information
    placename_json: dict[str, XIVPlaceNameTyped]

    # Marketboard Integration
    universalis: UniversalisAPI | None

    def __init__(self, session: Optional[aiohttp.ClientSession] = None, universalis: Optional[UniversalisAPI] = None) -> None:
        global URLS
        self.data_urls: dict[str, tuple[bool, str]] = URLS
        self.session = session
        self.universalis = universalis

    # def __getattribute__(self, name: str) -> Any:
    #     attr = super().__getattribute__(name)
    #     # This is the best way to prevent accessing functions/data prior to file validation and data structure building for the class.
    #     # As we need to use `await FFXIVHandler().build_handler()` to be able to do data building during object creation.
    #     # print("ATTR", "build_handler" in str(attr))
    #     # if callable(attr) and "build_handler" in str(attr):
    #     #     return attr
    #     # # We are accessing a function and haven't called `build_handler` so we fall into this logic.
    #     # elif callable(attr) and super().__getattribute__("_initialized") is False:
    #     #     raise RuntimeError("<FFXIVHandler> has not been properly initialized, please call <FFXIVHandler.build_handler> first.")
    #     # # We are accessing an attribute/property and the class hasn't been initialized so we fall into this logic.
    #     # elif super().__getattribute__("_initialized") is False:
    #     #     raise AttributeError("<FFXIVHandler> has not been properly initialized, please call <FFXIVHandler.get_handler> first.")
    #     # else:
    #     #     return attr

    async def file_validation(self) -> None:
        """
        Validate's the required files for FFXIVHandler to operate.
        - Files are located in `xiv_datamining`.
        """
        self.logger.info("Validating json files... | Path: %s", self.data_path)
        for key, data in URLS.items():
            # lets check for the json file, which is all we care about to build our data structures.
            f_path: Path = Path(self.data_path).joinpath(key + ".json")
            self.logger.info("Validating file... %s. | Exists: %s | Path: %s", key, f_path.exists(), f_path)
            if f_path.exists() is False:
                await self.fetch_csv_build_json(url=data[1], file_name=key + ".csv", convert_pound=data[0])
                self.logger.info("Finished retrieving and building data for file.| File: %s", key)

    @classmethod
    async def build_handler(cls, auto_builder: bool = True) -> FFXIVHandler:
        """
        Create your Singleton of `FFXIVHandler` and any subsequent usage will be retrieved via `get_handler()`

        Parameters
        -----------
        auto_builder: bool, optional
            Controls if the Class should generate the respective keys for item lookup, default is True.
            - Set to `False` if generating CSV/JSON files.
        session: :class:`aiohttp.ClientSession | None`, optional
            Either supply your own session or :class:`FFXIVHandler` will use an `async with` context manager for `aiohttp.ClientSession()`, by default None.

        Raises
        -------
        ValueError:
            If the FFXIVItemHandler class does not exist.

        Returns
        --------
        FFXIVItemHandler:
            A singleton class of FFXIVItemHandler
        """

        if cls._instance is None:
            raise ValueError("Failed to setup Handler. You need to initiate `<class FFXIVItemHandler>` first.")

        # One time data building as we are setting the `_initialized` attribute after all this is done.
        if cls._instance._initialized is False:
            await cls._instance.file_validation()

            # This is for NON-Development usage; otherwise setting auto_builder to false won't generate anything for searching/etc.
            if auto_builder is True:
                # Quick reference dictionaries for easier lookup.
                cls._instance.generate_reference_dict(file_name="item.json", value_get="name")

                # Recipe related dict/JSON
                cls._instance.generate_reference_dict(file_name="recipe.json", value_get="item_result")
                cls._instance.generate_reference_dict(file_name="recipe_lookup.json", no_ref_dict=True)
                cls._instance.generate_reference_dict(file_name="recipe_level.json", no_ref_dict=True)

                # Fishing related dict/JSON
                cls._instance.generate_reference_dict(file_name="fish_parameter.json", flip_key_value=True, value_get="item")
                cls._instance.generate_reference_dict(file_name="fishing_spot.json", no_ref_dict=True)

                # Gathering related dict/JSON.
                cls._instance.generate_reference_dict(file_name="gathering_item.json", value_get="item")
                cls._instance.generate_reference_dict(file_name="gathering_item_level.json", no_ref_dict=True)

                # Location related JSON
                cls._instance.generate_reference_dict(file_name="place_name.json", no_ref_dict=True)

        cls._instance._initialized = True
        return cls.get_handler()

    @classmethod
    def get_handler(cls) -> FFXIVHandler:
        if cls._instance is None:
            raise ValueError("Failed to setup Handler. You need to initiate `<class FFXIVItemHandler>` first.")
        elif cls._instance._initialized is False:
            raise RuntimeError("Please call <FFXIVItemHandler.build_handler()> before calling <FFXIVHandler.get_handler()>.")
        return cls._instance

    def __new__(cls, session: Optional[aiohttp.ClientSession] = None, *args: Any, **kwargs: Any) -> FFXIVHandler | None:
        if not hasattr(cls, "_instance"):
            cls._instance: FFXIVHandler = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def generate_reference_dict(
        self,
        file_name: str,
        value_get: Optional[str] = None,
        flip_key_value: bool = False,
        no_ref_dict: bool = False,
    ) -> None:
        """
        Generates the data for our table lookups and data storage.
        - The value_get is the key we are using to access the value information and storing that as our value for our reference dictionary.
            - `{ key : value_get }`

        - Will transform the `file_name` parameter into attributes for data accessing.
        Example:
        - file_name = "recipe.json" -> "recipe_json"
        - file_name = "item.json" -> ["item", "json"][0] -> "item_dict"

        Parameters
        -----------
        file_name: :class:`str`
            The the final part of the path specifying which file to load from `self.data_path`.
        value_get: :class:`str`, optional
            The value to retrieve from the assosciated dictionary, to be used in a key value pair as the quick referrence dict, default is None.
        flip_key_value: :class:`bool`, optional
            Swap the location of the key with the `value_get` parameter results from the dictionary. This is used for reference dict only!, default False.
        no_ref_dict: :class:`bool`, optional
            Bypass bool to only set the data as an attribute of the FFXIVHandler using the file_name parameter as seen in the example first entry, by default False.

        Raises
        -------
        :exc:`ValueError`
            If we do not provide a `value_get` parameter when making a reference dictionary.
        """
        # Typical usage is we are getting a `.json` file to parse.
        # first time startup will not have the `.csv` files or the `.json` files
        # so we need to fetch those files from the `xiv_datamining` Github repo.
        if self.data_path.joinpath(file_name).exists() is False:
            raise FileNotFoundError("Unable to locate the JSON file. | File Name: %s | File Path: %s", file_name, self.data_path)
        elif self.data_path.joinpath(file_name).is_dir() is True:
            raise TypeError("The file name provided is a directory. | File Name: %s | File Path: %s", file_name, self.data_path)

        # We load the data, store it local to our object and make a quick reference dict to help lookup.
        data: dict[str, XIVItemTyped] = json.loads(self.data_path.joinpath(file_name).read_bytes())
        setattr(self, file_name.replace(".", "_"), data)
        if no_ref_dict is True:
            self.logger.debug(
                "Set JSON data from %s | Attr: %s | Number of Items: %s | Path: %s",
                file_name,
                file_name.replace(".", "_"),
                len(data),
                self.data_path.joinpath(file_name),
            )
            return None

        if value_get is None:
            raise ValueError("You must provide a `value_get` parameter if not making a reference dict.")

        item_dict = {}
        for key, value in data.items():
            if isinstance(value, dict):
                temp: Any | None = value.get(value_get, None)

                if temp is None:
                    continue
                elif flip_key_value is True:
                    item_dict[temp] = key
                else:
                    item_dict[key] = temp

        # example:
        # file_name = "item.json" -> ["item", "json"] -> "item_dict"
        setattr(self, file_name.split(".")[0] + "_dict", item_dict)
        self.logger.debug(
            "Generated the reference dict from `%s`.| Attrs: %s , %s | Value Key: %s | Number of Items: %s | Path: %s",
            file_name,
            file_name.replace(".", "_"),
            file_name.split(".")[0] + "_dict",
            value_get,
            len(item_dict),
            self.data_path.joinpath(file_name),
        )

    # @overload
    # def get_item(self,item_id: int) -> FFXIVItem: ...

    # @overload
    # def get_item(self, item_id = None, item_name: str) -> list[FFXIVItem] | FFXIVItem: ...

    # @overload
    # def get_item(self,item_id: Optional[int] = None) -> list[FFXIVItem] | FFXIVItem: ...

    def get_item(
        self,
        item_id: Optional[int] = None,
        item_name: Optional[str] = None,
        *,
        match: int = 80,
        limit_results: int = 10,
    ) -> FFXIVItem | list[FFXIVItem]:
        """
        Retrieves a possible match to the `item_name` or `item_id` parameter as an FFXIV Item.

        Parameters
        -----------
        item_id: :class:`int` | None`, optional
            Search for an FFXIV Item by it's Item ID, by default None.
        item_name: :class:`str | None`, optional
            Search for an FFXIV Item by it's Name, by default None.
        match: :class:`int`, optional
            The percentage required for the Fuzzy match comparison, by default 80.
        limit_results: :class:`int`, optional
            You can limit the number of results if needed; otherwise it will return the only 10 entries by default.

        Returns
        --------
        :class:`FFXIVItem | list[FFXIVItem]`
            A list or single entry of an FFXIVItem.

        Raises
        -------
        :exc:`ValueError`
            If we fail to look up the Item by ID, Name or fail to find a close match to the Name.
            If no item_name and no item_id is provided.
        :exc:`KeyError`
            If we fail to find any matches related to the Name or ID provided.
        """

        if item_id is None and item_name is None:
            raise ValueError("You must provide an `item_id` or an `item_name`.")

        elif item_id is not None and item_name is not None:
            raise ValueError("You must provide only one parameter, either `item_id` or `item_name`")
        data = None

        if item_id is not None:
            self.logger.debug("Searching... Item ID: %s | Search Item Name: %s", item_id, item_name)

            # We are storing previously index'd item objects in our quick lookup dictionary.
            res: Optional[str | FFXIVItem] = self.item_dict.get(str(item_id), None)
            if isinstance(res, FFXIVItem):
                return res
            # If we get a string back it's most likely the name we stored as quick ref.
            elif isinstance(res, str):
                data: Optional[XIVItemTyped] = self.item_json.get(str(item_id), None)

            # If we fail to get a string or an FFXIVItem back clearly we have an issue.
            if res is None or data is None:
                raise ValueError("We failed to lookup Item ID: %s in our item.json file.", item_id)
            else:
                return FFXIVItem(data=data)

        matches: list[FFXIVItem] = []
        for key, value in self.item_dict.items():
            # Item Name lookup.
            if value is None:
                continue

            if item_name is not None:
                # This is to attempt to find our cached entries via exact matching.
                if isinstance(value, FFXIVItem) and value.name.lower() == item_name.lower():
                    return value

                elif isinstance(value, str) and value.lower() == item_name.lower():
                    self.logger.debug(
                        "Searching... Key: %s | Value: %s | Search ID: %s | Search Name: %s",
                        key,
                        value,
                        item_id,
                        item_name,
                    )
                    data = self.item_json.get(str(key), None)
                    if data is None:
                        raise ValueError("We failed to lookup Item Name: %s in our item.json file.", item_name)
                    return FFXIVItem(data=data)

                # Partial Name lookup matching.
                else:
                    res = value.name if isinstance(value, FFXIVItem) else value
                    ratio: int = fuzz.partial_ratio(s1=res.lower(), s2=item_name.lower())

                    if ratio >= match:
                        self.logger.debug(
                            "Searching... Partial Matching || Key: %s | Value: %s | Ratio: %s | Search ID: %s | Search Name: %s ",
                            key,
                            value,
                            ratio,
                            item_id,
                            item_name,
                        )
                        res = self.item_dict.get(str(key), None)

                        # Clearly we haven't looked this item up yet, so let's get our JSON data.
                        if isinstance(res, str):
                            data = self.item_json.get(str(key), None)

                        # Use the existing object and continue to the next entry.
                        elif isinstance(res, FFXIVItem):
                            matches.append(res)
                            continue

                        if res is None or data is None:
                            raise ValueError("We failed to lookup Item ID: %s in our item.json file.", item_id)
                        matches.append(FFXIVItem(data=data))
                        continue
            else:
                continue

        if len(matches) == 0:
            raise KeyError("Unable to find the item name provided. | Item Name: %s", item_name)
        self.logger.debug("Returning %s Partial Matches", len(matches[:limit_results]))
        return matches[:limit_results]

    def get_item_job_recipes(self, item_id: int) -> FFXIVJobRecipe:
        """
        Retrieves a possible match to the `item_id` parameter as a Job Recipe reference as a single item can be crafted by multiple jobs.

        Parameters
        -----------
        item_id: :class:`int`
            The recipe ID to search for.

        Returns
        --------
        :class:`FFXIVJobRecipe`
            The Job Recipe reference object to seperate the Recipes by Job Accronyms.

        Raises
        -------
        :exc:`ValueError`
            If we fail to look up the `item_id` provided.
        """

        self.logger.debug(
            "Searching... Job Recipe by Item ID: %s | Entries: %s",
            item_id,
            len(self.recipelookup_json),
        )
        data: Optional[XIVRecipeLookUpTyped] = self.recipelookup_json.get(str(item_id), None)
        if data is None:
            raise ValueError("We failed to lookup Item ID: %s in our recipelookup.json file", item_id)
        return FFXIVJobRecipe(data=data)

    def get_recipe(self, recipe_id: str) -> FFXIVRecipe:
        """
        Retrieves a possible match to the `recipe_id` parameter via our `Self.recipe_json` data.

        Parameters
        -----------
        recipe_id: :class:`str`
            The recipe ID to search for.

        Returns
        --------
        :class:`FFXIVRecipe`
            The Recipe JSON data represented as a Python object.

        Raises
        -------
        :exc:`ValueError`
            If we fail to find the `recipe_id` provided in our `recipe.json` file.
        """
        # I am storing str "Recipe ID" : int "Item Result ID"
        self.logger.debug("Searching... Recipe ID: %s | Entries: %s", recipe_id, len(self.recipe_json))
        data: Optional[XIVRecipeTyped] = self.recipe_json.get(recipe_id, None)
        if data is None:
            raise ValueError(
                "We failed to lookup Recipe ID: %s in our recipe.json file. Data is `None`",
                recipe_id,
            )
        return FFXIVRecipe(data=data)

    def get_recipe_level(self, recipe_level_id: int) -> FFXIVRecipeLevel:
        """
        Retrieves a possible match to the `recipe_level_id` parameter via our `Self.recipelevel_json` data.

        Parameters
        -----------
        recipe_level_id: :class:`str`
            The recipe level id to search for.

        Returns
        --------
        :class:`FFXIVRecipeLevel`
            The recipelevel JSON data represented as a Python object.

        Raises
        -------
        :exc:`ValueError`
            If we fail to find the `recipe_level_id` provided in our `recipelevel.json` file.
        """
        self.logger.debug(
            "Searching... Recipe Level ID: %s | Entries: %s",
            recipe_level_id,
            len(self.recipelevel_json),
        )
        data: Optional[XIVRecipeLevelTyped] = self.recipelevel_json.get(str(recipe_level_id), None)
        if data is None:
            raise ValueError(
                "We failed to lookup Recipe Level ID: %s in our recipelevel.json file",
                recipe_level_id,
            )
        return FFXIVRecipeLevel(data=data)

    def get_gathering_level(self, gathering_level_id: int) -> XIVGatheringItemLevelTyped:
        """
        Retrieves the JSON data related to the gathering item level, which includes `stars` and `item level` for the `item`.

        Parameters
        -----------
        gathering_level_id: :class:`int`
            The level ID to search for.

        Returns
        --------
        :class:`XIVGatheringItemLevelTyped`
            The JSON data from the `gathering_item_level.json` related to the `gathering_level_id` parameter passed in.

        Raises
        -------
        :exc:`ValueError`
            Failure to find the `gathering_level_id` parameter provided.
        """
        self.logger.debug(
            "Searching... Gathering Item Level ID: %s | Entries: %s",
            gathering_level_id,
            len(self.gatheringitemlevel_json),
        )
        data: Optional[XIVGatheringItemLevelTyped] = self.gatheringitemlevel_json.get(str(gathering_level_id), None)
        if data is None:
            raise ValueError(
                "We failed to lookup Gathering Item Level ID: %s in our gatheringitemlevel.json file",
                gathering_level_id,
            )
        return data

    def get_fishing_spot(self, fishing_spot_id: int) -> FFXIVFishingSpot:
        """
        Retrieve any information related to the provided `fishing_spot_id` parameter inside our `fishing_spot.json` file.

        Parameters
        -----------
        fishing_spot_id: :class:`int`
            The ID value for a fishing spot.

        Returns
        --------
        :class:`FFXIVFishingSpot`
            The JSON data related to the `place_id` parameter.

        Raises
        -------
        :exc:`ValueError`
            If the `fishing_spot_id` parameter does not exist in the `fishing_spot.json` file..
        """
        self.logger.debug(
            "Searching... Fishing Spot ID: %s | Entries: %s",
            fishing_spot_id,
            len(self.fishingspot_json),
        )
        data: Optional[XIVFishingSpotTyped] = self.fishingspot_json.get(str(fishing_spot_id), None)
        if data is None:
            raise ValueError(
                "We failed to lookup Fishing Spot ID: %s in our fishingspot.json file",
                fishing_spot_id,
            )
        return FFXIVFishingSpot(data=data)

    def get_place_name(self, place_id: int) -> XIVPlaceNameTyped:
        """
        Retrieve any information related to the provided `place_id` parameter inside our `place_name.json` file.

        Parameters
        -----------
        place_id: :class:`int`
            The ID value for a place.

        Returns
        --------
        :class:`XIVPlaceNameTyped`
            The JSON data related to the `place_id` parameter.

        Raises
        -------
        :exc:`ValueError`
            If the `place_id` parameter does not exist in the `place_name.json` file.
        """
        self.logger.debug(
            "Searching... Place Name ID: %s | Entries: %s",
            place_id,
            len(self.placename_json),
        )
        data: Optional[XIVPlaceNameTyped] = self.placename_json.get(str(place_id), None)
        if data is None:
            raise ValueError(
                "We failed to lookup Place Name ID: %s in our placename.json file",
                place_id,
            )
        return data

    def _is_fishable(self, item_id: int) -> FFXIVFishParameter:
        """
        Check's if an Item ID is gatherable via fishing.
        """
        key: Optional[str] = self.fishparameter_dict.get(item_id, None)
        self.logger.debug(
            "Searching... Fishing Parameter for Item ID: %s | Entries: %s ",
            item_id,
            len(self.fishparameter_dict),
        )
        if key is None:
            raise ValueError(
                "We failed to lookup Item ID: %s in our `self.fishparameter_dict` reference.",
                item_id,
            )
        else:
            data: Optional[XIVFishParameterTyped] = self.fishparameter_json.get(str(key), None)
        if data is not None:
            return FFXIVFishParameter(data=data)
        raise ValueError(
            "We failed to lookup Fish Parameter ID: %s in our `self.fishparameter_json` reference.",
            key,
        )

    def _is_gatherable(self, item_id: int) -> FFXIVGatheringItem:
        """
        Generates an array of Item IDs so we can see if an Item is Gatherable or not.
        """
        self.logger.debug(
            "Searching... Gathering Item for Item ID: %s | Entries: %s ",
            item_id,
            len(self.gatheringitem_dict),
        )
        for key, value in self.gatheringitem_dict.items():
            if item_id == value:
                data: XIVGatheringItemTyped | None = self.gatheringitem_json.get(key, None)
                if data is not None:
                    return FFXIVGatheringItem(data=data)
                else:
                    raise ValueError("We failed to lookup ")

        raise ValueError(
            "We failed to lookup Item ID: %s in our `self.gatheringitem_dict` reference.",
            item_id,
        )

    async def convert_csv_to_json(
        self,
        csv_name: str,
        *,
        auto_pep8: bool = True,
        convert_pound: bool = True,
        typed_dict: bool = False,
        typed_file_name: Optional[str] = None,
    ) -> None:
        """
        Parses our local `xiv_datamining` folder csv files into JSON files.
        - If the .csv files are no longer present, it will get the csv file, save it and parse that.
        - This assumes the csv file is located in `Path(__file__).parent.xiv_datamining`

        Parameters
        -----------
        csv_name: :class:`str`
            The name of the csv file to parse.
        typed_dict: :class:`bool`, optional
            If we want to generate a Typed Dict object from the CSV file, by default False.
        typed_file_name: :class:`str | None`, optional
            The file name to write out the Typed Dict data to, by default None.
                - If `None`: Defaults to `csv_name_typed.py`
        """
        json_name: str = csv_name.split(".")[0] + ".json"
        if typed_file_name is None:
            typed_file_name = csv_name.split(".")[0] + "_typed.py"
        # typed_class_name: str = "XIV" + csv_name.split(".")[0]
        typed_class_name = "XIV" + typed_file_name[:-3]

        if self.data_path.joinpath(csv_name).exists():
            self.logger.debug("Found local %s", csv_name)
            res, keys, types = self.csv_parse(
                path=self.data_path.joinpath(csv_name),
                convert_pound=convert_pound,
                auto_pep8=auto_pep8,
            )

            # ? Suggestion
            # This will make the JSON file regardless if it exists or not.
            # Could possible have a flag to prevent overwrite.. unsure.
            self.write_data_to_file(path=self.data_path, file_name=json_name, data=res)

            if typed_dict:
                res = self.generate_typed_dict(class_name=typed_class_name, keys=keys, key_types=types)
                self.write_data_to_file(path=Path(__file__).parent, file_name=typed_file_name, data=res)

        else:
            # In case we cannot find the local file we can use our pre-built URLS dict to
            # get the CSV file from the `xivapi` Github repo else prompt for a url.
            url_key = csv_name.split(".")[0]
            key_data: tuple[bool, str] | None = URLS.get(url_key)
            if key_data is None:
                url: str = input(f"Please provide a url for {csv_name}")
            else:
                url = key_data[1]

            data: bytes = await self.request_file_data(url=url)
            self.write_data_to_file(path=self.data_path, file_name=csv_name, data=data)
            await self.convert_csv_to_json(csv_name=csv_name, typed_dict=typed_dict)

        # Remove the CSV files since we don't need them after they have been converted.
        self.logger.debug("Removing CSV file %s", csv_name)
        self.data_path.joinpath(csv_name).unlink()

    async def request_file_data(self, url: str, **request_options: Unpack[_RequestOptions]) -> bytes:
        """
        Basic <aiohttp.ClientSession>.get()` url without headers.

        Parameters
        -----------
        url: :class:`str`
            The url content to read.

        **kwargs: :class:`RequestOptions`
            Any kwargs to be passed to the `aiohttp.ClientSession.get(**kwargs) parameter.

        Returns
        --------
        :class:`bytes`
            The ClientResponse.content.read() or ClientResponse.json() depending on the content_type.

        Raises
        -------
        :exc:`ConnectionError`
            If the status code is not equal to 200.
        """
        async with aiohttp.ClientSession() as session:
            res: ClientResponse = await session.get(url=url, **request_options)
            if res.status != 200:
                raise ConnectionError("Unable to access the url: %s", url)
            if res.content_type == "application/json":
                return await res.json()
            else:
                return await res.content.read()

    def write_data_to_file(
        self,
        file_name: str,
        data: bytes | dict | str,
        path: Path = Path(__file__).parent,
        mode: str = "w+",
    ) -> None:
        """
        Basic file dump with json handling. If the data parameter is of type `dict`, `json.dumps()` will be used with an indent of 4.

        Parameters
        -----------
        path: :class:`Path`, optional
            The Path to write the data, default's to :class:`FFXIVHandler.data_path` attribute.
        file_name: :class:`str`
            The name of the file, with `.lower()` applied; please also provide the file extension.
        data: :class:`bytes | dict | str`
            The data to write out to the path and file_name provided.
        """
        file_name = file_name.lower()
        with path.joinpath(file_name).open(mode=mode) as file:
            self.logger.debug("Wrote data to file %s located at: %s", path, file_name)
            if isinstance(data, bytes):
                file.write(data.decode(encoding="utf-8"))
            elif isinstance(data, dict):
                file.write(json.dumps(data, indent=4))
            else:
                file.write(data)
        self.logger.info("File write successful to path: %s ", path.joinpath(file_name).as_posix())

    def csv_parse(
        self, path: Path, convert_pound: bool = True, auto_pep8: bool = True
    ) -> tuple[dict[str, dict[str, int | str | list[int] | bool | None]], list[str], list[str]]:
        """
        Parse the CSV file, breaking out the Keys and Types to be return as a tuple for turning into Typed Dicts if needed.

        - All Keys, Values and Types are sanitized via self.sanitize_key_name, self.convert_values and self.sanitized_type_name.

        Parameters
        -----------
        path: :class:`Path`
            The Path to the CSV file.
        auto_pep8: bool, Optional
            If the keys should be formatted in PEP8 style.

        Returns
        --------
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
                    # The Pound symbol from item.csv is the Item ID.
                    if k == "#" and convert_pound:
                        k = "id"

                    # Removes the unused keys.
                    elif k in reject_keys:
                        continue

                    # ? Suggestion
                    # Pep 8 all "keys" as they will be used as attributes for the TypedDict/Class objects.
                    if auto_pep8 is True:
                        k: str = self.pep8_key_name(key_name=self.sanitize_key_name(key_name=k))
                    else:
                        k: str = self.sanitize_key_name(key_name=k)

                    sanitized_data[item][k] = self.convert_values(value=v)

            if auto_pep8 is True:
                return (
                    sanitized_data,
                    [self.pep8_key_name(key_name=self.sanitize_key_name(key_name=i)) for i in keys],
                    [self.sanitize_type_name(type_name=i) for i in types],
                )
            else:
                return (
                    sanitized_data,
                    [self.sanitize_key_name(key_name=i) for i in keys],
                    [self.sanitize_type_name(type_name=i) for i in types],
                )

    def sanitize_key_name(self, key_name: str) -> str:
        """
        Using .replace() to remove the chars `{,  }, <ms>, <s>` and replaces the `[, ]` chars with `_`
        - Replaces mdash `–`, `-` and space with underscore `_` char.
        - Replaces single quote `'` with nothing.
        - Replaces `<%>` with `_percent`.
        - Replaces `%` with `_percent`.
        - Replaces `1` and `2` with the word representation of the number. (eg `one`, `two`)
        - Replaces `(` and `)` with nothing.

        Parameters
        -----------
        key_name: :class:`str`
            The Key name to sanitize.

        Returns
        --------
        :class:`str`
            The sanizted key_name value.
        """

        # some fields have {} and other symbols that must be sanitized
        if len(key_name) > 1 and key_name[0].isnumeric():
            key_name = key_name.replace("1", "one").replace("2", "two")
        key_name = key_name.replace(":", "")
        key_name = key_name.replace("(", "").replace(")", "")
        key_name = key_name.replace("{", "").replace("}", "")
        key_name = key_name.replace("][", "_")  # do this first for [0][1] as an example
        key_name = key_name.replace("[", "").replace("]", "")
        key_name = key_name.replace("<ms>", "").replace("<s>", "")
        key_name = key_name.replace("<%>", "_percent")
        key_name = key_name.replace("%", "_percent")
        key_name = key_name.replace("'", "").replace(" ", "_").replace("-", "_").replace("–", "_")
        return key_name

    @classmethod
    def pep8_key_name(cls, key_name: str) -> str:
        """
        Converts the provided `key_name` parameter into something that is pep8 compliant yet clear as to what it is for.
        - Adds a `_` before any uppercase char in the `key_name` and then `.lowers()` that uppercase char.

        *Note*
            Has special cases in `cls.ignored_keys` to allow adding/removing of needed keys.



        Parameters
        -----------
        key_name: :class:`str`
            The string to format.

        Returns
        --------
        :class:`str`
            The formatted string.
        """
        # We have keys we don't want to format/change during generation so add them to the ignored_keys list.
        if key_name in cls.ignored_keys:
            return key_name

        for k, v in cls.pre_formatted_keys.items():
            if key_name == k:
                return v

        temp: str = key_name[:1].lower()
        for e in key_name[1:]:
            if e.isupper():
                temp += f"_{e.lower()}"
                continue
            temp += e
        return temp

    def sanitize_type_name(self, type_name: str) -> str:
        """
        Similar to sanitize_key_name, but this replaces the C/C# Type names with Python related Types.

        Parameters
        -----------
        type_name: :class:`str`
            The Type name from the CSV to replace.

        Returns
        --------
        :class:`str`
            The replaced type_name.
        """
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
        elif type_name.startswith(tuple(bool_type)):
            return "bool"
        elif type_name.startswith("str"):
            return "str"
        else:
            self.logger.warning("UNK value Type. | Type Name: %s", type_name)
            return f"Any #{type_name}"

    # ? Suggestion
    #  - This may break if they use other highlight colors/etc.
    @staticmethod
    def sanitize_html(data: str) -> str:
        """
        Very basic str replacement for key words.

        Parameters
        -----------
        data: :class:`str`
            The string to replace HTML element's from.

        Returns
        --------
        :class:`str`
            The modified string.
        """
        data = data.replace("<br>", "\n")
        data = data.replace('<span class="highlight-green">', "**", 1)
        data = data.replace('<span class="highlight-green">', "\n**")
        data = data.replace("</span>", "**\n")
        return data

    @staticmethod
    def convert_values(value: str) -> int | bool | str | list[int] | None:
        """
        Converts the JSON values from all strings into their respective values.

        Parameters
        -----------
        value: :class:`str`
            The value to be converted.

        Returns
        --------
        :class:`int | bool | str | list[int] | None`
            The converted value.
        """
        if len(value) == 0:
            return None

        elif value.isdigit():
            return int(value)

        elif value.lower() in ["false", "true"]:
            return value.lower() == "true"

        elif value.find(",") != -1:
            test: str = value.replace(",", "")
            if test.isdigit():
                return [int(entry) for entry in value.split(",")]
            else:
                return value
        else:
            return value

    def generate_typed_dict(self, class_name: str, keys: list[str], key_types: list[str]) -> str:
        """
        Take our sanitized Keys and Key Types from our CSV file parsing and generate a TypedDict as a string for us.

        Parameters
        -----------
        class_name: :class:`str`
            The name of the Typed Dict placed into `{class_name}(TypedDict):`.
        keys: :class:`list[str]`
            The keys for the Typed Dict.
        key_types: :class:`list[str]`
            The type values for the Typed Dict.

        Returns
        --------
        :class:`str`
            A Typed Dict as a str.
        """
        temp: list[str] = []
        temp.append(f"class {class_name}(TypedDict):")
        for key, k_type in zip(keys, key_types):
            if len(key) == 0:
                continue
            # This only works on Item.csv
            if key == "#":
                key = "id"
            temp.append(f"    {key}: {k_type}")
        return "\n".join(temp)

    def generate_enum(self, class_name: str, keys: list[int], values: list[str | int]) -> str:
        """
        Takes in keys and values to generate an basic Enum.
        - Structing the Enum in the way of `values = keys` (my_attribute = 0)

        Parameters
        -----------
        class_name: :class:`str`
            The name of the Enum placed into `{class_name}(Enum):`.
        keys: :class:`list[int]`
            The int value for the Enum values to equal `(values = keys)`.
        values: :class:`list[str | int]`
            The attributes to be used for the Enum.

        """
        temp: list[str] = []
        temp.append(f"class {class_name}(Enum):")
        for key, key_value in zip(keys, values):
            temp.append(f"    {key_value} = {key}")
        return "\n".join(temp)

    async def fetch_csv_build_json(self, url: str, file_name: str, **convert_args: Unpack[ConvertCSVtoJsonParams]) -> Literal[True]:
        """
        Function chain to use an `aiohttp.ClientSession.get()` for the provided url, then writes the data to the `file_name` provided.
        - File will be saved in `xiv_datamining/` directory.

        Parameters
        -----------
        url: :class:`str`
            The url to `.get()`.
        file_name: :class:`str`
            The file name to write the data to from the url request.
        **kwargs: :class:`Any`
            Any parameters to be passed into the :class:`FFIXVHandler.convert_csv_to_json()` function.

        Returns
        --------
        :class:`Literal[True]`
            Returns `True` on success.
        """

        res: bytes = await self.request_file_data(url=url)
        self.write_data_to_file(path=self.data_path, file_name=file_name, data=res)
        await self.convert_csv_to_json(csv_name=file_name, **convert_args)
        return True

    async def get_mb_current_data(
        self, item_names: Optional[list[str]] = None, item_ids: Optional[list[int]] = None, **kwargs: Unpack[MarketBoardParams]
    ) -> list[CurrentData] | CurrentData | None:
        """
        Bulk Universalis Marketboard data fetching.

        Parameters
        -----------
        item_names: :class:`Optional[list[str]]`, optional
            A list of item_names, by default None.
        item_ids: :class:`Optional[list[int]]`, optional
            A list of item_ids, by default None.

        Returns
        --------
        :class:`list[CurrentData] | CurrentData | None`
            The Universalis JSON data represented as a class.

        Raises
        -------
        :exc:`ValueError`
            If you provide parameter `item_names` and `item_ids`, please provide only one.
        """
        if item_names is not None and item_ids is not None:
            raise ValueError("You must provide either parameter `item_names` or `item_ids`.")

        # Just for the first call, let's setup UniversalisAPI
        if self.universalis is None:
            universalis = UniversalisAPI(session=self.session)
            self.universalis = universalis
        else:
            universalis: UniversalisAPI = self.universalis

        if item_names is not None and isinstance(item_names, list):
            for name in item_names:
                # Just in case we fail to find the item.
                try:
                    res: FFXIVItem | list[FFXIVItem] = self.get_item(item_name=name, limit_results=1)
                except ValueError:
                    return None

                if isinstance(res, list):
                    return await universalis.get_current_data(items=[entry.id for entry in res], **kwargs)
                return await universalis.get_current_data(items=res.id, **kwargs)
        elif item_ids is not None and isinstance(item_ids, list):
            return await universalis.get_current_data(items=item_ids, **kwargs)


class FFXIVItem(GarlandAPI):
    """
    Represents an FFXIV Item per XIV Datamining CSV.
    """

    logger: logging.Logger
    _ffxivhandler: FFXIVHandler

    id: int
    singular: str
    adjective: int
    plural: str
    possessive_pronoun: int
    starts_with_vowel: int
    pronoun: int
    article: int
    description: str | None
    name: str
    icon: int
    # ItemLevel - https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/ItemLevel.csv
    level_item: XIVItemLevelTyped
    rarity: int
    filter_group: int
    additional_data: int  # Row
    item_ui_category: XIVItemUICategoryEnum  # ItemUICategory
    # ItemSearchCategory - Don't really care about this attribute, I will leave it as an int.
    item_search_category: int
    equip_slot_category: XIVEquipSlotCategoryEnum  # EquipSlotCategory
    # ItemSortCategory - Don't really care about this attribute, I will leave it as an int
    item_sort_category: int
    stack_size: int
    is_unique: bool
    is_untradable: bool
    is_indisposable: bool
    lot: bool
    price_mid: int
    price_low: int
    can_be_hq: int
    dye_count: int
    is_crest_worthy: bool
    # ItemAction - https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/ItemAction.csv
    item_action: int
    cast_time: int
    cooldown: int
    # ClassJob - https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/ClassJob.csv
    class_job_repair: XIVClassJobTyped
    item_repair: int  # ? Suggestion -> ItemRepairResource - Mapped to a dict on FFXIVHandler.
    item_glamour: int  # ? Suggestion -> Item
    desynth: int
    is_collectable: bool
    always_collectable: bool
    aetherial_reduce: int
    level_equip: int
    required_pvp_rank: int
    equip_restriction: int
    class_job_category: XIVClassJobCategoryTyped  # ClassJobCategory
    grand_company: XIVGrandCompanyEnum  # GrandCompany
    item_series: XIVItemSeriesEnum  # ItemSeries
    base_param_modifier: int
    model_main: int
    model_sub: int
    class_job_use: XIVClassJobTyped  # ClassJob
    damage_phys: int
    damage_mag: int
    delay: int
    block_rate: int
    block: int
    defense_phys: int
    defense_mag: int
    base_param0: XIVBaseParamTyped  # BaseParam
    base_param_value0: int
    base_param1: XIVBaseParamTyped  # BaseParam
    base_param_value1: int
    base_param2: XIVBaseParamTyped  # BaseParam
    base_param_value2: int
    base_param3: XIVBaseParamTyped  # BaseParam
    base_param_value3: int
    base_param4: XIVBaseParamTyped  # BaseParam
    base_param_value4: int
    base_param5: XIVBaseParamTyped  # BaseParam
    base_param_value5: int
    item_special_bonus: XIVItemSpecialBonus  # ItemSpecialBonus
    item_special_bonus_param: int
    base_param_special0: XIVBaseParamTyped  # BaseParam
    base_param_value_special0: int
    base_param_special1: XIVBaseParamTyped  # BaseParam
    base_param_value_special1: int
    base_param_special2: XIVBaseParamTyped  # BaseParam
    base_param_value_special2: int
    base_param_special3: XIVBaseParamTyped  # BaseParam
    base_param_value_special3: int
    base_param_special4: XIVBaseParamTyped  # BaseParam
    base_param_value_special4: int
    base_param_special5: XIVBaseParamTyped  # BaseParam
    base_param_value_special5: int
    materialize_type: int
    materia_slot_count: int
    is_advanced_melding_permitted: bool
    is_pvp: bool
    sub_stat_category: int
    is_glamourous: bool

    def __init__(self, data: XIVItemTyped, session: Optional[aiohttp.ClientSession] = None) -> None:
        self.logger: logging.Logger = logging.getLogger()
        self._ffxivhandler = FFXIVHandler.get_handler()
        self.session: Optional[aiohttp.ClientSession] = session

        setattr(self, "_raw", data)

        for key, value in data.items():
            if isinstance(value, int) and value != 0:
                if key == "item_ui_category":
                    try:
                        setattr(self, key, XIVItemUICategoryEnum(value=value))
                    except ValueError:
                        self.logger.warning("Failed to lookup Enum Value: %s in XIVItemUICategoryEnum.", value)
                        setattr(self, key, value)
                elif key == "equip_slot_category":
                    try:
                        setattr(self, key, XIVEquipSlotCategoryEnum(value=value))
                    except ValueError:
                        self.logger.warning("Failed to lookup Enum Value: %s in XIVEquipSlotCategoryEnum.", value)
                        setattr(self, key, value)

                elif key == "grand_company":
                    try:
                        setattr(self, key, XIVGrandCompanyEnum(value=value))
                    except ValueError:
                        self.logger.warning("Failed to lookup Enum Value: %s in XIVGrandCompanyEnum.", value)
                        setattr(self, key, value)

                elif key == "item_special_bonus":
                    try:
                        setattr(self, key, XIVItemSpecialBonus(value=value))
                    except ValueError:
                        self.logger.warning("Failed to lookup Enum Value: %s in XIVItemSpecialBonus.", value)
                        setattr(self, key, value)

                elif key == "item_repair":
                    item = self._ffxivhandler.item_repair_dict.get(value, 0)
                    if item == 0:
                        setattr(self, key, 0)
                    else:
                        setattr(self, key, self._ffxivhandler.get_item(item_id=item))

                elif key == "item_series":
                    try:
                        setattr(self, key, XIVItemSeriesEnum(value=value))
                    except ValueError:
                        self.logger.warning("Failed to lookup Enum Value: %s in XIVItemSeriesEnum.", value)
                        setattr(self, key, value)

                elif key == "item_glamour":
                    setattr(self, key, self._ffxivhandler.get_item(item_id=value))
                else:
                    setattr(self, key, value)

            else:
                setattr(self, key, value)

        # Garland tools stuff
        setattr(self, "_garland_api", GarlandAPI(cache_location=Path(__file__).parent))
        setattr(self, "garland_link", f"https://www.garlandtools.org/db/#item/{self.id}")

        # Universalis stuff.
        self.__market__ = False
        self._no_market: tuple[str, ...] = (
            "Attribute not cached, call <%s.set_current_marketboard> first. | Attribute: %s",
            __class__.__name__,
            self.name,
        )
        self._ffxivhandler.item_dict[str(self.id)] = self

    def __len__(self) -> int:
        return len(str(self.id))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, self.__class__) and self.id == other.id

    def __getattr__(self, name: str) -> Any:
        # # Prevent accessing unset Garland Tools related attributes during runtime.
        # if self.__cached__ is False and name in self.__cached_slots__:
        #     raise AttributeError(self._no_cache)

        # Prevent accessing unset Universalis related attributes during runtime.
        # elif self.__market__ is False and name in self.__market_slots__:
        #     raise AttributeError(self._no_market)

        try:
            return super().__getattribute__(name)
        except AttributeError:
            return None

    def __hash__(self) -> int:
        return hash(self.id)

    def __lt__(self, other: object) -> bool:
        return isinstance(other, self.__class__) and self.id < other.id

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return f"\n{self.__class__.__name__}" + "\n".join([
            f"{e}: {getattr(self, e)}" for e in sorted(self.__dict__) if e.startswith("_") is False
        ])

    @property
    def recipe(self) -> FFXIVJobRecipe | None:
        """
        Retrieves any Recipe information related to the item.

        Returns
        --------
        :class:`FFXIVJobRecipe` | None
            Returns an object representing the Item from recipe.json.
        """
        try:
            return self._ffxivhandler.get_item_job_recipes(item_id=self.id)
        except ValueError:
            return None

    @property
    def fishing(self) -> FFXIVFishParameter | None:
        """
        Retrieves any Fishing information related to the item.

        Returns
        --------
        :class:`FFIXVFishParameter` | None
            Returns an object representing the Item from fishparameter.json
        """
        try:
            return self._ffxivhandler._is_fishable(item_id=self.id)
        except ValueError:
            return None

    @property
    def gathering(self) -> FFXIVGatheringItem | None:
        """
        Retrieves any Gathering information related to the item.

        Returns
        --------
        :class:`FFXIVGatheringItem` | None
            Returns an object representing the Item from gatheringitem.json
        """
        try:
            return self._ffxivhandler._is_gatherable(item_id=self.id)
        except ValueError:
            return None

    @property
    def garland_info(self) -> Any:
        pass

    @property
    def mb_current(self) -> Optional[CurrentData]:
        try:
            return self._mb_current
        except AttributeError:
            return None

    @property
    def mb_history(self) -> Any:
        pass

    async def mb_current_data(self, **kwargs: Unpack[MarketBoardParams]) -> CurrentData:
        # Just for the first call, let's setup UniversalisAPI
        if self._ffxivhandler.universalis is None:
            universalis = UniversalisAPI(session=self.session)
            self._ffxivhandler.universalis = universalis
        else:
            universalis: UniversalisAPI = self._ffxivhandler.universalis
        self._mb_current: CurrentData = await universalis.get_current_data(items=[self.id], **kwargs)
        return self._mb_current


class FFXIVJobRecipe:
    logger: ClassVar[logging.Logger] = logging.getLogger()
    _ffxivhandler: FFXIVHandler

    id: int
    CRP: FFXIVRecipe | None  # Recipe
    BSM: FFXIVRecipe | None  # Recipe
    ARM: FFXIVRecipe | None  # Recipe
    GSM: FFXIVRecipe | None  # Recipe
    LTW: FFXIVRecipe | None  # Recipe
    WVR: FFXIVRecipe | None  # Recipe
    ALC: FFXIVRecipe | None  # Recipe
    CUL: FFXIVRecipe | None  # Recipe

    def __init__(self, data: XIVRecipeLookUpTyped) -> None:
        setattr(self, "_raw", data)
        self._ffxivhandler = FFXIVHandler.get_handler()
        for key, value in data.items():
            if isinstance(value, int) and value == 0:
                continue
            elif key != "id":
                # This takes the value data and builds our FFXIVRecipe class from the raw JSON stored on our FFXIVHandler class.
                setattr(self, key, self._ffxivhandler.get_recipe(recipe_id=str(value)))
            else:
                setattr(self, key, value)

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return f"\n{self.__class__.__name__}" + "\n".join([
            f"{e}: {getattr(self, e)}" for e in sorted(self.__dict__) if e.startswith("_") is False
        ])


class FFXIVRecipe:
    """
    Represents an FFXIV Recipe per XIV Datamining CSV.

    """

    logger: ClassVar[logging.Logger] = logging.getLogger()
    _ffxivhandler: FFXIVHandler

    id: int  # The Recipe # in RecipeLookUp
    number: int
    craft_type: XIVCraftTypeEnum  # CraftType
    recipe_level_table: FFXIVRecipeLevel  # RecipeLevelTable
    item_result: FFXIVItem  # Item - This value is the FINISHED FFXIVItem.item_id value.
    amount_result: int
    item_ingredient0: FFXIVItem  # Item
    amount_ingredient0: int
    item_ingredient1: FFXIVItem  # Item
    amount_ingredient1: int
    item_ingredient2: FFXIVItem  # Item
    amount_ingredient2: int
    item_ingredient3: FFXIVItem  # Item
    amount_ingredient3: int
    item_ingredient4: FFXIVItem  # Item
    amount_ingredient4: int
    item_ingredient5: FFXIVItem  # Item
    amount_ingredient5: int
    item_ingredient6: FFXIVItem  # Item
    amount_ingredient6: int
    item_ingredient7: FFXIVItem  # Item
    amount_ingredient7: int
    recipe_notebook_list: int  # RecipeNotebookList
    display_priority: int
    is_secondary: bool
    material_quality_factor: int
    difficulty_factor: int
    quality_factor: int
    durability_factor: int
    required_quality: int
    required_craftsmanship: int
    required_control: int
    quick_synth_craftsmanship: int
    quick_synth_control: int
    secret_recipe_book: int  # SecretRecipeBook
    quest: int  # Quest
    can_quick_synth: bool
    can_hq: bool
    exp_rewarded: bool
    status_required: int  # Status
    item_required: int  # Item
    is_specialization_required: FFXIVItem
    is_expert: bool
    patch_number: int

    def __init__(self, data: XIVRecipeTyped) -> None:
        self._ffxivhandler: FFXIVHandler = FFXIVHandler.get_handler()
        setattr(self, "_raw", data)

        for key, value in data.items():
            if isinstance(value, int):
                if key in ["is_specialization_required", "item_result"] or (key.startswith("item_ingredient") and value != 0):
                    setattr(self, key, self._ffxivhandler.get_item(item_id=value))

                elif key == "recipe_level_table":
                    setattr(self, key, self._ffxivhandler.get_recipe_level(recipe_level_id=value))

                elif key == "craft_type":
                    try:
                        setattr(self, key, XIVCraftTypeEnum(value=value))
                    except ValueError:
                        self.logger.warning("Failed to lookup Enum Value: %s in XIVCraftTypeEnum.", value)
                        setattr(self, key, value)

                else:
                    setattr(self, key, value)

            else:
                setattr(self, key, value)

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return f"\n{self.__class__.__name__}" + "\n".join([
            f"{e}: {getattr(self, e)}" for e in sorted(self.__dict__) if e.startswith("_") is False
        ])
        # keys = ["craft_type", "recipe_level_table", "item_result", "item_ingredient"]
        # temp: list[str] = []
        # temp.append(self.__class__.__name__)
        # for key in keys:
        #     if key == "item_ingredient":
        #         temp.extend(getattr(self, key + str(i)) for i in range(0, 8))
        #     else:
        #         temp.append(getattr(self, key))
        # return "\n".join(temp)


class FFXIVRecipeLevel:
    logger: ClassVar[logging.Logger] = logging.getLogger()
    _ffxivhandler: FFXIVHandler

    id: int
    class_job_level: int
    stars: int
    suggested_craftsmanship: int
    difficulty: int
    quality: int
    progress_divider: int
    quality_divider: int
    progress_modifier: int
    quality_modifier: int
    durability: int
    conditions_flag: int

    def __init__(self, data: XIVRecipeLevelTyped) -> None:
        setattr(self, "_raw", data)

        for key, value in data.items():
            setattr(self, key, value)

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return f"\n{self.__class__.__name__}" + "\n".join([
            f"{e}: {getattr(self, e)}" for e in sorted(self.__dict__) if e.startswith("_") is False
        ])


class FFXIVFishParameter:
    logger: ClassVar[logging.Logger] = logging.getLogger()
    _ffxivhandler: FFXIVHandler

    text: str
    item: FFXIVItem  # Row
    gathering_item_level: XIVGatheringItemLevelTyped  # GatheringItemLevelConvertTable
    ocean_stars: int
    is_hidden: bool
    fishing_record_type: int  # FishingRecordType
    fishing_spot: FFXIVFishingSpot  # FishingSpot
    gathering_sub_category: int  # GatheringSubCategory
    is_in_log: bool
    achievement_credit: int

    def __init__(self, data: XIVFishParameterTyped) -> None:
        self._ffxivhandler: FFXIVHandler = FFXIVHandler.get_handler()
        setattr(self, "_raw", data)

        for key, value in data.items():
            if isinstance(value, int):
                if key == "item":
                    setattr(self, key, self._ffxivhandler.get_item(item_id=value))
                elif key == "gathering_item_level":
                    setattr(self, key, self._ffxivhandler.get_gathering_level(gathering_level_id=value))
                elif key == "fishing_spot":
                    setattr(self, key, self._ffxivhandler.get_fishing_spot(fishing_spot_id=value))
                else:
                    setattr(self, key, value)
            else:
                setattr(self, key, value)

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return f"\n{self.__class__.__name__}" + "\n".join([
            f"{e}: {getattr(self, e)}" for e in sorted(self.__dict__) if e.startswith("_") is False
        ])


class FFXIVFishingSpot:
    logger: ClassVar[logging.Logger] = logging.getLogger()
    _ffxivhandler: FFXIVHandler

    id: int
    gathering_level: int
    big_fish_on_reach: str
    big_fish_on_end: str
    fishing_spot_category: int
    rare: bool
    territory_type: int  # TerritoryType
    place_name_main: XIVPlaceNameTyped  # PlaceName
    place_name_sub: XIVPlaceNameTyped  # PlaceName
    x: int
    z: int
    radius: int
    item0: FFXIVItem  # Item
    item1: FFXIVItem  # Item
    item2: FFXIVItem  # Item
    item3: FFXIVItem  # Item
    item4: FFXIVItem  # Item
    item5: FFXIVItem  # Item
    item6: FFXIVItem  # Item
    item7: FFXIVItem  # Item
    item8: FFXIVItem  # Item
    item9: FFXIVItem  # Item
    place_name: XIVPlaceNameTyped  # PlaceName
    order: int

    def __init__(self, data: XIVFishingSpotTyped) -> None:
        self._ffxivhandler: FFXIVHandler = FFXIVHandler.get_handler()
        setattr(self, "_raw", data)

        for key, value in data.items():
            if isinstance(value, int) and value != 0:
                if key.startswith("item"):
                    setattr(self, key, self._ffxivhandler.get_item(item_id=value))
                elif key in ["place_name_main", "place_name_sub", "place_name"]:
                    setattr(self, key, self._ffxivhandler.get_place_name(place_id=value))
                else:
                    setattr(self, key, value)
            else:
                setattr(self, key, value)

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return f"\n{self.__class__.__name__}" + "\n".join([
            f"{e}: {getattr(self, e)}" for e in sorted(self.__dict__) if e.startswith("_") is False
        ])


class FFXIVGatheringItem:
    logger: ClassVar[logging.Logger] = logging.getLogger()
    _ffxivhandler: FFXIVHandler

    item: int  # Row
    gathering_item_level: XIVGatheringItemLevelTyped  # GatheringItemLevelConvertTable
    quest: bool  # Quest
    is_hidden: bool

    def __init__(self, data: XIVGatheringItemTyped) -> None:
        self._ffxivhandler = FFXIVHandler.get_handler()
        setattr(self, "_raw", data)

        for key, value in data.items():
            if key == "gathering_item_level" and isinstance(value, int):
                setattr(self, key, self._ffxivhandler.get_gathering_level(gathering_level_id=value))
            else:
                setattr(self, key, value)

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return f"\n{self.__class__.__name__}" + "\n".join([
            f"{e}: {getattr(self, e)}" for e in sorted(self.__dict__) if e.startswith("_") is False
        ])


class FFXIVPlaceName:
    logger: ClassVar[logging.Logger] = logging.getLogger()
    _ffxivhandler: FFXIVHandler

    id: int
    name: str
    name_no_article: str

    def __init__(self, data: XIVFishingSpotTyped) -> None:
        self._ffxivhandler = FFXIVHandler.get_handler()
        setattr(self, "_raw", data)

        for key, value in data.items():
            setattr(self, key, value)

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return f"\n{self.__class__.__name__}" + "\n".join([
            f"{e}: {getattr(self, e)}" for e in sorted(self.__dict__) if e.startswith("_") is False
        ])
