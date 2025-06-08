from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from pprint import pformat
from typing import TYPE_CHECKING, Any, ClassVar, Optional, Union

import aiohttp

from ._enums import *

if TYPE_CHECKING:
    from _types import *


__all__ = ("CurrentData", "CurrentKeys", "UniversalisAPI")


class UniversalisAPI:
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
    logger: ClassVar[logging.Logger] = logging.getLogger(__name__)
    session: Optional[aiohttp.ClientSession]

    # JSON response sanitizing.
    _pre_formatted_keys: ClassVar[dict[str, str]] = {
        "HQ": "_hq",
        "ID": "_id",
        "NQ": "_nq",
    }
    _ignored_keys: ClassVar[list[str]] = [""]

    @property
    def pre_formatted_keys(self) -> dict[str, str]:
        return self._pre_formatted_keys

    def set_pre_formatted_keys(self, keys: dict[str, str]) -> dict[str, str]:
        self._pre_formatted_keys.update(keys)
        return self._pre_formatted_keys

    def __init__(self, session: Optional[aiohttp.ClientSession] = None) -> None:
        # This will be for GarlandAPI and UniversalisAPI or anything needing a ClientSession
        # Setting it to None by default will be the best as to keep the class as light weight as possible at runtime unless needed.
        self.session = session

        # Universalis API
        self.base_api_url = "https://universalis.app/api/v2"
        self.api_call_time = datetime.now()
        self.max_api_calls = 20

        # These are the "Trimmed" API fields for Universalis Market Results.
        self.api_trim_item_fields = "&fields=itemID%2Clistings.quantity%2Clistings.worldName%2Clistings.pricePerUnit%2Clistings.hq%2Clistings.total%2Clistings.tax%2Clistings.retainerName%2Clistings.creatorName%2Clistings.lastReviewTime%2ClastUploadTime"

    def __del__(self) -> None:
        try:
            self._ = asyncio.create_task(self.__adel__())
            self.logger.debug("Closed `aiohttp.ClientSession`| Session: %s", self.session)
        except RuntimeError:
            self.logger.error("Failed to close our `aiohttp.ClientSession`")

    async def __adel__(self) -> None:
        if self.session is not None:
            await self.session.close()

    async def _request(self, url: str, **request_params: Any) -> Any:
        cur_time: datetime = datetime.now()
        max_diff = timedelta(milliseconds=1000 / self.max_api_calls)
        if (cur_time - self.api_call_time) < max_diff:
            sleep_time: float = (max_diff - (cur_time - self.api_call_time)).total_seconds() + 0.1
            await asyncio.sleep(delay=sleep_time)

        if self.session is None:
            self.session = aiohttp.ClientSession()
        data: aiohttp.ClientResponse = await self.session.get(url=url, **request_params)
        if data.status != 200:
            self.logger.error("We encountered an error in Universalis _request. Status: %s | API: %s", data.status, url)
            raise ConnectionError("We encountered an error in Universalis _request. Status: %s | API: %s", data.status, url)
        elif data.status == 400:
            self.logger.error(
                "We encountered an error in Universalis _request due to invalid Parameters. Status: %s | API: %s", data.status, url
            )
            raise ConnectionError(
                "We encountered an error in Universalis _request due to invalid Parameters. Status: %s | API: %s", data.status, url
            )
        # 404 - The world/DC or item requested is invalid. When requesting multiple items at once, an invalid item ID will not trigger this.
        # Instead, the returned list of unresolved item IDs will contain the invalid item ID or IDs.
        elif data.status == 404:
            self.logger.error(
                "We encountered an error in Universalis _request due to invalid World/DC or Item ID. Status: %s | API: %s", data.status, url
            )
            raise ConnectionError(
                "We encountered an error in Universalis _request due to invalid World/DC or Item ID. Status: %s | API: %s", data.status, url
            )

        self.api_call_time = datetime.now()
        res: Any = await data.json()
        return res

    async def get_current_data(
        self,
        items: Union[list[str] | list[int], str | int],
        *,
        world_or_dc: DataCenterEnum | WorldEnum = DataCenterEnum.Crystal,
        num_listings: int = 10,
        num_history_entries: int = 10,
        item_quality: ItemQualityEnum = ItemQualityEnum.NQ,
        trim_item_fields: bool = True,
    ) -> CurrentData:
        # Sanitize the value as a str for usage.
        if isinstance(items, int):
            items = str(items)
        elif isinstance(items, list) and len(items) == 1:
            items = items[0]

        # ? Suggestion
        # Handle lists over 1k items.
        if isinstance(items, list):
            self.logger.debug(
                "<Universalis.get_current_data>. | Datacenter: %s | Num of Items: %s | Data Type: %s",
                world_or_dc.name,
                len(items),
                type(items),
            )
            for e in items:
                items = ",".join(str(e))
        else:
            self.logger.debug(
                "<Universalis.get_current_data>. | Datacenter: %s | Item: %s | Data Type: %s",
                world_or_dc.name,
                items,
                type(items),
            )
        api_url: str = (
            f"{self.base_api_url}/{world_or_dc.name}/{items}?listings={num_listings}&entries={num_history_entries}&hq={item_quality.value}"
        )
        if trim_item_fields:
            api_url += self.api_trim_item_fields
        self.logger.debug("<Universalis.get_current_data> URL: %s", api_url)
        res: CurrentTyped = await self._request(url=api_url)
        return CurrentData(data=res)

    # todo - need to finish this command, understand overloads to define return types better
    async def get_history_data(
        self,
        items: Union[list[str], str],
        data_center: DataCenterEnum = DataCenterEnum.Crystal,
        num_listings: int = 10,
        min_price: int = 0,
        max_price: Optional[int] = None,
        history: int = 604800000,
    ) -> CurrentTyped | HistoryTyped:
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
            The Datacenter to fetch the results from, by default DataCenterEnum.Crystal.
        num_listings: :class:`int`, optional
            _description_, by default 10.
        min_price: :class:`int`, optional
            _description_, by default 0.
        max_price: :class:`Union[int, None]`, optional
            The max price of the item, by default None.
        history: :class:`int`, optional
            The timestamp float value for how far to go into the history., by default 604800000.

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
        res: CurrentTyped | HistoryTyped = await self._request(url=api_url)
        return res

    @classmethod
    def pep8_key_name(cls, key_name: str) -> str:
        """
        Converts the provided `key_name` parameter into something that is pep8 compliant yet clear as to what it is for.
        - Adds a `_` before any uppercase char in the `key_name` and then `.lowers()` that uppercase char.

        .. note::
            Has special cases in `cls._ignored_keys` to allow adding/removing of needed keys.



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
        if key_name in cls._ignored_keys:
            return key_name

        for k, v in cls._pre_formatted_keys.items():
            if k in key_name:
                key_name.replace(k, v)

        temp: str = key_name[:1].lower()
        for e in key_name[1:]:
            if e.isupper():
                temp += f"_{e.lower()}"
                continue
            temp += e
        return temp


class CurrentData:
    item_id: int
    world_id: int
    last_upload_time: int
    dc_name: str  # dc only
    listings: list[CurrentKeys]
    recent_history: list[CurrentKeys]
    current_average_price: float | int
    current_average_price_nq: float | int
    current_average_price_hq: float | int
    regular_sale_velocity: float | int
    nq_sale_velocity: float | int
    hq_sale_velocity: float | int
    average_price: float | int
    average_price_nq: float | int
    average_price_hq: float | int
    min_price: int
    min_price_nq: int
    min_price_hq: int
    max_price: int
    max_price_nq: int
    max_price_hq: int
    stack_size_histogram: dict[str, int]
    stack_size_histogram_nq: dict[str, int]
    stack_size_histogram_hq: dict[str, int]
    world_upload_times: dict[str, int]
    world_name: str
    listings_count: int
    recent_history_count: int
    units_for_sale: int
    units_sold: int
    has_data: bool

    def __init__(self, data: CurrentTyped) -> None:
        for key, value in data.items():
            key = UniversalisAPI.pep8_key_name(key_name=key)
            if (isinstance(value, list) and key == "recent_history") or key == "listings":
                # ? Suggestion
                # I need to learn how to properly type hint this data structure given I am checking the keys but not "properly"
                setattr(self, key, [CurrentKeys(data=entry) for entry in value if isinstance(entry, dict)])  # type: ignore
            else:
                setattr(self, key, value)

    def __repr__(self) -> str:
        return pformat(vars(self))

    def __str__(self) -> str:
        return self.__repr__()


class CurrentKeys:
    """
    -> Univertsalis API Current DC/World JSON Response Keys. \n
    Related to :class:`UniversalisAPICurrentTyped` keys.
    """

    last_review_time: int
    price_per_unit: int
    quantity: int
    stain_id: int
    world_name: str
    world_id: int
    creator_name: str
    creator_id: Optional[int]
    hq: bool
    is_crafted: bool
    listing_id: str
    materia: list
    on_mannequin: bool
    retainer_city: int
    retainer_id: int
    retainer_name: str
    seller_id: Optional[int]
    total: int
    tax: int
    timestamp: int
    buyer_name: str

    def __init__(self, data: CurrentKeysTyped) -> None:
        for key, value in data.items():
            key = UniversalisAPI.pep8_key_name(key_name=key)
            setattr(self, key, value)

    def __repr__(self) -> str:
        return pformat(vars(self))

    def __str__(self) -> str:
        return self.__repr__()
