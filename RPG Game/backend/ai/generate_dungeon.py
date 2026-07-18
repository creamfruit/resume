from models.dungeon import Dungeon, DungeonRoom
from engine.enemy_factory import create_enemy, create_boss
import random

BOSS_EVERY_N_ROOMS = 5


def _weighted_choice(rng: random.Random, weights: dict[str, int]) -> str:
    pool = [(k, max(0, int(v))) for k, v in dict(weights or {}).items() if int(v or 0) > 0]
    if not pool:
        return "combat"
    total = sum(weight for _, weight in pool)
    pick = rng.randint(1, total)
    running = 0
    for room_type, weight in pool:
        running += weight
        if pick <= running:
            return room_type
    return pool[-1][0]


def _room_from_type(depth: int, risk: int, room_type: str) -> DungeonRoom:
    if room_type == "combat":
        return DungeonRoom(type="combat", enemy=create_enemy(depth, risk))
    return DungeonRoom(type=room_type, enemy=None)


def _slot_room_type(
    slot: int,
    depth: int,
    risk: int,
    rng: random.Random,
    seen: list[str],
) -> str:
    early_depth = depth <= 3
    high_risk = risk >= 4
    extreme_risk = risk >= 6
    counts = {key: seen.count(key) for key in ("combat", "event", "rest", "trap", "treasure", "shrine")}

    if slot == 1:
        weights = {
            "combat": 60 + (risk * 10),
            "event": 18,
            "rest": 18 if early_depth else 10,
            "shrine": 16 if early_depth else 10,
            "treasure": 8,
            "trap": 6 if not high_risk else 12,
        }
        return _weighted_choice(rng, weights)

    if slot == 2:
        weights = {
            "combat": 28 + (risk * 4),
            "event": 24,
            "treasure": 24 + (6 if risk >= 3 else 0),
            "rest": 18 if counts.get("rest", 0) == 0 else 10,
            "shrine": 18 if counts.get("shrine", 0) == 0 else 10,
            "trap": 8 + (risk * 2),
        }
        return _weighted_choice(rng, weights)

    if slot == 3:
        weights = {
            "combat": 42 + (risk * 8),
            "trap": 20 + (risk * 5),
            "event": 18,
            "treasure": 10 + (4 if risk >= 4 else 0),
            "rest": 12 if not high_risk and counts.get("rest", 0) == 0 else 6,
            "shrine": 10 if not high_risk and counts.get("shrine", 0) == 0 else 6,
        }
        return _weighted_choice(rng, weights)

    # Pre-boss room: bias toward recovery for safer runs, pressure/combat for harder runs.
    weights = {
        "combat": 18 + (risk * 10),
        "trap": 8 + (risk * 4),
        "event": 16,
        "treasure": 16 + (8 if high_risk else 0),
        "rest": 24 if not high_risk or counts.get("rest", 0) == 0 else 8,
        "shrine": 20 if not extreme_risk or counts.get("shrine", 0) == 0 else 8,
    }

    room_type = _weighted_choice(rng, weights)
    if high_risk and counts.get("combat", 0) == 0 and room_type not in {"combat", "trap"}:
        return "combat"
    return room_type


def _enforce_cadence(room_types: list[str], depth: int, risk: int) -> list[str]:
    out = list(room_types[:])
    high_risk = risk >= 4

    # Ensure there is at least one recovery pivot on calmer runs.
    if depth <= 3 or risk <= 2:
        if not any(t in {"rest", "shrine"} for t in out):
            out[-1] = "shrine" if risk >= 2 else "rest"

    # Ensure there is at least one payout room before boss.
    if not any(t in {"treasure", "event"} for t in out):
        replace_idx = 1 if len(out) > 1 else 0
        out[replace_idx] = "treasure" if risk >= 2 else "event"

    # Harder runs should still contain real pressure before the boss.
    if high_risk and not any(t in {"combat", "trap"} for t in out):
        out[2 if len(out) > 2 else 0] = "combat"

    # Avoid dead-feeling low risk paths with too many passive rooms.
    if risk <= 1 and sum(1 for t in out if t in {"rest", "shrine", "event"}) >= 3:
        out[0] = "combat"

    return out


def generate_dungeon(depth: int, risk: int) -> Dungeon:
    rng = random.Random()
    room_types: list[str] = []

    for slot in range(1, BOSS_EVERY_N_ROOMS):
        room_types.append(_slot_room_type(slot, depth, risk, rng, room_types))

    room_types = _enforce_cadence(room_types, depth, risk)
    rooms = [_room_from_type(depth, risk, room_type) for room_type in room_types]
    rooms.append(DungeonRoom(type="boss", enemy=create_boss(depth, risk)))

    return Dungeon(
        depth=depth,
        risk=risk,
        rooms=rooms,
        boss_floor=True,
    )
