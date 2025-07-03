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

__all__ = (
    "CraftType",
    "EquipSlotCategory",
    "FishingSpotCategory",
    "GrandCompany",
    "InventoryLocation",
    "ItemSeries",
    "ItemSpecialBonus",
    "ItemUICategory",
    "Jobs",
    "Localization",
    "SaleType",
)


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


class Localization(Enum):
    en = "en"
    de = "de"
    ja = "ja"
    fr = "fr"


class SaleType(Enum):
    aggregated = 0
    history = 1


class Jobs(Enum):
    gladiator = 1
    pugilist = 2
    marauder = 3
    lancer = 4
    archer = 5
    conjurer = 6
    thaumaturge = 7
    carpenter = 8
    blacksmith = 9
    armorer = 10
    goldsmith = 11
    leatherworker = 12
    weaver = 13
    alchemist = 14
    culinarian = 15
    miner = 16
    botanist = 17
    fisher = 18
    paladin = 19
    monk = 20
    warrior = 21
    dragoon = 22
    bard = 23
    white_mage = 24
    black_mage = 25
    arcanist = 26
    summoner = 27
    scholar = 28
    rogue = 29
    ninja = 30
    machinist = 31
    dark_knight = 32
    astrologian = 33
    samurai = 34
    red_mage = 35
    blue_mage = 36
    gunbreaker = 37
    dancer = 38
    reaper = 39
    sage = 40
    viper = 41
    pictomancer = 42


class CraftType(Enum):
    Carpenter = 0
    Blacksmith = 1
    Armorer = 2
    Goldsmith = 3
    Leatherworker = 4
    Weaver = 5
    Alchemist = 6
    Culinarian = 7


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


class GrandCompany(Enum):
    Maelstorm = 1
    Order_of_the_Twin_Adder = 2
    Immortal_Flames = 3


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
