"""Minimal persistent economy sidecar for the rebuilt battle system.

`core/player_state.py` stays identity + progression only by design (a
regression test enforces that equipment/stash/rune/economy fields never
migrate onto it). Push-your-luck banking (core/gauntlet.py) still needs
somewhere real to land, so this is that somewhere -- shaped to satisfy
`services/chest.py::grant_chest` and `services/currency.py::add_currency`
(both duck-typed against `.chests` / `.gold` / `.resources`) without
pulling in the legacy `models.player.Player` god-model's stash,
equipment, and rune-loadout fields, none of which the new system has
built yet. When a real inventory/shop phase arrives for the new game,
this is the object it extends -- not a second wallet.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Wallet:
    gold: int = 0
    resources: dict[str, int] = field(default_factory=dict)
    chests: dict[str, int] = field(default_factory=dict)


def wallet_payload(wallet: Wallet) -> dict[str, Any]:
    return {
        "gold": wallet.gold,
        "resources": dict(wallet.resources),
        "chests": dict(wallet.chests),
    }
