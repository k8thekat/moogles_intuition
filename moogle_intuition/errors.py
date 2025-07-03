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

import logging

__all__ = ("MoogleLookupError", "MoogleNetworkError")

LOGGER = logging.getLogger("moogle.errors")


class MoogleNetworkError(Exception):  # noqa: D101
    def __init__(self, status_code: int, url: str, error_reason: str) -> None:  # noqa: D107
        message = "We encountered an error during a request to Moogle in %s. Current URL: %r | Status Code: %s"
        super().__init__(message, error_reason, url, status_code)
        LOGGER.error(message, error_reason, url, status_code)


class MoogleLookupError(Exception):  # noqa: D101
    def __init__(self, query: str, param_name: str, function_name: str, obj: object) -> None:  # noqa: D107
        message = "<%s.%s> | We failed to lookup %s | %s: %r"
        super().__init__(message, obj.__class__.__name__, function_name, query, param_name, query)
        LOGGER.error(message, obj.__class__.__name__, function_name, query, param_name, query)
