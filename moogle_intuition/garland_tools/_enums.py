from enum import Enum

__all__ = ("GarlandToolsAPI_IconTypeEnum", "GarlandToolsAPI_PatchEnum")


# todo - find out more of these
class GarlandToolsAPI_IconTypeEnum(Enum):
    item = "item"
    achievement = "achievement"


class GarlandToolsAPI_PatchEnum(Enum):
    arr = 1
    hw = 2
    sb = 3
    shb = 4
    ew = 5
    dt = 6
