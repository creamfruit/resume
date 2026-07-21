from models.player import Player

def equip_item(player: Player, stash_index: int):
    if stash_index < 0 or stash_index >= len(player.stash):
        return {"error": "Invalid stash index"}

    item = player.stash[stash_index]
    slot = item.slot

    # Unequip old item
    if player.equipment[slot]:
        player.stash.append(player.equipment[slot])

    player.equipment[slot] = item
    player.stash.pop(stash_index)

    return {
        "message": f"Equipped {item.name}",
        "equipment": player.equipment
    }

def unequip_item(player: Player, slot: str):
    if slot not in player.equipment or not player.equipment[slot]:
        return {"error": "Nothing equipped in that slot"}

    item = player.equipment[slot]
    player.stash.append(item)
    player.equipment[slot] = None

    return {
        "message": f"Unequipped {item.name}",
        "equipment": player.equipment
    }
