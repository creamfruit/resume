ABILITY_EFFECTS = {
    "Frenzy": {"attack_bonus": 2},
    "Thick Hide": {"defense_bonus": 2},
    "Poison Strike": {"dot": 2}
}

def apply_abilities(enemy, player):
    damage_over_time = 0

    for ability in enemy.abilities:
        effect = ABILITY_EFFECTS.get(ability)

        if not effect:
            continue

        if "attack_bonus" in effect:
            enemy.attack += effect["attack_bonus"]

        if "dot" in effect:
            damage_over_time += effect["dot"]

    return damage_over_time
