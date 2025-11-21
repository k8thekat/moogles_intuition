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
import datetime
import logging
from typing import TYPE_CHECKING, ClassVar, Literal, Optional, Unpack, overload

from moogle_intuition import Item, Moogle
from moogle_intuition.errors import MoogleLookupError
from moogle_intuition.modules import FishingSpot, PlaceName, SpearFishingSpot

from ._enums import ColorRef, InventoryLocation

if TYPE_CHECKING:
    from collections.abc import Iterator

    import aiohttp
    from aiohttp_client_cache.session import CachedSession
    from async_garlandtools import GarlandToolsAsync
    from async_universalis import CurrentData, CurrentDataEntries, UniversalisAPI

    from moogle_intuition._types import CurMarketBoardParams, Shopping, ShoppingCurrency, ShoppingItem
    from moogle_intuition.ff14angler import Angler

    from ._types import AllagonToolsInventoryCSV, FurnitureFixtures, FurnitureMaterial, FurnitureProperty, MakePlaceData



LOGGER = logging.getLogger(__name__)

ATOOLS_OMIT_INV_LOCS: list[InventoryLocation] = [
    InventoryLocation.FREE_COMPANY,
    InventoryLocation.CURRENCY,
    InventoryLocation.CRYSTALS,
    InventoryLocation.GLAMOUR_CHEST,
    InventoryLocation.MARKET,
    InventoryLocation.ARMOIRE,
    InventoryLocation.ARMORY,
    InventoryLocation.EQUIPPED_GEAR,
]

ATOOLS_OMIT_ITEM_NAMES: list[str] = []

__all__ = ("ATOOLS_OMIT_INV_LOCS", "ATOOLS_OMIT_ITEM_NAMES", "MakePlace")


