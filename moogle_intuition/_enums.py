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
    "ItemSeries",
    "ItemSpecialBonus",
    "ItemUICategory",
)


class CraftType(Enum):
    carpenter = 0
    blacksmith = 1
    armorer = 2
    goldsmith = 3
    leatherworker = 4
    weaver = 5
    alchemist = 6
    culinarian = 7

    def to_abbr(self, name: Optional[str] = None) -> str:
        """Converters the `name` attribute into it's abbreviated form.

        ```_mapping: dict[str, str] = {
            "carpenter": "CRP",
            "blacksmith": "BSM",
            "armorer": "ARM",
            "goldsmith": "GSM",
            "leatherworker": "LTW",
            "weaver": "WVR",
            "alchemist": "ALC",
            "culinarian": "CUL",
        }
        ```

        Returns
        -------
            A :class:`str` represensation of the abbreviated :class:`Self.name` if possible.

        """
        _mapping: dict[str, str] = {
            "carpenter": "crp",
            "blacksmith": "bsm",
            "armorer": "arm",
            "goldsmith": "gsm",
            "leatherworker": "ltw",
            "weaver": "wvr",
            "alchemist": "alc",
            "culinarian": "cul",
        }
        if name is not None:
            return _mapping.get(name.lower(), "UNK").upper()
        return _mapping.get(self.name.lower(), "UNK").upper()


class Currency(IntEnum):
    """Representation of FF14 Currencies.

    Values:
    ---
    allagan_tomestone_of_poetics = 28
    serpent_seal = 21
    allagan_tomestone_of_mathematics = 48
    purple_crafters_scrips = 33913
    allagan_tomestone_of_heliometry = 47
    allied_seal = 27
    centurio_seal = 10307
    bicolor_gemstone = 26807
    skybuilders_scrip = 28063
    orange_gatherers_scrip = 41785
    orange_crafters_scrip = 41784
    purple_gatherers_scrip = 33914
    gil = 0
    """

    allagan_tomestone_of_poetics = 28
    serpent_seal = 21
    allagan_tomestone_of_mathematics = 48
    purple_crafters_scrips = 33913
    allagan_tomestone_of_heliometry = 47
    allied_seal = 27
    centurio_seal = 10307
    bicolor_gemstone = 26807
    skybuilders_scrip = 28063
    orange_gatherers_scrip = 41785
    orange_crafters_scrip = 41784
    purple_gatherers_scrip = 33914
    gil = 0

    @property
    def name(self) -> str:
        return super().name.replace("_", " ")


class EquipSlotCategory(Enum):
    unk = 0
    mainhand = 1
    offhand = 2
    head = 3
    body = 4
    gloves = 5
    waist = 6
    legs = 7
    feet = 8
    ears = 9
    neck = 10
    wrists = 11
    finger = 12
    mainhand_only = 13
    both_hands = 14
    soulcrystal = 17
    legs_no_feet = 18
    body_nohead_nogloves_nolegs_nofeet = 19
    body_nolegs_nogloves = 20
    body_nolegs_nofeet = 21
    body_nogloves = 22


class FishingSpotCategory(Enum):
    unk = 0
    ocean = 1
    freshwater = 2
    dunefishing = 3
    skyfishing = 4
    cloudfishing = 5
    hellfishing = 6
    aetherfishing = 7
    saltfishing = 8
    starfishing = 9


class GrandCompany(Enum):
    maelstorm = 1
    order_of_the_twin_adder = 2
    immortal_flames = 3

    @property
    def name(self) -> str:
        return super().name.replace("_", " ")


class ItemSeries(Enum):
    pugilists_arm = 1
    gladiators_arm = 2
    marauders_arm = 3
    archers_arm = 4
    lancers_arm = 5
    one_handed_thaumaturges_arm = 6
    two_handed_thaumaturges_arm = 7
    one_handed_conjurers_arm = 8
    two_handed_conjurers_arm = 9
    arcanists_grimoire = 10
    shield = 11
    carpenters_primary_tool = 12
    carpenters_secondary_tool = 13
    blacksmiths_primary_tool = 14
    blacksmiths_secondary_tool = 15
    armorers_primary_tool = 16
    armorers_secondary_tool = 17
    goldsmiths_primary_tool = 18
    goldsmiths_secondary_tool = 19
    leatherworkers_primary_tool = 20
    leatherworkers_secondary_tool = 21
    weavers_primary_tool = 22
    weavers_secondary_tool = 23
    alchemists_primary_tool = 24
    alchemists_secondary_tool = 25
    culinarians_primary_tool = 26
    culinarians_secondary_tool = 27
    miners_primary_tool = 28
    miners_secondary_tool = 29
    botanists_primary_tool = 30
    botanists_secondary_tool = 31
    fishers_primary_tool = 32
    fishing_tackle = 33
    head = 34
    body = 35
    legs = 36
    hands = 37
    feet = 38
    unobtainable = 39
    necklace = 40
    earrings = 41
    bracelets = 42
    ring = 43
    medicine = 44
    ingredient = 45
    meal = 46
    seafood = 47
    stone = 48
    metal = 49
    lumber = 50
    cloth = 51
    leather = 52
    bone = 53
    reagent = 54
    dye = 55
    part = 56
    furnishing = 57
    materia = 58
    crystal = 59
    catalyst = 60
    miscellany = 61
    soul_crystal = 62
    other = 63
    construction_permit = 64
    roof = 65
    exterior_wall = 66
    window = 67
    door = 68
    roof_decoration = 69
    exterior_wall_decoration = 70
    placard = 71
    fence = 72
    interior_wall = 73
    flooring = 74
    ceiling_light = 75
    outdoor_furnishing = 76
    table = 77
    tabletop = 78
    wall_mounted = 79
    rug = 80
    minion = 81
    gardening = 82
    demimateria = 83
    rogues_arm = 84
    seasonal_miscellany = 85
    triple_triad_card = 86
    dark_knights_arm = 87
    machinists_arm = 88
    astrologians_arm = 89
    airship_hull = 90
    airship_rigging = 91
    airship_aftcastle = 92
    airship_forecastle = 93
    orchestrion_roll = 94
    painting = 95
    samurais_arm = 96
    red_mages_arm = 97
    scholars_arm = 98
    fishers_secondary_tool = 99
    currency = 100
    submersible_hull = 101
    submersible_stern = 102
    submersible_bow = 103
    submersible_bridge = 104
    blue_mages_arm = 105
    gunbreakers_arm = 106
    dancers_arm = 107
    reapers_arm = 108
    sages_arm = 109
    vipers_arm = 110
    pictomancers_arm = 111
    outfits = 112


