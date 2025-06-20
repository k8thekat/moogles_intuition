from __future__ import annotations

import logging
from pprint import pformat
from typing import TYPE_CHECKING, Any, ClassVar, Optional

import aiohttp
import bs4
from bs4.element import AttributeValueList, NavigableString

if TYPE_CHECKING:
    from collections.abc import Iterator

    from bs4._typing import _AtMostOneElement, _AttributeValue, _QueryResults, _StrainableAttribute

    from ._types import BaitsTyped, FishingDataTyped


__all__ = ("FF14Angler", "FF14Fish", "FishingBaits")


class FF14Angler:
    """
    A class to handle parsing `https://en.ff14angler.com/` spot and location id information into a data structure that yields useful information such as
    the best lure, chance to catch and any other restrictions associated with the fish.

    """

    logger: ClassVar[logging.Logger] = logging.getLogger(__name__)

    session: Optional[aiohttp.ClientSession]
    location_map: Optional[dict[str, int]]

    def __init__(self, session: Optional[aiohttp.ClientSession]) -> None:
        self.session = session
        pass

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        self.logger.debug(pformat(vars(self)))
        return f"\n\n__{self.__class__.__name__}__\n" + "\n".join([
            f"{e}: {getattr(self, e)}" for e in sorted(self.__dict__) if e.startswith("_") is False
        ])

    async def get_fish_data(self, location_id: int, spearfishing: bool = False) -> Optional[dict[int, FishingDataTyped]]:
        """
        Retrieve FF14 Angler data from `https://en.ff14angler.com/spot/[location_id]` via `aiohttp.ClientSession.get()`.
        - Parses the data into a dictionary keyed off the {:class:`int` : :class:`FishingDataTyped`}

        - **Warning** - Do not use a `FishingSpotID` from `xivdataminig` that does not related to the ID that ff14angler.com uses.


        Parameters
        -----------
        location_id: :class:`int`
            The Location ID from FF14angler.com website.

        Returns
        --------
        :class:`Optional[dict[int, FishingDataTyped]]`
            A dictionary with the key value being the fish ID and data representing the tables found on the ff14angler.com/spot/location_id page..
        """
        if self.session is None:
            self.session = aiohttp.ClientSession()

        url: str = "https://en.ff14angler.com/spot/" + str(location_id)
        res: aiohttp.ClientResponse = await self.session.get(url=url)
        if res.status != 200:
            self.logger.error(
                "<%s.get_fish_data> failed to access the url. | Status Code: %s | URL: %s", __class__.__name__, res.status, url
            )
            return None
        if res.content_type == "application/json":
            self.logger.error(
                "<%s.get_fish_data> is of the wrong content_type. | Content Type: %s | URL: %s", __class__.__name__, res.content_type, url
            )
            return None
        else:
            fishing_html_data: bytes = await res.content.read()

        soup = FF14Soup(fishing_html_data, "html.parser", session=None)

        # ID is the ff14 angler fishing ID, each entry is a dictionary containing
        #    name, TackleID->percent, Restrictions
        fishing_data: dict[int, FishingDataTyped] = {}

        # get the available fish, skipping headers/etc
        info_section: Optional[CustomTag] = soup.find(class_="info_section list")
        if info_section is None:
            self.logger.error("<%s.get_fish_data> failed to find `class_='info_section list'`.", __class__.__name__)
            return None

        info_sec_children: list[CustomTag] = list(info_section.children)

        try:
            # Attempt to index to the fish data, this could fail.
            poss_fish: CustomTag = info_sec_children[5]
        except IndexError:
            self.logger.error("<%s.get_fish_data> had an <IndexError> for `poss_fish`.", __class__.__name__)
            return None
        avail_fish: list[CustomTag] = list(poss_fish.children)

        cur_fish_tug = "UNK"
        cur_fish_double = 0
        for fish_index in range(1, len(avail_fish), 2):
            cur_fish_page: CustomTag = avail_fish[fish_index]
            cur_fish: list[CustomTag] = list(cur_fish_page.children)

            # This could fail with an IndexError
            try:
                cur_fish_data: CustomTag = cur_fish[3]
            except IndexError:
                self.logger.error("<%s.get_fish_data> had an <IndexError> for `cur_fish_data`", __class__.__name__)
                return fishing_data

            cur_fish_id_name: Optional[CustomTag] = cur_fish_data.find("a")
            if cur_fish_id_name is None:
                return fishing_data

            poss_cur_fish_id: Optional[_AttributeValue] = cur_fish_id_name.get("href")
            if poss_cur_fish_id is None or isinstance(poss_cur_fish_id, AttributeValueList):
                return fishing_data

            cur_fish_id = int(poss_cur_fish_id.split("/")[-1])
            # This could break due to an IndexError.
            try:
                poss_fish_name: CustomTag = list(cur_fish_id_name.children)[2]
            except IndexError:
                self.logger.warning("<%s.get_fish_data> had an <IndexError> for `poss_fish_name`", __class__.__name__)
                continue

            if isinstance(poss_fish_name, NavigableString):
                cur_fish_name: str = poss_fish_name.strip()
            else:
                self.logger.warning(
                    "<%s.get_fish_data> encountered an <TypeError>, `poss_fish_name` is not of type `bs4.NavigableString`. | Type: %s",
                    __class__.__name__,
                    type(poss_fish_name),
                )
                continue

            restriction_list: list[str] = []
            cur_fish_restrictions: CustomTag = cur_fish[5]

            if cur_fish_restrictions.string != None:
                restrict_str: str = cur_fish_restrictions.string.strip()
                if len(restrict_str):
                    restriction_list.append(restrict_str.title())
            else:
                for entry in cur_fish_restrictions.children:
                    if entry.name == "img":
                        entry_title: Optional[_AttributeValue] = entry.get("title", None)
                        if entry_title is None:
                            self.logger.warning(
                                "<%s.get_fish_data> encountered a KeyError for `entry_title` in `cur_fish_restrictions`.",
                                __class__.__name__,
                            )
                            continue
                        if isinstance(entry_title, str):
                            restriction = entry_title.split(" ")
                            restriction_list.append((" ".join(restriction[1:])).title())

                    # What in the holy fuck is up with their typing..
                    # I cannot call `entry.name is None`; the rest of the code evals to `Never`... sigh..
                    elif isinstance(entry, NavigableString) and entry.name is not None and entry.string is not None:
                        restrict_str = entry.string.strip()
                        if len(restrict_str):
                            restriction_list.append(restrict_str.title())
                    else:
                        self.logger.warning(
                            "<%s.get_fish_data> encountered a <TypeError> for `entry` in `cur_fish_restrictions`. | Type: %s | Name Attr: %s | String Attr: %s",
                            __class__.__name__,
                            type(entry),
                            entry.name,
                            entry.string,
                        )
                        continue

            # Index Check
            # Checking Fish Tug information in a new section.
            try:
                possible_tug_data: CustomTag = cur_fish[7]
                tug_section: _AtMostOneElement = possible_tug_data.find(class_="tug_sec")
                cur_fish_tug = None if tug_section is None or tug_section.string is None else tug_section.string.strip()

            except IndexError:
                self.logger.warning("<%s.get_fish_data> had an <IndexError> for `possible_tug_data`", __class__.__name__)

            # Index check
            # Checking Fish Double Hook information in a new section.
            try:
                cur_fish_double_data: CustomTag = cur_fish[9]
                cur_fish_double_page: Optional[CustomTag] = cur_fish_double_data.find(class_="strong")
                if cur_fish_double_page is not None and cur_fish_double_page.string != None:
                    cur_fish_double = int(cur_fish_double_page.string.strip()[1:])
                else:
                    cur_fish_double = 0
            except IndexError:
                self.logger.warning("<%s.get_fish_data> had an <IndexError> for `cur_fish_double_data`", __class__.__name__)

            fishing_data[cur_fish_id] = {
                "fish_name": cur_fish_name,
                "restrictions": restriction_list,
                "hook_time": cur_fish_tug,
                "double_fish": cur_fish_double,
                "baits": {},
            }

        effective_bait_header: Optional[CustomTag] = soup.find(id="effective_bait")
        if effective_bait_header is not None:
            effective_bait: list[CustomTag] = list(effective_bait_header.children)

            # get the bait IDs and insert them into the data set
            fish_ids: list[int | float] = []
            # Could be an Index Error
            try:
                poss_entries: CustomTag = effective_bait[1]
            except IndexError:
                self.logger.error("<%s.get_fish_data> had an <IndexError> for `poss_entries`", __class__.__name__)
                return fishing_data

            # all entries have a blank gap, we also skip the first box as
            # it is empty due to the grid design
            fish_entries: list[CustomTag] = list(poss_entries.children)
            for index in range(3, len(fish_entries), 2):
                cur_fish_entry: Optional[CustomTag] = fish_entries[index].find("a")
                # poss_fish_name: Optional[_AttributeValue] = cur_fish_entry.get("title")
                if cur_fish_entry is None:
                    continue
                poss_fish_id: Optional[_AttributeValue] = cur_fish_entry.get("href")
                if isinstance(poss_fish_id, str):
                    cur_fish_id = int(poss_fish_id.split("/")[-1])
                    fish_ids.append(cur_fish_id)

            # now cycle through and grab % values for each fish, similar to the above
            # every other entry is blank
            for bait_index in range(3, len(effective_bait), 2):
                bait_numbers: list[CustomTag] = list(effective_bait[bait_index].children)
                try:
                    bait_info_page: CustomTag = bait_numbers[0]
                except IndexError:
                    self.logger.warning("<%s.get_fish_data> had an <IndexError> for `cur_bait_info_page`", __class__.__name__)
                    continue

                bait_info: Optional[CustomTag] = bait_info_page.find("a")
                if bait_info is None:
                    continue
                poss_id: Optional[_AttributeValue] = bait_info.get("href", None)
                if isinstance(poss_id, str):
                    bait_id = int(poss_id.split("/")[-1])
                else:
                    self.logger.warning("<%s.get_fish_data> encountered a <TypeError>, `poss_id`. | Type: %s ", type(poss_id))
                    continue

                bait_name: Optional[_AttributeValue] = bait_info.get("title", None)
                if bait_name is None or isinstance(bait_name, AttributeValueList):
                    continue
                for cur_bait_index in range(2, len(bait_numbers), 2):
                    add_bait_info_header: Optional[CustomTag] = bait_numbers[cur_bait_index].find("canvas")
                    if add_bait_info_header is None:
                        continue
                    page_percent: Optional[_AttributeValue] = add_bait_info_header.get("value")
                    if isinstance(page_percent, str):
                        bait_percent = float(page_percent) / 100
                        # ? This could cause issues in the future if we get floating points instead of whole ints.
                        cur_fish_id = int(fish_ids[int((cur_bait_index - 2) / 2)])
                        fishing_data[cur_fish_id]["baits"][bait_id] = {"bait_name": bait_name, "hook_percent": f"{bait_percent:.2f}"}
        return fishing_data

    def match_select_spot(self, tag: bs4.Tag) -> bool:
        """
        Creates a generic `bs4.Tag` with set values to check against within the `bs4.BeautifulSoup.find()` name parameter.
        - This is in reference to the `bs4._typing` -> `_TagMatchFunction` type alias.

        Parameters
        -----------
        tag: :class:`bs4.Tag`
            A generic `bs4.Tag` class.

        Returns
        --------
        :class:`bool`
            _description_.
        """
        return tag.name == "select" and tag.has_attr("name") and tag.get("name") == "spot"

    async def get_location_id_mapping(self) -> Optional[dict[str, int]]:
        """
        Fetches the Location ID values and names from `FF14Angler` Location dropdown container, then set's our `__class__.location_map` attribute.
        - These will be used to map to the `XIVdatamining` FishingSpot names.
        - We can then use the `https://en.ff14angler.com/spot/[X]` where `X` is the `ff14angler_location_id` in the returned dictionary.

        Returns
        --------
        Optional[:class:`dict[str, int]`]
            A dictionary of `location_name: ff14angler_location_id`.
        """
        url = "https://en.ff14angler.com/"
        async with aiohttp.ClientSession() as session:
            res: aiohttp.ClientResponse = await session.get(url=url)
            if res.status != 200:
                return None
                # raise ConnectionError("Unable to access the url: %s", url)
            if res.content_type == "application/json":
                return None
            else:
                fishing_html_data: bytes = await res.content.read()

        # fishing_html_data: bytes = await self.request_file_data(url=url)

        soup = FF14Soup(fishing_html_data, "html.parser", session=None)
        locations: dict[str, int] = {}

        # get the available locations and their IDs
        page_data: CustomTag | None = soup.find(self.match_select_spot)

        if page_data is None:
            self.logger.error("<%s.get_location_id_mapping failed to get page data from url: %s", __class__.__name__, url)
            return locations

        for cur_location in page_data.children:
            if cur_location.name != "optgroup":
                continue

            option_grp: list[CustomTag] | None = cur_location.find_all("option")
            if option_grp is None:
                return locations
            for option_data in option_grp:
                loc_id: Optional[_AttributeValue] = option_data.get("value")
                if loc_id is None or isinstance(loc_id, AttributeValueList):
                    continue
                loc_name: str = option_data.get_text().strip() if option_data.string == None else option_data.string.strip()

                # This is a monkey patch as FF14Angler removed two of the bit's defining the unicode char for em-dash.
                if loc_name.startswith("Sui") and loc_name.endswith("Sato"):
                    loc_name = "Sui–no–Sato"

                locations[loc_name] = int(loc_id)
        setattr(self, "location_map", locations)
        return locations

    def GetFishLocations(FishID):
        r = requests.get("https://en.ff14angler.com/fish/" + str(FishID))
        fishing_html_data = r.content

        soup = BeautifulSoup(fishing_html_data, "html.parser")

        # just a list of IDs for locations
        Locations = []

        # get the available fish, skipping headers/etc
        AvailableLocations = list(list(soup.find(class_="info_section list").children)[3].children)

        for CurLocationIndex in range(1, len(AvailableLocations), 2):
            CurLocation = list(AvailableLocations[CurLocationIndex].children)
            print(CurLocation)
            CurLocationInfo = CurLocation[0].find("a")
            if CurLocationInfo:
                CurLocationID = int(CurLocationInfo.get("href").split("/")[-1])
                Locations.append(CurLocationID)

        return Locations

    def MatchSelectFish(tag):
        return tag.name == "select" and tag.has_attr("name") and tag.get("name") == "fish"

    def GetFishIDMapping():
        r = requests.get("https://en.ff14angler.com/")
        fishing_html_data = r.content

        soup = BeautifulSoup(fishing_html_data, "html.parser")
        Fish = {}

        # get the available locations and their IDs
        AllLocations = list()
        for CurFish in soup.find(MatchSelectFish).children:
            if CurFish.name == "option":
                FishID = CurFish.get("value")
                FishName = CurFish.string.strip()
                Fish[FishName] = int(FishID)

        return Fish


