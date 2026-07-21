from engine.enemy_factory import scale_enemy
from engine.ability_registry import ABILITY_REGISTRY

def compile_dungeon(dungeon_ai, depth: int):
    compiled_rooms = []

    for room in dungeon_ai.rooms:
        compiled = {
            "type": room.type,
            "theme": room.theme,
            "enemies": []
        }

        if room.enemies:
            for enemy in room.enemies:
                stats = scale_enemy(depth, enemy.archetype)

                abilities = []
                for a in enemy.abilities:
                    key = a.lower()
                    if key in ABILITY_REGISTRY:
                        abilities.append(ABILITY_REGISTRY[key])

                compiled["enemies"].append({
                    "name": enemy.name,
                    "archetype": enemy.archetype,
                    "stats": stats,
                    "abilities": abilities
                })

        compiled_rooms.append(compiled)

    return {
        "theme": dungeon_ai.dungeon_theme,
        "rooms": compiled_rooms
    }
