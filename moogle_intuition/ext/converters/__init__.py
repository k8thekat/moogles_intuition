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

import datetime
import logging
from typing import TYPE_CHECKING, Optional

from moogle_intuition import Item
from moogle_intuition._types import CurrencySpender, ShoppingCurrency, ShoppingItem

if TYPE_CHECKING:
    from async_universalis import CurrentData, CurrentDataEntries


LOGGER = logging.getLogger(__name__)

__all__ = ("Converter",)


class Converter:
    """Parsing data returns from :class:`Moogle` functions."""

    @staticmethod
    def parse_shopping_data(
        data: dict[int, CurrencySpender],
        sale_velocity_limit: int = 1,
        timefmt: str = "%d/%m | %H:%M(%Z)",
    ) -> list[str]:
        """Parses the data :class:`CurrencySpender` from the function :class:`Moogle.currency_spender`.

        .. note::
            Example:
            `Name: Eikon Metal[14150] | Timestamp: 03/11 | 03:46(UTC) | Sale Velocity: 19.142857 | Avg Price Cur(1440.7273) |
            Hist(189.7) | Min(294) | Currency Cost: 5 | PPU/Currency: 58.800000`

        Parameters
        ----------
        data: :class:`dict[int, CurrencySpender]`
            The resulting data from :class:`Moogle.currency_spender`.
        sale_velocity_limit: :class:`int`, optional
            The minimum threshold for the sale velocity of the item, by default 1.
        timefmt: :class:`str`, optional
            The :class:`datetime.strftime()` format to use, by default "%d/%m | %H:%M(%Z)".

        Returns
        -------
        :class:`list[str]`
            A list of each items resulting Universalis marketboard data as :class:`str` sorted
            by sale velocity starting at the lowest to the highest value.

        """
        output: list[str] = []
        entries: list[CurrentData] = []
        for entry in data:
            value: CurrencySpender | None = data.get(entry)
            if value is None or value["item"].mb_current is None:
                continue
            entries.append(value["item"].mb_current)

        for cur_data in sorted(entries, key=lambda x: x.regular_sale_velocity):
            if cur_data.regular_sale_velocity < sale_velocity_limit:
                continue
            value: CurrencySpender | None = data.get(cur_data.item_id)
            cost: int = 0 if value is None else value["cost"]
            timestamp: str | int = (
                cur_data.last_upload_time.strftime(timefmt)
                if isinstance(cur_data.last_upload_time, datetime.datetime)
                else cur_data.last_upload_time
            )
            temp: str = (
                f"Name: {cur_data.name}[{cur_data.item_id}] | Timestamp: {timestamp} | Sale Velocity: {cur_data.regular_sale_velocity} | "
                f"Avg Price Cur({cur_data.current_average_price}) | Hist({cur_data.average_price}) | Min({cur_data.min_price}) | "
                f"Currency Cost: {cost} | PPU/Currency: {cur_data.min_price / cost:2f}"
            )

            output.append(temp)

        return output

    @staticmethod
    def parse_crafting_cost(
        data: dict[int, ShoppingItem],
        *,
        recipe_item: Optional[Item] = None,
        currency: Optional[ShoppingCurrency] = None,
    ) -> str:
        """Handles the information from :class:`Recipe.get_crafting_cost()` and presents it in a readable compact format.

        .. note::
            Total Vendor Gil may not include total cost to craft the :class:`Recipe.item_result`
            as some items may not be purchased from a Vendor or TradeShops.

        Parameters
        ----------
        data: :class:`dict[int, ShoppingItem]`
            The :class:`Recipe.get_crafting_cost()` data result.
        recipe_item: :class:`Optional[Item]`, optional
            The :class:`Item` these ingredients belong to, if not included will omit header with related info, default is None.
        currency: :class:`Optional[ShoppingCurrency]`, optional
            The currency information, by default None.

        Returns
        -------
        :class:`str`
            A breakdown of the cost to craft the entire :class:`Item` combined with the cost of each individual ingredient.

        """
        if currency is None:
            currency = {"marketboard_gil": 0, "currencies": {0: 0}}

        vendor_gil: bool = False
        output: list[str] = []
        for entry in data:
            market_cost = 0
            vendor_cost = 0
            vendor_gil = False
            value: ShoppingItem | None = data.get(entry)
            if value is None or value["item"].mb_current is None:
                continue
            item: Item = value["item"]
            # Marketboard/Universalis Info.
            if item.mb_current is not None:
                LOGGER.debug("<%s.%s> | Parsing Universalis for Item | Item: %s", __class__.__name__, "_parse_makeplace_item", item)
                marketboard: CurrentData = item.mb_current
                market_listing: CurrentDataEntries = sorted(marketboard.listings, key=lambda x: x.price_per_unit)[0]
                currency["marketboard_gil"] += market_listing.price_per_unit * value["count"]
                tax_per = market_listing.tax / market_listing.quantity
                market_cost = int(market_listing.price_per_unit * value["count"] + tax_per)
            else:
                LOGGER.debug(
                    "<%s.%s> | No Universalis Marketboard information. | Item: %s ",
                    __class__.__name__,
                    "parse_crafting_cost",
                    item,
                )

            # Vendors info...
            if item.vendors is not None:
                LOGGER.debug("<%s.%s> | Parsing Vendors for Item | Item: %s", __class__.__name__, "_parse_makeplace_item", item)
                currency_item: Item | None = item.vendors[0].get("currency")
                price = item.vendors[0].get("price", 0)
                if currency_item is None and vendor_gil is False:
                    currency["currencies"][0] += price * value["count"]
                    vendor_cost = price * value["count"]
                    vendor_gil = True
            else:
                LOGGER.debug("<%s.%s> | No Vendor information. | Item: %s ", __class__.__name__, "parse_crafting_cost", item)

            # Tradeshop Info...
            if item.tradeshops is not None:
                LOGGER.debug("<%s.%s> | Parsing TradeShops for Item | Item: %s", __class__.__name__, "_parse_makeplace_item", item)
                currency_item: Item | None = item.tradeshops[0].get("currency")
                price = item.tradeshops[0].get("price", 0)
                # Essentially we fail to lookup "gil"
                if currency_item is None and vendor_gil is False:
                    currency["currencies"][0] += price * value["count"]
                    vendor_cost = price * value["count"]
                    vendor_gil = True
            else:
                LOGGER.debug("<%s.%s> | No Tradeshop information. | Item: %s ", __class__.__name__, "parse_crafting_cost", item)

            output.append(
                f"- {item.name} [{item.id}] | Count: {value['count']} | Total Market Gil Cost: {market_cost:,d} | "
                f"Total Vendor Gil Cost: {vendor_cost:,d} ",
            )
        msg = f"Total Market Gil Cost: {currency['marketboard_gil']:,d} | Total Vendor Gil: {currency['currencies'][0]:,d}"

        if recipe_item is not None:
            msg = f"Name: {recipe_item.name} [{recipe_item.id}]" + msg

        output[0:0] = [msg]

        return "\n".join(output)
