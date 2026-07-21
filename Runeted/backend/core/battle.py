"""Core combat loop: enemy move → player response → resolution, one
round at a time.

The enemy's move for the round is never announced to the player ahead
of time — that "telegraph" design (name + effect shown a round before
it resolves) was removed because it made every fight a solved puzzle:
once the exact next move is known, there's always one exact correct
counter. What the player sees instead is the enemy's full move pool
with live cooldown state (`Battle.movelist()` / `core/intent.py`) — a
move just used is briefly unavailable, so play is choosing the best
response to what the enemy *could* do, not what a label says it will.

Round order:
1. The enemy has already picked its move for this round (decided by
   the intent system from whichever of its moves are currently off
   cooldown and affordable) — this is authoritative server state, not
   shown to the player before it resolves.
2. The player responds with one skill from their loadout (or holds).
   A response must be known, off cooldown, and affordable in stamina —
   otherwise it is rejected and nothing about the battle changes.
   Using a skill starts its cooldown and spends stamina whether or not
   it counters. What happens next depends on the skill's kind:
   - attack (or holding): the player's strike lands; a counter match
     negates the enemy move's effect and exposes the enemy next round.
   - defend: no strike; the enemy move's effect is blocked regardless
     of counter tags — only the contact graze can land.
   - dodge: no strike; the whole enemy move is evaded. This goes
     through the same single dodge roll as passive dodge chance.
   - buff: no strike; grants a temporary attack bonus for the next
     `buff_duration` rounds.
   - recovery: no strike; costs 0 stamina and restores stamina, so the
     player always has a legal action.
3. If the player struck and it kills, the battle ends and the enemy's
   move never resolves.
4. The enemy's move resolves (spending enemy stamina). The dodge
   chance comes from DerivedStats plus any rune dodge bonus this round
   (a dodge skill raises it to certainty) and this is the only dodge
   calculation in the game. An uncountered, undodged, unblocked move
   always chips, though a rune shield may absorb the chip.
5. Cooldowns tick, buffs count down, both sides regenerate stamina, and
   the enemy's next move is picked (from whatever is off cooldown and
   affordable; a total lockout falls back to the cheapest move in the
   library as a legal-action guarantee, reported as `downgraded_from`).
   Still not shown to the player — only revealed, after the fact, in
   the round event once it has already resolved.

Passive runes (core/runes.py) hook into the round through the shared
passive engine: battle fires the standard triggers — start_of_turn and
below_hp at round start, on_hit when the player's strike lands,
on_take_hit when the player loses HP to the enemy's move — through
engine/passive_system.resolve_triggered_effects (same models, chances,
thresholds, and limits as item passives). The resolved effects are then
mapped onto battle state here, the one module that owns it: damage_mult
adds to this round's strike, dodge_mod to this round's dodge roll,
shield to an absorb pool that persists until consumed, lifesteal heals
the player from strike damage, thorns reflects a share of damage taken
(an enemy HP decrease, so the enemy-HP invariant is untouched). A round
with no runes equipped fires nothing and draws no rng, so baseline
combat is byte-identical to the pre-rune loop. A lethal hit ends the
round before reactive passives fire, preserving the no-simultaneous-
death rule. Every fired hook is reported in the event's `rune_events`.

Combat reads DerivedStats only — raw player/enemy fields never appear in
the damage math. At default attributes dodge chance is 0, so baseline
combat stays deterministic.

Invariant: enemy HP may never increase unless a named heal/regen/
lifesteal-style event fired that round. Violations are logged with the
named events that fired (or that none did) and raised as errors. No such
effects exist yet, so any increase is a hard bug; later phases must
register their healing effects in the round's `healing_events`.

Each round returns a structured RoundEvent dict (see core/events.py).
"""
from __future__ import annotations

import logging
import random
from typing import Any

from core.events import EnemyTurn, PlayerTurn, ResourceDelta, RoundEvent, StatusChange
from core.intent import Intent, IntentTracker, is_counter
from core.player_state import PlayerState
from core.resolution import Outcome, resolve, summary
from core.runes import RuneEquipment
from core.skills import Skill, SkillLoadout, cooldown_of, default_loadout, stamina_cost_of
from core.stats import StatContribution, compute_player_stats, derive_enemy_stats
from engine.passive_system import resolve_triggered_effects

