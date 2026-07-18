import random
from models.enemy import Enemy
from ai.enemy_designer import design_enemy_with_ai

ARCHETYPE_BASE = {
    "brute": {"hp": 1.25, "atk": 1.10, "def": 0.90, "crit": 0.03},
    "caster": {"hp": 0.90, "atk": 1.25, "def": 0.85, "crit": 0.05},
    "skirmisher": {"hp": 0.95, "atk": 1.05, "def": 0.90, "crit": 0.08},
    "tank": {"hp": 1.45, "atk": 0.95, "def": 1.25, "crit": 0.02},
    "summoner": {"hp": 1.00, "atk": 1.00, "def": 1.00, "crit": 0.04},
}

ELITE_VARIANTS = {
    "brute": ["crusher", "berserker"],
    "caster": ["hexweaver", "stormcaller"],
    "skirmisher": ["shadowstep", "venomrunner"],
    "tank": ["bulwark", "ironhide"],
    "summoner": ["broodlord", "bonecaller"],
}


def elite_chance(depth: int, risk: int) -> float:
    base = 0.04
    curve = (depth * 0.006) + (risk * 0.028)
    return min(0.40, base + curve)



def _variance(rng: random.Random, lo: float = 0.88, hi: float = 1.22) -> float:
    return rng.uniform(lo, hi)



def _base_stat_block(depth: int, risk: int, elite: bool, boss: bool, rng: random.Random) -> tuple[int, int]:
    if boss:
        hp = int((230 + depth * 60 + risk * 28) * _variance(rng, 0.95, 1.22))
        atk = int((24 + depth * 7 + risk * 4) * _variance(rng, 0.92, 1.20))
    else:
        hp = int((36 + depth * 16 + risk * 11) * _variance(rng, 0.90, 1.25))
        atk = int((7 + depth * 3 + risk * 2) * _variance(rng, 0.88, 1.22))

    early_depth = max(0, 3 - max(1, int(depth)))
    if early_depth > 0:
        # Smooth the first few runs so the player can learn dodge/loadout flow
        # before enemy damage spikes too hard.
        hp *= (1.0 - (0.05 * early_depth))
        atk *= (1.0 - (0.09 * early_depth))
        if boss:
            atk *= 0.95

    if elite:
        hp = int(hp * rng.uniform(1.35, 1.75))
        atk = int(atk * rng.uniform(1.25, 1.60))

    return max(20, hp), max(4, atk)



def _apply_archetype_stats(archetype: str, hp: int, atk: int, rng: random.Random, boss: bool) -> tuple[int, int, int, float]:
    mods = ARCHETYPE_BASE.get(archetype, ARCHETYPE_BASE["brute"])
    hp_out = int(hp * mods["hp"] * _variance(rng, 0.95, 1.10))
    atk_out = int(atk * mods["atk"] * _variance(rng, 0.95, 1.12))

    base_def = 2 + (hp_out // 70)
    defense = int(base_def * mods["def"] * _variance(rng, 0.85, 1.25))
    defense = max(0, min(60 if boss else 40, defense))

    crit = float(mods["crit"] + rng.uniform(0.0, 0.04))
    crit = max(0.01, min(0.20 if boss else 0.14, crit))

    return max(1, hp_out), max(1, atk_out), defense, round(crit, 3)



def create_enemy(depth: int, risk: int) -> Enemy:
    rng = random.Random()
    is_elite = rng.random() < elite_chance(depth, risk)

    design = design_enemy_with_ai(depth=depth, risk=risk, tier="elite" if is_elite else "normal", elite=is_elite)
    hp, atk = _base_stat_block(depth, risk, elite=is_elite, boss=False, rng=rng)
    hp, atk, defense, crit = _apply_archetype_stats(design.archetype, hp, atk, rng=rng, boss=False)

    level = max(1, depth + risk + (2 if is_elite else 0) + rng.randint(0, 2))
    name = design.name
    if is_elite and not name.lower().startswith("elite"):
        name = f"Elite {name}"

    abilities = design.abilities or []
    combat_mods = {}
    if is_elite:
        variants = ELITE_VARIANTS.get(design.archetype, ["veteran"])
        variant = rng.choice(variants)
        combat_mods["elite_variant"] = variant
        if variant == "crusher":
            abilities = abilities + ["Crushing Followthrough"]
        elif variant == "berserker":
            abilities = abilities + ["Rage Burst"]
        elif variant == "hexweaver":
            abilities = abilities + ["Hex Pulse"]
        elif variant == "stormcaller":
            abilities = abilities + ["Static Charge"]
        elif variant == "shadowstep":
            abilities = abilities + ["Slip Counter"]
        elif variant == "venomrunner":
            abilities = abilities + ["Venom Cut"]
        elif variant == "bulwark":
            abilities = abilities + ["Bulwark Plating"]
        elif variant == "ironhide":
            abilities = abilities + ["Ironhide"]
        elif variant == "broodlord":
            abilities = abilities + ["Brood Swarm"]
        elif variant == "bonecaller":
            abilities = abilities + ["Bone Harvest"]

    return Enemy(
        name=name,
        level=level,
        hp=hp,
        max_hp=hp,
        attack=atk,
        abilities=abilities,
        elite=is_elite,
        tier="elite" if is_elite else "normal",
        archetype=design.archetype,
        defense=defense,
        crit_chance=crit,
        combat_mods=combat_mods,
    )



def create_boss(depth: int, risk: int) -> Enemy:
    rng = random.Random()
    design = design_enemy_with_ai(depth=depth, risk=risk, tier="boss", elite=False)

    hp, atk = _base_stat_block(depth, risk, elite=True, boss=True, rng=rng)
    hp, atk, defense, crit = _apply_archetype_stats(design.archetype, hp, atk, rng=rng, boss=True)

    level = max(1, depth + risk + 4 + rng.randint(0, 2))
    name = design.name if design.name.lower().startswith("the ") else f"The {design.name}"

    abilities = design.abilities or []
    if len(abilities) < 2:
        extra = ["Cataclysm Roar", "Soul Rend", "Abyssal Pulse", "Dark Reprisal"]
        while len(abilities) < 2:
            pick = rng.choice(extra)
            if pick not in abilities:
                abilities.append(pick)

    return Enemy(
        name=name,
        level=level,
        hp=hp,
        max_hp=hp,
        attack=atk,
        abilities=abilities[:5],
        elite=False,
        tier="boss",
        archetype=design.archetype,
        defense=defense,
        crit_chance=crit,
    )
