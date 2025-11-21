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
from typing import Literal

__all__ = ("ColorRef",)


class ColorRef(Enum):
    """Generic colour reference chart based upon FFXIV Dyes to Hex color codes without the alpha bit."""

    snow_white = "e4dfd0"
    ash_grey = "aca8a2"
    goobbue_grey = "898784"
    slate_grey = "656565"
    charcoal_grey = "484742"
    soot_black = "2b2923"
    rose_pink = "e69f96"
    lilac_purple = "836969"
    rolanberry_red = "5b1729"
    dalamud_red = "781a1a"
    rust_red = "622207"
    wine_red = "451511"
    coral_pink = "cc6c5e"
    blood_red = "913b27"
    salmon_pink = "e4aa8a"
    sunset_orange = "b75c2d"
    mesa_red = "7d3906"
    bark_brown = "6a4b37"
    chocolate_brown = "6e3d24"
    russet_brown = "4f2d1f"
    kobold_brown = "30211b"
    cork_brown = "c99156"
    qiqirn_brown = "996e3f"
    opo_opo_brown = "7b5c2d"
    aldgoat_brown = "a2875c"
    pumpkin_orange = "c57424"
    acorn_brown = "8e581b"
    orchard_brown = "644216"
    chestnut_brown = "3d290d"
    gobbiebag_brown = "b9a489"
    shale_brown = "92816c"
    mole_brown = "615245"
    loam_brown = "3f3329"
    bone_white = "ebd3a0"
    ul_brown = "b7a370"
    desert_yellow = "dbb457"
    honey_yellow = "fac62b"
    millioncorn_yellow = "e49e34"
    coeurl_yellow = "bc8804"
    cream_yellow = "f2d770"
    halatali_yellow = "a58430"
    raisin_brown = "403311"
    mud_green = "585230"
    sylph_green = "bbbb8a"
    lime_green = "abb054"
    moss_green = "707326"
    meadow_green = "8b9c63"
    olive_green = "4b5232"
    marsh_green = "323621"
    apple_green = "9bb363"
    cactuar_green = "658241"
    hunter_green = "284b2c"
    ochu_green = "406339"
    adamantoise_green = "5f7558"
    nophica_green = "3b4d3c"
    deepwood_green = "1e2a21"
    celeste_green = "96bdb9"
    turquoise_green = "437272"
    morbol_green = "1f4646"
    ice_blue = "b2c4ce"
    sky_blue = "83b0d2"
    seafog_blue = "6481a0"
    peacock_blue = "3b6886"
    rhotano_blue = "1c3d54"
    corpse_blue = "8e9bac"
    ceruleum_blue = "4f5766"
    woad_blue = "2f3851"
    ink_blue = "1a1f27"
    raptor_blue = "5b7fc0"
    othard_blue = "2f5889"
    storm_blue = "234172"
    void_blue = "112944"
    royal_blue = "273067"
    midnight_blue = "181937"
    shadow_blue = "373747"
    abyssal_blue = "312d57"
    lavender_purple = "877fae"
    gloom_purple = "514560"
    currant_purple = "322c3b"
    iris_purple = "b79ebc"
    grape_purple = "3b2a3d"
    lotus_pink = "fecef5"
    colibri_pink = "dc9bca"
    plum_purple = "79526c"
    regal_purple = "66304e"
    ruby_red = "e40011"
    cherry_pink = "f5379b"
    canary_yellow = "fef864"
    vanilla_yellow = "fbf1b4"
    dragoon_blue = "000ea2"
    turquoise_blue = "04afcd"
    violet_purple = "a798c5"
    azure_blue = "8394c6"
    neon_green = "dbfb47"
    carmine_red = "f03b53"
    neon_pink = "f749c5"
    bright_orange = "fa9849"
    neon_yellow = "f0f632"
    pure_white = "f9f8f4"
    jet_black = "1e1e1e"
    pastel_pink = "fdc8c6"
    dark_red = "321919"
    dark_brown = "28211c"
    pastel_green = "bacfaa"
    dark_green = "152c2c"
    pastel_blue = "96a4d9"
    dark_blue = "121f2d"
    pastel_purple = "bbb5da"
    dark_purple = "232026"

    @staticmethod
    def to_hex(dye: ColourRefLit) -> ColorRef:
        """Fetch a hex value based upon Dye name.

        Parameters
        ----------
        dye: :class:`Literal`
            The Final Fantasy Dye names.

        Returns
        -------
        :class:`ColorRef`
            A :class:`ColorRef` object.

        Raises
        ------
        LookupError
            If the `dye` parameter doesn't exist.

        """
        res = ColorRef.__dict__.get(dye.lower(), None)
        if res is None:
            msg = "The Dye specified was not found. | Dye: %s"
            raise LookupError(msg, dye)
        return res

    @property
    def name(self) -> str:
        return super().name.replace("_", " ")

