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

import copy
import csv
import logging
from typing import TYPE_CHECKING, ClassVar, Literal, NamedTuple, Optional, Unpack

from moogle_intuition import Item as MoogleItem, Moogle, Recipe as MoogleRecipe
from moogle_intuition.errors import MoogleLookupError
from moogle_intuition.ext.allagan_tools._types import RecipeCrafting
from moogle_intuition.modules import JobRecipe as MoogleJobRecipe

from ._enums import InventoryLocation

if TYPE_CHECKING:
    from collections.abc import Iterator

    from moogle_intuition._types import ItemData, ObjectParams, RecipeData, RecipeLookUpData
    from moogle_intuition.ext.allagan_tools._types import AllaganToolsData
    from moogle_intuition.modules import DataTypeAliases

    from ._types import AllaganToolsInventoryCSV, RecipeCrafting


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
DATETIMEFMT: str = "%d/%m | %H:%M(%Z)"

__all__ = ("ATOOLS_OMIT_INV_LOCS", "ATOOLS_OMIT_ITEM_NAMES", "AllaganTools", "InventoryItem", "Recipe")
__version__ = "1.0.1"


class VersionInfo(NamedTuple):
    major: int
    minor: int
    revision: int
    release_level: Literal["release", "development"]


version_info: VersionInfo = VersionInfo(major=1, minor=0, revision=1, release_level="development")


