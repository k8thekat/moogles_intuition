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

from enum import Enum, IntEnum
from typing import Optional

__all__ = (
    "CraftType",
    "Currency",
    "EquipSlotCategory",
    "Expansion",
    "FishingSpotCategory",
    "GrandCompany",
    "InventoryLocation",
    "ItemSeries",
    "ItemSpecialBonus",
    "ItemUICategory",
)


class CraftType(Enum):
    Carpenter = 0
    Blacksmith = 1
    Armorer = 2
    Goldsmith = 3
    Leatherworker = 4
    Weaver = 5
    Alchemist = 6
    Culinarian = 7

    def to_abbr(self, name: Optional[str] = None) -> str:
        """Converters the `name` attribute into it's abbreviated form.

        ```_mapping: dict[str, str] = {
            "Carpenter": "CRP",
            "Blacksmith": "BSM",
            "Armorer": "ARM",
            "Goldsmith": "GSM",
            "Leatherworker": "LTW",
            "Weaver": "WVR",
            "Alchemist": "ALC",
            "Culinarian": "CUL",
        }
        ```

        Returns
        -------
            A :class:`str` represensation of the abbreviated :class:`Self.name` if possible.

        """
        _mapping: dict[str, str] = {
            "Carpenter": "CRP",
            "Blacksmith": "BSM",
            "Armorer": "ARM",
            "Goldsmith": "GSM",
            "Leatherworker": "LTW",
            "Weaver": "WVR",
            "Alchemist": "ALC",
            "Culinarian": "CUL",
        }
        if name is not None:
            return _mapping.get(name, "UNK")
        return _mapping.get(self.name, "UNK")


class Currency(IntEnum):
    """Representation of FF14 Currencies.

    Values:
    ---
    Allagan_Tomestone_of_Poetics = 28
    Serpent_Seal = 21
    Allagan_Tomestone_of_Mathematics = 48
    Purple_Crafters_Scrips = 33913
    Allagan_Tomestone_of_Heliometry = 47
    Allied_Seal = 27
    Centurio_Seal = 10307
    Bicolor_Gemstone = 26807
    Skybuilders_Scrip = 28063
    Orange_Gatherers_Scrip = 41785
    Orange_Crafters_Scrip = 41784
    Purple_Gatherers_Scrip = 33914
    Gil = 0
    """

    Allagan_Tomestone_of_Poetics = 28
    Serpent_Seal = 21
    Allagan_Tomestone_of_Mathematics = 48
    Purple_Crafters_Scrips = 33913
    Allagan_Tomestone_of_Heliometry = 47
    Allied_Seal = 27
    Centurio_Seal = 10307
    Bicolor_Gemstone = 26807
    Skybuilders_Scrip = 28063
    Orange_Gatherers_Scrip = 41785
    Orange_Crafters_Scrip = 41784
    Purple_Gatherers_Scrip = 33914
    Gil = 0


class EquipSlotCategory(Enum):
    UNK = 0
    MainHand = 1
    OffHand = 2
    Head = 3
    Body = 4
    Gloves = 5
    Waist = 6
    Legs = 7
    Feet = 8
    Ears = 9
    Neck = 10
    Wrists = 11
    Finger = 12
    MainHand_Only = 13
    Both_Hands = 14
    SoulCrystal = 17
    Legs_No_Feet = 18
    Body_NoHead_NoGloves_NoLegs_NoFeet = 19
    Body_NoLegs_NoGloves = 20
    Body_NoLegs_NoFeet = 21
    Body_NoGloves = 22


class FishingSpotCategory(Enum):
    UNK = 0
    Ocean = 1
    Freshwater = 2
    Dunefishing = 3
    Skyfishing = 4
    Cloudfishing = 5
    Hellfishing = 6
    Aetherfishing = 7
    Saltfishing = 8
    Starfishing = 9


class GrandCompany(Enum):
    Maelstorm = 1
    Order_of_the_Twin_Adder = 2
    Immortal_Flames = 3


