# ruff: noqa
"""
Copyright (C) 2021-2024 Katelynn Cadwallader.

This file is part of Kuma Kuma.

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

__title__ = "Moogle's Intuition"
__author__ = "k8thekat"
__license__ = "GNU"
__version__ = "0.0.1"
__credits__ = "Universalis, GarlandTools, Square Enix"

from typing import Literal, NamedTuple
from . import _enums as enums
from . import modules as modules
from . import _types as types


class VersionInfo(NamedTuple):
    Major: int
    Minor: int
    Revision: int
    releaseLevel: Literal["alpha", "beta", "pre-release", "release", "development"]


version_info: VersionInfo = VersionInfo(Major=0, Minor=0, Revision=1, releaseLevel="development")

del NamedTuple, Literal, VersionInfo