class AllaganTools(Moogle):
    """An expanded handler similar to :class:`Moogle`; but has the ability to parse `Allagan Tools` CSV data."""

    # Handles interactions with AllaganTools CSV data and Moogles Intuition as a separate class.
    def parse_atools_csv(
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
        res: Iterator[AllaganToolsInventoryCSV] = csv.DictReader(data.split("\n")[1:], fieldnames=_keys)  # type: ignore[reportAssignmentType]
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
                item: MoogleItem = self.get_item(item=entry["name"], limit_results=1, match=95)
            except MoogleLookupError:
                LOGGER.warning("<%s.%s> | Failed to lookup item name. | item: %s", __class__.__name__, "_parse_atools_csv", entry["name"])
                continue

            inv_item: InventoryItem | None = InventoryItem.from_obj(obj=item, **entry)
            # if inv_item is None:
            #     LOGGER.warning(
            #         "<%s.%s> | Failed to convert Item -> InventoryItem. | item: %s", __class__.__name__, "_parse_atools_csv", item,
            #     )
            #     continue
            # If we have inventory locations to omit and our item is NOT in that list of locations, lets add it to our results.
            if inv_item.location not in omit_inv_locs:
                inventory.append(inv_item)

        return inventory


class InventoryItem(MoogleItem):
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

    _jobrecipes: Optional[MoogleJobRecipe | JobRecipe]

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

    def __init__(self, data: ItemData, atools_data: AllaganToolsData, **kwargs: Unpack[ObjectParams]) -> None:
        """Build your InventoryItem object.

        Parameters
        ----------
        data: :class:`ItemData`
            The JSON data from XIV Item JSON.
        atools_data: :class:`ItemData`
            The JSON data from Allagan Tools CSV parsing.
        **kwargs: :class:`Unpack[ObjectParams]`
            Any additional functionality such as a :class:`Angler` object or :class:`UniversalisAPI` object.
            - By default the :class:`Moogle` object is required for functionality.

        """
        super().__init__(data, moogle=kwargs["moogle"])
        self._repr_keys = ["name", "id", "quality", "quantity", "location", "source"]
        __slots__ = (
            "inventory_location",
            # "name",
            "source",
            "total_quantity_available",
            "type",
        )
        for key in __slots__:
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

        if self._jobrecipes is not None:
            self._jobrecipes = self._get_item_job_recipes(self.id)

    def __eq__(self, other: object) -> bool:  # noqa: D105
        return super().__eq__(other=other)

    def __hash__(self) -> int:  # noqa: D105
        return super().__hash__()

    def __lt__(self, other: object) -> bool:  # noqa: D105
        return super().__lt__(other=other)

    def __copy__(self) -> InventoryItem:
        """A "generic" copy of the object typically to `de-reference` similar objects.

        Returns
        -------
        :class:`InventoryItem`
            A new `InventoryItem` object.

        """
        new_data: AllaganToolsData = {}
        new_data["inventory_location"] = self.location.name
        new_data["total_quantity_available"] = self.quantity
        new_data["source"] = self.source
        new_data["type"] = self.quality
        new = InventoryItem(self._raw, atools_data=new_data, moogle=self._moogle) # pyright: ignore[reportArgumentType] # I am unsure how to narrow the scope of the `self._raw` for an Item.
        new._external = self.external
        return new


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
            The converted inventory location as an Enum, otherwise will return a `NULL` inventory slot if lookup fails.

        """
        for key, value in InventoryItem._locations.items():
            if location.lower().startswith(key):
                return value

        return InventoryLocation.NULL

    @staticmethod
    def from_obj(obj: MoogleItem, **data: Unpack[AllaganToolsData]) -> InventoryItem:
        """Converts an existing :class:`MoogleItem` into an InventoryItem for use with Inventory deduction via Recipe/Crafting ingredients.

        Parameters
        ----------
        obj: :class:`MoogleItem`
            An existing Moogle Item object to be converted.
        **data: :class:`Unpack[AllaganToolsData]`, optional
            All keys in :class:`AllaganToolsData` are optional, default values will be filled in.
            ```
            "inventory_location" = "NULL"
            "total_quantity_available" = 1
            "source" = "UNK"
            "type" = "NQ"
            ```

        Returns
        -------
        :class:`InventoryItem`
            The resulting converted item with the additional attributes set including any external data attached to the original Item.

        """
        # Key validation for our passed in data.
        new_data: AllaganToolsData = {}
        new_data["inventory_location"] = data.get("inventory_location", "NULL")
        new_data["total_quantity_available"] = data.get("total_quantity_available", 1)
        new_data["source"] = data.get("source", "UNK")
        new_data["type"] = data.get("type", "NQ")
        new: InventoryItem = InventoryItem(data=obj._raw, atools_data=new_data, moogle=obj._moogle)  # pyright: ignore[reportArgumentType] # We have type control via object validation.
        new._external = obj.external
        return new

    @property
    def jobrecipes(self) -> Optional[JobRecipe]:
        """Any recipe information stored in seperately attached attributes related to the :class:`Item`, if applicable.

        Returns
        -------
        :class:`Optional[JobRecipe]`
            Returns any related recipe information as an object representing the data from the recipe.json.

        """
        if type(self._jobrecipes) is MoogleJobRecipe:
            return JobRecipe.from_obj(self._jobrecipes)
        if type(self._jobrecipes) is JobRecipe:
            return self._jobrecipes
        return None

    @property
    def recipe(self) -> Optional[Recipe]:
        """The first job specific recipe, if applicable.

        Returns
        -------
        :class:`Optional[Recipe]`
            A representation of a Final Fantasy 14 Recipe.

        """
        if self._jobrecipes is not None:
            return Recipe.from_obj(self._jobrecipes[0])
        return self._jobrecipes

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


class JobRecipe(MoogleJobRecipe):
    _item: MoogleItem | InventoryItem
    CRP: Optional[MoogleRecipe | Recipe]
    "Carpenter related Job Recipe, if applicable."
    BSM: Optional[MoogleRecipe | Recipe]
    "Blacksmith related Job Recipe, if applicable."
    ARM: Optional[MoogleRecipe | Recipe]
    "Armorsmith related Job Recipe, if applicable."
    GSM: Optional[MoogleRecipe | Recipe]
    "Goldsmith related Job Recipe, if applicable."
    LTW: Optional[MoogleRecipe | Recipe]
    "Leatherworker related Job Recipe, if applicable."
    WVR: Optional[MoogleRecipe | Recipe]
    "Weaver related Job Recipe, if applicable."
    ALC: Optional[MoogleRecipe | Recipe]
    "Alchemist related Job Recipe, if applicable."
    CUL: Optional[MoogleRecipe | Recipe]
    "Culinarian related Job Recipe, if applicable."

    def __init__(self, data: RecipeLookUpData, item: InventoryItem, **kwargs: Unpack[ObjectParams]) -> None:
        """Build your :class:`JobRecipe` obj.

        Parameters
        ----------
        data: :class:`RecipeLookUpData`
            _description_.
        item: :class:`InventoryItem`
            _description_.

        """
        super().__init__(data=data, item=item, **kwargs)

        # This ensure consistency when accessing attributes.
        self._item = item

        # This is to update the Job attributes to the proper objects for Allagan Tools
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

    def _get_recipe(self, recipe_id: str) -> Recipe:
        """Lookup a Final Fantasy 14 Recipe by ID.

        Parameters
        ----------
        recipe_id: :class:`str`
            The recipe ID.

        Returns
        -------
        :class:`Recipe`
            A Recipe object containing crafting related information.

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

        if type(self._item) is InventoryItem:
            return Recipe(recipe_id=recipe_id, data=data, item=self._item, moogle=self._moogle)
        return Recipe(recipe_id=recipe_id, data=data, item=InventoryItem.from_obj(self._item), moogle=self._moogle)

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

    @staticmethod
    def from_obj(obj: MoogleJobRecipe) -> JobRecipe:
        """Convert your Moogle JobRecipe item into a Allagan Tools :class:`JobRecipe`.

        Similar to :class:`JobRecipe`; but simply a transformer to handle the :class:`Recipe` objects.

        Parameters
        ----------
        obj: :class:`MoogleJobRecipe`
            Convert an existing Moogle JobRecipe object into an Allagan Tools Recipe.

        Returns
        -------
        :class:`JobRecipe`
            A Allagan Tools based JobRecipe object to house the Allagan Tools Recipe objects.

        """
        new: JobRecipe = JobRecipe(obj._raw, item=InventoryItem.from_obj(obj._item), moogle=obj._moogle)  # pyright: ignore[reportArgumentType] # Type control comes from the function obj Type.
        return new


class Recipe(MoogleRecipe):
    """An extension of :class:`MoogleRecipe` for Allagan Tools interactions and functionality.

    .. note::
        Has functionality to calculate item quanity based upon provided Inventory information, see `inventory_crafting()`

    """

    item_result: MoogleItem | InventoryItem
    amount_result: int

    ingredient0: Optional[MoogleItem | InventoryItem | int]
    amount_ingredient0: Optional[int]
    ingredient1: Optional[MoogleItem | InventoryItem | int]
    amount_ingredient1: Optional[int]
    ingredient2: Optional[MoogleItem | InventoryItem | int]
    amount_ingredient2: Optional[int]
    ingredient3: Optional[MoogleItem | InventoryItem | int]
    amount_ingredient3: Optional[int]
    ingredient4: Optional[MoogleItem | InventoryItem | int]
    amount_ingredient4: Optional[int]
    ingredient5: Optional[MoogleItem | InventoryItem | int]
    amount_ingredient5: Optional[int]
    ingredient6: Optional[MoogleItem | InventoryItem | int]
    amount_ingredient6: Optional[int]
    ingredient7: Optional[MoogleItem | InventoryItem | int]
    amount_ingredient7: Optional[int]

    def __init__(self, recipe_id: str, data: RecipeData, item: InventoryItem, **kwargs: Unpack[ObjectParams]) -> None:
        """__init__ _summary_.

        Parameters
        ----------
        recipe_id: :class:`str`
            _description_.
        data: :class:`RecipeData`
            _description_.
        item: :class:`InventoryItem`
            _description_.

        """
        super().__init__(recipe_id=recipe_id, data=data, item=item, **kwargs)
        # We replace MoogleRecipe keys, because of the amount changes.
        # self._repr_keys = ["id", "craft_type", "item_result", "is_expert", "item_required", "amount_result"]
        # self._repr_keys.extend([f"item_ingredient{idx}" for idx in range(8)])
        for entry in [f"amount_ingredient{idx}" for idx in range(8)]:
            self._repr_keys.remove(entry)

        self.item_result = item
        # This all relies on the above `super()` call.
        ikeys = [f"ingredient{idx}" for idx in range(8)]
        for idx, entry in enumerate(ikeys):
            value: int | MoogleItem | None = getattr(self, entry)
            if isinstance(value, MoogleItem):
                amount: int | None = getattr(self, f"amount_ingredient{idx}")
                if amount is not None:
                    setattr(self, entry, InventoryItem.from_obj(value, total_quantity_available=amount))
                    setattr(self, f"amount_ingredient{idx}", amount)

    def __iter__(self) -> Iterator[InventoryItem]:
        """Yields a tuple containing :class:`Item` and item count:class:`int`."""
        _iter = 0
        while _iter < 8:
            try:
                ingredient: Optional[InventoryItem] = getattr(self, f"ingredient{_iter}")
                # count: Optional[int] = getattr(self, f"amount_ingredient{_iter}")
                if isinstance(ingredient, int) or (ingredient is None):
                    _iter += 1
                    continue

            except IndexError:
                raise StopIteration from IndexError

            _iter += 1
            yield ingredient

    @staticmethod
    def from_obj(obj: MoogleRecipe) -> Recipe:
        """Convert your Moogle Recipe item into a Allagan Tools :class:`Recipe`.

        Similar to :class:`MoogleRecipe`; but simply a transformer to handle the :class:`Recipe` objects.

        Parameters
        ----------
        obj: :class:`MoogleRecipe`
            Convert an existing Moogle Recipe object into an Allagan Tools Recipe.

        Returns
        -------
        :class:`Recipe`
            A Allagan Tools based Recipe object to house the Allagan Tools Item objects.

        """
        new: Recipe = Recipe(recipe_id=str(obj.id), data=obj._raw, item=InventoryItem.from_obj(obj.item_result), moogle=obj._moogle)  # pyright: ignore[reportArgumentType] # We know the type of the data due to the obj being passed in.
        return new


    def inventory_crafting(self, count: int = 1, **data: Unpack[RecipeCrafting]) -> RecipeCrafting:
        """Calculates the missing and used "Items" based upon the supplied Inventory array.

        Which can be used to calculate crafting cost, missing number of items vs completion or other stats.

        .. note::
            Use (:class:`Recipe.total_ingredient_quantity` / `data["used"]`) to calculate percent of ingredients for Recipe.

        Parameters
        ----------
        count: :class:`int`, optional
            The number of said item you wish to craft, by default 1.

        Returns
        -------
        :class:`RecipeCrafting`
            A dictionary with relevant crafting data seperated by the keys "used", "missing" and
            "inventory" which each house an array of :class:`InventoryItem`s.

        """
        i_item: InventoryItem
        inventory: list[InventoryItem] = data.get("inventory", [])
        used: list[InventoryItem] = data.get("used", [])
        missing: list[InventoryItem] = data.get("missing", [])

        LOGGER.debug("<%s.%s> | Running deductions. | len(inventory): %s | len(self): %s", self, "crafting_cost", len(inventory), len(self))
        res: RecipeCrafting = {"inventory": inventory, "missing": missing, "used": used}
        for recipe_item in self:
            if recipe_item in inventory:
                i_item = inventory[inventory.index(recipe_item)]
                offset: int = i_item.quantity - (count * recipe_item.quantity)
                # If the recipe calls for more items than we have in our inventory,
                # lets check if below 0, make a copy of the item and insert it into our
                # "missing" list and set the negative quantity accordingly.
                if offset <= 0:
                    offset = abs(offset)
                    # Update our used array.
                    if recipe_item not in used:
                        # This assumes we used all the inventory item quantity;
                        # so with the copy we automatically have our "used" quantity.
                        used.append(copy.copy(i_item))
                    else:
                        used[used.index(recipe_item)].quantity += i_item.quantity

                    # clearly we used up all our inventory item; so remove it.
                    if offset == 0:
                        inventory.remove(i_item)
                        continue

                    # Update our missing array only when we don't have enough items.
                    if recipe_item not in missing:
                        # We need to adjust the "Missing" because we were short on quantity only.
                        m_item: InventoryItem = copy.copy(recipe_item)
                        m_item.quantity = offset
                        missing.append(m_item)
                    else:
                        missing[missing.index(recipe_item)].quantity += offset

                # This updates our inventory
                # This assumes we had more inventory quantity than the recipe; so using the quantity from the recipe
                # should provide an accurate "usage" quantity value.
                i_item.quantity = offset
                if recipe_item not in used:
                    used.append(copy.copy(recipe_item))
                else:
                    used[used.index(recipe_item)].quantity += offset
            else:
                if recipe_item.jobrecipes is not None:
                    res = next(iter(recipe_item.jobrecipes)).inventory_crafting(count=count, **res)
                else:
                    # We only want to add "non" recipe items because we know they
                    # don't have the Recipe item from above and we are deducting the ingredients of the recipe from their inventory.
                    if recipe_item not in missing:
                        missing.append(copy.copy(recipe_item))
                    else:
                        missing[missing.index(recipe_item)].quantity += recipe_item.quantity


        return res
