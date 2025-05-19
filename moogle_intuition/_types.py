from __future__ import annotations

from enum import IntEnum
from typing import TYPE_CHECKING, Any, TypedDict

# APIResponseAliases = Union["MarketboardItemTyped",]


class FFXIVUserDBTyped(TypedDict):
    """
    Our ffxivuser DB structure.
    """

    id: int
    discord_id: int
    guild_id: int
    home_world: int
    loc: str


class FFXIVWatchListDBTyped(TypedDict):
    """
    Our watchlist DB structure.
    """

    universalis_id: int
    item_id: str
    price_min: int
    price_max: int
    last_check: float


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


class ItemIDFieldsTyped(TypedDict):
    """
    Item ID's tied to multiple languages.

    Parameters
    -----------
        en,
        de,
        ja,
        fr,
    """

    en: str
    de: str
    ja: str
    fr: str


class ItemIDTyped(TypedDict):
    """
    Item IDs
    """

    itemid: ItemIDFieldsTyped


class LocationIDsTyped(TypedDict):
    id: int
    name: str
    alt_name: str


class UniversalisAPI_AggregatedFieldsTyped(TypedDict, total=False):
    """
    -> Universalis API Aggregated DC/World Json Response fields.\n
    Related to :class:`UniversalisAPIAggregatedKeysTyped` keys.
    """

    price: int
    worldId: int
    tempstamp: int
    quantity: float


class UniversalisAPI_AggregatedKeysTyped(TypedDict, total=False):
    """
    -> Universalis API Aggregated DC/World JSON Response Keys.\n
    Related to :class:`UniversalisAPIAggregatedTyped` keys.
    """

    minListing: UniversalisAPI_AggregatedFieldsTyped
    recentPurchase: UniversalisAPI_AggregatedFieldsTyped
    averageSalePrice: UniversalisAPI_AggregatedFieldsTyped
    dailySaleVelocy: UniversalisAPI_AggregatedFieldsTyped


class UniversalisAPI_AggregatedTyped(TypedDict, total=False):
    """
    -> Universalis API Aggregated DC/World JSON Response.\n
    `./universalis_data/data/universalis_api_aggregated_dc.json`
    `./universalis_data/data/universalis_api_aggregated_world.json`
    """

    itemId: int
    nq: UniversalisAPI_AggregatedKeysTyped
    hq: UniversalisAPI_AggregatedKeysTyped
    worldUploadTimes: UniversalisAPI_AggregatedKeysTyped


class UniversalisAPI_CurrentKeysTyped(TypedDict, total=False):
    """
    -> Univertsalis API Current DC/World JSON Response Keys. \n
    Related to :class:`UniversalisAPICurrentTyped` keys.
    """

    lastReviewTime: int
    pricePerUnit: int
    quantity: int
    stainID: int
    worldName: str
    worldID: int
    creatorName: str
    creatorID: int | None
    hq: bool
    isCrafted: bool
    listingID: str
    materia: list
    onMannequin: bool
    retainerCity: int
    retainerID: int
    retainerName: str
    sellerID: int | None
    total: int
    tax: int
    timestamp: int
    buyerName: str


class UniversalisAPI_CurrentTyped(TypedDict, total=False):
    """
    -> Univertsalis API Current DC/World JSON Response. \n
    `./universalis_data/data/universalis_api_current_dc.json`
    `./universalis_data/data/universalis_api_current_world.json`
    """

    itemID: int
    worldID: int
    lastUploadTime: int
    dcName: str  # DC only
    listings: list[UniversalisAPI_CurrentKeysTyped]
    recentHistory: list[UniversalisAPI_CurrentKeysTyped]
    currentAveragePrice: float | int
    currentAveragePriceNQ: float | int
    currentAveragePriceHQ: float | int
    regularSaleVelocity: float | int
    nqSaleVelocity: float | int
    hqSaleVelocity: float | int
    averagePrice: float | int
    averagePriceNQ: float | int
    averagePriceHQ: float | int
    minPrice: int
    minPriceNQ: int
    minPriceHQ: int
    maxPrice: int
    maxPriceNQ: int
    maxPriceHQ: int
    stackSizeHistogram: dict[str, int]
    stackSizeHistogramNQ: dict[str, int]
    stackSizeHistogramHQ: dict[str, int]
    worldUploadTimes: dict[str, int]
    worldName: str
    listingsCount: int
    recentHistoryCount: int
    unitsForSale: int
    unitsSold: int
    hasData: bool


