from models.player import Player
from ai.generate_dungeon import generate_dungeon
from engine.loot import generate_loot
from services.stash import add_to_stash
import random

ROOM_AFFIXES = [
    {
        "id": "shielded",
        "name": "Shielded",
        "desc": "Incoming player damage is partially absorbed.",
    },
    {
        "id": "bloodbound",
        "name": "Bloodbound",
        "desc": "Damaging this enemy hurts the player too.",
    },
    {
        "id": "enraged",
        "name": "Enraged",
        "desc": "Enemy attacks hit harder.",
    },
]

# AUTO MODE (keep this for quick testing)
def run_dungeon(player: Player, risk: int = 0):
    dungeon = generate_dungeon(player.depth, risk)
    combat_logs = []
    boss_defeated = False

    # auto-simulating combat is no longer the main play loop,
    # but we keep it so your old flow still works.
    from engine.combat import simulate_combat

    for room in dungeon.rooms:
        enemy = room.enemy
        result = simulate_combat(player, enemy)

        combat_logs.append({
            "room_type": room.type,
            "enemy": enemy.name,
            "result": result
        })

        if not result["victory"]:
            return {
                "success": False,
                "depth": player.depth,
                "risk": risk,
                "boss_defeated": boss_defeated,
                "player": player,
                "combat": combat_logs,
                "stash": player.stash
            }

        exp_gain = enemy.level * (20 + risk * 10) * (2 if room.type == "boss" else 1)
        player.gain_exp(int(exp_gain))

        if room.type == "boss":
            boss_defeated = True

    loot = []
    loot1 = generate_loot(is_boss=False, risk=risk, luck_bonus=player.loot_luck)
    add_to_stash(player, loot1)
    loot.append(loot1)

    if boss_defeated:
        loot2 = generate_loot(is_boss=True, risk=risk)
        add_to_stash(player, loot2)
        loot.append(loot2)

    player.depth += 1

    return {
        "success": True,
        "depth_cleared": dungeon.depth,
        "next_depth": player.depth,
        "risk": risk,
        "boss_defeated": boss_defeated,
        "loot": loot,
        "player": player,
        "stash": player.stash,
        "combat": combat_logs
    }

# INTERACTIVE MODE HELPERS
def start_interactive_dungeon(player: Player, risk: int):
    dungeon = generate_dungeon(player.depth, risk)

    # store rooms in simple list for session service
    rooms = []
    for r in dungeon.rooms:
        affix = None
        if risk >= 3 and r.type == "combat":
            if random.random() < (0.25 + (risk * 0.08)):
                affix = random.choice(ROOM_AFFIXES)
        elif risk >= 5 and r.type == "boss":
            if random.random() < 0.45:
                affix = random.choice(ROOM_AFFIXES)
        rooms.append({"type": r.type, "enemy": r.enemy, "affix": affix})
    return {"depth": dungeon.depth, "risk": risk, "rooms": rooms}

def complete_interactive_dungeon(player: Player, risk: int, boss_defeated: bool):
    # Reward after interactive clear
    loot = []
    loot1 = generate_loot(is_boss=False, risk=risk, depth=player.depth, luck_bonus=player.loot_luck)
    add_to_stash(player, loot1)
    loot.append(loot1)

    if boss_defeated:
        loot2 = generate_loot(is_boss=True, risk=risk, depth=player.depth, luck_bonus=player.loot_luck)
        add_to_stash(player, loot2)
        loot.append(loot2)

    player.depth += 1

    return {
        "success": True,
        "next_depth": player.depth,
        "boss_defeated": boss_defeated,
        "loot": loot,
        "player": player,
        "stash": player.stash
    }
