from __future__ import annotations

from typing import TypedDict


class GarlandToolsAPI_ItemAttrTyped(TypedDict, total=False):
    """
    This is the JSON structure for :class:`GarlandToolsAPI_ItemTyped.attr`
    """

    pysical_damage: int
    magic_damage: int
    delay: float
    strength: int
    dexterity: int
    vitality: int
    intelligence: int
    mind: int
    piety: int
    gp: int
    cp: int
    tenacity: int
    direct_hit_rate: int
    critical_hit: int
    fire_resistance: int
    ice_resistance: int
    wind_resistance: int
    earth_resistance: int
    lightning_resistance: int
    water_resistance: int
    determination: int
    skill_speed: int
    spell_speed: int
    slow_resistance: int
    petrification_resistance: int
    paralysis_resistance: int
    silence_resistance: int
    blind_resistance: int
    poison_resistance: int
    stun_resistance: int
    sleep_resistance: int
    bind_resistance: int
    heavy_resistance: int
    doom_resistance: int
    craftsmanship: int
    control: int
    gathering: int
    perception: int


class GarlandToolsAPI_ItemCraftTyped(TypedDict, total=False):
    """
    This is the JSON structure from :class:`GarlandToolsAPI_ItemKeysTyped.craft`.
    """

    id: int  # 907
    job: int  # 15
    rlvl: int  # 4
    durability: int  # 40
    quality: int  # 104
    progress: int  # 10
    lvl: int  # 4
    materialQualityFactor: int  # 0
    yield_: int  # 3
    hq: int  # 1
    quickSynth: int  # 1
    ingredients: list[
        GarlandToolsAPI_ItemCraftIngredientsTyped
    ]  # [{"id": 5516, "amount": 3}, {"id": 2, "amount": 1}]
    complexity: dict  # {"nq": 31, "hq": 51}


class GarlandToolsAPI_ItemCraftIngredientsTyped(TypedDict):
    """
    This is the JSON structure from :class:`GarlandToolsAPI_CraftTyped.ingredients`.
    """

    id: int
    amount: int


class GarlandToolsAPI_ItemFishTyped(TypedDict, total=False):
    """
    This is the JSON structure for :class:`GarlandToolsAPI_ItemTyped.fish`.
    """

    guide: str  # Appears to be a little Guide/tip; just a duplicate of the "description"
    icon: int  # Appears to be the fishing Guide ICON
    spots: list[GarlandToolsAPI_ItemFishSpotsTyped]


class GarlandToolsAPI_FishingLocationsTyped(TypedDict):
    i: int  # The ID of the location (Related to GarlandToolsAPI_ItemFishTyped.spots.spot)
    n: str  # The name of the location
    l: int
    c: int
    z: int  # I believe the Z is the ZONE ID
    x: float | int  # I believe the X cords in terms of the map.
    y: float | int  # I believe the Y cords in terms of the map.


class GarlandToolsAPI_ItemFishSpotsTyped(TypedDict, total=False):
    """
    This is the JSON structure for :class:`GarlandToolsAPI_ItemFishTyped.spots`.

    Parameters
    -----------
    spot: :class:`int`
        Possibly related to a Map/loc -- Unsure.. Same field as `fishingSpots`.
        -> `https://www.garlandtools.org/db/#fishing/{spot}
    hookset: :class:`str`
        The type of Hook action to use
    tug: :class:`str`
        The strength of the bite
    ff14angerId: :class:`int`
        This key belongs to the FF14 Angler Website.
        - `https://{loc}.ff14angler.com/fish/{ff14angerId}`
    baits: :class:`list[list[int]]`
        This key has a list of ints that related to
        - `https://www.garlandtools.org/db/#item/{baits.id}`
    """

    spot: int
    hookset: str
    tug: str
    ff14angerId: int
    baits: list[list[int]]


class GarlandToolsAPI_ItemIngredientsTyped(TypedDict, total=False):
    """
    This is the JSON structure for :class:`GarlandToolsAPI_ItemTyped.ingredients`.
    """

    name: str
    id: int
    icon: int
    category: int
    ilvl: int
    price: int
    ventures: list[int]
    nodes: list[int]
    vendors: list[int]


