import json
import random
import re
from typing import List

from ai.enemy_schema import AIEnemyDesign
from ai.item_designer import MODEL_NAME
from ai.gemini_client import get_client, has_api_key

_ALLOWED_ARCHETYPES = {"brute", "caster", "skirmisher", "tank", "summoner"}

_BASE_ABILITIES = [
    "Frenzy",
    "Thick Hide",
    "Poison Strike",
    "Shadow Step",
    "Arcane Lash",
    "Bone Spear",
    "Crippling Hex",
    "Bleeding Jab",
    "Guard Break",
    "Howl of Fear",
    "Ember Pulse",
]

_PREFIXES = [
    "Ashen",
    "Hollow",
    "Ravenous",
    "Gloom",
    "Iron",
    "Grim",
    "Rot",
    "Night",
    "Blood",
    "Oathbound",
]

_CORES = [
    "Cultist",
    "Marauder",
    "Warden",
    "Stalker",
    "Sentinel",
    "Reaver",
    "Acolyte",
    "Executioner",
    "Harvester",
    "Beast",
]

_SUFFIXES = ["of Cinders", "of the Pit", "of Hollow Oaths", "of Ruin", "of Black Salt", "of the Mire"]



def _fallback_name(rng: random.Random, tier: str, elite: bool) -> str:
    base = f"{rng.choice(_PREFIXES)} {rng.choice(_CORES)}"
    if rng.random() < 0.35:
        base = f"{base} {rng.choice(_SUFFIXES)}"
    if tier == "boss":
        return f"The {base}"
    if elite:
        return f"Elite {base}"
    return base



def _fallback_abilities(rng: random.Random, tier: str, elite: bool) -> List[str]:
    lo = 1 if (elite or tier == "boss") else 0
    hi = 4 if tier == "boss" else 3
    count = rng.randint(lo, hi)
    if count <= 0:
        return []
    return rng.sample(_BASE_ABILITIES, k=min(count, len(_BASE_ABILITIES)))



def _clean_text(v: str, default: str = "Unknown") -> str:
    t = re.sub(r"\s+", " ", str(v or "")).strip()
    t = re.sub(r"[^a-zA-Z0-9 '\-]", "", t)
    t = t[:48].strip()
    return t or default



def _extract_text(resp) -> str:
    text = getattr(resp, "text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()

    candidates = getattr(resp, "candidates", None)
    if isinstance(candidates, list) and candidates:
        cand = candidates[0]
        content = getattr(cand, "content", None)
        parts = getattr(content, "parts", None)
        if isinstance(parts, list) and parts:
            part_text = getattr(parts[0], "text", None)
            if isinstance(part_text, str):
                return part_text.strip()

    return ""



def _clamp_design(data: AIEnemyDesign, tier: str, elite: bool, rng: random.Random) -> AIEnemyDesign:
    name = _clean_text(data.name, default=_fallback_name(rng, tier=tier, elite=elite))
    archetype = str(data.archetype or "").lower().strip()
    if archetype not in _ALLOWED_ARCHETYPES:
        archetype = rng.choice(sorted(_ALLOWED_ARCHETYPES))

    abilities = []
    seen = set()
    for raw in (data.abilities or []):
        cleaned = _clean_text(raw, default="")
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        abilities.append(cleaned)

    max_abilities = 5 if tier == "boss" else 4
    if len(abilities) > max_abilities:
        abilities = abilities[:max_abilities]

    if not abilities and (elite or tier == "boss"):
        abilities = _fallback_abilities(rng, tier=tier, elite=elite)

    trait = _clean_text(data.trait, default="")[:80]

    return AIEnemyDesign(name=name, archetype=archetype, abilities=abilities, trait=trait)



def design_enemy_with_ai(depth: int, risk: int, tier: str, elite: bool, rng_seed: int | None = None) -> AIEnemyDesign:
    rng = random.Random(rng_seed)

    fallback = AIEnemyDesign(
        name=_fallback_name(rng, tier=tier, elite=elite),
        archetype=rng.choice(sorted(_ALLOWED_ARCHETYPES)),
        abilities=_fallback_abilities(rng, tier=tier, elite=elite),
        trait="",
    )

    if not has_api_key():
        return fallback

    prompt = f"""
Return ONE enemy as strict JSON only (no markdown).

Context:
- Dark fantasy dungeon crawler.
- Depth: {depth}
- Risk: {risk}
- Tier: {tier}
- Elite: {elite}

Output schema:
{{
  "name": "string",
  "archetype": "brute|caster|skirmisher|tank|summoner",
  "abilities": ["string", "string"],
  "trait": "short flavor trait"
}}

Rules:
- Keep names grounded and menacing.
- Abilities should read like RPG move names.
- No numbers.
- No lore dumps.
- Return only JSON.
""".strip()

    try:
        client = get_client()
        resp = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        text = _extract_text(resp)
        parsed = AIEnemyDesign(**json.loads(text))
        return _clamp_design(parsed, tier=tier, elite=elite, rng=rng)
    except Exception:
        return fallback
