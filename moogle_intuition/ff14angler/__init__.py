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

import logging
from typing import TYPE_CHECKING, Any, Literal, Optional, overload

import aiohttp
import bs4
from bs4.element import AttributeValueList, NavigableString

if TYPE_CHECKING:
    from collections.abc import Iterator

    from bs4._typing import (
        _AtMostOneElement as bs4AtMostOneElement,  # pyright: ignore[reportPrivateUsage]
        _AttributeValue as bs4AttributeValue,  # pyright: ignore[reportPrivateUsage]
        _QueryResults as bs4QueryResults,  # pyright: ignore[reportPrivateUsage]
        _StrainableAttribute as bs4StrainableAttr,  # pyright: ignore[reportPrivateUsage]
    )

    from ._types import Baits, FishingData


__all__ = ("Angler", "AnglerBaits", "AnglerFish")

LOGGER: logging.Logger = logging.getLogger(__name__)


class PartialAngler:
    _repr_keys: list[str]

    def __init__(self) -> None:
        LOGGER.debug("<%s.__init__()>", __class__.__name__)

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


class Angler(PartialAngler):
    """A class to handle parsing `https://en.ff14angler.com/`.

    Supports spot and location id information by turning the data into a structure that yields useful information such as
    the best lure, chance to catch and any other restrictions associated with the fish.

    .. note::
        Inherits attributes and functions from :class:`PartialAngler`.


    """

    session: Optional[aiohttp.ClientSession]
    _session: Optional[aiohttp.ClientSession]

    def __init__(self, session: Optional[aiohttp.ClientSession] = None) -> None:
        """Build our :class:`Angler` object.

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

    async def _request(self, url: str) -> Optional[bytes]:
        if self.session is None:
            if self._session is None:
                session: aiohttp.ClientSession = aiohttp.ClientSession()
                self._session = session
                LOGGER.debug("<%s._request> | Creating local `aiohttp.ClientSession()` | session: %s", __class__.__name__, session)
            else:
                session = self._session
        else:
            session = self.session

        res: aiohttp.ClientResponse = await session.get(url=url)
        if res.status != 200:
            LOGGER.error("<%s._request> failed to access the url. | Status Code: %s | URL: %s", __class__.__name__, res.status, url)
            return None
            # raise ConnectionError("Unable to access the url: %s", url)
        if res.content_type == "application/json":
            LOGGER.error(
                "<%s._request> is of the wrong content_type. | Content Type: %s | URL: %s",
                __class__.__name__,
                res.content_type,
                url,
            )
            return None
        return await res.content.read()

    @overload
    async def get_location_fish_data(self, location_id: int, fish_id: int = ...) -> Optional[FishingData]: ...

    @overload
    async def get_location_fish_data(self, location_id: int, fish_id: None = ...) -> Optional[dict[int, FishingData]]: ...

    async def get_location_fish_data(
        self,
        location_id: int,
        fish_id: Optional[int] = None,
    ) -> Optional[dict[int, FishingData] | FishingData]:
        """Retrieve FF14 Angler data from `https://en.ff14angler.com/spot/[location_id]` via `aiohttp.ClientSession.get()`.

        - Parses the data into a dictionary keyed off the {:class:`int` : :class:`FishingDataTyped`}

        .. warning::
            - Do not use any spot or location ID information from `xivdataminig`/`Moogle`, it's not related.


        Parameters
        ----------
        location_id: :class:`int`
            The Location ID from FF14angler.com website.
        fish_id: :class:`int`, optional
            The Fish ID to pick out of the location data, if any.

        Returns
        -------
        :class:`Optional[dict[int, FishingDataTyped]]`
            A dictionary with the key value being the fish ID and data representing the tables found on the
            ff14angler.com/spot/location_id page..

        """
        LOGGER.debug("Fetching FF14Angler location data for Location ID: %s | Fish ID: %s ", location_id, fish_id)

        url: str = "https://en.ff14angler.com/spot/" + str(location_id)

        fishing_html_data: Optional[bytes] = await self._request(url=url)
        if fishing_html_data is None:
            LOGGER.error("<%s.get_location_id_mapping> failed to get data from url: %s", __class__.__name__, url)
            return None

        soup = AnglerSoup(fishing_html_data, "html.parser")
        # ID is the ff14 angler fishing ID, each entry is a dictionary containing
        #    name, TackleID->percent, Restrictions
        fishing_data: dict[int, FishingData] = {}

        # get the available fish, skipping headers/etc
        info_section: Optional[CustomTag] = soup.find(class_="info_section list")
        if info_section is None:
            LOGGER.error("<%s.get_fish_data> failed to find `class_='info_section list'`.", __class__.__name__)
            return None

        info_sec_children: list[CustomTag] = list(info_section.children)

        try:
            # Attempt to index to the fish data, this could fail.
            poss_fish: CustomTag = info_sec_children[5]
        except IndexError:
            LOGGER.exception("<%s.get_fish_data> had an <IndexError> for `poss_fish`.", __class__.__name__)
            return None
        avail_fish: list[CustomTag] = list(poss_fish.children)

        flag = False
        cur_fish_tug = "UNK"
        cur_fish_double = 0
        for fish_index in range(1, len(avail_fish), 2):
            if flag is True and fish_id is not None:
                break
            cur_fish_page: CustomTag = avail_fish[fish_index]
            cur_fish: list[CustomTag] = list(cur_fish_page.children)

            # This could fail with an IndexError
            try:
                cur_fish_data: CustomTag = cur_fish[3]
            except IndexError:
                LOGGER.exception("<%s.get_fish_data> had an <IndexError> for `cur_fish_data`", __class__.__name__)
                return fishing_data

            cur_fish_id_name: Optional[CustomTag] = cur_fish_data.find("a")
            if cur_fish_id_name is None:
                return fishing_data

            poss_cur_fish_id: Optional[bs4AttributeValue] = cur_fish_id_name.get("href")
            if poss_cur_fish_id is None or isinstance(poss_cur_fish_id, AttributeValueList):
                return fishing_data

            cur_fish_id = int(poss_cur_fish_id.split("/")[-1])

            # If we find our fish in our results, lets set our flag.
            if cur_fish_id == fish_id:
                flag = True

            # This could break due to an IndexError.
            try:
                poss_fish_name: CustomTag = list(cur_fish_id_name.children)[2]
            except IndexError:
                LOGGER.warning("<%s.get_fish_data> had an <IndexError> for `poss_fish_name`", __class__.__name__)
                continue

            if isinstance(poss_fish_name, NavigableString):
                cur_fish_name: str = poss_fish_name.strip()
            else:
                LOGGER.warning(
                    "<%s.get_fish_data> encountered an <TypeError>, `poss_fish_name` is not of type `bs4.NavigableString`. | Type: %s",
                    __class__.__name__,
                    type(poss_fish_name),
                )
                continue

            restriction_list: list[str] = []
            cur_fish_restrictions: CustomTag = cur_fish[5]

            if cur_fish_restrictions.string is not None:
                restrict_str: str = cur_fish_restrictions.string.strip()
                if len(restrict_str):
                    restriction_list.append(restrict_str.title())
            else:
                for entry in cur_fish_restrictions.children:
                    if entry.name == "img":
                        entry_title: Optional[bs4AttributeValue] = entry.get("title", None)
                        if entry_title is None:
                            LOGGER.warning(
                                "<%s.get_fish_data> encountered a KeyError for `entry_title` in `cur_fish_restrictions`.",
                                __class__.__name__,
                            )
                            continue
                        if isinstance(entry_title, str):
                            restriction = entry_title.split(" ")
                            restriction_list.append((" ".join(restriction[1:])).title())

                    # What in the holy fuck is up with their typing..
                    # I cannot call `entry.name is None`; the rest of the code evals to `Never`... sigh..
                    elif isinstance(entry, NavigableString) and entry.string is not None:
                        restrict_str = entry.string.strip()
                        if len(restrict_str):
                            restriction_list.append(restrict_str.title())
                    else:
                        LOGGER.warning(
                            (
                                "<%s.get_fish_data> encountered a <TypeError> for `entry` in `cur_fish_restrictions`. | Type: %s | "
                                "Name Attr: %s | String Attr: %s"
                            ),
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
                tug_section: bs4AtMostOneElement = possible_tug_data.find(class_="tug_sec")
                cur_fish_tug = None if tug_section is None or tug_section.string is None else tug_section.string.strip()

            except IndexError:
                LOGGER.warning("<%s.get_fish_data> had an <IndexError> for `possible_tug_data`", __class__.__name__)

            # Index check
            # Checking Fish Double Hook information in a new section.
            try:
                cur_fish_double_data: CustomTag = cur_fish[9]
                cur_fish_double_page: Optional[CustomTag] = cur_fish_double_data.find(class_="strong")
                if cur_fish_double_page is not None and cur_fish_double_page.string is not None:
                    cur_fish_double = int(cur_fish_double_page.string.strip()[1:])
                else:
                    cur_fish_double = 0
            except IndexError:
                LOGGER.warning("<%s.get_fish_data> had an <IndexError> for `cur_fish_double_data`", __class__.__name__)

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
            # We will be using this list layout as our index into `fishing_data`.
            fish_ids: list[int] = []
            # Could be an Index Error
            try:
                poss_entries: CustomTag = effective_bait[1]
            except IndexError:
                LOGGER.exception("<%s.get_fish_data> had an <IndexError> for `poss_entries`", __class__.__name__)
                return fishing_data

            # all entries have a blank gap, we also skip the first box as
            # it is empty due to the grid design
            fish_entries: list[CustomTag] = list(poss_entries.children)
            # This is used for `fish_id` to break early with the exact data.
            fish_index = -1
            for index in range(3, len(fish_entries), 2):
                cur_fish_entry: Optional[CustomTag] = fish_entries[index].find("a")
                # poss_fish_name: Optional[_AttributeValue] = cur_fish_entry.get("title")
                if cur_fish_entry is None:
                    continue
                poss_fish_id: Optional[bs4AttributeValue] = cur_fish_entry.get("href")
                if isinstance(poss_fish_id, str):
                    # If our fish id in the header matches our passed in fish_id
                    cur_fish_id = int(poss_fish_id.split("/")[-1])
                    fish_ids.append(cur_fish_id)
                    if fish_id and cur_fish_id == fish_id:
                        fish_index = len(fish_ids) - 1
                        break

            # now cycle through and grab % values for each fish, similar to the above
            # every other entry is blank
            for bait_index in range(3, len(effective_bait), 2):
                bait_numbers: list[CustomTag] = list(effective_bait[bait_index].children)
                try:
                    bait_info_page: CustomTag = bait_numbers[0]
                except IndexError:
                    LOGGER.warning("<%s.get_fish_data> had an <IndexError> for `cur_bait_info_page`", __class__.__name__)
                    continue

                bait_info: Optional[CustomTag] = bait_info_page.find("a")
                if bait_info is None:
                    continue

                poss_id: Optional[bs4AttributeValue] = bait_info.get("href", None)
                if isinstance(poss_id, str):
                    bait_id = int(poss_id.split("/")[-1])
                else:
                    LOGGER.warning(
                        "<%s.get_fish_data> encountered a <TypeError>, `poss_id`. | Type: %s ",
                        __class__.__name__,
                        type(poss_id),
                    )
                    continue

                bait_name: Optional[bs4AttributeValue] = bait_info.get("title", None)
                if bait_name is None or isinstance(bait_name, AttributeValueList):
                    continue

                if fish_id is not None and fish_index != -1:
                    cur_bait_index = (fish_index * 2) + 2
                    if len(bait_numbers) > cur_bait_index:
                        add_bait_info_header: Optional[CustomTag] = bait_numbers[cur_bait_index].find("canvas")
                        if add_bait_info_header is None:
                            continue
                        page_percent: Optional[bs4AttributeValue] = add_bait_info_header.get("value")
                        if isinstance(page_percent, str):
                            bait_percent = float(page_percent) / 100

                            fishing_data[fish_id]["baits"][bait_id] = {
                                "bait_name": bait_name,
                                "hook_percent": float(format(bait_percent, ".2f")),
                            }
                else:
                    for cur_bait_index in range(2, len(bait_numbers), 2):
                        if int(fish_ids[int((cur_bait_index - 2) / 2)]) == fish_index:
                            break
                        add_bait_info_header: Optional[CustomTag] = bait_numbers[cur_bait_index].find("canvas")
                        if add_bait_info_header is None:
                            continue
                        page_percent: Optional[bs4AttributeValue] = add_bait_info_header.get("value")
                        if isinstance(page_percent, str):
                            bait_percent = float(page_percent) / 100
                            cur_fish_id = int(fish_ids[int((cur_bait_index - 2) / 2)])
                            fishing_data[cur_fish_id]["baits"][bait_id] = {
                                "bait_name": bait_name,
                                "hook_percent": float(format(bait_percent, ".2f")),
                            }
        if flag is True and fish_id is not None:
            return fishing_data[fish_id]
        return fishing_data

    def match_select_spot(self, tag: bs4.Tag) -> bool:
        """Creates a generic `bs4.Tag` with set values to check against within the `bs4.BeautifulSoup.find()` name parameter.

        .. note::
            - This is in reference to the `bs4._typing` -> `_TagMatchFunction` type alias.

        Parameters
        ----------
        tag: :class:`bs4.Tag`
            A generic `bs4.Tag` class.

        Returns
        -------
        :class:`bool`
            If the tag has the right name, attributes and the `name` key value is == "spot".

        """
        return tag.name == "select" and tag.has_attr("name") and tag.get("name") == "spot"

    @overload
    async def get_location_id_mapping(self, *, include_inverted_map: Literal[True]) -> Optional[tuple[dict[str, int], dict[int, str]]]: ...

    @overload
    async def get_location_id_mapping(self, *, include_inverted_map: bool = False) -> Optional[dict[str, int]]: ...

    async def get_location_id_mapping(
        self,
        *,
        include_inverted_map: bool = False,
    ) -> Optional[tuple[dict[str, int], dict[int, str]]] | Optional[dict[str, int]]:
        """Fetches the Location ID values and names from `FF14Angler` Location dropdown container on the main page.

        .. note::
            - Data structure is `{location_name[str] : location_id[int]}`
            - These will be used to map to the `XIVdatamining` FishingSpot names.
            - We can then use the `https://en.ff14angler.com/spot/[X]` where `X` is the `ff14angler_location_id` in the returned dictionary.


        Parameters
        ----------
        include_inverted_map: :class:`bool`
            If you want an additional dict array with the key, value pairs inverted to `{value : key}`.
            - Data structure is inverted to `{location_id[int]: location_name[str]}`
            - The data return is a tuple of the original array and the inverted array.

        Returns
        -------
        Optional[:class:`dict[str, int]`]
            A dictionary of `location_name: ff14angler_location_id`.

        """
        url = "https://en.ff14angler.com/"
        fishing_html_data: Optional[bytes] = await self._request(url=url)
        if fishing_html_data is None:
            LOGGER.error("<%s.get_location_id_mapping> failed to get data from url: %s", __class__.__name__, url)
            return None

        # fishing_html_data: bytes = await self.request_file_data(url=url)

        soup = AnglerSoup(fishing_html_data, "html.parser")
        locations: dict[str, int] = {}

        # get the available locations and their IDs
        page_data: Optional[CustomTag] = soup.find(self.match_select_spot)

        if page_data is None:
            LOGGER.error("<%s.get_location_id_mapping failed to get page data from url: %s", __class__.__name__, url)
            return locations

        for cur_location in page_data.children:
            if cur_location.name != "optgroup":
                continue

            option_grp: Optional[list[CustomTag]] = cur_location.find_all("option")
            if option_grp is None:
                return locations
            for option_data in option_grp:
                loc_id: Optional[bs4AttributeValue] = option_data.get("value")
                if loc_id is None or isinstance(loc_id, AttributeValueList):
                    continue
                loc_name: str = option_data.get_text().strip() if option_data.string is None else option_data.string.strip()

                # This is a monkey patch as FF14Angler removed two of the bit's defining the unicode char for em-dash.
                if loc_name.startswith("Sui") and loc_name.endswith("Sato"):
                    loc_name = "Sui–no–Sato"

                locations[loc_name] = int(loc_id)
        LOGGER.debug("Fetched FF14Angler Location to ID mapping data. | Entries: %s", len(locations))

        if include_inverted_map is True:
            inverted_locs: dict[int, str] = {v: k for k, v in locations.items()}
            # setattr(self, "inverted_location_map", inverted_locs)
            return locations, inverted_locs

        # setattr(self, "location_map", locations)
        return locations

    async def get_fish_locations(self, fish_id: int) -> Optional[list[int]]:
        """Retrieves the data related to the `fish_id` parameters fishing spots on FF14 Angler website.

        Parameters
        ----------
        fish_id: :class:`int`
            The FF14 Angler Fish ID to search for and get the FF14 Angler fishing spots.

        Returns
        -------
        :class:`Optional[list[int]]`
            Returns a list of FF14 Angler compatible fishing spot IDs related to the provided `fish_id` parameter.

        """
        LOGGER.debug("Fetching FF14Angler Fish location data for Fish ID: %s", fish_id)
        url = "https://en.ff14angler.com/fish/" + str(fish_id)
        fishing_html_data: Optional[bytes] = await self._request(url=url)

        soup = AnglerSoup(fishing_html_data, "html.parser")

        # just a list of IDs for locations
        locations: list[int] = []

        page_data: Optional[CustomTag] = soup.find(class_="info_section list")
        if page_data is None:
            LOGGER.error("<%s.get_fish_locations failed to get page data from url: %s", __class__.__name__, url)
            return locations
        try:
            # get the available fish, skipping headers/etc
            avail_locations: list[CustomTag] = list(list(page_data.children)[3].children)
        except IndexError:
            LOGGER.exception("<%s.get_fish_location> had an <IndexError> for `avail_locations`.", __class__.__name__)
            return None

        for cur_loc_index in range(1, len(avail_locations), 2):
            cur_loc: list[CustomTag] = list(avail_locations[cur_loc_index].children)
            cur_loc_info: CustomTag | None = cur_loc[0].find("a")
            if cur_loc_info is not None:
                temp: Optional[bs4AttributeValue] = cur_loc_info.get("href")
                if isinstance(temp, str):
                    cur_loc_id = int(temp.split("/")[-1])
                    locations.append(cur_loc_id)

        return locations

    def match_select_fish(self, tag: bs4.Tag) -> bool:
        """Creates a generic `bs4.Tag` with set values to check against within the `bs4.BeautifulSoup.find()` name parameter.

        - This is in reference to the `bs4._typing` -> `_TagMatchFunction` type alias.

        Parameters
        ----------
        tag: :class:`bs4.Tag`
            A generic `bs4.Tag` class.

        Returns
        -------
        :class:`bool`
            If the tag has the right name, attributes and the `name` key value is == "fish".

        """
        return tag.name == "select" and tag.has_attr("name") and tag.get("name") == "fish"

    async def get_fish_id_mapping(self) -> Optional[dict[str, int]]:
        """Creates a Fish name to ID mapping.

        Fetches the Fish ID values and names from `FF14Angler` Fish dropdown container,
        then returns the data structure in `fish_name : fish_id`.

        .. note::
            - These will be used to map to the `XIVdatamining` fish names.
            - We can then use the `https://en.ff14angler.com/fish/[X]` where `X` is the `fish_id` in the returned dictionary.


        Returns
        -------
        Optional[:class:`dict[str, int]`]
            A dictionary of `fish_name: fish_id`.

        """
        url = "https://en.ff14angler.com/"
        fishing_html_data: Optional[bytes] = await self._request(url=url)

        soup = AnglerSoup(fishing_html_data, "html.parser")
        fish: dict[str, int] = {}

        page_data: CustomTag | None = soup.find(self.match_select_fish)
        if page_data is None:
            LOGGER.error("<%s.get_fish_id_mapping> failed to get page data from url: %s", __class__.__name__, url)
            return fish
        # get the available locations and their IDs
        for cur_fish in page_data.children:
            if cur_fish.name == "option":
                fish_id: Optional[bs4AttributeValue] = cur_fish.get("value")
                if fish_id is None or isinstance(fish_id, AttributeValueList):
                    continue
                if cur_fish.string is None:
                    continue
                fish_name = cur_fish.string.strip()
                # Ignores the prompt in the box.
                if fish_name.startswith("Select"):
                    continue
                fish[fish_name] = int(fish_id)
        # setattr(self, "fish_map", fish)
        LOGGER.debug("Fetched FF14Angler Fish to ID mapping data. | Entries: %s", len(fish))
        return fish


class AnglerSoup(bs4.BeautifulSoup):
    """An overwrite class for `bs4.BeautifulSoup` overwrites, do not build/use.

    ..note:
        - This alleviates the littered `isinstance()` checks on commonly used functions.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def find(self, *args: Any, **kwargs: bs4StrainableAttr) -> Optional[CustomTag]:
        """Uses the build in `bs4.BeautifulSoup.find` via `super()` to overwrite the return type into something more manageable.

        ..note:
            - This `.find()` is the same as `bs4.Tag.find()` and purely for return type overwriting.

        Parameters
        ----------
        *args: Any
            Any args to be passed to the `bs4.Tag.find(*args)` function call.
        **kwargs: _StrainableAttribute
            Any kwargs to be passed to the `bs4.Tag.find(**kwargs)` function call.

        Returns
        -------
        :class:`Optional[CustomTag]`
            Returns either `None` or :class:`CustomTag` typed class.

        """
        res: Optional[bs4AtMostOneElement] = super().find(*args, **kwargs)
        # For some reason `isinstance(res, CustomTag)` is returning False
        # despite the return type of `res == "bs4.element.Tag" or `res == "bs4.Tag"`
        if res is not None and isinstance(res, bs4.Tag):
            return res  # pyright: ignore[reportReturnType]
        return None


