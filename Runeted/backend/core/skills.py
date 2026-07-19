"""Skill system: the player's active, per-turn combat choice.

A skill is what the player commits to each round — it has a value that
feeds one shared budget, a value-scaled cooldown and stamina cost, and
(for attacks) `counters` tags matched against the telegraphed intent.
This used to be labelled "equipped runes" in battle; the mechanics are
unchanged, only the concept is renamed. The passive Rune system
(models/rune.py / services/rune_system.py) is a separate, later phase
and is not referenced here.

Skill kinds (the `method` tag stays the coarse category):
- attack   (offense):  strike + counter attempt against the telegraph
- defend   (defense):  blocks the telegraphed effect, deals no damage
- dodge    (defense):  evades the whole telegraphed move, deals no damage
- buff     (utility):  spends stamina for a temporary attack bonus
- recovery (utility):  costs 0 stamina and restores stamina, so an empty
                       stamina bar never leaves the player without a
                       legal action

Loadout rules, enforced at construction (the only place loadouts are
built): at most SKILL_SLOT_CAP skills, and their total value may not
exceed the value budget (base cap plus any equipped budget modifiers).
"""
from __future__ import annotations

from typing import Iterable, Literal

from pydantic import BaseModel, Field

SKILL_SLOT_CAP = 6
SKILL_VALUE_BUDGET = 10

COOLDOWN_MIN = 1
COOLDOWN_MAX = 3
STAMINA_COST_MIN = 1

SkillKind = Literal["attack", "defend", "dodge", "buff", "recovery"]
SkillMethod = Literal["offense", "defense", "utility", "drawback", "amplifier"]


class SkillStatus(BaseModel):
    """Status effect a skill applies, shown as icon + duration on the button."""
    status: str
    duration: int = Field(ge=1)
    detail: str = ""


class Skill(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=80)
    rarity: str = "common"
    value: int = Field(ge=-3, le=5)
    element: str = "physical"
    method: SkillMethod = "offense"
    kind: SkillKind = "attack"
    icon: str = "sigil"
    counters: list[str] = Field(default_factory=list)
    applies_status: SkillStatus | None = None
    # Overrides the value-derived stamina cost (recovery skills cost 0).
    stamina_cost: int | None = Field(default=None, ge=0)
    # Buff skills: temporary attack bonus and how many rounds it lasts.
    buff_attack_mult: float = Field(default=0.0, ge=0.0, le=2.0)
    buff_duration: int = Field(default=0, ge=0)
    # Recovery skills: stamina restored on use.
    stamina_restore: float = Field(default=0.0, ge=0.0)
    # Raises the loadout's value budget while equipped.
    budget_modifier: int | None = Field(default=None, ge=0, le=3)


def cooldown_of(skill: Skill) -> int:
    """Stronger skills cool longer: cooldown follows skill value, clamped."""
    return max(COOLDOWN_MIN, min(COOLDOWN_MAX, int(skill.value)))


def stamina_cost_of(skill: Skill) -> int:
    """Stronger effects cost more stamina: cost follows skill value,
    floored — unless the skill declares its own cost (recovery costs 0)."""
    if skill.stamina_cost is not None:
        return int(skill.stamina_cost)
    return max(STAMINA_COST_MIN, int(skill.value))


