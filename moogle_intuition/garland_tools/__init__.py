from __future__ import annotations

import logging
from io import BytesIO
from typing import TYPE_CHECKING, ClassVar, Optional

from garlandtools import GarlandTools

from ._enums import GarlandToolsAPI_IconTypeEnum, GarlandToolsAPI_PatchEnum

if TYPE_CHECKING:
    from pathlib import Path

    from requests_cache import CachedResponse, OriginalResponse

    from ._types import GarlandToolsAPI_FishingLocationsTyped, GarlandToolsAPI_ItemTyped, GarlandToolsAPI_MobTyped, GarlandToolsAPI_NPCTyped


__all__ = ("GarlandAPI",)


class GarlandAPI(GarlandTools):
    """
    My own wrapper for the GarlandTools API.
    - Handling the status code checks.
    - Typed Data returns and conversions for some functions.
    """

    def __init__(self, cache_location: Path, cache_expire_after: int = 86400) -> None:
        self.logger: logging.Logger = logging.getLogger()
        if cache_location.exists() and cache_location.is_file():
            raise FileExistsError("You specified a Path to a File, it must be a directory.")
        super().__init__(cache_location=cache_location.as_posix(), cache_expire_after=cache_expire_after)

    def icon(
        self,
        icon_id: int,
        icon_type: GarlandToolsAPI_IconTypeEnum = GarlandToolsAPI_IconTypeEnum.item,
    ) -> BytesIO:
        """
        icon _summary_

        Parameters
        -----------
        icon_id: :class:`int`
            _description_.
        icon_type: :class:`GarlandToolsAPIIconTypeEnum`, optional
            _description_, by default GarlandToolsAPIIconTypeEnum.item.

        Returns
        --------
        :class:`BytesIO`
            _description_.

        Raises
        -------
        :exc:`ConnectionError`
            _description_.
        """
        res: OriginalResponse | CachedResponse = super().icon(icon_type=icon_type.value, icon_id=icon_id)
        if res.status_code == 200:
            return BytesIO(initial_bytes=res.content)
        self.logger.error(
            "We encountered an error looking up this Icon ID: %s Type: %s from garlandtools.icon API. | Status Code: %s",
            icon_id,
            icon_type,
            res.status_code,
        )
        raise ConnectionError(
            "We encountered an error looking up this Icon ID: %s Type: %s for garlandtools.icon API. | Status Code: %s",
            icon_id,
            icon_type,
            res.status_code,
        )

    def item(self, item_id: int) -> GarlandToolsAPI_ItemTyped:
        """
        item _summary_

        Parameters
        -----------
        item_id: :class:`int`
            _description_.

        Returns
        --------
        :class:`GarlandToolsAPI_ItemTyped`
            _description_.

        Raises
        -------
        :exc:`ConnectionError`
            _description_.
        """
        res: OriginalResponse | CachedResponse = super().item(item_id=item_id)
        if res.status_code == 200:
            data: GarlandToolsAPI_ItemTyped = res.json()
            return data
        self.logger.error(
            "We encountered an error looking up this Item ID: %s for GarlandTools. | Status Code: %s",
            item_id,
            res.status_code,
        )
        raise ConnectionError(
            "We encountered an error looking up this Item ID: %s for GarlandTools. | Status Code: %s",
            item_id,
            res.status_code,
        )

    def npc(self, npc_id: int) -> GarlandToolsAPI_NPCTyped:
        """
        npc _summary_

        Parameters
        -----------
        npc_id: :class:`int`
            _description_.

        Returns
        --------
        :class:`GarlandToolsAPI_NPCTyped`
            _description_.

        Raises
        -------
        :exc:`ConnectionError`
            _description_.
        """
        res: OriginalResponse | CachedResponse = super().npc(npc_id=npc_id)
        if res.status_code == 200:
            data: dict[str, GarlandToolsAPI_NPCTyped] = res.json()
            return data["npc"]
        self.logger.error(
            "We encountered an error looking up this NPC ID: %s for GarlandTools. | Status Code: %s",
            npc_id,
            res.status_code,
        )
        raise ConnectionError(
            "We encountered an error looking up this NPC ID: %s for GarlandTools. | Status Code: %s",
            npc_id,
            res.status_code,
        )

    def mob(self, mob_id: int) -> GarlandToolsAPI_MobTyped:
        """
        mob _summary_

        Parameters
        -----------
        mob_id: :class:`int`
            _description_.

        Returns
        --------
        :class:`GarlandToolsAPI_MobTyped`
            _description_.

        Raises
        -------
        :exc:`ConnectionError`
            _description_.
        """
        res: OriginalResponse | CachedResponse = super().mob(mob_id=mob_id)
        if res.status_code == 200:
            data: dict[str, GarlandToolsAPI_MobTyped] = res.json()
            return data["mob"]
        self.logger.error(
            "We encountered an error looking up this Mob ID: %s for GarlandTools. | Status Code: %s",
            mob_id,
            res.status_code,
        )
        raise ConnectionError(
            "We encountered an error looking up this Mob ID: %s for GarlandTools. | Status Code: %s",
            mob_id,
            res.status_code,
        )

    def fishing(self) -> GarlandToolsAPI_FishingLocationsTyped:
        """
        fishing _summary_

        Returns
        --------
        :class:`GarlandToolsAPI_FishingLocationsTyped`
            _description_.

        Raises
        -------
        :exc:`ConnectionError`
            _description_.
        """
        res: OriginalResponse | CachedResponse = super().fishing()
        if res.status_code == 200:
            data: dict[str, GarlandToolsAPI_FishingLocationsTyped] = res.json()
            return data["browse"]
        self.logger.error(
            "We encountered an error looking up Fishing Locations for GarlandTools. | Status Code: %s",
            res.status_code,
        )
        raise ConnectionError(
            "We encountered an error looking up Fishing Locations for GarlandTools. | Status Code: %s",
            res.status_code,
        )
