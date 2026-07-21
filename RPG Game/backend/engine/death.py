from __future__ import annotations

from typing import Any, Dict


def resolve_battle_outcome(player: Any, enemy: Any) -> Dict[str, Any]:
    player_hp = float(getattr(player, "hp", 0.0) or 0.0)
    enemy_hp = float(getattr(enemy, "hp", 0.0) or 0.0)

    if enemy_hp <= 0.0 and player_hp > 0.0:
        return {"winner": "player", "reason": "enemy_defeated", "player_hp": player_hp, "enemy_hp": enemy_hp}
    if player_hp <= 0.0 and enemy_hp > 0.0:
        return {"winner": "enemy", "reason": "player_defeated", "player_hp": player_hp, "enemy_hp": enemy_hp}
    if enemy_hp <= 0.0 and player_hp <= 0.0:
        return {"winner": "draw", "reason": "simultaneous_defeat", "player_hp": player_hp, "enemy_hp": enemy_hp}
    return {"winner": "pending", "reason": "battle_continues", "player_hp": player_hp, "enemy_hp": enemy_hp}
