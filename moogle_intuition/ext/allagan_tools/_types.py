from __future__ import annotations

from typing import TYPE_CHECKING, NotRequired, TypedDict

if TYPE_CHECKING:
    from . import InventoryItem


class AllaganToolsInventoryCSV(TypedDict):
    favourite: NotRequired[bool]
    icon: NotRequired[str]
    name: str
    type: str
    total_quantity_available: int
    source: str
    inventory_location: str

class AllaganToolsData(TypedDict, total=False):
    favourite: bool
    icon: str
    name: str
    type: str
    total_quantity_available: int
    source: str
    inventory_location: str


class RecipeCrafting(TypedDict, total=False):
    inventory: list[InventoryItem]
    missing: list[InventoryItem]
    used: list[InventoryItem]