# The skill catalog. The first six are the former battle runes, carried
# over verbatim (same ids, values, counters) as attack skills; the rest
# are the move types added after playtesting.
SKILL_CATALOG: list[dict[str, object]] = [
    {
        "id": "ember_drive", "name": "Ember Drive", "rarity": "common",
        "value": 2, "element": "fire", "method": "offense", "kind": "attack",
        "icon": "flame", "counters": ["brute"],
        "applies_status": {"status": "exposed", "duration": 1, "detail": "on a successful counter"},
    },
    {
        "id": "frost_guard", "name": "Frost Guard", "rarity": "uncommon",
        "value": 1, "element": "ice", "method": "defense", "kind": "attack",
        "icon": "frost", "counters": ["skirmisher"],
        "applies_status": {"status": "exposed", "duration": 1, "detail": "on a successful counter"},
    },
    {
        "id": "venom_hex", "name": "Venom Hex", "rarity": "rare",
        "value": 3, "element": "poison", "method": "offense", "kind": "attack",
        "icon": "venom", "counters": ["caster"],
        "applies_status": {"status": "exposed", "duration": 1, "detail": "on a successful counter"},
    },
    {
        "id": "stone_steadfast", "name": "Stone Steadfast", "rarity": "rare",
        "value": 2, "element": "physical", "method": "defense", "kind": "attack",
        "icon": "stone", "counters": ["tank"],
        "applies_status": {"status": "exposed", "duration": 1, "detail": "on a successful counter"},
    },
    {
        "id": "arcane_resonance", "name": "Arcane Resonance", "rarity": "epic",
        "value": 4, "element": "arcane", "method": "utility", "kind": "attack",
        "icon": "arcane", "counters": ["summoner"],
        "applies_status": {"status": "exposed", "duration": 1, "detail": "on a successful counter"},
    },
    {
        "id": "blood_pact", "name": "Blood Pact", "rarity": "uncommon",
        "value": 4, "element": "physical", "method": "amplifier", "kind": "attack",
        "icon": "blood", "counters": ["brute"], "budget_modifier": 1,
        "applies_status": {"status": "exposed", "duration": 1, "detail": "on a successful counter"},
    },
    # Kind-countering attacks: counter a move type from any archetype.
    {
        "id": "breaker_lunge", "name": "Breaker Lunge", "rarity": "uncommon",
        "value": 2, "element": "physical", "method": "offense", "kind": "attack",
        "icon": "sword", "counters": ["heavy", "guard_break"],
        "applies_status": {"status": "exposed", "duration": 1, "detail": "on a successful counter"},
    },
    {
        "id": "flurry_break", "name": "Flurry Break", "rarity": "uncommon",
        "value": 2, "element": "physical", "method": "offense", "kind": "attack",
        "icon": "cross", "counters": ["multi"],
        "applies_status": {"status": "exposed", "duration": 1, "detail": "on a successful counter"},
    },
    # Defensive move types: mitigate the telegraph instead of dealing damage.
    {
        "id": "bulwark", "name": "Bulwark", "rarity": "common",
        "value": 1, "element": "physical", "method": "defense", "kind": "defend",
        "icon": "shield", "counters": [],
    },
    {
        "id": "sidestep", "name": "Sidestep", "rarity": "common",
        "value": 2, "element": "physical", "method": "defense", "kind": "dodge",
        "icon": "wind", "counters": [],
    },
    # Buff: stamina for a temporary bonus.
    {
        "id": "war_chant", "name": "War Chant", "rarity": "common",
        "value": 2, "element": "physical", "method": "utility", "kind": "buff",
        "icon": "banner", "counters": [],
        "buff_attack_mult": 0.5, "buff_duration": 2,
        "applies_status": {"status": "empowered", "duration": 2, "detail": "+50% attack"},
    },
    # Recovery: always a legal action, even at 0 stamina.
    {
        "id": "second_wind", "name": "Second Wind", "rarity": "common",
        "value": 0, "element": "physical", "method": "utility", "kind": "recovery",
        "icon": "leaf", "counters": [],
        "stamina_cost": 0, "stamina_restore": 3.0,
    },
]

# Default battle loadout: two kind-countering attacks (every dangerous
# telegraph in every archetype deck is heavy, multi, or guard_break),
# one defend, one dodge, one buff, one recovery. Total value 9 <= 10.
DEFAULT_LOADOUT_IDS = [
    "breaker_lunge",  # attack — counters heavy and guard_break moves
    "flurry_break",   # attack — counters multi moves
    "bulwark",        # defend — blocks any telegraphed effect
    "sidestep",       # dodge — evades the whole move
    "war_chant",      # buff — temporary attack bonus
    "second_wind",    # recovery — 0 cost, restores stamina
]