class InventoryLocation(IntEnum):
    """Enum for specifying Item Location in relation to the in game world.

    Parameters
    ----------
        NULL = 0 |
        BAG = 1 |
        MARKET = 2 |
        PREMIUM_SADDLEBAG_LEFT = 3 |
        PREMIUM_SADDLEBAG_RIGHT = 4 |
        SADDLEBAG_LEFT = 5 |
        SADDLEBAG_RIGHT = 6 |
        FREE_COMPANY = 7 |
        GLAMOUR_CHEST = 8 |
        ARMORY = 9 |
        EQUIPPED = 10 | This is from Allagon Tools Inventory exports
        CRYSTALS = 11 |
        CURRENCY = 12 |
        ARMOIRE = 13 | This is from Allagon Tools Inventory exports
        HOUSING = 99 | Items from Housing plots.

    """

    null = 0
    bag = 1
    market = 2
    premium_saddlebag_left = 3
    premium_saddlebag_right = 4
    saddlebag_left = 5
    saddlebag_right = 6
    free_company = 7
    glamour_chest = 8
    armory = 9
    equipped_gear = 10
    crystals = 11
    currency = 12
    armoire = 13
    housing_interior_placed = 90
    housing_interior_stored = 91
    housing_exterior_placed = 92
    housing_exterior_stored = 93


class ItemSeries(Enum):
    Pugilists_Arm = 1
    Gladiators_Arm = 2
    Marauders_Arm = 3
    Archers_Arm = 4
    Lancers_Arm = 5
    One_handed_Thaumaturges_Arm = 6
    Two_handed_Thaumaturges_Arm = 7
    One_handed_Conjurers_Arm = 8
    Two_handed_Conjurers_Arm = 9
    Arcanists_Grimoire = 10
    Shield = 11
    Carpenters_Primary_Tool = 12
    Carpenters_Secondary_Tool = 13
    Blacksmiths_Primary_Tool = 14
    Blacksmiths_Secondary_Tool = 15
    Armorers_Primary_Tool = 16
    Armorers_Secondary_Tool = 17
    Goldsmiths_Primary_Tool = 18
    Goldsmiths_Secondary_Tool = 19
    Leatherworkers_Primary_Tool = 20
    Leatherworkers_Secondary_Tool = 21
    Weavers_Primary_Tool = 22
    Weavers_Secondary_Tool = 23
    Alchemists_Primary_Tool = 24
    Alchemists_Secondary_Tool = 25
    Culinarians_Primary_Tool = 26
    Culinarians_Secondary_Tool = 27
    Miners_Primary_Tool = 28
    Miners_Secondary_Tool = 29
    Botanists_Primary_Tool = 30
    Botanists_Secondary_Tool = 31
    Fishers_Primary_Tool = 32
    Fishing_Tackle = 33
    Head = 34
    Body = 35
    Legs = 36
    Hands = 37
    Feet = 38
    Unobtainable = 39
    Necklace = 40
    Earrings = 41
    Bracelets = 42
    Ring = 43
    Medicine = 44
    Ingredient = 45
    Meal = 46
    Seafood = 47
    Stone = 48
    Metal = 49
    Lumber = 50
    Cloth = 51
    Leather = 52
    Bone = 53
    Reagent = 54
    Dye = 55
    Part = 56
    Furnishing = 57
    Materia = 58
    Crystal = 59
    Catalyst = 60
    Miscellany = 61
    Soul_Crystal = 62
    Other = 63
    Construction_Permit = 64
    Roof = 65
    Exterior_Wall = 66
    Window = 67
    Door = 68
    Roof_Decoration = 69
    Exterior_Wall_Decoration = 70
    Placard = 71
    Fence = 72
    Interior_Wall = 73
    Flooring = 74
    Ceiling_Light = 75
    Outdoor_Furnishing = 76
    Table = 77
    Tabletop = 78
    Wall_mounted = 79
    Rug = 80
    Minion = 81
    Gardening = 82
    Demimateria = 83
    Rogues_Arm = 84
    Seasonal_Miscellany = 85
    Triple_Triad_Card = 86
    Dark_Knights_Arm = 87
    Machinists_Arm = 88
    Astrologians_Arm = 89
    Airship_Hull = 90
    Airship_Rigging = 91
    Airship_Aftcastle = 92
    Airship_Forecastle = 93
    Orchestrion_Roll = 94
    Painting = 95
    Samurais_Arm = 96
    Red_Mages_Arm = 97
    Scholars_Arm = 98
    Fishers_Secondary_Tool = 99
    Currency = 100
    Submersible_Hull = 101
    Submersible_Stern = 102
    Submersible_Bow = 103
    Submersible_Bridge = 104
    Blue_Mages_Arm = 105
    Gunbreakers_Arm = 106
    Dancers_Arm = 107
    Reapers_Arm = 108
    Sages_Arm = 109
    Vipers_Arm = 110
    Pictomancers_Arm = 111
    Outfits = 112


class ItemSpecialBonus(Enum):
    UNK = 1
    Set_Bonus_ = 2
    Sanction_ = 4
    Set_Bonus_Capped_ = 6
    Eureka_Effect_ = 7
    Save_the_Queen_Area_Effect = 8