class FF14Soup(bs4.BeautifulSoup):
    """
    An overwrite class for `bs4.BeautifulSoup` overwrites, do not build/use.
    - This alleviates the littered `isinstance()` checks on commonly used functions.
    """

    def __init__(self, *args: Any, session: Optional[aiohttp.ClientSession], **kwargs: Any) -> None:
        self.session: Optional[aiohttp.ClientSession] = session
        super().__init__(*args, **kwargs)

    def find(self, *args: Any, **kwargs: _StrainableAttribute) -> Optional[CustomTag]:
        """
        Uses the build in `bs4.BeautifulSoup.find` via `super()` to overwrite the return type into something more manageable.
        - This `.find()` is the same as `bs4.Tag.find()` and purely for return type overwriting.

        Parameters
        -----------
        *args: Any
            Any args to be passed to the `bs4.Tag.find(*args)` function call.
        **kwargs: _StrainableAttribute
            Any kwargs to be passed to the `bs4.Tag.find(**kwargs)` function call.
        Returns
        --------
        :class:`Optional[CustomTag]`
            Returns either `None` or :class:`CustomTag` typed class.
        """
        res: Optional[_AtMostOneElement] = super().find(*args, **kwargs)
        # For some reason `isinstance(res, CustomTag)` is returning False
        # despite the return type of `res == "bs4.element.Tag" or `res == "bs4.Tag"`
        if res is not None and isinstance(res, bs4.Tag):
            return res  # pyright: ignore[reportReturnType]
        return None