class UniversalisAPI_HistoryKeysTyped(TypedDict, total=False):
    """
    -> Universalis API History DC/World JSON Response Keys.\n
    Related to :class:`UniversalisAPIHistoryTyped` keys.
    """

    hq: bool
    pricePerUnit: int
    quantity: int
    buyerName: str
    onMannequin: bool
    timestamp: int


class UniversalisAPI_HistoryTyped(TypedDict, total=False):
    """
    -> Universalis API History DC/World JSON Response. \n
    `./local_data/api_examples/universalis_api_history_dc.json`
    `./local_data/api_examples/universalis_api_history_world.json`
    """

    itemID: int
    lastUploadTime: int
    entries: list[UniversalisAPI_HistoryKeysTyped]
    dcName: str
    worldID: int
    worldName: str
    stackSizeHistogram: dict[str, int]
    stackSizeHistogramNQ: dict[str, int]
    stackSizeHistogramHQ: dict[str, int]
    regularSaleVelocity: float | int
    nqSaleVelocity: float | int
    hqSaleVelocity: float | int


class XIVFishParameterTyped(TypedDict):
    text: str | None
    item: int  # Row
    gathering_item_level: int  # GatheringItemLevelConvertTable
    ocean_stars: int
    is_hidden: bool
    fishing_record_type: int  # FishingRecordType
    fishing_spot: int  # FishingSpot
    gathering_sub_category: int  # GatheringSubCategory
    is_in_log: bool
    achievement_credit: int


class XIVGatheringItemTyped(TypedDict):
    item: int  # Row
    gathering_item_level: int  # GatheringItemLevelConvertTable
    quest: bool  # Quest
    is_hidden: int


class XIVItemTyped(TypedDict):
    id: int
    singular: str
    adjective: int
    plural: str
    possessive_pronoun: int
    starts_with_vowel: int
    pronoun: int
    article: int
    description: str
    name: str
    icon: int
    level_item: int  # ItemLevel
    rarity: int
    filter_group: int
    additional_data: int  # Row
    item_ui_category: int  # ItemUICategory
    item_search_category: int  # ItemSearchCategory
    equip_slot_category: int  # EquipSlotCategory
    item_sort_category: int  # ItemSortCategory
    stack_size: int
    is_unique: bool
    is_untradable: bool
    is_indisposable: bool
    lot: bool
    price_mid: int
    price_low: int
    can_be_hq: int
    dye_count: int
    is_crest_worthy: bool
    item_action: int  # ItemAction
    cast_time: int
    cooldown: int
    class_job_repair: int  # ClassJob
    item_repair: int  # ItemRepairResource
    item_glamour: int  # Item
    desynth: int
    is_collectable: bool
    always_collectable: bool
    aetherial_reduce: int
    level_equip: int
    required_pvp_rank: int
    equip_restriction: int
    class_job_category: int  # ClassJobCategory
    grand_company: int  # GrandCompany
    item_series: int  # ItemSeries
    base_param_modifier: int
    model_main: int
    model_sub: int
    class_job_use: int  # ClassJob
    damage_phys: int
    damage_mag: int
    delay: int
    block_rate: int
    block: int
    defense_phys: int
    defense_mag: int
    base_param0: int  # BaseParam
    base_param_value0: int
    base_param1: int  # BaseParam
    base_param_value1: int
    base_param2: int  # BaseParam
    base_param_value2: int
    base_param3: int  # BaseParam
    base_param_value3: int
    base_param4: int  # BaseParam
    base_param_value4: int
    base_param5: int  # BaseParam
    base_param_value5: int
    item_special_bonus: int  # ItemSpecialBonus
    item_special_bonus_param: int
    base_param_special0: int  # BaseParam
    base_param_value_special0: int
    base_param_special1: int  # BaseParam
    base_param_value_special1: int
    base_param_special2: int  # BaseParam
    base_param_value_special2: int
    base_param_special3: int  # BaseParam
    base_param_value_special3: int
    base_param_special4: int  # BaseParam
    base_param_value_special4: int
    base_param_special5: int  # BaseParam
    base_param_value_special5: int
    materialize_type: int
    materia_slot_count: int
    is_advanced_melding_permitted: bool
    is_pvp: bool
    sub_stat_category: int
    is_glamourous: bool


