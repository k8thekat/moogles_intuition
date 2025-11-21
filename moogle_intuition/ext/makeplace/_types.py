from __future__ import annotations

from typing import NotRequired, TypedDict


class MakePlaceData(TypedDict):
    lightLevel: float
    houseSize: str
    interiorFixture: list[FurnitureFixtures]
    interiorScale: int
    interiorFurniture: list[FurnitureFixtures]
    exteriorScale: int
    exteriorFixture: list[FurnitureFixtures]
    exteriorFurniture: list[FurnitureFixtures]
    metaData: dict[str, int]
    properties: dict[str, str]


class FurnitureFixtures(TypedDict):
    level: NotRequired[str]
    type: NotRequired[str]
    name: str
    itemId: int
    color: NotRequired[str]
    transform: NotRequired[Transform]
    properties: NotRequired[FurnitureProperty]


class FurnitureProperty(TypedDict):
    material: NotRequired[FurnitureMaterial]
    color: NotRequired[str]


class FurnitureMaterial(TypedDict):
    name: str
    itemId: int


class Transform(TypedDict):
    location: list[float]
    rotation: list[float]
    scale: list[int]


class AllagonToolsInventoryCSV(TypedDict):
    favourite: NotRequired[bool]
    icon: NotRequired[str]
    name: str
    type: str
    total_quantity_available: int
    source: str
    inventory_location: str