class ItemSpecialBonus(Enum):
    unk = 1
    set_bonus_ = 2
    sanction_ = 4
    set_bonus_capped_ = 6
    eureka_effect_ = 7
    save_the_queen_area_effect = 8


class ItemUICategory(Enum):
    unkown = 0
    pugilists_arm = 1
    gladiators_arm = 2
    marauders_arm = 3
    archers_arm = 4
    lancers_arm = 5
    one_handed_thaumaturges_arm = 6
    two_handed_thaumaturges_arm = 7
    one_handed_conjurers_arm = 8
    two_handed_conjurers_arm = 9
    arcanists_grimoire = 10
    shield = 11
    carpenters_primary_tool = 12
    carpenters_secondary_tool = 13
    blacksmiths_primary_tool = 14
    blacksmiths_secondary_tool = 15
    armorers_primary_tool = 16
    armorers_secondary_tool = 17
    goldsmiths_primary_tool = 18
    goldsmiths_secondary_tool = 19
    leatherworkers_primary_tool = 20
    leatherworkers_secondary_tool = 21
    weavers_primary_tool = 22
    weavers_secondary_tool = 23
    alchemists_primary_tool = 24
    alchemists_secondary_tool = 25
    culinarians_primary_tool = 26
    culinarians_secondary_tool = 27
    miners_primary_tool = 28
    miners_secondary_tool = 29
    botanists_primary_tool = 30
    botanists_secondary_tool = 31
    fishers_primary_tool = 32
    fishing_tackle = 33
    head = 34
    body = 35
    legs = 36
    hands = 37
    feet = 38
    unobtainable = 39
    necklace = 40
    earrings = 41
    bracelets = 42
    ring = 43
    medicine = 44
    ingredient = 45
    meal = 46
    seafood = 47
    stone = 48
    metal = 49
    lumber = 50
    cloth = 51
    leather = 52
    bone = 53
    reagent = 54
    dye = 55
    part = 56
    furnishing = 57
    materia = 58
    crystal = 59
    catalyst = 60
    miscellany = 61
    soul_crystal = 62
    other = 63
    construction_permit = 64
    roof = 65
    exterior_wall = 66
    window = 67
    door = 68
    roof_decoration = 69
    exterior_wall_decoration = 70
    placard = 71
    fence = 72
    interior_wall = 73
    flooring = 74
    ceiling_light = 75
    outdoor_furnishing = 76
    table = 77
    tabletop = 78
    wall_mounted = 79
    rug = 80
    minion = 81
    gardening = 82
    demimateria = 83
    rogues_arm = 84
    seasonal_miscellany = 85
    triple_triad_card = 86
    dark_knights_arm = 87
    machinists_arm = 88
    astrologians_arm = 89
    airship_hull = 90
    airship_rigging = 91
    airship_aftcastle = 92
    airship_forecastle = 93
    orchestrion_roll = 94
    painting = 95
    samurais_arm = 96
    red_mages_arm = 97
    scholars_arm = 98
    fishers_secondary_tool = 99
    currency = 100
    submersible_hull = 101
    submersible_stern = 102
    submersible_bow = 103
    submersible_bridge = 104
    blue_mages_arm = 105
    gunbreakers_arm = 106
    dancers_arm = 107
    reapers_arm = 108
    sages_arm = 109
    vipers_arm = 110
    pictomancers_arm = 111
    outfits = 112


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

    a_realm_reborn = 2
    heavensward = 3
    stormblood = 4
    shadowbringers = 5
    endwalker = 6
    dawntrail = 7


    @property
    def name(self) -> str:
        return super().name.replace("_", " ")
    # @staticmethod
    # def resolve_patch(value: float) -> Expansion:
    #     """Resolve a float patch value into an :class:`Expansion` object.

    #     Parameters
    #     ----------
    #     value: :class:`float`
    #         The float value representing the patch, eg `2.4`.

    #     """
    #     return Expansion(value=int(value))
