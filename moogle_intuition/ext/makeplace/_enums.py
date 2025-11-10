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

from enum import Enum
from typing import Literal

__all__ = ("ColorRef",)


class ColorRef(Enum):
    """Generic colour reference chart based upon FFXIV Dyes to Hex color codes without the alpha bit."""

    Snow_White = "E4DFD0"
    Ash_Grey = "ACA8A2"
    Goobbue_Grey = "898784"
    Slate_Grey = "656565"
    Charcoal_Grey = "484742"
    Soot_Black = "2B2923"
    Rose_Pink = "E69F96"
    Lilac_Purple = "836969"
    Rolanberry_Red = "5B1729"
    Dalamud_Red = "781A1A"
    Rust_Red = "622207"
    Wine_Red = "451511"
    Coral_Pink = "CC6C5E"
    Blood_Red = "913B27"
    Salmon_Pink = "E4AA8A"
    Sunset_Orange = "B75C2D"
    Mesa_Red = "7D3906"
    Bark_Brown = "6A4B37"
    Chocolate_Brown = "6E3D24"
    Russet_Brown = "4F2D1F"
    Kobold_Brown = "30211B"
    Cork_Brown = "C99156"
    Qiqirn_Brown = "996E3F"
    Opo_opo_Brown = "7B5C2D"
    Aldgoat_Brown = "A2875C"
    Pumpkin_Orange = "C57424"
    Acorn_Brown = "8E581B"
    Orchard_Brown = "644216"
    Chestnut_Brown = "3D290D"
    Gobbiebag_Brown = "B9A489"
    Shale_Brown = "92816C"
    Mole_Brown = "615245"
    Loam_Brown = "3F3329"
    Bone_White = "EBD3A0"
    Ul_Brown = "B7A370"
    Desert_Yellow = "DBB457"
    Honey_Yellow = "FAC62B"
    Millioncorn_Yellow = "E49E34"
    Coeurl_Yellow = "BC8804"
    Cream_Yellow = "F2D770"
    Halatali_Yellow = "A58430"
    Raisin_Brown = "403311"
    Mud_Green = "585230"
    Sylph_Green = "BBBB8A"
    Lime_Green = "ABB054"
    Moss_Green = "707326"
    Meadow_Green = "8B9C63"
    Olive_Green = "4B5232"
    Marsh_Green = "323621"
    Apple_Green = "9BB363"
    Cactuar_Green = "658241"
    Hunter_Green = "284B2C"
    Ochu_Green = "406339"
    Adamantoise_Green = "5F7558"
    Nophica_Green = "3B4D3C"
    Deepwood_Green = "1E2A21"
    Celeste_Green = "96BDB9"
    Turquoise_Green = "437272"
    Morbol_Green = "1F4646"
    Ice_Blue = "B2C4CE"
    Sky_Blue = "83B0D2"
    Seafog_Blue = "6481A0"
    Peacock_Blue = "3B6886"
    Rhotano_Blue = "1C3D54"
    Corpse_Blue = "8E9BAC"
    Ceruleum_Blue = "4F5766"
    Woad_Blue = "2F3851"
    Ink_Blue = "1A1F27"
    Raptor_Blue = "5B7FC0"
    Othard_Blue = "2F5889"
    Storm_Blue = "234172"
    Void_Blue = "112944"
    Royal_Blue = "273067"
    Midnight_Blue = "181937"
    Shadow_Blue = "373747"
    Abyssal_Blue = "312D57"
    Lavender_Purple = "877FAE"
    Gloom_Purple = "514560"
    Currant_Purple = "322C3B"
    Iris_Purple = "B79EBC"
    Grape_Purple = "3B2A3D"
    Lotus_Pink = "FECEF5"
    Colibri_Pink = "DC9BCA"
    Plum_Purple = "79526C"
    Regal_Purple = "66304E"
    Ruby_Red = "E40011"
    Cherry_Pink = "F5379B"
    Canary_Yellow = "FEF864"
    Vanilla_Yellow = "FBF1B4"
    Dragoon_Blue = "000EA2"
    Turquoise_Blue = "04AFCD"
    Violet_Purple = "A798C5"
    Azure_Blue = "8394C6"
    Neon_Green = "DBFB47"
    Carmine_Red = "F03B53"
    Neon_Pink = "F749C5"
    Bright_Orange = "FA9849"
    Neon_Yellow = "F0F632"
    Pure_White = "F9F8F4"
    Jet_Black = "1E1E1E"
    Pastel_Pink = "FDC8C6"
    Dark_Red = "321919"
    Dark_Brown = "28211C"
    Pastel_Green = "BACFAA"
    Dark_Green = "152C2C"
    Pastel_Blue = "96A4D9"
    Dark_Blue = "121F2D"
    Pastel_Purple = "BBB5DA"
    Dark_Purple = "232026"

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
        res = ColorRef.__dict__.get(dye, None)
        if res is None:
            msg = "The Dye specified was not found. | Dye: %s"
            raise LookupError(msg, dye)
        return res


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