ColourRefLit = Literal[
    "Snow_White",
    "Ash_Grey",
    "Goobbue_Grey",
    "Slate_Grey",
    "Charcoal_Grey",
    "Soot_Black",
    "Rose_Pink",
    "Lilac_Purple",
    "Rolanberry_Red",
    "Dalamud_Red",
    "Rust_Red",
    "Wine_Red",
    "Coral_Pink",
    "Blood_Red",
    "Salmon_Pink",
    "Ruby_Red",
    "Cherry_Pink",
    "Sunset_Orange",
    "Mesa_Red",
    "Bark_Brown",
    "Chocolate_Brown",
    "Russet_Brown",
    "Kobold_Brown",
    "Cork_Brown",
    "Qiqirn_Brown",
    "Opo_opo_Brown",
    "Aldgoat_Brown",
    "Pumpkin_Orange",
    "Acorn_Brown",
    "Orchard_Brown",
    "Chestnut_Brown",
    "Gobbiebag_Brown",
    "Shale_Brown",
    "Mole_Brown",
    "Loam_Brown",
    "Bone_White",
    "Ul_Brown",
    "Desert_Yellow",
    "Honey_Yellow",
    "Millioncorn_Yellow",
    "Coeurl_Yellow",
    "Cream_Yellow",
    "Halatali_Yellow",
    "Raisin_Brown",
    "Canary_Yellow",
    "Vanilla_Yellow",
    "Mud_Green",
    "Sylph_Green",
    "Lime_Green",
    "Moss_Green",
    "Meadow_Green",
    "Olive_Green",
    "Marsh_Green",
    "Apple_Green",
    "Cactuar_Green",
    "Hunter_Green",
    "Ochu_Green",
    "Adamantoise_Green",
    "Nophica_Green",
    "Deepwood_Green",
    "Celeste_Green",
    "Turquoise_Green",
    "Morbol_Green",
    "Ice_Blue",
    "Sky_Blue",
    "Seafog_Blue",
    "Peacock_Blue",
    "Rhotano_Blue",
    "Corpse_Blue",
    "Ceruleum_Blue",
    "Woad_Blue",
    "Ink_Blue",
    "Raptor_Blue",
    "Othard_Blue",
    "Storm_Blue",
    "Void_Blue",
    "Royal_Blue",
    "Midnight_Blue",
    "Shadow_Blue",
    "Abyssal_Blue",
    "Dragoon_Blue",
    "Turquoise_Blue",
    "Lavender_Purple",
    "Gloom_Purple",
    "Currant_Purple",
    "Iris_Purple",
    "Grape_Purple",
    "Lotus_Pink",
    "Colibri_Pink",
    "Plum_Purple",
    "Regal_Purple",
    "Pure_White",
    "Jet_Black",
    "Pastel_Pink",
    "Dark_Red",
    "Dark_Brown",
    "Pastel_Green",
    "Dark_Green",
    "Pastel_Blue",
    "Dark_Blue",
    "Pastel_Purple",
    "Dark_Purple",
    "Metallic_Silver",
    "Metallic_Gold",
    "Metallic_Red",
    "Metallic_Orange",
    "Metallic_Yellow",
    "Metallic_Green",
    "Metallic_Sky_Blue",
    "Metallic_Blue",
    "Metallic_Purple",
    "Gunmetal_Black",
    "Pearl_White",
    "Metallic_Brass",
]



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

    NULL = 0
    BAG = 1
    MARKET = 2
    PREMIUM_SADDLEBAG_LEFT = 3
    PREMIUM_SADDLEBAG_RIGHT = 4
    SADDLEBAG_LEFT = 5
    SADDLEBAG_RIGHT = 6
    FREE_COMPANY = 7
    GLAMOUR_CHEST = 8
    ARMORY = 9
    EQUIPPED_GEAR = 10
    CRYSTALS = 11
    CURRENCY = 12
    ARMOIRE = 13
    HOUSING_INTERIOR_PLACED = 90
    HOUSING_INTERIOR_STORED = 91
    HOUSING_EXTERIOR_PLACED = 92
    HOUSING_EXTERIOR_STORED = 93