class SkillLoadout:
    def __init__(self, skills: Iterable[Skill], capacity: int | None = None,
                 value_budget: int | None = None):
        self.capacity = int(capacity if capacity is not None else SKILL_SLOT_CAP)
        self.skills: dict[str, Skill] = {}
        for skill in skills:
            if len(self.skills) >= self.capacity:
                raise ValueError(f"Loadout exceeds the {self.capacity} slot cap")
            self.skills[skill.id] = skill
        base_budget = int(value_budget if value_budget is not None else SKILL_VALUE_BUDGET)
        self.value_budget = base_budget + sum(
            int(s.budget_modifier or 0) for s in self.skills.values()
        )
        self.total_value = sum(int(s.value) for s in self.skills.values())
        if self.total_value > self.value_budget:
            raise ValueError(
                f"Loadout value {self.total_value} exceeds the {self.value_budget} value budget"
            )
        self._cooldowns: dict[str, int] = {}

    def get(self, skill_id: str) -> Skill | None:
        return self.skills.get(str(skill_id))

    def remaining_cooldown(self, skill_id: str) -> int:
        return max(0, int(self._cooldowns.get(str(skill_id), 0)))

    def can_use(self, skill_id: str) -> bool:
        return str(skill_id) in self.skills and self.remaining_cooldown(skill_id) == 0

    def available(self) -> list[Skill]:
        return [s for sid, s in self.skills.items() if self.remaining_cooldown(sid) == 0]

    def use(self, skill_id: str) -> Skill:
        sid = str(skill_id)
        skill = self.skills.get(sid)
        if skill is None:
            raise ValueError(f"Skill '{sid}' is not in the loadout")
        if self.remaining_cooldown(sid) > 0:
            raise ValueError(f"Skill '{sid}' is on cooldown for {self.remaining_cooldown(sid)} more round(s)")
        self._cooldowns[sid] = cooldown_of(skill)
        return skill

    def tick(self) -> None:
        """End-of-round cooldown decay."""
        for sid in list(self._cooldowns):
            self._cooldowns[sid] = max(0, self._cooldowns[sid] - 1)
            if self._cooldowns[sid] == 0:
                del self._cooldowns[sid]


def describe_skill(skill: Skill) -> dict[str, str]:
    """Single source of the skill text the UI shows: `short` for compact
    surfaces, `full` for the info modal (including what it counters)."""
    cost = stamina_cost_of(skill)
    cooldown = cooldown_of(skill)
    tail = f"{cost} stamina · {cooldown}-round cooldown"
    counters = ", ".join(skill.counters) if skill.counters else "nothing"

    if skill.kind == "attack":
        short = f"Counters {counters} · {tail}"
        body = (
            f"An attack: your strike lands, and if the enemy's telegraphed move is "
            f"one it counters ({counters}), the move's effect is negated and the "
            f"enemy is left exposed next round (your next strike deals bonus damage)."
        )
    elif skill.kind == "defend":
        short = f"Blocks any telegraphed effect · {tail}"
        body = (
            "A defend: you deal no damage this round, but the effect portion of the "
            "enemy's telegraphed move is blocked no matter what it counters — only "
            "the contact graze can land."
        )
    elif skill.kind == "dodge":
        short = f"Evades the whole move · {tail}"
        body = (
            "A dodge: you deal no damage this round and evade the enemy's "
            "telegraphed move entirely — contact and effect both miss."
        )
    elif skill.kind == "buff":
        short = f"+{skill.buff_attack_mult:.0%} attack for {skill.buff_duration} rounds · {tail}"
        body = (
            f"A buff: you deal no damage this round, but your strikes deal "
            f"+{skill.buff_attack_mult:.0%} damage for the next {skill.buff_duration} rounds."
        )
    else:  # recovery
        short = f"Restores {skill.stamina_restore:g} stamina · {tail}"
        body = (
            f"A recovery: costs nothing and restores {skill.stamina_restore:g} stamina, "
            "so you always have a legal action even with an empty stamina bar. "
            "You deal no damage this round."
        )

    full = (
        f"{skill.name} ({skill.rarity} {skill.element} {skill.method} skill). {body} "
        f"Costs {cost} stamina and cools down for {cooldown} round(s) whenever used."
    )
    return {"short": short, "full": full}


def catalog_skills() -> list[Skill]:
    return [Skill(**entry) for entry in SKILL_CATALOG]


def skill_by_id(skill_id: str) -> Skill | None:
    for entry in SKILL_CATALOG:
        if str(entry["id"]) == str(skill_id):
            return Skill(**entry)
    return None


def default_loadout() -> SkillLoadout:
    by_id = {str(entry["id"]): entry for entry in SKILL_CATALOG}
    skills = [Skill(**by_id[sid]) for sid in DEFAULT_LOADOUT_IDS if sid in by_id]
    return SkillLoadout(skills)