class XIVRecipeTyped(TypedDict):
    id: int  # The Recipe # in RecipeLookUp
    number: int
    craft_type: int  # CraftType
    recipe_level_table: Any  # RecipeLevelTable
    item_result: Any  # Item - This value is the FINISHED FFXIVItem.item_id value.
    amount_result: int
    item_ingredient0: Any  # Item
    amount_ingredient0: int
    item_ingredient1: Any  # Item
    amount_ingredient1: int
    item_ingredient2: Any  # Item
    amount_ingredient2: int
    item_ingredient3: Any  # Item
    amount_ingredient3: int
    item_ingredient4: Any  # Item
    amount_ingredient4: int
    item_ingredient5: Any  # Item
    amount_ingredient5: int
    item_ingredient6: Any  # Item
    amount_ingredient6: int
    item_ingredient7: Any  # Item
    amount_ingredient7: int
    recipe_notebook_list: Any  # RecipeNotebookList
    display_priority: int
    is_secondary: bool
    material_quality_factor: int
    difficulty_factor: int
    quality_factor: int
    durability_factor: int
    required_quality: int
    required_craftsmanship: int
    required_control: int
    quick_synth_craftsmanship: int
    quick_synth_control: int
    secret_recipe_book: Any  # SecretRecipeBook
    quest: Any  # Quest
    can_quick_synth: bool
    can_hq: bool
    exp_rewarded: bool
    status_required: Any  # Status
    item_required: Any  # Item
    is_specialization_required: int  # This point's to an Item ID
    is_expert: bool
    patch_number: int


class XIVRecipeLookUpTyped(TypedDict):
    id: int
    CRP: int  # Recipe
    BSM: int  # Recipe
    ARM: int  # Recipe
    GSM: int  # Recipe
    LTW: int  # Recipe
    WVR: int  # Recipe
    ALC: int  # Recipe
    CUL: int  # Recipe


class XIVRecipeLevelTyped(TypedDict):
    id: int
    class_job_level: int
    stars: int
    suggested_craftsmanship: int
    difficulty: int
    quality: int
    progress_divider: int
    quality_divider: int
    progress_modifier: int
    quality_modifier: int
    durability: int
    conditions_flag: int


class XIVItemLevelTyped(TypedDict):
    id: int
    strength: int
    dexterity: int
    vitality: int
    intelligence: int
    mind: int
    piety: int
    HP: int
    MP: int
    TP: int
    GP: int
    CP: int
    physical_damage: int
    magical_damage: int
    delay: int
    additional_effect: int
    attack_speed: int
    block_rate: int
    block_strength: int
    tenacity: int
    attack_power: int
    defense: int
    direct_hit_rate: int
    evasion: int
    magic_defense: int
    critical_hit_power: int
    critical_hit_resilience: int
    critical_hit: int
    critical_hit_evasion: int
    slashing_resistance: int
    piercing_resistance: int
    blunt_resistance: int
    projectile_resistance: int
    attack_magic_potency: int
    healing_magic_potency: int
    enhancement_magic_potency: int
    enfeebling_magic_potency: int
    fire_resistance: int
    ice_resistance: int
    wind_resistance: int
    earth_resistance: int
    lightning_resistance: int
    water_resistance: int
    magic_resistance: int
    determination: int
    skill_speed: int
    spell_speed: int
    haste: int
    morale: int
    enmity: int
    enmity_reduction: int
    careful_desynthesis: int
    exp_bonus: int
    regen: int
    refresh: int
    movement_speed: int
    spikes: int
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
    reduced_durability_loss: int
    increased_spiritbond_gain: int
    craftsmanship: int
    control: int
    gathering: int
    perception: int