class CustomTag(bs4.Tag):
    """Class is purely for typing overwrites, do not build/use."""

    @property
    def children(self) -> Iterator[CustomTag]:
        """Overwrites the type from `bs4.Tag` -> `Iterator[PageElement]` into an `Iterator[CustomTag]`.

        .. note::
        - `super().children` -> Iterate over all direct children of this `PageElement`.

        """
        return super().children  # pyright: ignore[reportReturnType]

    def find(self, *args: Any, **kwargs: bs4StrainableAttr) -> Optional[CustomTag]:
        """Uses the built in `bs4.Tag.find` via `super()` to overwrite the return type into something more manageable.

        Parameters
        ----------
        *args: Any
            Any args to be passed to the `bs4.Tag.find(*args)` function call.
        **kwargs: bs4StrainableAttr
            Any kwargs to be passed to the `bs4.Tag.find(**kwargs)` function call.


        Returns
        -------
        Optinal[CustomTag]
            Returns either `None` or :class:`CustomTag` typed class.

        """
        res: Optional[bs4AtMostOneElement] = super().find(*args, **kwargs)
        if res is not None and isinstance(res, CustomTag):
            return res
        return None

    def find_all(
        self,
        *args: Any,
        **kwargs: bs4StrainableAttr,
    ) -> Optional[list[CustomTag]]:
        """Uses the built in `bs4.Tag.find_all` via `super()` to overwrite the return type into something more manageable.

        .. note::
            `super().find_all`: Look in the children of this `PageElement` and find all `PageElement` objects that match the given criteria.


        Parameters
        ----------
        *args: Any
            Any args to be passed to the `bs4.Tag.find_all(*args)` function call.
        **kwargs: _StrainableAttribute
            Any kwargs to be passed to the `bs4.Tag.find_all(**kwargs)` function call.

        Returns
        -------
        :class:`Optional[list[CustomTag]]`
            Returns either `None` or :class:`list[CustomTag]` typed class.

        """
        res: bs4QueryResults = super().find_all(*args, **kwargs)
        return res  # pyright: ignore[reportReturnType]