class MakePlace(Moogle):
    """Handling MakePlace related functionality."""

    def __init__(
        self,
        *,
        session: Optional[aiohttp.ClientSession | CachedSession] = None,
        universalis: Optional[UniversalisAPI] = None,
        angler: Optional[Angler] = None,
        garlandtools: Optional[GarlandToolsAsync] = None,
    ) -> None:
        """Build your MakePlace.

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
        super().__init__(session, universalis, angler, garlandtools)

    def _parse_atools_csv(
        self,
        data: bytes | str,
        *,
        omit_item_names: Optional[list[str]] = None,
        omit_inv_locs: Optional[list[InventoryLocation]] = None,
    ) -> list[InventoryItem]:
        r"""Parse a Allagon Tools Inventory CSV.

        Take's the `bytes` or `str` array and returns a list of :class:`InventoryItem`.
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
        :class:`list[InventoryItem]`
            Returns a list of converted CSV data into InventoryItem.

        """
        if isinstance(data, bytes):
            data = data.decode(encoding="utf-8")

        keys = data.split("\n")[0]

        if omit_inv_locs is None:
            omit_inv_locs = ATOOLS_OMIT_INV_LOCS

        if omit_item_names is None:
            omit_item_names = ATOOLS_OMIT_ITEM_NAMES

        # Keys= "Favorite?", "Icon", "Name", "Type", "Total Quantity Available", "Source", "Inventory Location"
        # We know the structure of res to be Iterator[AllagonToolsInventoryCSV].
        # _keys: list[str] = keys.strip().replace("?", "").lower().replace(" ", "_").split(",")
        _keys: list[str] = ["favorite", "icon", "name", "type", "total_quantity_available", "source", "inventory_location"]
        res: Iterator[AllagonToolsInventoryCSV] = csv.DictReader(data.split("\n")[1:], fieldnames=_keys)  # type: ignore[reportAssignmentType]
        next(res)  # force bypass the header/keys
        LOGGER.debug(
            "<%s.%s> | Reading CSV data. | keys: %s | data size: %s",
            __class__.__name__,
            "_parse_atools_csv",
            _keys,
            len(data[len(keys) :]),
        )
        inventory: list[InventoryItem] = []
        for entry in res:
            if entry["name"].lower().startswith("free company credits") or entry["name"].lower() in omit_item_names:
                LOGGER.debug("<%s.%s> | Skipping entry. | entry: %s", __class__.__name__, "_parse_atools_csv", entry["name"])
                continue
            # Given we are using item names; there is a "small" chance it will return incorrect items
            # but it should find everything as it's directly from the game.
            try:
                item: Item = self.get_item(item=entry["name"], limit_results=1, match=95)
            except MoogleLookupError:
                LOGGER.warning("<%s.%s> | Failed to lookup item name. | item: %s", __class__.__name__, "_parse_atools_csv", entry["name"])
                continue
            # inv_item = InventoryItem(item_id=item.id, atools_data=entry, moogle=self)
            inv_item = InventoryItem(item=item, atools_data=entry)
            # If we have inventory locations to omit and our item is NOT in that list of locations, lets add it to our results.
            if inv_item.location not in omit_inv_locs:
                inventory.append(inv_item)

        return inventory

    def _parse_makeplace_json(self, data: MakePlaceData) -> list[InventoryItem]:
        """Parses MakePlace JSON data structure into a list of :class:`Item`.

        .. note::
            A simple `json.loads()` will suffice for passing in the required data as long as the proper keys are present.


        Parameters
        ----------
        data: :class:`MakePlaceData`
            The MakePlace JSON data to parse.

        Returns
        -------
        :class:`list[Item]`
            A list of :class:`Item`.

        Raises
        ------
        :class:`MoogleLookupError`
            If we are unable to find any of the Item IDs in the data provided for any reason.

        """
        items: list[InventoryItem] = []
        keys: list[str] = ["interiorFixture", "interiorFurniture", "exteriorFixture", "exteriorFurniture"]
        bad_keys: list[str] = ["district", "side door"]
        for key in keys:
            value: list[FurnitureFixtures] = data.get(key, None)
            for entry in value:
                if "type" in entry and entry["type"].lower() in bad_keys:
                    continue
                try:
                    item = self.get_item(item=str(entry["itemId"]), limit_results=1)
                    struct: AllagonToolsInventoryCSV = {"name" : item.name,
                                                                    "type": "NQ",
                                                                    "total_quantity_available" : 1,
                                                                    "source": "makeplace",
                                                                    "inventory_location": "0"}
                    inv_item = InventoryItem(item, struct)
                    for item_entry in items:
                        if item_entry.item == inv_item:
                            item_entry.quantity +=1
                except MoogleLookupError:
                        LOGGER.error("<%s.%s> | Failed Item lookup. | Value: %s",
                                     __class__.__name__,
                                     "_parse_makeplace_json",
                                     str(entry["itemId"]))
                        continue
                properties: FurnitureProperty | None = entry.get("properties")
                if properties is not None:
                    colour: str | None = properties.get("color")
                    if colour is not None:
                        temp = ""

                        try:
                            temp = ColorRef(colour[:-2])
                            item = self.get_item(item=temp.name.replace("_", " "), limit_results=1)
                            struct: AllagonToolsInventoryCSV = {"name" : temp.name.replace("_", " "),
                                                                "type": "NQ",
                                                                "total_quantity_available": 1,
                                                                "source": "makeplace",
                                                                "inventory_location": "0"}
                            inv_item = InventoryItem(item, struct)
                            # Update our quantity...
                            for item_entry in items:
                                if item_entry.item == inv_item:
                                    item_entry.quantity +=1

                        except ValueError:
                            LOGGER.error(
                                "<%s.%s> | Failed Color Hex lookup. | Value: %s",
                                __class__.__name__,
                                "_parse_makeplace_json",
                                colour,
                            )
                            continue
                        except MoogleLookupError:
                            LOGGER.error("<%s.%s> | Failed Item lookup. | Value: %s", __class__.__name__, "_parse_makeplace_json", temp)
                            continue

                    material: FurnitureMaterial | None = properties.get("material")
                    if material is not None:
                        temp = ""
                        try:
                            temp = material.get("itemId")
                            try:
                                item: Item = self.get_item(item=str(temp), limit_results=1)
                            except MoogleLookupError:
                                LOGGER.error("<%s.%s> | Failed Item lookup. | Value: %s", __class__.__name__, "_parse_makeplace_json", temp)
                                continue
                            struct: AllagonToolsInventoryCSV = {"name" : item.name,
                                                                "type": "NQ",
                                                                "total_quantity_available": 1,
                                                                "source": "makeplace",
                                                                "inventory_location": "0"}
                            inv_item = InventoryItem(item, struct)
                            for item_entry in items:
                                if item_entry.item == inv_item:
                                    item_entry.quantity +=1
                        except MoogleLookupError:
                            LOGGER.error("<%s.%s> | Failed Item lookup. | Value: %s", __class__.__name__, "_parse_makeplace_json", temp)
                            continue

        return items

    def _parse_makeplace_item(
        self,
        data: ShoppingItem,
        currency: ShoppingCurrency,
        *,
        depth: int = 0,
    ) -> tuple[list[str], ShoppingCurrency]:
        """Parse each :class:`MakePlaceItem` data struct into a Markdown format.

        Parameters
        ----------
        data: :class:`ShoppingItem`
            The data to be parsed.
        currency: :class:`ShoppingCurrency`
            A data struct to hold any currencies we need during parsing.
        depth: :class:`int`, optional
            Controls the Header size during recursive iteraction for the :class:`Item` name header, by default 0.

        Returns
        -------
        :class:`tuple[list[str], ShoppingCurrency]`
            The list of Markdown formatted strings and the :class:`ShoppingCurrency` object filled with data during iterations.

        """
        output: list[str] = []
        item: Item = data["item"]
        header = f"{depth * '#'}## __[{item.name}]({item.garland_tools_url})__ [{item.id}]"
        output.append(header)
        output.append(f"> Count: {data.get('count')}\n")
        ingredients: list[ShoppingItem] = data.get("ingredients", [])
        # This is just simply parsing the `Item` object.
        # Ingredient Information, Name, URL, ID and Count
        # Gathering...
        if item.gathering is not None:
            LOGGER.debug("<%s.%s> | Parsing Gathering for Item | Item: %s", __class__.__name__, "_parse_makeplace_item", item)
            output.append("#### **Gathering**:")
            if item.gathering.nodes is not None:
                for node in item.gathering.nodes[:3]:
                    zone_name = node.zone_name.name if isinstance(node.zone_name, PlaceName) else f"ID: {node.zone_name}"
                    output.append(
                        f"> **Lv. {node.lvl}** | [{zone_name}, {node.area_name}]({node.garland_tools_url}) | `{node.coords}`\n",
                    )
        # Fishing...
        if item.fishing is not None and isinstance(item.fishing.fishing_spot, FishingSpot):
            LOGGER.debug("<%s.%s> | Parsing Fishing for Item | Item: %s", __class__.__name__, "_parse_makeplace_item", item)
            output.append(f"#### **Fishing**: Angler URL -> {item.fishing.fishing_spot.angler_url}")
            fishing_spot: FishingSpot = item.fishing.fishing_spot
            place_name = fishing_spot.place_name.name if isinstance(fishing_spot.place_name, PlaceName) else fishing_spot.place_name
            output.append(
                f"> {place_name} | {fishing_spot.fishing_spot_category.name} | `{fishing_spot.x}, {fishing_spot.z}",
            )
        # Spearfishing...
        if item.spear_fishing is not None:
            LOGGER.debug("<%s.%s> | Parsing SpearFishing for Item | Item: %s", __class__.__name__, "_parse_makeplace_item", item)
            output.append(f"#### **SpearFishing**: Angler URL -> {item.spear_fishing.territory_type.angler_url}")
            spearfishing_spot: SpearFishingSpot = item.spear_fishing.territory_type
            output.append(
                f"> {spearfishing_spot.place_name} | Shadow: {spearfishing_spot.is_shadow_node} | "
                f"`{spearfishing_spot.x}, {spearfishing_spot.y}",
            )

        # Marketboard/Universalis Info.
        if item.mb_current is not None:
            LOGGER.debug("<%s.%s> | Parsing Universalis for Item | Item: %s", __class__.__name__, "_parse_makeplace_item", item)
            marketboard: CurrentData = item.mb_current
            market_listing: CurrentDataEntries = sorted(marketboard.listings, key=lambda x: x.price_per_unit)[0]
            currency["marketboard_gil"] += market_listing.tax + market_listing.total
            # TODO(@k8thekat): Improve timestamp display, show date and time as UTC.
            if isinstance(market_listing.last_review_time, datetime.datetime):
                output.append(f"#### __Marketboard__: [{market_listing.last_review_time.date()}]")
            else:
                output.append(f"#### __Marketboard__: [{market_listing.last_review_time}]")

            output.append(f"> **World/DC**: {market_listing.world_name}/{market_listing.dc_name}\n")
            output.append(f"> **PPU [Listing Count]**: {market_listing.price_per_unit:,d} gil [{market_listing.quantity:,d}]\n")
            output.append(f"> **Total**: {market_listing.tax + market_listing.total:,d} gil")

        # Vendors info...
        if item.vendors is not None:
            LOGGER.debug("<%s.%s> | Parsing Vendors for Item | Item: %s", __class__.__name__, "_parse_makeplace_item", item)
            vendor_cur_flag = True
            output.append("#### **Vendor**:")
            for cur_vendor in item.vendors[:3]:
                output.append(
                    f"- [{cur_vendor.get('name')} | {cur_vendor.get('shop_name')}]({cur_vendor.get('url', 'N/A')})",
                )
                currency_item: Item | None = cur_vendor.get("currency")
                price = cur_vendor.get("price", 0)
                if currency_item is not None:
                    # See if the currency exists; if not set a default value of 0
                    if currency["currencies"].get(currency_item.id) is None:
                        currency["currencies"][currency_item.id] = 0

                    output.append(f"\t - Currency: {currency_item} | Cost: {price}")
                    if vendor_cur_flag is True:
                        currency["currencies"][currency_item.id] += price
                        vendor_cur_flag = False
                else:
                    output.append(f"\t - Currency: Gil | Cost: {price}")
                    if vendor_cur_flag is True:
                        currency["currencies"][0] += price
                        vendor_cur_flag = False

        # Tradeshop Info...
        if item.tradeshops is not None:
            LOGGER.debug("<%s.%s> | Parsing TradeShops for Item | Item: %s", __class__.__name__, "_parse_makeplace_item", item)
            shop_cur_flag = True
            output.append("#### **Tradeshops**:")
            for cur_shop in item.tradeshops[:3]:
                output.append(
                    f"- [{cur_shop.get('name')} | {cur_shop.get('shop_name')}]({cur_shop.get('url', 'N/A')})",
                )
                currency_item: Item | None = cur_shop.get("currency")
                price = cur_shop.get("price", 0)
                if currency_item is not None:
                    # See if the currency exists; if not set a default value of 0
                    if currency["currencies"].get(currency_item.id) is None:
                        currency["currencies"][currency_item.id] = 0

                    output.append(f"\t - Currency: {currency_item.name} | Cost: {price}")
                    if shop_cur_flag is True:
                        currency["currencies"][currency_item.id] += price
                        shop_cur_flag = False
                else:
                    output.append(f"\t - Currency: Gil | Cost: {price}")
                    if shop_cur_flag is True:
                        currency["currencies"][0] += price
                        shop_cur_flag = False

        if len(ingredients) > 0:
            LOGGER.debug(
                "<%s.%s> | Parsing Crafting Ingredients for Item | Item: %s | # of Ingredients: %s | Array: %s",
                __class__.__name__,
                "_parse_makeplace_item",
                item,
                len(ingredients),
                ingredients,
            )
            for entry in ingredients:
                res = self._parse_makeplace_item(data=entry, currency=currency, depth=depth + 1)
                # We want to insert a link/ref for the Item this ingredient is related to.
                res[0][1:1] = [f"- **Crafting Ingredient for** [{item.name}]({item.name.lower().replace(' ', '-')}-{item.id})"]
                output.extend(res[0])
        return output, currency

    def _parse_makeplace_shopping(self, data: Shopping) -> Optional[list[str]]:
        """Create an array of Markdown formatted strings from our :class:`Shopping` provided data.

        Parameters
        ----------
        data: :class:`Shopping`
            Our MakePlace Shopping data from :class:`Moogle.makeplace_housing`.

        Returns
        -------
        :class:`Optional[list[str]]`
            List of Markdown formatted strings.

        Raises
        ------
        :class:`MoogleLookupError`
            If we fail to find the Currency Item ID in our Final Fantasy 14 Items.

        """
        output: list[str] = []
        output.append("# MakePlace Shopping List:")
        output.append("*Note*: Marketboard Total includes Tax. *(mb listing count * price per unit + tax)*\n")
        output.append(f"__[TeamCraft List URL]({data.get('teamcraft_url', '')})__")
        items: dict[int, ShoppingItem] | None = data.get("items")
        if items is None:
            return None
        output.append(f"\n- Total # of Items: {data.get('total_item_count', 'UNK')}\n----")

        items: dict[int, ShoppingItem] | None = data.get("items")
        if items is None:
            return None

        data["currencies"] = {"marketboard_gil": 0, "currencies": {0: 0}}
        currency: ShoppingCurrency = data["currencies"]

        for entry in items:
            value: ShoppingItem | None = items.get(entry)
            if value is None:
                continue
            res = self._parse_makeplace_item(data=value, currency=currency)
            output.extend(res[0])
            currency = res[1]
            output.append("\n")
            output.append("---")
        output.append("## Total Costs:")
        output.append(f"**Total Marketboard Gil**: {currency['marketboard_gil']:,d}\n")
        output.append(f"**Total Vendor Gil**: {currency['currencies'][0]:,d}\n")
        output.append("### Currencies:")
        for key, count in currency["currencies"].items():
            if key == 0:
                continue
            try:
                currency_item: Item = self.get_item(item=str(key), limit_results=1)
            except MoogleLookupError:
                LOGGER.error("<%s.%s> | Failed to find Currency Item | Item: %s", __class__.__name__, "_parse_makeplace_shopping", key)
                raise

            output.append(f"[{currency_item.name}]({currency_item.garland_tools_url}) | Count: {count:,d}\n")

        return output

    async def create_itemlist(
        self,
        makeplace_data: MakePlaceData,
        atools_data: bytes | str,
        omit_item_names: Optional[list[str]] = None,
        omit_inv_locs: Optional[list[InventoryLocation]] = None,
    ) -> list[InventoryItem]:
        """Compares MakePlace JSON data with Allagon Tools CSV data to find items not in your inventory.

        Parameters
        ----------
        makeplace_data: :class:`MakePlaceData`
            The MakePlace JSON data.
        atools_data: :class:`bytes | str`
            The Allagon Tools CSV data.
        omit_inv_locs: :class:`Optional[list[InventoryLocationEnum]]`, optional
            The inventory location of the item to omit from our returned list, by default is None.
            - If `None`, will use the global `ATOOLS_OMIT_INV_LOCS`.
        omit_item_names: :class:`Optional[list[str]]`, optional
            Any item names to omit such as `Free Company Credits` as it's not apart of the XIV Item.json, by default [].
            - If `None`, will use the global `ATOOLS_OMIT_ITEM_NAMES`.


        Returns
        -------
        :class:`list[InventoryItem]`
            A list of Moogles Intution :class:`Item` objects representing the items not found in your inventory.

        """
        have_items: list[InventoryItem] = self._parse_atools_csv(atools_data, omit_inv_locs=omit_inv_locs, omit_item_names=omit_item_names)
        want_items: list[InventoryItem] = self._parse_makeplace_json(makeplace_data)
        for inv_entry in have_items:
            for want in want_items:
                # We found an item we want in our inventory; so remove it from our want list.
                # We want to make sure we have enough in our inventory. As Want Items will have duplicates of a
                # single Item to simulate quantity needed.
                if want.id == inv_entry.id and inv_entry.quantity > 0:
                    want_items.remove(want)
                    inv_entry.quantity -= 1
                    break
        return want_items

    @overload
    async def makeplace_housing(self, items: list[Item], *, to_markdown: Literal[True]) -> Optional[list[str]]: ...

    @overload
    async def makeplace_housing(self, items: list[Item], *, to_markdown: bool = ...) -> Shopping: ...

    # TODO(@k8thekat): See about using our InventoryItem array and deduct item.recipe ingredients from our on hand quantity/etc
    async def makeplace_housing(
        self,
        items: list[Item],
        *,
        to_markdown: bool = False,
        **kwargs: Unpack[CurMarketBoardParams],
    ) -> Shopping | Optional[list[str]]:
        """Parses an array of :class:`Item` objects to convert into a :class:`MakePlaceShopping` data struct..

        .. note::
            Iterates through our list of :class:`Item` objects and populate attributes such as `mb_current`, `gathering`,
            `recipe` and `garlandtools_data` to then be parsed into :class:`MakePlaceShopping`.


        Parameters
        ----------
        items: :class:`list[Item]`
            A list of Final Fantasy 14 Item objects.
        to_markdown: :class:`bool`, optional
            Convert the resulting data into a Markdown style sheet, by default False.
        **kwargs: :class:`Unpack[CurmarketBoardParams]`
            Any additional params to pass to `<UniversalisAPI.get_bulk_current_data()>`.

        Returns
        -------
        :class:`MakePlaceShopping | Optional[list[str]]`
            Either a :class:`TypedDict` structured with the parsed data or
            if `to_marketdown` is `True` will return a list of strings formatted in a Markdown structure..

        """
        shopping: Shopping = {}
        url: str | None = self.teamcraft_list(items)
        shopping["teamcraft_url"] = "" if url is None else url
        shopping["total_item_count"] = len(items)
        shopping["items"] = {}

        for item in items:
            if item.mb_current is None:
                await item.get_current_marketboard(**kwargs)
            if item.garlandtools_data is None:
                # print("Garland Tools Data for Item", item.name)
                await item.get_garlandtools_data()
                item.get_vendors()
                item.get_tradeshops()
            if item.gathering is not None:
                await item.gathering.get_gathering_nodes()
            # See if the item already exists; if not populate a generic `Crafting` dict for it.
            # else, we update the count and go to our next entry.
            if shopping["items"].get(item.id) is None:
                shopping["items"][item.id] = {"item": item, "count": 1, "ingredients": []}
            else:
                shopping["items"][item.id]["count"] += 1
                continue

            # Recipe check, then update our Crafting struct related to key.
            if item.recipe is not None:
                # set up an ingredients list related to our Item.
                item_ingredients: list[ShoppingItem] = shopping["items"][item.id].get("ingredients", [])
                for recipe in item.recipe:
                    for ingredient in recipe:

                        # If the ingredient has a recipe; let's parse it's information.
                        if ingredient[0].recipe is not None:
                            # We are going to access the "items" key only to update our parent level Item.
                            # print("Parsing ingredient Name | Count", ingredient[0].name, ingredient[1])
                            data: Shopping = await self.makeplace_housing(items=[ingredient[0]])
                            res: dict[int, ShoppingItem] | None = data.get("items", None)
                            if res is not None:
                                # We update the count based upon the recipe ingredient amount at top level.
                                res[ingredient[0].id]["count"] = ingredient[1]
                                item_ingredients.extend(list(res.values()))
                            else:
                                continue
                        else:
                            if item.mb_current is None:
                                await item.get_current_marketboard(**kwargs)
                            if ingredient[0].garlandtools_data is None:
                                # print("Garland Tools Data for Item", item.name)
                                await ingredient[0].get_garlandtools_data()
                                ingredient[0].get_vendors()
                                ingredient[0].get_tradeshops()
                                if ingredient[0].gathering is not None:
                                    await ingredient[0].gathering.get_gathering_nodes()
                            item_ingredients.append({"item": ingredient[0], "count": ingredient[1], "ingredients": []})
                    break
        if to_markdown is True:
            return self._parse_makeplace_shopping(data=shopping)
        return shopping



class InventoryItem(Item):
    """Represents an Item from a parsed Allagon Tools Inventory CSV file.

    Attributes
    ----------
    name: :class:`str`
        The name of the item.
    id: :class:`int`
        The item ID.
    quality: :class:`Literal["HQ", "NQ"]`
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
    quality: Literal["HQ", "NQ"]
    quantity: int
    source: str
    location: InventoryLocation

    _locations: ClassVar[dict[str, InventoryLocation]] = {
        "armory": InventoryLocation.ARMORY,
        "armoire": InventoryLocation.ARMOIRE,
        "bag": InventoryLocation.BAG,
        "currency": InventoryLocation.CURRENCY,
        "crystals": InventoryLocation.CRYSTALS,
        "equipped gear": InventoryLocation.EQUIPPED_GEAR,
        "free company": InventoryLocation.FREE_COMPANY,
        "glamour chest": InventoryLocation.GLAMOUR_CHEST,
        "market": InventoryLocation.MARKET,
        "premium saddlebag left": InventoryLocation.PREMIUM_SADDLEBAG_LEFT,
        "premium saddlebag right": InventoryLocation.PREMIUM_SADDLEBAG_RIGHT,
        "saddlebag left": InventoryLocation.SADDLEBAG_LEFT,
        "saddlebag right": InventoryLocation.SADDLEBAG_RIGHT,
        "housing interior placed": InventoryLocation.HOUSING_INTERIOR_PLACED,
        "housing interior storeroom": InventoryLocation.HOUSING_INTERIOR_STORED,
        "housing exterior placed": InventoryLocation.HOUSING_EXTERIOR_PLACED,
        "housing exterior storeroom": InventoryLocation.HOUSING_EXTERIOR_STORED,
    }

    __slots__ = (
        "inventory_location",
        # "name",
        "source",
        "total_quantity_available",
        "type",
    )

    # def __init__(self, item_id: int, data: AllagonToolsInventoryCSV, **kwargs: Unpack[ObjectParams]) -> None:
    def __init__(self, item: Item, atools_data: AllagonToolsInventoryCSV) -> None:
        """Build your InventoryItem object.

        Parameters
        ----------
        item: :class:`int`
            Our Moogle's Intuition :class:`Item` object.
        atools_data: :class:`AllagonToolsInventoryCSV`
            The JSON data.

        """
        # super().__init__(atools_data, moogle=kwargs["moogle"])
        # self.id = item_id
        self.item: Item = item
        self.id = item.id
        self.name = item.name
        self._repr_keys = ["name", "id", "quality", "quantity", "location", "source"]
        for key in self.__slots__:
            value: Optional[int | bool | str] = atools_data.get(key, None)
            if value is None:
                continue

            if key.lower() == "type":
                if isinstance(value, str) and value.lower() == "nq":
                    self.quality = "NQ"

                elif isinstance(value, str) and value.lower() == "hq":
                    self.quality = "HQ"

            elif key.lower() == "total_quantity_available":
                self.quantity = int(value)

            elif key.lower() == "inventory_location" and isinstance(value, str):
                self.location = self._convert_inv_loc_to_enum(location=value)

            else:
                setattr(self, key, value)

    def __eq__(self, other: object) -> bool:
        return super().__eq__(other=other)

    def __hash__(self) -> int:
        return super().__hash__()

    def __lt__(self, other: object) -> bool:
        return super().__lt__(other=other)

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
        for key, value in InventoryItem._locations.items():
            if location.lower().startswith(key):
                return value

        return InventoryLocation.NULL