class CustomTag(bs4.Tag):
    """
    This class is purely for typing overwrites, do not build/use.

    """

    @property
    def children(self) -> Iterator[CustomTag]:
        """
        Overwrites the type from `bs4.Tag` -> `Iterator[PageElement]` into an `Iterator[CustomTag]`.
        - `super().children` -> Iterate over all direct children of this `PageElement`.

        """
        return super().children  # pyright: ignore[reportReturnType]

    def find(self, *args: Any, **kwargs: _StrainableAttribute) -> Optional[CustomTag]:
        """
        Uses the built in `bs4.Tag.find` via `super()` to overwrite the return type into something more manageable.

        Parameters
        -----------
        *args: Any
            Any args to be passed to the `bs4.Tag.find(*args)` function call.
        **kwargs: _StrainableAttribute
            Any kwargs to be passed to the `bs4.Tag.find(**kwargs)` function call.
        Returns
        --------
        :class:`Optional[CustomTag]`
            Returns either `None` or :class:`CustomTag` typed class.
        """
        res: Optional[_AtMostOneElement] = super().find(*args, **kwargs)
        if res is not None and isinstance(res, CustomTag):
            return res

    def find_all(
        self,
        *args: Any,
        **kwargs: _StrainableAttribute,
    ) -> Optional[list[CustomTag]]:
        """
        Uses the built in `bs4.Tag.find_all` via `super()` to overwrite the return type into something more manageable.
        - `super().find_all` -> Look in the children of this `PageElement` and find all `PageElement` objects that match the given criteria.

        Parameters
        -----------
        *args: Any
            Any args to be passed to the `bs4.Tag.find_all(*args)` function call.
        **kwargs: _StrainableAttribute
            Any kwargs to be passed to the `bs4.Tag.find_all(**kwargs)` function call.
        Returns
        --------
        :class:`Optional[list[CustomTag]]`
            Returns either `None` or :class:`list[CustomTag]` typed class.

        """
        res: _QueryResults = super().find_all(*args, **kwargs)
        if res is not None:
            return res  # pyright: ignore[reportReturnType]


class FishingBaits:
    logger: ClassVar[logging.Logger] = logging.getLogger(__name__)
    bait_name: str
    hook_percet: float | int | str

    def __init__(self, data: BaitsTyped) -> None:
        for key, value in data.items():
            setattr(self, key, value)


class FF14Fish:
    logger: ClassVar[logging.Logger] = logging.getLogger(__name__)
    item_id: int
    fish_name: str
    restrictions: list[str]
    hook_time: Optional[str]
    double_fish: int
    baits: dict[int, FishingBaits]

    def __init__(self, item_id: int, data: FishingDataTyped) -> None:
        setattr(self, "item_id", item_id)
        for key, value in data.items():
            if key.lower() == "baits" and isinstance(value, dict):
                for k, v in value.items():
                    self.baits[k] = FishingBaits(data=v)

            else:
                setattr(self, key, value)

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        self.logger.debug(pformat(vars(self)))
        return f"\n\n__{self.__class__.__name__}__\n" + "\n".join([
            f"{e}: {getattr(self, e)}" for e in sorted(self.__dict__) if e.startswith("_") is False
        ])