class AnglerBaits(PartialAngler):
    """A represensation of Angler baits and the related chance to hook based upon their website data.

    .. note::
        Inherits attributes and functions from :class:`PartialAngler`.


    Attributes
    ----------
    bait_name: :class:`str`
        The name of the FF14 bait.
    hook_percent: :class:`float | int`
        The percent chance catch if using the specified `bait_name` for the `<AnglerFish>` class.

    """

    bait_name: str
    hook_percent: float | int
    _raw: Baits

    def __init__(self, data: Baits) -> None:
        """Build the :class:`AnglerBaits` object.

        Parameters
        ----------
        data: :class:`BaitsTyped`
            _description_.

        """
        LOGGER.debug("<%s.__init__()> data: %s", __class__.__name__, data)
        self._raw = data
        for key, value in data.items():
            setattr(self, key, value)


class AnglerFish:
    """Represents a FF14 Angler fish data.

    .. warning::
        - The `item_id` attribute is *NOT* the same as `<Item.item_id>`

    Attributes
    ----------
    location_name: :class:`str`, optional
        The fishing spot name for this Fish.
    item_id: :class:`int`
        The Item ID in relation to FF14Angler Fish IDs.
    fish_name: :class:`str`
        The name of the fish.
    resitrctions: list[str]
        Any restrictions the Fish may have, such as Time of Day, Weather or ???(UNK).
    hook_time: :class:`str`, optional
        The average time in seconds it takes for the fish to bite.
    double_fish: :class:`int`
        The number of fish returned when using "Double Hook" Fishing action.
    baits: :class:`dict[int, FishingBaits]`
        The baits used to hook the fish separated by the ID of the bait in relation to FF14Angler bait IDs.

    Property
    ---------
    ff14angler_url: :class:`str`
        The FF14 Angler URL for the Fish.

    """

    # I am supplying this value only to make it easier when you have this class by itself.
    location_name: Optional[str]

    item_id: int
    fish_name: str
    restrictions: list[str]
    hook_time: Optional[str]
    double_fish: int
    baits: dict[int, AnglerBaits]

    _raw: FishingData

    @property
    def ff14angler_url(self) -> str:
        """The FF14Angler website url for the Fish."""
        return f"https://en.ff14angler.com/fish/{self.item_id}"

    def __init__(self, item_id: int, data: FishingData, location_name: Optional[str] = None) -> None:
        """Build your :class:`AnglerFish` object.

        Parameters
        ----------
        item_id: :class:`int`
            The FF14 Angler fish id.
        data: :class:`FishingData`
            The FF14 Angler fish data.
        location_name: :class:`Optional[str]`, optional
            The FF14 Angler fishing location, by default None.

        """
        LOGGER.debug("<%s.__init__()> location: %s | data: %s", __class__.__name__, location_name, data)
        self._raw = data
        self.item_id = item_id
        self.location_name = location_name
        self.baits = {}
        for key, value in data.items():
            if key.lower() == "baits" and isinstance(value, dict):
                for k, v in value.items():  # type: ignore[reportUnkownVariableType]
                    # setattr(self, "baits", {k: FishingBaits(data=v)})
                    self.baits[k] = AnglerBaits(data=v)  # type: ignore[reportUnkownArgumentType]

            else:
                setattr(self, key, value)

    def __str__(self) -> str:  # noqa: D105
        return self.__repr__()

    def __repr__(self) -> str:  # noqa: D105
        return f"\n\n__{self.__class__.__name__}__\n" + "\n".join([
            f"{e}: {getattr(self, e)}" for e in sorted(self.__dict__) if e.startswith("_") is False
        ])

    def best_bait(self) -> Optional[AnglerBaits]:
        """Retrieves the optimal chance Fishing bait related to the `<AnglerFish.location_name>` class.

        Returns
        -------
        :class:`Optional[AnglerBaits]`
            Returns the best Fishing bait to use at this fishing spot.

        """
        chance = 0
        best_bait: Optional[AnglerBaits] = None
        for value in self.baits.values():
            if value.hook_percent > chance:
                chance: float | int = value.hook_percent
                best_bait = value
        return best_bait