class GarlandToolsAPI_ItemKeysTyped(TypedDict, total=False):
    """
    This is the JSON structure for :class:`GarlandToolsAPI_ItemTyped.item`.
    - See garland_itemX.json
    """

    name: str
    description: str
    jobCategories: str
    repair: int
    equip: int
    sockets: int
    glamourerous: int  # possibly use as a bool
    elvl: int
    jobs: int
    id: int
    patch: int
    patchCategory: int
    price: int
    ilvl: int
    category: int
    dyecount: bool
    tradeable: bool
    sell_price: int
    rarity: int
    stackSize: int
    icon: int

    # Most Items may or may not have these values below.
    nodes: list[int]
    vendors: list[int]
    tradeShops: list[GarlandToolsAPI_ItemTradeShopsTyped]
    ingredients_of: dict[
        str, int
    ]  # The Crafted Item ID as the KEY and the VALUE is the number of them to make the Crafted Item.
    levels: list[int]
    desyntheFrom: list[int]
    desynthedTo: list[int]
    alla: dict[str, list[str]]
    supply: dict[str, int]  # The Grand Company Supply Mission. Keys: count: int, xp: int, seals: int
    drops: list[int]
    craft: list[GarlandToolsAPI_ItemCraftTyped]
    ventures: list[int]

    # Weapons/Gear Keys
    attr: GarlandToolsAPI_ItemAttrTyped
    att_hq: GarlandToolsAPI_ItemAttrTyped
    attr_max: GarlandToolsAPI_ItemAttrTyped
    downgrades: list[int]  # The items just below this in terms of ilvl/stats
    models: list[str]
    repair_item: int  # The Garland Tools Item ID to repair the Weapon/Gear
    sharedModels: list
    slot: int  # The Item slot on the Equipment panel
    upgrades: list[int]  # The items just above this in terms of ilvl/stats

    # This belows to Fish type items specifically.
    fish: GarlandToolsAPI_ItemFishTyped
    fishingSpots: list[int]  # This probably belongs to FFXIV and lines up with a Zone ID


class GarlandToolsAPI_ItemTyped(TypedDict, total=False):
    """
    This is the JSON structure from :class:`GarlandToolsAPIWrapper.item()` function.
    """

    item: GarlandToolsAPI_ItemKeysTyped
    ingredients: list[GarlandToolsAPI_ItemIngredientsTyped]
    partials: list[GarlandToolsAPI_ItemPartialsTyped]


class GarlandToolsAPI_ItemTradeShopsTyped(TypedDict, total=False):
    """
    This is the JSON structure from :class:`GarlandToolsAPI_Item.tradeShops`.
    """

    shop: str  # The Shop Name
    npcs: list[int]  # A list of NPC IDs.
    listings: GarlandToolsAPI_ItemTradeShopsListingsTyped


class GarlandToolsAPI_ItemTradeShopsListingsTyped(TypedDict, total=False):
    """
    This is the JSON structure from :class:`GarlandToolsAPI_ItemTradeShopsTyped.listings`.
    """

    item: list[GarlandToolsAPI_ItemCraftIngredientsTyped]
    currency: list[GarlandToolsAPI_ItemCraftIngredientsTyped]


class GarlandToolsAPI_ItemPartialsTyped(TypedDict, total=False):
    """
    This is the JSON structure from :class:`GarlandToolsAPI_ItemTyped.partials`.
    """

    type: str
    id: str
    obj: GarlandToolsAPI_ItemPartislObjTyped


class GarlandToolsAPI_ItemPartislObjTyped(TypedDict, total=False):
    """

    This is the JSON structure from :class:`GarlandToolsAPI_ItemPartialsTyped.obj`.

    Parameters
    ----------
    i: :class:`int`
        This appears to be the same value as the :class:`GarlandToolsAPI_ItemPartialsTyped.id` key but as an INT type.
    n: :class:`str`
        This appears to be the name of the :class:`GarlandToolsAPI_ItemPartialsTyped.type`.
    t: :class:`str`
        This appears to be the title of the :class:`GarlandToolsAPI_ItemPartialsTyped.type`.

    """

    i: int
    n: str
    l: int
    s: int
    q: int
    t: str
    a: int
    c: list[str]


class GarlandToolsAPI_MobTyped(TypedDict):
    """
    This is the JSON structure from :class:`GarlandToolsAPIWrapper.mob()` function.
    """

    name: str
    id: int
    quest: int
    zoneid: int
    lvl: str
    drops: list[int]


class GarlandToolsAPI_NPCAppearanceTyped(TypedDict, total=False):
    """
    This is the JSON structure from :class:`GarlandToolsAPI_NPCTyped.appearance`
    """

    gender: str  # "Female",
    race: str  # "Miqo'te",
    tribe: str  # "Seeker of the Sun",
    height: int  # 50,
    face: int  # 1,
    jaw: int  # 1,
    eyebrows: int  # 1,
    nose: int  # 1,
    skinColor: str  # "24, 2",
    skinColorCode: str  # "#DAB29E",
    bust: int  # 0,
    hairStyle: int  # 134201,
    hairColor: str  # "1, 3",
    hairColorCode: str  # "#BFBFBF",
    eyeSize: str  # "Large",
    eyeShape: int  # 1,
    eyeColor: str  # "2, 5",
    eyeColorCode: str  # "#B9AF90",
    mouth: int  # 1,
    extraFeatureName: str  # "Tail",
    extraFeatureShape: int  # 1,
    extraFeatureSize: int  # 50,
    hash: int  # 1864024670


class GarlandToolsAPI_NPCTyped(TypedDict, total=False):
    """
    This is the JSON structure from :class:`GarlandAPIWrapper.npc()` function.
    """

    name: str
    id: int
    patch: float
    title: str
    coords: list[float | str]
    zoneid: int
    areaid: int
    appearance: GarlandToolsAPI_NPCAppearanceTyped
    photo: str  # "Enpc_1000236.png"
