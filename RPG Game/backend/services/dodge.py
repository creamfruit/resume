from models.player import Player
from models.enemy import Enemy

def resolve_enemy_attack(player: Player, enemy: Enemy, dodge_success: bool) -> dict:
    base = max(1, enemy.attack - player.defense)

    # Base dodge reduction by tier
    if enemy.tier == "boss":
        reduction = 0.35
    elif enemy.elite:
        reduction = 0.55
    else:
        reduction = 0.75

    # Dex bonus adds up to +20% of the reduction effectiveness
    # Example: reduction 0.75 with +0.20 bonus => 0.90 effective reduction cap 0.90
    reduction = min(0.90, reduction + (reduction * player.dodge_bonus))

    if dodge_success:
        damage = int(base * (1 - reduction))
        outcome = "DODGE SUCCESS"
    else:
        damage = base
        outcome = "DODGE FAIL"

    player.hp -= damage

    return {
        "outcome": outcome,
        "base_damage": base,
        "final_damage": damage,
        "player_hp": player.hp,
        "enemy": enemy.name,
        "enemy_tier": enemy.tier,
        "dex_bonus": player.dodge_bonus
    }
