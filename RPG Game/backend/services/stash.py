from models.player import Player
from models.item import Item

def add_to_stash(player: Player, item: Item):
    player.stash.append(item)

def get_stash(player: Player):
    return player.stash