class XIVClassJobTyped(TypedDict):
    id: int
    name: str
    abbreviation: str
    class_job_category: int  # ClassJobCategory
    exp_array_index: int
    battle_class_index: int
    job_index: int
    doh_dol_job_index: int
    modifier_hit_points: int
    modifier_mana_points: int
    modifier_strength: int
    modifier_vitality: int
    modifier_dexterity: int
    modifier_intelligence: int
    modifier_mind: int
    modifier_piety: int
    pv_p_action_sort_row: int
    class_job_parent: int  # ClassJob
    name_english: str
    item_starting_weapon: int  # Item
    role: int
    starting_town: int  # Town
    monster_note: int  # MonsterNote
    primary_stat: int
    limit_break1: int  # Action
    limit_break2: int  # Action
    limit_break3: int  # Action
    u_i_priority: int
    item_soul_crystal: int  # Item
    unlock_quest: int  # Quest
    relic_quest: int  # Quest
    prerequisite: int  # Quest
    starting_level: int
    party_bonus: int
    is_limited_job: bool
    can_queue_for_duty: bool


class XIVClassJobCategoryTyped(TypedDict):
    id: int
    name: str
    ADV: bool
    GLA: bool
    PGL: bool
    MRD: bool
    LNC: bool
    ARC: bool
    CNJ: bool
    THM: bool
    CRP: bool
    BSM: bool
    ARM: bool
    GSM: bool
    LTW: bool
    WVR: bool
    ALC: bool
    CUL: bool
    MIN: bool
    BTN: bool
    FSH: bool
    PLD: bool
    MNK: bool
    WAR: bool
    DRG: bool
    BRD: bool
    WHM: bool
    BLM: bool
    ACN: bool
    SMN: bool
    SCH: bool
    ROG: bool
    NIN: bool
    MCH: bool
    DRK: bool
    AST: bool
    SAM: bool
    RDM: bool
    BLU: bool
    GNB: bool
    DNC: bool
    RPR: bool
    SGE: bool
    VPR: bool
    PCT: bool


class XIVBaseParamTyped(TypedDict):
    id: int
    packet_index: int
    name: str
    description: str
    order_priority: int
    one_h_wpn_percent: int
    oh_percent: int
    head_percent: int
    chest_percent: int
    hands_percent: int
    waist_percent: int
    legs_percent: int
    feet_percent: int
    earring_percent: int
    necklace_percent: int
    bracelet_percent: int
    ring_percent: int
    two_h_wpn_percent: int
    under_armor_percent: int
    chest_head_percent: int
    chest_head_legs_feet_percent: int
    legs_feet_percent: int
    head_chest_hands_legs_feet_percent: int
    chest_legs_gloves_percent: int
    chest_legs_feet_percent: int
    meld_param0: int
    meld_param1: int
    meld_param2: int
    meld_param3: int
    meld_param4: int
    meld_param5: int
    meld_param6: int
    meld_param7: int
    meld_param8: int
    meld_param9: int
    meld_param10: int
    meld_param11: int
    meld_param12: int


class XIVGatheringItemLevelTyped(TypedDict):
    id: int
    gathering_item_level: int
    stars: int


class XIVFishingSpotTyped(TypedDict):
    id: int
    gathering_level: int
    big_fish_on_reach: str
    big_fish_on_end: str
    fishing_spot_category: int
    rare: bool
    territory_type: int  # TerritoryType
    place_name_main: int  # PlaceName
    place_name_sub: int  # PlaceName
    x: int
    z: int
    radius: int
    item0: int  # Item
    item1: int  # Item
    item2: int  # Item
    item3: int  # Item
    item4: int  # Item
    item5: int  # Item
    item6: int  # Item
    item7: int  # Item
    item8: int  # Item
    item9: int  # Item
    place_name: int  # PlaceName
    order: int


class XIVPlaceNameTyped(TypedDict):
    id: int
    name: str
    name_no_article: str
