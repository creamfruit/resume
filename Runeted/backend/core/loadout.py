"""Persistent skill/rune loadout selection: what a player has chosen to
bring into their next battle, built and edited outside of combat on the
Skills and Runes pages.

Kept separate from `core/player_state.py` (identity + progression only,
by design) and from `SkillLoadout`/`RuneEquipment` themselves, which
carry live, battle-scoped state (cooldowns, a fixed slot/budget
snapshot) rebuilt fresh every battle -- not something to persist across
fights. This module owns two fixed-length slot arrays -- `skill_slots`
(length `SKILL_SLOT_CAP`) and `rune_slots` (length `RUNE_SLOT_CAP`,
whatever the rune system actually has, not forced to match skills) --
each entry either a catalog id or `None` (empty). The slot *position*
is meaningful here (it's what the grid UI shows and lets the player
swap directly), even though `SkillLoadout`/`RuneEquipment` themselves
don't care about order, only membership.

Every mutation enforces the same budget/slot rules `SkillLoadout`/
`RuneEquipment` already apply at construction by literally building one
with the candidate change and only committing if it doesn't raise --
there is no second, parallel rule set to drift out of sync with battle.
A swap can never violate budget (it only reorders the same equipped
items, so total value/cost is unchanged), so it skips that check and
just validates the two slot indices exist.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from core.runes import (
    DEFAULT_EQUIPPED_IDS,
    RUNE_SLOT_CAP,
    Rune,
    RuneEquipment,
    catalog_runes,
    rune_by_id,
)
from core.skills import (
    DEFAULT_LOADOUT_IDS,
    SKILL_SLOT_CAP,
    Skill,
    SkillLoadout,
    catalog_skills,
    skill_by_id,
)


def _padded_slots(ids: list[str], cap: int) -> list[str | None]:
    slots: list[str | None] = list(ids[:cap])
    slots += [None] * (cap - len(slots))
    return slots


def _default_skill_slots() -> list[str | None]:
    return _padded_slots(list(DEFAULT_LOADOUT_IDS), SKILL_SLOT_CAP)


def _default_rune_slots() -> list[str | None]:
    return _padded_slots(list(DEFAULT_EQUIPPED_IDS), RUNE_SLOT_CAP)


@dataclass
class LoadoutSelection:
    # New accounts start on the same default loadout/equipment battle
    # already used before this system existed -- nothing changes until
    # a player actually visits the Skills or Runes page.
    skill_slots: list[str | None] = field(default_factory=_default_skill_slots)
    rune_slots: list[str | None] = field(default_factory=_default_rune_slots)

    # ---------- Skills ----------

    def build_skill_loadout(self) -> SkillLoadout:
        skills = [s for s in (skill_by_id(sid) for sid in self.skill_slots if sid is not None) if s is not None]
        return SkillLoadout(skills)

    def _check_skill_slot(self, slot: int) -> None:
        if not (0 <= slot < len(self.skill_slots)):
            raise ValueError(f"Skill slot {slot} does not exist (0-{len(self.skill_slots) - 1})")

    def equip_skill(self, slot: int, skill_id: str) -> None:
        """Put a skill into a specific slot. Validated by actually
        constructing a SkillLoadout with the candidate slots -- the
        exact value-budget rule battle enforces, including a
        budget_modifier skill raising the cap for the whole loadout.
        Raises ValueError (selection left untouched) for an out-of-
        range slot, an unknown skill, or one already equipped
        elsewhere, or a budget violation."""
        self._check_skill_slot(slot)
        if self.skill_slots[slot] is not None:
            raise ValueError(f"Skill slot {slot} is already occupied by '{self.skill_slots[slot]}'")
        if skill_by_id(skill_id) is None:
            raise ValueError(f"Unknown skill '{skill_id}'")
        if skill_id in self.skill_slots:
            raise ValueError(f"'{skill_id}' is already equipped")
        trial = list(self.skill_slots)
        trial[slot] = skill_id
        skills = [s for s in (skill_by_id(sid) for sid in trial if sid is not None) if s is not None]
        SkillLoadout(skills)  # raises ValueError on value-budget violation
        self.skill_slots = trial

    def unequip_skill(self, slot: int) -> None:
        self._check_skill_slot(slot)
        self.skill_slots[slot] = None

    def swap_skill_slots(self, slot_a: int, slot_b: int) -> None:
        """Exchange two slots' contents directly -- works for
        filled<->filled (a real swap), filled<->empty (a move), and is
        a no-op for empty<->empty. Always legal: reordering the same
        equipped items can never change the total value."""
        self._check_skill_slot(slot_a)
        self._check_skill_slot(slot_b)
        self.skill_slots[slot_a], self.skill_slots[slot_b] = self.skill_slots[slot_b], self.skill_slots[slot_a]

    def recommended_skill_id(self) -> str | None:
        """A sensible pick for an empty slot, for anyone without a
        strong opinion yet: prefer whichever member of the curated
        default loadout isn't already equipped and still fits: it's
        the game's own considered starter build (two kind-countering
        attacks, a defend, a dodge, a buff, a recovery), not a new
        scoring system. If the whole default set is already equipped
        or none of it still fits, fall back to the highest-value
        catalog skill that does. None if nothing fits at all (no empty
        slot, or the budget is fully spent)."""
        if None not in self.skill_slots:
            return None
        equipped = {sid for sid in self.skill_slots if sid is not None}
        empty_slot = self.skill_slots.index(None)

        def fits(skill_id: str) -> bool:
            trial = list(self.skill_slots)
            trial[empty_slot] = skill_id
            skills = [s for s in (skill_by_id(sid) for sid in trial if sid is not None) if s is not None]
            try:
                SkillLoadout(skills)
                return True
            except ValueError:
                return False

        by_id: dict[str, Skill] = {s.id: s for s in catalog_skills()}
        candidates = [sid for sid in by_id if sid not in equipped and fits(sid)]
        if not candidates:
            return None
        for sid in DEFAULT_LOADOUT_IDS:
            if sid in candidates:
                return sid
        return max(candidates, key=lambda sid: by_id[sid].value)

    # ---------- Runes ----------

    def build_rune_equipment(self) -> RuneEquipment:
        runes = [r for r in (rune_by_id(rid) for rid in self.rune_slots if rid is not None) if r is not None]
        return RuneEquipment(runes)

    def _check_rune_slot(self, slot: int) -> None:
        if not (0 <= slot < len(self.rune_slots)):
            raise ValueError(f"Rune slot {slot} does not exist (0-{len(self.rune_slots) - 1})")

    def equip_rune(self, slot: int, rune_id: str) -> None:
        """Same pattern as equip_skill, against RuneEquipment's own
        cost-budget rule."""
        self._check_rune_slot(slot)
        if self.rune_slots[slot] is not None:
            raise ValueError(f"Rune slot {slot} is already occupied by '{self.rune_slots[slot]}'")
        if rune_by_id(rune_id) is None:
            raise ValueError(f"Unknown rune '{rune_id}'")
        if rune_id in self.rune_slots:
            raise ValueError(f"'{rune_id}' is already equipped")
        trial = list(self.rune_slots)
        trial[slot] = rune_id
        runes = [r for r in (rune_by_id(rid) for rid in trial if rid is not None) if r is not None]
        RuneEquipment(runes)  # raises ValueError on cost-budget violation
        self.rune_slots = trial

    def unequip_rune(self, slot: int) -> None:
        self._check_rune_slot(slot)
        self.rune_slots[slot] = None

    def swap_rune_slots(self, slot_a: int, slot_b: int) -> None:
        self._check_rune_slot(slot_a)
        self._check_rune_slot(slot_b)
        self.rune_slots[slot_a], self.rune_slots[slot_b] = self.rune_slots[slot_b], self.rune_slots[slot_a]

    def recommended_rune_id(self) -> str | None:
        """Same principle as recommended_skill_id, against the default
        equipped rune set and RuneEquipment's cost budget."""
        if None not in self.rune_slots:
            return None
        equipped = {rid for rid in self.rune_slots if rid is not None}
        empty_slot = self.rune_slots.index(None)

        def fits(rune_id: str) -> bool:
            trial = list(self.rune_slots)
            trial[empty_slot] = rune_id
            runes = [r for r in (rune_by_id(rid) for rid in trial if rid is not None) if r is not None]
            try:
                RuneEquipment(runes)
                return True
            except ValueError:
                return False

        by_id: dict[str, Rune] = {r.id: r for r in catalog_runes()}
        candidates = [rid for rid in by_id if rid not in equipped and fits(rid)]
        if not candidates:
            return None
        for rid in DEFAULT_EQUIPPED_IDS:
            if rid in candidates:
                return rid
        return max(candidates, key=lambda rid: by_id[rid].cost)