class ItemUICategory(Enum):
    Pugilists_Arm = 1
    Gladiators_Arm = 2
    Marauders_Arm = 3
    Archers_Arm = 4
    Lancers_Arm = 5
    One_handed_Thaumaturges_Arm = 6
    Two_handed_Thaumaturges_Arm = 7
    One_handed_Conjurers_Arm = 8
    Two_handed_Conjurers_Arm = 9
    Arcanists_Grimoire = 10
    Shield = 11
    Carpenters_Primary_Tool = 12
    Carpenters_Secondary_Tool = 13
    Blacksmiths_Primary_Tool = 14
    Blacksmiths_Secondary_Tool = 15
    Armorers_Primary_Tool = 16
    Armorers_Secondary_Tool = 17
    Goldsmiths_Primary_Tool = 18
    Goldsmiths_Secondary_Tool = 19
    Leatherworkers_Primary_Tool = 20
    Leatherworkers_Secondary_Tool = 21
    Weavers_Primary_Tool = 22
    Weavers_Secondary_Tool = 23
    Alchemists_Primary_Tool = 24
    Alchemists_Secondary_Tool = 25
    Culinarians_Primary_Tool = 26
    Culinarians_Secondary_Tool = 27
    Miners_Primary_Tool = 28
    Miners_Secondary_Tool = 29
    Botanists_Primary_Tool = 30
    Botanists_Secondary_Tool = 31
    Fishers_Primary_Tool = 32
    Fishing_Tackle = 33
    Head = 34
    Body = 35
    Legs = 36
    Hands = 37
    Feet = 38
    Unobtainable = 39
    Necklace = 40
    Earrings = 41
    Bracelets = 42
    Ring = 43
    Medicine = 44
    Ingredient = 45
    Meal = 46
    Seafood = 47
    Stone = 48
    Metal = 49
    Lumber = 50
    Cloth = 51
    Leather = 52
    Bone = 53
    Reagent = 54
    Dye = 55
    Part = 56
    Furnishing = 57
    Materia = 58
    Crystal = 59
    Catalyst = 60
    Miscellany = 61
    Soul_Crystal = 62
    Other = 63
    Construction_Permit = 64
    Roof = 65
    Exterior_Wall = 66
    Window = 67
    Door = 68
    Roof_Decoration = 69
    Exterior_Wall_Decoration = 70
    Placard = 71
    Fence = 72
    Interior_Wall = 73
    Flooring = 74
    Ceiling_Light = 75
    Outdoor_Furnishing = 76
    Table = 77
    Tabletop = 78
    Wall_mounted = 79
    Rug = 80
    Minion = 81
    Gardening = 82
    Demimateria = 83
    Rogues_Arm = 84
    Seasonal_Miscellany = 85
    Triple_Triad_Card = 86
    Dark_Knights_Arm = 87
    Machinists_Arm = 88
    Astrologians_Arm = 89
    Airship_Hull = 90
    Airship_Rigging = 91
    Airship_Aftcastle = 92
    Airship_Forecastle = 93
    Orchestrion_Roll = 94
    Painting = 95
    Samurais_Arm = 96
    Red_Mages_Arm = 97
    Scholars_Arm = 98
    Fishers_Secondary_Tool = 99
    Currency = 100
    Submersible_Hull = 101
    Submersible_Stern = 102
    Submersible_Bow = 103
    Submersible_Bridge = 104
    Blue_Mages_Arm = 105
    Gunbreakers_Arm = 106
    Dancers_Arm = 107
    Reapers_Arm = 108
    Sages_Arm = 109
    Vipers_Arm = 110
    Pictomancers_Arm = 111
    Outfits = 112


class Expansion(Enum):
    """Expansion Enum...

    Parameters
    ----------
    A_Realm_Reborn = 2
    Heavensward = 3
    Stormblood = 4
    Shadowbringers = 5
    Endwalker = 6
    Dawntrail = 7

    """

    A_Realm_Reborn = 2
    Heavensward = 3
    Stormblood = 4
    Shadowbringers = 5
    Endwalker = 6
    Dawntrail = 7

    # @staticmethod
    # def resolve_patch(value: float) -> Expansion:
    #     """Resolve a float patch value into an :class:`Expansion` object.

    #     Parameters
    #     ----------
    #     value: :class:`float`
    #         The float value representing the patch, eg `2.4`.

    #     """
    #     return Expansion(value=int(value))
