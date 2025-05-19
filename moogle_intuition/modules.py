from __future__ import annotations

import asyncio
import csv
import json
import logging
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from random import randint
from typing import TYPE_CHECKING, Any, ClassVar, Self, Union, overload

import aiohttp
from garlandtools import GarlandTools
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
    DataCenterEnum,
    DataCenterToWorlds,
    GarlandToolsAPI_PatchEnum,
    GarlandToolsAPIIconTypeEnum,
    InventoryLocations,
    ItemQualityEnum,
    JobEnum,
    LocalizationEnum,
    WorldEnum,
    XIVCraftTypeEnum,
    XIVEquipSlotCategoryEnum,
    XIVGrandCompanyEnum,
    XIVItemSeriesEnum,
    XIVItemSpecialBonus,
    XIVItemUICategoryEnum,
)
from ._types import (
    GarlandToolsAPI_FishingLocationsTyped,
    GarlandToolsAPI_ItemKeysTyped,
    GarlandToolsAPI_MobTyped,
    GarlandToolsAPI_NPCTyped,
    UniversalisAPI_CurrentKeysTyped,
)

if TYPE_CHECKING:
    import asqlite
    from aiohttp import ClientResponse
    from requests_cache import CachedResponse, OriginalResponse

    from ._types import (
        FFXIVUserDBTyped,
        FFXIVWatchListDBTyped,
        GarlandToolsAPI_FishingLocationsTyped,
        GarlandToolsAPI_ItemAttrTyped,
        GarlandToolsAPI_ItemCraftIngredientsTyped,
        GarlandToolsAPI_ItemCraftTyped,
        GarlandToolsAPI_ItemFishSpotsTyped,
        GarlandToolsAPI_ItemFishTyped,
        GarlandToolsAPI_ItemIngredientsTyped,
        GarlandToolsAPI_ItemKeysTyped,
        GarlandToolsAPI_ItemPartialsTyped,
        GarlandToolsAPI_ItemTradeShopsTyped,
        GarlandToolsAPI_ItemTyped,
        GarlandToolsAPI_MobTyped,
        GarlandToolsAPI_NPCTyped,
        ItemIDFieldsTyped,
        LocationIDsTyped,
        UniversalisAPI_CurrentKeysTyped,
        UniversalisAPI_CurrentTyped,
        UniversalisAPI_HistoryTyped,
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


class FFXIVHandler:
    """
    Our handler type class for interacting with FFXIV Items, Recipes and other Data structures inside of FFXIV.

    Parameters
    -----------
    auto_builder: bool, optional
        Controls if the Class should generate the respective keys for item lookup, default is True.
        - Set to `False` if generating CSV/JSON files.

    """

    logger: ClassVar[logging.Logger] = logging.getLogger()

    # File Paths
    data_path: ClassVar[Path] = Path(__file__).parent.joinpath("xiv_datamining")
    session: aiohttp.ClientSession

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
    xiv_data_item_url: ClassVar[str] = (
        "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/Item.csv"
    )

    # Recipe Handling.
    # I am storing "Recipe ID" : "Item Result ID"
    # recipe_dict: dict[str, int]
    recipe_json: dict[str, XIVRecipeTyped]
    xiv_data_recipe_url: ClassVar[str] = (
        "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/Recipe.csv"
    )

    # Job Recipe Table
    recipelookup_json: dict[str, XIVRecipeLookUpTyped]
    xiv_data_recipe_lookup_url: ClassVar[str] = (
        "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/RecipeLookup.csv"
    )
    # Recipe Level Table
    recipelevel_json: dict[str, XIVRecipeLevelTyped]
    xiv_data_recipe_level_url: ClassVar[str] = (
        "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/RecipeLevelTable.csv"
    )

    # Gatherable Items Handling.
    gatheringitem_dict: dict[str, int]
    gatheringitem_json: dict[str, XIVGatheringItemTyped]
    xiv_data_gathering_item_url: ClassVar[str] = (
        "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/GatheringItem.csv"
    )

    gatheringitemlevel_json: dict[str, XIVGatheringItemLevelTyped]
    xiv_data_gathering_item_level_url: ClassVar[str] = (
        "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/GatheringItemLevelConvertTable.csv"
    )

    # Fishing Related
    fishparameter_json: dict[str, XIVFishParameterTyped]
    # This is stored with FLIPPED key to values ("Item ID" : "Dict Index")
    fishparameter_dict: dict[int, str]
    xiv_data_fish_parameter_url: ClassVar[str] = (
        "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/FishParameter.csv"
    )
    fishingspot_json: dict[str, XIVFishingSpotTyped]
    xiv_data_fishing_spot_url: ClassVar[str] = (
        "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/FishingSpot.csv"
    )

    # Location Information
    placename_json: dict[str, XIVPlaceNameTyped]
    xiv_data_place_name_url = (
        "https://raw.githubusercontent.com/xivapi/ffxiv-datamining/refs/heads/master/csv/PlaceName.csv"
    )

    def __init__(self, auto_builder: bool = True) -> None:
        self.logger.name = f" {__class__.__name__} "
        # self.session = aiohttp.ClientSession()
        if auto_builder is True:
            # Quick reference dictionaries for easier lookup.
            self.generate_reference_dict(file_name="item.json", value_get="name")

            # Recipe related dict/JSON
            self.generate_reference_dict(file_name="recipe.json", value_get="item_result")
            self.generate_reference_dict(file_name="recipelookup.json", no_ref_dict=True)
            self.generate_reference_dict(file_name="recipelevel.json", no_ref_dict=True)

            # Fishing related dict/JSON
            self.generate_reference_dict(
                file_name="fishparameter.json", flip_key_value=True, value_get="item"
            )
            self.generate_reference_dict(file_name="fishingspot.json", no_ref_dict=True)

            # Gathering related dict/JSON.
            self.generate_reference_dict(file_name="gatheringitem.json", value_get="item")
            self.generate_reference_dict(file_name="gatheringitemlevel.json", no_ref_dict=True)

            # Location related JSON
            self.generate_reference_dict(file_name="placename.json", no_ref_dict=True)

    @classmethod
    def get_handler(cls) -> FFXIVHandler:
        """
        Retrieves an existing FFXIVItemHandler class object.\n

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
            raise ValueError(
                "Failed to setup Handler. You need to initiate `<class FFXIVItemHandler>` first."
            )
        return cls._instance

    def __new__(cls, auto_builder: bool = True, *args: Any, **kwargs: Any) -> FFXIVHandler | None:
        if not hasattr(cls, "_instance"):
            cls._instance: FFXIVHandler = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def generate_reference_dict(
        self,
        file_name: str,
        value_get: str | None = None,
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

    def get_item(
        self,
        item_id: int | None = None,
        item_name: str | None = None,
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
            res: str | FFXIVItem | None = self.item_dict.get(str(item_id), None)
            if isinstance(res, FFXIVItem):
                return res
            # If we get a string back it's most likely the name we stored as quick ref.
            elif isinstance(res, str):
                data: XIVItemTyped | None = self.item_json.get(str(item_id), None)

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
                        raise ValueError(
                            "We failed to lookup Item Name: %s in our item.json file.", item_name
                        )
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
                            raise ValueError(
                                "We failed to lookup Item ID: %s in our item.json file.", item_id
                            )
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
        data: XIVRecipeLookUpTyped | None = self.recipelookup_json.get(str(item_id), None)
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
        data: XIVRecipeTyped | None = self.recipe_json.get(recipe_id, None)
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
        data: XIVRecipeLevelTyped | None = self.recipelevel_json.get(str(recipe_level_id), None)
        if data is None:
            raise ValueError(
                "We failed to lookup Recipe Level ID: %s in our recipelevel.json file",
                recipe_level_id,
            )
        return FFXIVRecipeLevel(data=data)

    # TODO - docstring
    def get_gathering_level(self, gathering_level_id: int) -> XIVGatheringItemLevelTyped:
        self.logger.debug(
            "Searching... Gathering Item Level ID: %s | Entries: %s",
            gathering_level_id,
            len(self.gatheringitemlevel_json),
        )
        data: XIVGatheringItemLevelTyped | None = self.gatheringitemlevel_json.get(
            str(gathering_level_id), None
        )
        if data is None:
            raise ValueError(
                "We failed to lookup Gathering Item Level ID: %s in our gatheringitemlevel.json file",
                gathering_level_id,
            )
        return data

    # TODO - docstring
    def get_fishing_spot(self, fishing_spot_id: int) -> FFXIVFishingSpot:
        self.logger.debug(
            "Searching... Fishing Spot ID: %s | Entries: %s",
            fishing_spot_id,
            len(self.fishingspot_json),
        )
        data: XIVFishingSpotTyped | None = self.fishingspot_json.get(str(fishing_spot_id), None)
        if data is None:
            raise ValueError(
                "We failed to lookup Fishing Spot ID: %s in our fishingspot.json file",
                fishing_spot_id,
            )
        return FFXIVFishingSpot(data=data)

    # TODO - docstring
    def get_place_name(self, place_id: int) -> XIVPlaceNameTyped:
        self.logger.debug(
            "Searching... Place Name ID: %s | Entries: %s",
            place_id,
            len(self.placename_json),
        )
        data: XIVPlaceNameTyped | None = self.placename_json.get(str(place_id), None)
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
        key: str | None = self.fishparameter_dict.get(item_id, None)
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
            data: XIVFishParameterTyped | None = self.fishparameter_json.get(str(key), None)
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

    async def data_building(
        self,
        csv_name: str,
        auto_pep8: bool = True,
        convert_pound: bool = True,
        typed_dict: bool = False,
        typed_file_name: str | None = None,
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
            self.write_to_file(path=self.data_path, file_name=json_name, data=res)

            if typed_dict:
                res = self.generate_typed_dict(class_name=typed_class_name, keys=keys, key_types=types)
                self.write_to_file(path=Path(__file__).parent, file_name=typed_file_name, data=res)
        else:
            data: bytes = await self.get_file_data(url=input("Please provide a URL for this CSV file:"))
            self.write_to_file(path=self.data_path, file_name=csv_name, data=data)
            await self.data_building(csv_name=csv_name, typed_dict=typed_dict)

    async def get_file_data(self, url: str) -> bytes:
        """
        Basic **GET** url without headers.

        Parameters
        -----------
        url: :class:`str`
            The url content to read.

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
            res: ClientResponse = await session.get(url=url)
            if res.status != 200:
                raise ConnectionError()
            if res.content_type == "application/json":
                return await res.json()
            else:
                return await res.content.read()

    def write_to_file(
        self,
        file_name: str,
        data: bytes | dict | str,
        path: Path = Path(__file__).parent,
        mode: str = "w+",
    ) -> None:
        """
        Basic file dump with json handling. Pass data in as a dict and it will be written out in JSON format with an indent of 4.

        Parameters
        -----------
        path: :class:`Path`, optional
            The Path to write the data, default's to this files
        file_name: :class:`str`
            The name of the file, changed to all lowercase.
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

    def pep8_key_name(self, key_name: str) -> str:
        """
        Converts the provided `key_name` parameter into something that is pep8 compliant yet clear as to what it is for.
        - Adds a `_` before any uppercase char in the `key_name` and then `.lowers()` that uppercase char.

        *Note*
            Has special cases in `self.ignored_keys` to allow adding/removing of needed keys.



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
        if key_name in self.ignored_keys:
            return key_name

        for k, v in self.pre_formatted_keys.items():
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


class FFXIVItem:
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

    def __init__(self, data: XIVItemTyped) -> None:
        self.logger: logging.Logger = logging.getLogger()
        self._ffxivhandler = FFXIVHandler.get_handler()

        setattr(self, "_raw", data)

        for key, value in data.items():
            if isinstance(value, int) and value != 0:
                if key == "item_ui_category":
                    try:
                        setattr(self, key, XIVItemUICategoryEnum(value=value))
                    except ValueError:
                        self.logger.warning(
                            "Failed to lookup Enum Value: %s in XIVItemUICategoryEnum.", value
                        )
                        setattr(self, key, value)
                elif key == "equip_slot_category":
                    try:
                        setattr(self, key, XIVEquipSlotCategoryEnum(value=value))
                    except ValueError:
                        self.logger.warning(
                            "Failed to lookup Enum Value: %s in XIVEquipSlotCategoryEnum.", value
                        )
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
        setattr(self, "_garland_api", GarlandAPIWrapper(cache_location=Path(__file__).parent))
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
                if key in ["is_specialization_required", "item_result"] or (
                    key.startswith("item_ingredient") and value != 0
                ):
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


class GarlandAPIWrapper(GarlandTools):
    """
    My own wrapper for the GarlandTools API.
    - Handling the status code checks.
    - Typed Data returns and conversions for some functions.
    """

    def __init__(self, cache_location: Path, cache_expire_after: int = 86400) -> None:
        self.logger: logging.Logger = logging.getLogger()
        if cache_location.exists() and cache_location.is_file():
            raise FileExistsError("You specified a Path to a File, it must be a directory.")
        super().__init__(cache_location=cache_location.as_posix(), cache_expire_after=cache_expire_after)

    def icon(
        self,
        icon_id: int,
        icon_type: GarlandToolsAPIIconTypeEnum = GarlandToolsAPIIconTypeEnum.item,
    ) -> BytesIO:
        """
        icon _summary_

        Parameters
        -----------
        icon_id: :class:`int`
            _description_.
        icon_type: :class:`GarlandToolsAPIIconTypeEnum`, optional
            _description_, by default GarlandToolsAPIIconTypeEnum.item.

        Returns
        --------
        :class:`BytesIO`
            _description_.

        Raises
        -------
        :exc:`ConnectionError`
            _description_.
        """
        res: OriginalResponse | CachedResponse = super().icon(icon_type=icon_type.value, icon_id=icon_id)
        if res.status_code == 200:
            return BytesIO(initial_bytes=res.content)
        self.logger.error(
            "We encountered an error looking up this Icon ID: %s Type: %s from garlandtools.icon API. | Status Code: %s",
            icon_id,
            icon_type,
            res.status_code,
        )
        raise ConnectionError(
            "We encountered an error looking up this Icon ID: %s Type: %s for garlandtools.icon API. | Status Code: %s",
            icon_id,
            icon_type,
            res.status_code,
        )

    def item(self, item_id: int) -> GarlandToolsAPI_ItemTyped:
        """
        item _summary_

        Parameters
        -----------
        item_id: :class:`int`
            _description_.

        Returns
        --------
        :class:`GarlandToolsAPI_ItemTyped`
            _description_.

        Raises
        -------
        :exc:`ConnectionError`
            _description_.
        """
        res: OriginalResponse | CachedResponse = super().item(item_id=item_id)
        if res.status_code == 200:
            data: GarlandToolsAPI_ItemTyped = res.json()
            return data
        self.logger.error(
            "We encountered an error looking up this Item ID: %s for GarlandTools. | Status Code: %s",
            item_id,
            res.status_code,
        )
        raise ConnectionError(
            "We encountered an error looking up this Item ID: %s for GarlandTools. | Status Code: %s",
            item_id,
            res.status_code,
        )

    def npc(self, npc_id: int) -> GarlandToolsAPI_NPCTyped:
        """
        npc _summary_

        Parameters
        -----------
        npc_id: :class:`int`
            _description_.

        Returns
        --------
        :class:`GarlandToolsAPI_NPCTyped`
            _description_.

        Raises
        -------
        :exc:`ConnectionError`
            _description_.
        """
        res: OriginalResponse | CachedResponse = super().npc(npc_id=npc_id)
        if res.status_code == 200:
            data: dict[str, GarlandToolsAPI_NPCTyped] = res.json()
            return data["npc"]
        self.logger.error(
            "We encountered an error looking up this NPC ID: %s for GarlandTools. | Status Code: %s",
            npc_id,
            res.status_code,
        )
        raise ConnectionError(
            "We encountered an error looking up this NPC ID: %s for GarlandTools. | Status Code: %s",
            npc_id,
            res.status_code,
        )

    def mob(self, mob_id: int) -> GarlandToolsAPI_MobTyped:
        """
        mob _summary_

        Parameters
        -----------
        mob_id: :class:`int`
            _description_.

        Returns
        --------
        :class:`GarlandToolsAPI_MobTyped`
            _description_.

        Raises
        -------
        :exc:`ConnectionError`
            _description_.
        """
        res: OriginalResponse | CachedResponse = super().mob(mob_id=mob_id)
        if res.status_code == 200:
            data: dict[str, GarlandToolsAPI_MobTyped] = res.json()
            return data["mob"]
        self.logger.error(
            "We encountered an error looking up this Mob ID: %s for GarlandTools. | Status Code: %s",
            mob_id,
            res.status_code,
        )
        raise ConnectionError(
            "We encountered an error looking up this Mob ID: %s for GarlandTools. | Status Code: %s",
            mob_id,
            res.status_code,
        )

    def fishing(self) -> GarlandToolsAPI_FishingLocationsTyped:
        """
        fishing _summary_

        Returns
        --------
        :class:`GarlandToolsAPI_FishingLocationsTyped`
            _description_.

        Raises
        -------
        :exc:`ConnectionError`
            _description_.
        """
        res: OriginalResponse | CachedResponse = super().fishing()
        if res.status_code == 200:
            data: dict[str, GarlandToolsAPI_FishingLocationsTyped] = res.json()
            return data["browse"]
        self.logger.error(
            "We encountered an error looking up Fishing Locations for GarlandTools. | Status Code: %s",
            res.status_code,
        )
        raise ConnectionError(
            "We encountered an error looking up Fishing Locations for GarlandTools. | Status Code: %s",
            res.status_code,
        )


class UniversalisAPIWrapper:
    """
    My built in class to handle Universalis API queries.
    """

    # Last time an API call was made.
    api_call_time: datetime

    # Current limit is 20 API calls per second.
    max_api_calls: int

    # Universalis API stuff
    base_api_url: str
    api_trim_item_fields: str

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self.session: aiohttp.ClientSession = session
        self.logger: logging.Logger = logging.getLogger()
        self.logger.name = __class__.__name__

        # Universalis API
        self.base_api_url = "https://universalis.app/api/v2"
        self.api_call_time = datetime.now()
        self.max_api_calls = 20

        # These are the "Trimmed" API fields for Universalis Market Results.
        self.api_trim_item_fields = "&fields=itemID%2Clistings.quantity%2Clistings.worldName%2Clistings.pricePerUnit%2Clistings.hq%2Clistings.total%2Clistings.tax%2Clistings.retainerName%2Clistings.creatorName%2Clistings.lastReviewTime%2ClastUploadTime"

    async def universalis_call_api(
        self, url: str
    ) -> UniversalisAPI_CurrentTyped | UniversalisAPI_HistoryTyped:
        cur_time: datetime = datetime.now()
        max_diff = timedelta(milliseconds=1000 / self.max_api_calls)
        if (cur_time - self.api_call_time) < max_diff:
            sleep_time: float = (max_diff - (cur_time - self.api_call_time)).total_seconds() + 0.1
            await asyncio.sleep(delay=sleep_time)

        data: ClientResponse = await self.session.get(url=url)
        if data.status != 200:
            self.logger.error(
                "We encountered an error in Universalis call_api. Status: %s | API: %s",
                data.status,
                url,
            )
            raise ConnectionError(
                "We encountered an error in Universalis call_api. Status: %s | API: %s",
                data.status,
                url,
            )
        elif data.status == 400:
            self.logger.error(
                "We encountered an error in Universalis call_api due to invalid Parameters. Status: %s | API: %s",
                data.status,
                url,
            )
            raise ConnectionError(
                "We encountered an error in Universalis call_api due to invalid Parameters. Status: %s | API: %s",
                data.status,
                url,
            )
        # 404 - The world/DC or item requested is invalid. When requesting multiple items at once, an invalid item ID will not trigger this.
        # Instead, the returned list of unresolved item IDs will contain the invalid item ID or IDs.
        elif data.status == 404:
            self.logger.error(
                "We encountered an error in Universalis call_api due to invalid World/DC or Item ID. Status: %s | API: %s",
                data.status,
                url,
            )
            raise ConnectionError(
                "We encountered an error in Universalis call_api due to invalid World/DC or Item ID. Status: %s | API: %s",
                data.status,
                url,
            )

        self.api_call_time = datetime.now()
        res: UniversalisAPI_CurrentTyped = await data.json()
        return res

    async def get_universalis_current_mb_data(
        self,
        items: Union[FFXIVItem, list[FFXIVItem], list[str], str],
        world_or_dc: DataCenterEnum | WorldEnum = DataCenterEnum.Crystal,
        num_listings: int = 10,
        num_history_entries: int = 10,
        item_quality: ItemQualityEnum = ItemQualityEnum.NQ,
        trim_item_fields: bool = True,
    ) -> UniversalisAPI_CurrentTyped:
        print("MARKETBOARD DATA", "DATACENTER", world_or_dc.name, "LEN", len(items), type(items))

        if isinstance(items, list):
            for e in items:
                items = ",".join([str(e.item_id) if isinstance(e, FFXIVItem) else e])
        api_url: str = f"{self.base_api_url}/{world_or_dc.name}/{items}?listings={num_listings}&entries={num_history_entries}&hq={item_quality.value}"
        if trim_item_fields:
            api_url += self.api_trim_item_fields

        res: UniversalisAPI_CurrentTyped = await self.universalis_call_api(url=api_url)  # type: ignore - I know the response type because of the URL
        return res

    # todo - need to finish this command, understand overloads to define return types better
    async def marketboard_history_data(
        self,
        items: Union[list[str], str],
        data_center: DataCenterEnum = DataCenterEnum(value=8),
        num_listings: int = 10,
        min_price: int = 0,
        max_price: Union[int, None] = None,
        history: int = 604800000,
    ) -> UniversalisAPI_CurrentTyped | UniversalisAPI_HistoryTyped:
        """

        Universalis Marketboard History Data

        API: https://docs.universalis.app/#market-board-sale-history

        Example URL:
         `https://universalis.app/api/v2/history/Crystal/4698?entriesToReturn=10&statsWithin=604800000&minSalePrice=0&maxSalePrice=9999999999999999`

        Parameters
        -----------
        items: :class:`Union[list[str], str]`
            The Item IDs to look up, limit of 99 entries.
        data_center: :class:`DataCenterEnum`, optional
            _description_, by default DataCenterEnum(value=8).
        num_listings: :class:`int`, optional
            _description_, by default 10.
        min_price: :class:`int`, optional
            _description_, by default 0.
        max_price: :class:`Union[int, None]`, optional
            _description_, by default None.
        history: :class:`int`, optional
            _description_, by default 604800000.

        Raises
        -------
        ValueError:
            If the length of `items` exceeds 99.

        Returns
        --------
        :class:`Any`
            _description_.
        """
        if len(items) > 100:
            raise ValueError(
                "We encountered an error in Universalis.history_marketboard_data(), the array length of items was too long, must be under 100. | %s",
                len(items),
            )

        if isinstance(items, list):
            items = ",".join(items)

        api_url: str = f"{self.base_api_url}/history/{data_center}/{items}?entriesToReturn={num_listings}&statsWithin={history}&minSalePrice={min_price}&maxSalePrice={max_price}"
        res: UniversalisAPI_CurrentTyped | UniversalisAPI_HistoryTyped = await self.universalis_call_api(
            url=api_url
        )
        return res
