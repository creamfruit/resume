import json
import random

from ai.gemini_client import get_client, has_api_key
from ai.item_schema import AIDesignedItem
from engine.passive_system import clamp_passives

# Balance clamps (VERY IMPORTANT)
RARITY_DAMAGE_BOUNDS = {
    "legendary": (35, 55),
    "mythic": (55, 80),
    "relic": (80, 105),
}

MODEL_NAME = "gemini-2.5-flash-lite"


def _clamp_item(ai_item: AIDesignedItem) -> AIDesignedItem:
    lo, hi = RARITY_DAMAGE_BOUNDS[ai_item.rarity]
    ai_item.damage = max(lo, min(hi, int(ai_item.damage)))

    ai_item.passives = clamp_passives(ai_item.passives, ai_item.rarity)

    return ai_item


def _fallback_item(slot: str, rarity: str) -> AIDesignedItem:
    lo, hi = RARITY_DAMAGE_BOUNDS[rarity]
    dmg = random.randint(lo, hi)
    return AIDesignedItem(
        name=f"{rarity.title()} {slot.title()}",
        slot=slot,
        rarity=rarity,
        damage=dmg,
        passives=[],
        flavor="",
    )


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


def design_item_with_ai(slot: str, rarity: str, risk: int, depth: int, luck_bonus: float) -> AIDesignedItem:
    if not has_api_key():
        return _fallback_item(slot, rarity)

    client = get_client()

    prompt = f"""
Return ONE item as JSON ONLY (no markdown).

Context:
- Dungeon RPG (D&D-ish).
- Slot: {slot}
- Rarity: {rarity}
- Dungeon depth: {depth}
- Risk: {risk}
- Player luck bonus: {luck_bonus}

Output schema:
{{
  "name": "string",
  "slot": "weapon" | "armor",
  "rarity": "legendary" | "mythic" | "relic",
  "damage": int,
  "passives": [
    {{
      "name": "string",
      "trigger": "on_hit|on_take_hit|on_kill|on_dodge|below_hp|start_of_turn|end_of_turn",
      "chance": number,
      "threshold": number,
      "effects": [
        {{
          "type": "damage_mult|shield|lifesteal|bleed|dot|thorns|dodge_mod|self_damage|stat_drain|enemy_buff",
          "value": number,
          "target": "self|enemy",
          "chance": number,
          "duration": int,
          "stacks": int,
          "stat": "str|dex|int|vit|luck",
          "scaling": "flat|percent"
        }}
      ],
      "cursed": boolean
    }}
  ],
  "flavor": "short string"
}}

Notes:
- Passives can be strong buffs OR cursed tradeoffs (self_damage, stat_drain, enemy_buff).
- Make passives thematic and synergistic; do not create overpowered combos.
- Use 1-3 effects per passive max.
- Return ONLY JSON.
""".strip()

    resp = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
    )

    text = _extract_text(resp)
    data = json.loads(text)
    try:
        ai_item = AIDesignedItem(**data)
        return _clamp_item(ai_item)
    except Exception:
        return _fallback_item(slot, rarity)
