from __future__ import annotations

from typing import Optional, TypedDict


class BaitsTyped(TypedDict):
    bait_name: str
    hook_percent: float | int | str


class FishingDataTyped(TypedDict):
    fish_name: str
    restrictions: list[str]
    hook_time: Optional[str]
    double_fish: int
    baits: dict[int, BaitsTyped]
