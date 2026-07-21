from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from models.item import Item, ItemSlot

class Player(BaseModel):
    # Progression
    level: int = 1
    exp: int = 0
    exp_to_next: int = 100
    prestige: int = 0

    # Dungeon progress
    depth: int = 1

    # Stats
    stat_points: int = 0
    strength: int = 5
    dexterity: int = 5
    intelligence: int = 5
    vitality: int = 5
    luck: int = 5

    # Combat base
    base_attack: int = 10
    base_defense: int = 5
    max_hp: int = 100
    hp: int = 100

    # Economy
    gold: int = 0

    # Combat resources
    max_stamina: int = 100
    stamina: int = 100
    last_action: str = ""
    action_streak: int = 0
    action_cooldowns: Dict[str, int] = Field(default_factory=dict)
    combo_windows: Dict[str, int] = Field(default_factory=dict)

    # Inventory
    stash: List[Item] = Field(default_factory=list)

    # Equipment
    equipment: Dict[ItemSlot, Optional[Item]] = Field(
        default_factory=lambda: {"weapon": None, "armor": None}
    )

    # Combat state (turn-session scoped but stored here for now)
    status: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    combat_mods: Dict[str, object] = Field(default_factory=dict)

    # Gathering/Crafting (Step: rune systems)
    runecrafting_level: int = 1
    runecrafting_xp: int = 0
    runecrafting_xp_to_next: int = 100
    resources: Dict[str, int] = Field(default_factory=lambda: {
        "rune_essence": 50,
        "arcane_chest": 0,
        "rune_relic": 0,
        "idle_tonic": 2,
        "timber": 0,
        "raw_fish": 0,
        "ore": 0,
        "crafted_supplies": 0,
    })
    runes: Dict[str, int] = Field(default_factory=dict)

    # Slayer + Prayer
    slayer_level: int = 1
    slayer_xp: int = 0
    slayer_xp_to_next: int = 100
    slayer_task: Dict[str, object] = Field(default_factory=lambda: {
        "target": "", "remaining": 0, "total": 0, "tier": "normal"
    })
    active_prayer: str = ""

    # Build runes (socketed power system)
    rune_items: List[Dict[str, object]] = Field(default_factory=list)
    rune_loadout: List[Optional[str]] = Field(default_factory=lambda: [None] * 6)

    # Idle systems
    idle_skills: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    idle_activity: Dict[str, object] = Field(default_factory=lambda: {
        "skill": "",
        "started_at": 0.0,
        "last_tick_at": 0.0,
    })
    idle_upgrades: Dict[str, int] = Field(default_factory=lambda: {
        "efficiency": 0,
        "rare_find": 0,
        "duration_cap": 0,
    })
    idle_boosts: List[Dict[str, float]] = Field(default_factory=list)
    idle_last_summary: Dict[str, object] = Field(default_factory=dict)

    # Battle loadout systems (mana-cap, random roll, skill tree)
    mana_cap: int = 20
    battle_skills: List[str] = Field(default_factory=lambda: [
        "quick_slash",
        "cleave",
        "guard_stance",
        "focus_channel",
        "self_bleed",
        "blank_stumble",
    ])
    battle_tree: Dict[str, int] = Field(default_factory=lambda: {
        "power_training": 0,
        "iron_guard": 0,
        "echo_reroll": 0,
        "loaded_slot_one": 0,
        "curse_attunement": 0,
        "affliction_mastery": 0,
    })
    battle_state: Dict[str, object] = Field(default_factory=lambda: {
        "last_roll": "",
        "rerolls": 0,
        "curse_charge": 0.0,
    })
    battle_presets: Dict[str, List[str]] = Field(default_factory=dict)
    battle_mastery: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    objectives_claimed: List[str] = Field(default_factory=list)
    mechanics_learned: Dict[str, int] = Field(default_factory=dict)
    guide_flags: Dict[str, object] = Field(default_factory=lambda: {
        "dismissed": False,
    })
    progress_counters: Dict[str, float] = Field(default_factory=lambda: {
        "enemies_defeated": 0.0,
        "bosses_defeated": 0.0,
        "dungeons_cleared": 0.0,
        "idle_seconds": 0.0,
    })

    class Config:
        arbitrary_types_allowed = True

    # -------------------------
    # Derived stats
    # -------------------------
    @property
    def weapon_power(self) -> int:
        return self.equipment["weapon"].power if self.equipment["weapon"] else 0

    @property
    def armor_power(self) -> int:
        return self.equipment["armor"].power if self.equipment["armor"] else 0

    @property
    def attack(self) -> int:
        # STR matters a lot for damage scaling
        # weapon adds flat power
        return self.base_attack + self.weapon_power + int(self.strength * 1.5)

    @property
    def defense(self) -> int:
        # VIT matters for defense
        return self.base_defense + self.armor_power + int(self.vitality * 1.2)

    @property
    def dodge_bonus(self) -> float:
        # DEX increases dodge window size (front-end) and reduces damage slightly (later)
        # 5 dex -> 0.0 bonus, 25 dex -> +0.20 bonus (cap)
        return min(0.20, max(0.0, (self.dexterity - 5) * 0.01))

    @property
    def loot_luck(self) -> float:
        # Luck increases better loot odds (used step 12)
        return min(0.25, max(0.0, (self.luck - 5) * 0.01))

    @property
    def rune_slot_capacity(self) -> int:
        # Default loadout size is fixed at 6 slots before slot modifiers are equipped.
        return 6

    # -------------------------
    # Stat spending
    # -------------------------
    def spend_stat(self, stat: str, amount: int = 1) -> bool:
        if amount <= 0:
            return False
        if self.stat_points < amount:
            return False

        if stat == "strength":
            self.strength += amount
        elif stat == "dexterity":
            self.dexterity += amount
        elif stat == "intelligence":
            self.intelligence += amount
        elif stat == "vitality":
            self.vitality += amount
            # Vitality also increases max HP slightly
            self.max_hp += 2 * amount
            self.hp = min(self.hp + 2 * amount, self.max_hp)
        elif stat == "luck":
            self.luck += amount
        else:
            return False

        self.stat_points -= amount
        return True

    # -------------------------
    # Progression
    # -------------------------
    def gain_exp(self, amount: int):
        self.exp += amount
        while self.exp >= self.exp_to_next:
            self.exp -= self.exp_to_next
            self.level_up()

    def level_up(self):
        self.level += 1
        self.stat_points += 5
        self.exp_to_next = int(self.exp_to_next * 1.5)
        self.max_hp += 10
        self.hp = self.max_hp

    # -------------------------
    # Crafting helpers
    # -------------------------
    def add_resource(self, key: str, amount: int):
        if amount <= 0:
            return
        self.resources[key] = int(self.resources.get(key, 0) or 0) + int(amount)

    def spend_resource(self, key: str, amount: int) -> bool:
        amount = int(amount)
        if amount <= 0:
            return True
        cur = int(self.resources.get(key, 0) or 0)
        if cur < amount:
            return False
        self.resources[key] = cur - amount
        return True

    def add_rune(self, rune: str, amount: int):
        if amount <= 0:
            return
        self.runes[rune] = int(self.runes.get(rune, 0) or 0) + int(amount)

    def gain_runecrafting_xp(self, amount: int):
        amount = int(amount)
        if amount <= 0:
            return
        self.runecrafting_xp += amount
        while self.runecrafting_xp >= self.runecrafting_xp_to_next:
            self.runecrafting_xp -= self.runecrafting_xp_to_next
            self.runecrafting_level += 1
            self.runecrafting_xp_to_next = int(self.runecrafting_xp_to_next * 1.35)

    def sync_rune_loadout(self):
        cap = int(self.rune_slot_capacity)
        current = list(self.rune_loadout or [])
        if len(current) < cap:
            current.extend([None] * (cap - len(current)))
        elif len(current) > cap:
            current = current[:cap]
        self.rune_loadout = current

    def gain_slayer_xp(self, amount: int):
        amount = int(amount)
        if amount <= 0:
            return
        self.slayer_xp += amount
        while self.slayer_xp >= self.slayer_xp_to_next:
            self.slayer_xp -= self.slayer_xp_to_next
            self.slayer_level += 1
            self.slayer_xp_to_next = int(self.slayer_xp_to_next * 1.35)

    # -------------------------
    # Idle systems
    # -------------------------
    def idle_skill_state(self, skill: str) -> Dict[str, float]:
        key = str(skill or "").strip().lower()
        if not key:
            key = "idle"
        if key not in self.idle_skills:
            self.idle_skills[key] = {
                "level": 1.0,
                "xp": 0.0,
                "xp_to_next": 100.0,
                "total_xp": 0.0,
            }
        data = self.idle_skills[key]
        data["level"] = float(max(1.0, data.get("level", 1.0)))
        data["xp"] = float(max(0.0, data.get("xp", 0.0)))
        data["xp_to_next"] = float(max(25.0, data.get("xp_to_next", 100.0)))
        data["total_xp"] = float(max(0.0, data.get("total_xp", 0.0)))
        return data

    def gain_idle_xp(self, skill: str, amount: float) -> Dict[str, int]:
        amt = float(amount or 0.0)
        if amt <= 0:
            return {"levels": 0}
        data = self.idle_skill_state(skill)
        data["xp"] += amt
        data["total_xp"] += amt

        levels = 0
        while data["xp"] >= data["xp_to_next"]:
            data["xp"] -= data["xp_to_next"]
            data["level"] += 1.0
            levels += 1
            # High-cap leveling curve designed for very long progression.
            data["xp_to_next"] = max(50.0, data["xp_to_next"] * 1.12 + (data["level"] * 0.75))
        return {"levels": levels}

    def clear_expired_idle_boosts(self, now_ts: float) -> None:
        now = float(now_ts or 0.0)
        kept: List[Dict[str, float]] = []
        for boost in list(self.idle_boosts or []):
            expires = float(boost.get("expires_at", 0.0) or 0.0)
            if expires > now:
                kept.append(boost)
        self.idle_boosts = kept

    # -------------------------
    # Prestige
    # -------------------------
    def prestige_reset(self):
        self.prestige += 1

        self.level = 1
        self.exp = 0
        self.exp_to_next = 100
        self.depth = 1

        self.stat_points = 0
        self.strength = 5
        self.dexterity = 5
        self.intelligence = 5
        self.vitality = 5
        self.luck = 5

        self.base_attack = 10 + self.prestige
        self.base_defense = 5 + self.prestige

        self.max_hp = 100 + (self.prestige * 10)
        self.hp = self.max_hp

        self.gold = 0
        self.max_stamina = 100
        self.stamina = 100
        self.last_action = ""
        self.action_streak = 0
        self.action_cooldowns = {}
        self.combo_windows = {}
        self.stash.clear()
        self.equipment = {"weapon": None, "armor": None}
        self.status = {}
        self.combat_mods = {}
        self.runecrafting_level = 1
        self.runecrafting_xp = 0
        self.runecrafting_xp_to_next = 100
        self.resources = {
            "rune_essence": 50,
            "arcane_chest": 0,
            "rune_relic": 0,
            "idle_tonic": 2,
            "timber": 0,
            "raw_fish": 0,
            "ore": 0,
            "crafted_supplies": 0,
        }
        self.runes = {}
        self.slayer_level = 1
        self.slayer_xp = 0
        self.slayer_xp_to_next = 100
        self.slayer_task = {"target": "", "remaining": 0, "total": 0, "tier": "normal"}
        self.active_prayer = ""
        self.rune_items = []
        self.rune_loadout = [None, None]
        self.idle_skills = {}
        self.idle_activity = {"skill": "", "started_at": 0.0, "last_tick_at": 0.0}
        self.idle_upgrades = {"efficiency": 0, "rare_find": 0, "duration_cap": 0}
        self.idle_boosts = []
        self.idle_last_summary = {}
        self.mana_cap = 20
        self.battle_skills = [
            "quick_slash",
            "cleave",
            "guard_stance",
            "focus_channel",
            "self_bleed",
            "blank_stumble",
        ]
        self.battle_tree = {
            "power_training": 0,
            "iron_guard": 0,
            "echo_reroll": 0,
            "loaded_slot_one": 0,
            "curse_attunement": 0,
            "affliction_mastery": 0,
        }
        self.battle_state = {"last_roll": "", "rerolls": 0, "curse_charge": 0.0}
        self.battle_presets = {}
        self.battle_mastery = {}
        self.objectives_claimed = []
        self.progress_counters = {
            "enemies_defeated": 0.0,
            "bosses_defeated": 0.0,
            "dungeons_cleared": 0.0,
            "idle_seconds": 0.0,
        }
