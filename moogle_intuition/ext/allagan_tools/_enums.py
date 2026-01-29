from enum import IntEnum


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
