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

from typing import TYPE_CHECKING, Any, NotRequired, TypedDict

if TYPE_CHECKING:
    from ff14angler import Angler
    from universalis import DataCenter, ItemQuality, UniversalisAPI, World

    from .modules import Moogle


class CurMarketBoardParams(TypedDict):
    world_or_dc: NotRequired[DataCenter | World]
    num_listings: NotRequired[int]
    num_history_entries: NotRequired[int]
    item_quality: NotRequired[ItemQuality]
    trim_item_fields: NotRequired[bool]


class HistMarketBoardParams(TypedDict):
    world_or_dc: NotRequired[DataCenter | World]
    num_listings: NotRequired[int]
    min_price: NotRequired[int]
    max_price: NotRequired[int]
    history: NotRequired[int]


class CSVParseParams(TypedDict):
    format_keys: bool
    convert_pound: bool


class ObjectParams(TypedDict):
    moogle: Moogle
    universalis: NotRequired[UniversalisAPI]
    angler: NotRequired[Angler]


class FishParameterData(TypedDict):
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


class GatheringItemData(TypedDict):
    id: int
    item: int  # Row
    gathering_item_level: int  # GatheringItemLevelConvertTable
    quest: bool  # Quest
    is_hidden: int


class ItemData(TypedDict):
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


class RecipeData(TypedDict):
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


class RecipeLookUpData(TypedDict):
    id: int
    CRP: int  # Recipe
    BSM: int  # Recipe
    ARM: int  # Recipe
    GSM: int  # Recipe
    LTW: int  # Recipe
    WVR: int  # Recipe
    ALC: int  # Recipe
    CUL: int  # Recipe


class RecipeLevelData(TypedDict):
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


class ItemLevelData(TypedDict):
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


class ClassJobData(TypedDict):
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


class ClassJobCategoryData(TypedDict):
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


class BaseParamData(TypedDict):
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


class GatheringItemLevelData(TypedDict):
    id: int
    gathering_item_level: int
    stars: int


class FishingSpotData(TypedDict):
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


class PlaceNameData(TypedDict):
    id: int
    name: str
    name_no_article: str


class GetItemParams(TypedDict, total=False):
    match: int
    limit_results: int


class AllagonToolsInventoryCSV(TypedDict):
    favourite: bool
    icon: NotRequired[str]
    name: str
    type: str
    total_quantity_available: int
    source: str
    inventory_location: str


class SpearFishingItemData(TypedDict):
    id: int
    description: str
    item: int
    gathering_item_level: int
    fishing_record_type: int
    territory_type: int
    is_visible: bool


class SpearFishingNotebookData(TypedDict):
    id: int
    gathering_level: int
    is_shadow_node: bool
    territory_type: int
    x: int
    y: int
    radius: int
    place_name: int
    gathering_point_base: int