logger = logging.getLogger("core.battle")

EXPOSED_DAMAGE_BONUS = 0.5
# A dodge skill makes this round's single dodge roll a certainty.
DODGE_SKILL_CHANCE = 1.0
# Passive dodge (pipeline + rune bonuses) can never reach certainty.
DODGE_CHANCE_CAP = 0.35
# Auto-battle spends a counter only on moves at least this dangerous.
AUTO_DANGER_THRESHOLD = 1.0
MAX_ROUNDS = 200
_HP_EPSILON = 1e-6


class Battle:
    def __init__(
        self,
        player: PlayerState,
        enemy: Any,
        loadout: SkillLoadout | None = None,
        runes: RuneEquipment | None = None,
        contributions: tuple[StatContribution, ...] = (),
        rng_seed: int | None = None,
        auto: bool = False,
    ):
        self.player = player
        self.enemy = enemy
        self.loadout = loadout if loadout is not None else default_loadout()
        self.runes = runes if runes is not None else RuneEquipment(())
        self._rune_passives = self.runes.passives()
        self.auto = bool(auto)

        self.stats = compute_player_stats(player, contributions)
        self.enemy_stats = derive_enemy_stats(enemy)

        start_hp = self.stats.max_hp if player.hp is None else min(float(player.hp), self.stats.max_hp)
        self.player_hp = round(start_hp, 2)
        self.enemy_hp = round(float(getattr(enemy, "hp", None) or self.enemy_stats.max_hp), 2)

        start_stamina = self.stats.max_stamina if player.stamina is None else min(float(player.stamina), self.stats.max_stamina)
        self.player_stamina = round(start_stamina, 2)
        enemy_stamina = getattr(enemy, "stamina", None)
        if enemy_stamina is None:
            enemy_stamina = self.enemy_stats.max_stamina
        self.enemy_stamina = round(min(float(enemy_stamina), self.enemy_stats.max_stamina), 2)

        # The tracker draws from the rng for move selection each round;
        # dodge/passive-chance rolls draw from the same stream, so a
        # fixed seed still reproduces a whole battle deterministically.
        self._rng = random.Random(rng_seed)
        self.tracker = IntentTracker(
            getattr(enemy, "archetype", None) or "brute",
            self._rng,
            stamina_budget=self.enemy_stamina,
        )

        self.round_no = 0
        self.rounds: list[dict[str, Any]] = []
        self.outcome = resolve(self.player_hp, self.enemy_hp)
        self._enemy_exposed = False
        # Active temporary bonuses from buff skills:
        # {"status", "attack_mult", "rounds_left", "applied_round"}
        self._buffs: list[dict[str, Any]] = []
        # Rune passive state: a shield pool that persists until consumed,
        # and per-round strike/dodge bonuses reset each round.
        self._player_shield = 0.0
        self._round_strike_bonus = 0.0
        self._round_dodge_bonus = 0.0
        self._enemy_hp_checkpoint = self.enemy_hp

    @property
    def finished(self) -> bool:
        return self.outcome is not Outcome.IN_PROGRESS

    def movelist(self) -> list[dict[str, Any]]:
        """The enemy's full move pool with live cooldown state — see
        core/intent.py:IntentTracker.movelist. Safe to call any time,
        including after the battle has finished. Never reveals which
        specific move is about to resolve, only what's currently off
        cooldown and therefore possible."""
        return self.tracker.movelist()

    def buff_attack_bonus(self) -> float:
        return sum(float(b["attack_mult"]) for b in self._buffs)

    def _fire_runes(self, trigger: str, damage: float = 0.0) -> list[dict[str, Any]]:
        """Fire one passive trigger through the shared passive engine and
        map the resolved effects onto battle state. Returns the fired
        hooks for the round's `rune_events`."""
        if not self._rune_passives:
            return []
        fired = resolve_triggered_effects(
            self._rune_passives,
            trigger,
            source=self.player,
            target=self.enemy,
            context={
                "source_hp": self.player_hp,
                "source_max_hp": self.stats.max_hp,
                "damage": damage,
            },
            rng=self._rng,
        )
        events: list[dict[str, Any]] = []
        for effect in fired:
            entry = {
                "trigger": trigger,
                "passive": effect["passive_name"],
                "type": effect["type"],
                "value": float(effect["value"]),
                "amount": 0.0,
            }
            if effect["type"] == "damage_mult" and effect["target"] == "self":
                self._round_strike_bonus += float(effect["value"])
                entry["amount"] = float(effect["value"])
            elif effect["type"] == "dodge_mod":
                self._round_dodge_bonus += float(effect["value"])
                entry["amount"] = float(effect["value"])
            elif effect["type"] == "shield":
                self._player_shield = round(self._player_shield + float(effect["value"]), 2)
                entry["amount"] = float(effect["value"])
            elif effect["type"] == "lifesteal":
                heal = round(min(float(effect["value"]) * damage, self.stats.max_hp - self.player_hp), 2)
                if heal > 0:
                    self.player_hp = round(self.player_hp + heal, 2)
                entry["amount"] = max(0.0, heal)
            elif effect["type"] == "thorns":
                reflect = round(float(effect["value"]) * damage, 2)
                if reflect > 0:
                    self.enemy_hp = round(max(0.0, self.enemy_hp - reflect), 2)
                entry["amount"] = reflect
            # Other passive-engine effect types (dot, bleed, stat_drain,
            # ...) have no core hook yet; they are reported unapplied so
            # a later phase can wire them without changing the contract.
            events.append(entry)
        return events

    def choose_auto_response(self) -> str | None:
        """Safest available response to the enemy's current (server-
        authoritative, not player-visible) move, if it's dangerous: the
        cheapest matching counter-attack; failing that, the cheapest
        defend/dodge mitigation. Low-danger moves are held through, and
        auto never spends turns on buffs or recovery."""
        intent = self.tracker.current
        if intent.effect_mult < AUTO_DANGER_THRESHOLD:
            return None
        counters = [
            s for s in self.loadout.available()
            if s.kind == "attack" and is_counter(s.counters, intent)
            and stamina_cost_of(s) <= self.player_stamina
        ]
        if counters:
            return min(counters, key=lambda s: (cooldown_of(s), s.id)).id
        mitigations = [
            s for s in self.loadout.available()
            if s.kind in ("defend", "dodge") and stamina_cost_of(s) <= self.player_stamina
        ]
        if mitigations:
            return min(mitigations, key=lambda s: (stamina_cost_of(s), s.id)).id
        return None

    def _validate_response(self, response: str):
        """Reject unknown, cooling, or unaffordable responses before any
        state changes."""
        skill = self.loadout.get(response)
        if skill is None:
            raise ValueError(f"Skill '{response}' is not in the loadout")
        cooling = self.loadout.remaining_cooldown(response)
        if cooling > 0:
            raise ValueError(f"Skill '{response}' is on cooldown for {cooling} more round(s)")
        cost = stamina_cost_of(skill)
        if cost > self.player_stamina:
            raise ValueError(
                f"Skill '{response}' costs {cost} stamina but only {self.player_stamina} is available"
            )
        return skill, cost

    def play_round(self, response: str | None = None) -> dict[str, Any]:
        if self.finished:
            raise RuntimeError("Battle is already resolved")
        self._enforce_enemy_hp_invariant(self._enemy_hp_checkpoint, self.enemy_hp, [], when="between turns")
        intent = self.tracker.current

        if self.auto and response is None:
            response = self.choose_auto_response()

        skill: Skill | None = None
        stamina_spent = 0.0
        if response:
            skill, cost = self._validate_response(response)
            self.loadout.use(response)
            self.player_stamina = round(self.player_stamina - cost, 2)
            stamina_spent = float(cost)

        self.round_no += 1
        php0, ehp0 = self.player_hp, self.enemy_hp
        ps0, es0 = self.player_stamina + stamina_spent, self.enemy_stamina
        healing_events: list[tuple[str, float]] = []  # named heal/regen/lifesteal events this round
        statuses_applied: list[StatusChange] = []
        statuses_removed: list[StatusChange] = []

        # Round-start rune hooks (per-round bonuses reset first; the
        # shield pool persists until consumed).
        self._round_strike_bonus = 0.0
        self._round_dodge_bonus = 0.0
        rune_events: list[dict[str, Any]] = []
        rune_events += self._fire_runes("start_of_turn")
        rune_events += self._fire_runes("below_hp")

        # Holding is a plain strike; only attack skills also strike.
        strikes = skill is None or skill.kind == "attack"
        action = skill.kind if skill else "strike"
        matched = skill is not None and skill.kind == "attack" and is_counter(skill.counters, intent)
        defended = skill is not None and skill.kind == "defend"

        stamina_restored = 0.0
        if skill is not None and skill.kind == "recovery":
            stamina_restored = round(min(float(skill.stamina_restore), self.stats.max_stamina - self.player_stamina), 2)
            self.player_stamina = round(self.player_stamina + stamina_restored, 2)
        if skill is not None and skill.kind == "buff":
            status_name = skill.applies_status.status if skill.applies_status else "empowered"
            # Re-singing a buff refreshes it rather than stacking it.
            self._buffs = [b for b in self._buffs if b["status"] != status_name]
            self._buffs.append({
                "status": status_name,
                "attack_mult": float(skill.buff_attack_mult),
                "rounds_left": int(skill.buff_duration),
                "applied_round": self.round_no,
            })
            statuses_applied.append(StatusChange(
                "player", status_name,
                f"+{skill.buff_attack_mult:.0%} attack for {skill.buff_duration} round(s)",
            ))

        # The exposed status is consumed by the next strike, so it
        # carries over rounds spent defending, dodging, or recovering.
        exposed_bonus = 0.0
        player_damage = 0.0
        if strikes:
            if self._enemy_exposed:
                exposed_bonus = EXPOSED_DAMAGE_BONUS
                self._enemy_exposed = False
                statuses_removed.append(StatusChange("enemy", "exposed", "consumed by player strike"))
            attack = self.stats.attack * (1.0 + exposed_bonus + self.buff_attack_bonus() + self._round_strike_bonus)
            player_damage = round(max(1.0, attack - self.enemy_stats.defense), 2)
            self.enemy_hp = round(max(0.0, self.enemy_hp - player_damage), 2)
            rune_events += self._fire_runes("on_hit", damage=player_damage)

        enemy_resolved = self.enemy_hp > 0.0
        enemy_damage = 0.0
        enemy_stamina_spent = 0.0
        dodged = False
        if enemy_resolved:
            enemy_stamina_spent = float(min(intent.stamina_cost, self.enemy_stamina))
            self.enemy_stamina = round(self.enemy_stamina - enemy_stamina_spent, 2)
            # The single dodge roll: passive chance from the derived-stats
            # pipeline plus this round's rune bonus (capped), raised to
            # certainty by a dodge skill.
            if skill is not None and skill.kind == "dodge":
                dodge_chance = DODGE_SKILL_CHANCE
            else:
                dodge_chance = min(DODGE_CHANCE_CAP, self.stats.dodge_chance + self._round_dodge_bonus)
            dodged = dodge_chance > 0 and self._rng.random() < dodge_chance
            effect_stopped = matched or defended
            if not dodged:
                mult = intent.contact_mult + (0.0 if effect_stopped else intent.effect_mult)
                raw = self.enemy_stats.attack * mult - self.stats.defense
                # A correct counter or a defend may zero the round; an
                # unmitigated, undodged move always chips, though a rune
                # shield may absorb the chip.
                enemy_damage = round(max(0.0 if effect_stopped else 1.0, raw), 2)
                if enemy_damage > 0 and self._player_shield > 0:
                    absorbed = round(min(self._player_shield, enemy_damage), 2)
                    self._player_shield = round(self._player_shield - absorbed, 2)
                    enemy_damage = round(enemy_damage - absorbed, 2)
                    rune_events.append({
                        "trigger": "on_take_hit", "passive": "shield",
                        "type": "shield_absorbed", "value": absorbed, "amount": absorbed,
                    })
                self.player_hp = round(max(0.0, self.player_hp - enemy_damage), 2)
                # Reactive hooks fire only if the hit actually cost HP and
                # the player survived it (a lethal hit ends the round).
                if enemy_damage > 0 and self.player_hp > 0:
                    rune_events += self._fire_runes("on_take_hit", damage=enemy_damage)
            if matched:
                self._enemy_exposed = True
                statuses_applied.append(StatusChange("enemy", "exposed", "takes bonus damage next round"))

        self.outcome = resolve(self.player_hp, self.enemy_hp)
        player_regen = 0.0
        enemy_regen = 0.0
        if not self.finished:
            self.loadout.tick()
            for buff in list(self._buffs):
                if buff["applied_round"] == self.round_no:
                    continue  # buffs start counting down the round after they were sung
                buff["rounds_left"] -= 1
                if buff["rounds_left"] <= 0:
                    self._buffs.remove(buff)
                    statuses_removed.append(StatusChange("player", buff["status"], "expired"))
            player_regen = round(min(self.stats.stamina_regen, self.stats.max_stamina - self.player_stamina), 2)
            self.player_stamina = round(self.player_stamina + player_regen, 2)
            enemy_regen = round(min(self.enemy_stats.stamina_regen, self.enemy_stats.max_stamina - self.enemy_stamina), 2)
            self.enemy_stamina = round(self.enemy_stamina + enemy_regen, 2)
            self.tracker.advance(stamina_budget=self.enemy_stamina)
        else:
            self._write_back()

        self._enforce_enemy_hp_invariant(max(0.0, ehp0 - player_damage), self.enemy_hp, healing_events, when="this round")
        self._enemy_hp_checkpoint = self.enemy_hp

        event = RoundEvent(
            round_no=self.round_no,
            outcome=self.outcome.value,
            player=PlayerTurn(
                action=action,
                response=skill.id if skill else None,
                response_name=skill.name if skill else None,
                matched=matched,
                exposed_bonus_applied=exposed_bonus > 0.0,
                damage_dealt=player_damage,
                stamina_spent=stamina_spent,
                stamina_restored=stamina_restored,
                stamina_regen=player_regen,
                hp=ResourceDelta(php0, self.player_hp),
                stamina=ResourceDelta(ps0, self.player_stamina),
            ),
            enemy=EnemyTurn(
                intent_kind=intent.kind,
                intent_name=intent.name,
                intent_description=intent.description,
                downgraded_from=intent.downgraded_from,
                resolved=enemy_resolved,
                effect_negated=matched or defended,
                dodged=dodged,
                damage_dealt=enemy_damage,
                stamina_spent=enemy_stamina_spent,
                stamina_regen=enemy_regen,
                hp=ResourceDelta(ehp0, self.enemy_hp),
                stamina=ResourceDelta(es0, self.enemy_stamina),
            ),
            statuses_applied=tuple(statuses_applied),
            statuses_removed=tuple(statuses_removed),
            rune_events=tuple(rune_events),
        ).to_dict()
        self.rounds.append(event)
        return event

    def _enforce_enemy_hp_invariant(
        self,
        baseline: float,
        current: float,
        healing_events: list[tuple[str, float]],
        when: str,
    ) -> None:
        """Enemy HP may only rise by explicitly named healing events."""
        allowed = sum(amount for _, amount in healing_events)
        if current > baseline + allowed + _HP_EPSILON:
            fired = ", ".join(f"{name} (+{amount})" for name, amount in healing_events) or "none"
            logger.error(
                "Enemy HP invariant violated %s: %.2f -> %.2f; named healing events fired: %s",
                when, baseline, current, fired,
            )
            raise RuntimeError(
                f"Enemy HP rose {when} ({baseline} -> {current}) with healing events: {fired}"
            )

    def _write_back(self) -> None:
        self.player.hp = self.player_hp
        self.player.stamina = self.player_stamina

    def run_to_completion(self, max_rounds: int = MAX_ROUNDS) -> dict[str, Any]:
        """Drive the battle with the auto-battle policy until it resolves."""
        was_auto = self.auto
        self.auto = True
        try:
            while not self.finished and self.round_no < max_rounds:
                self.play_round()
        finally:
            self.auto = was_auto
        return summary(self.outcome, self.round_no, self.player_hp, self.enemy_hp)
