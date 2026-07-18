# engine/status_effects.py
from __future__ import annotations
from typing import Any, Dict, Tuple

# Status format (stored on player/enemy):
# target.status = {
#   "burn": {"turns": 2, "potency": 6},
#   "weak": {"turns": 2, "potency": 0.20},
#   ...
# }

SUPPORTED = {"burn", "freeze", "weak", "vulnerable", "guard", "bleed"}


def _ensure_status(target: Any) -> Dict:
    s = getattr(target, "status", None)
    if not isinstance(s, dict):
        s = {}
        setattr(target, "status", s)
    return s


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def add_status(target: Any, status_id: str, turns: int, potency: float) -> Dict:
    status_id = str(status_id).lower().strip()
    if status_id not in SUPPORTED:
        return {"applied": False, "reason": f"unsupported_status:{status_id}"}

    s = _ensure_status(target)
    existing = s.get(status_id)

    if isinstance(existing, dict):
        existing_turns = int(existing.get("turns", 0) or 0)
        existing_pot = float(existing.get("potency", 0) or 0)
        s[status_id] = {
            "turns": max(existing_turns, int(turns)),
            "potency": max(existing_pot, float(potency)),
        }
    else:
        s[status_id] = {"turns": int(turns), "potency": float(potency)}

    setattr(target, "status", s)
    return {"applied": True, "status": {status_id: s[status_id]}}


def get_status(target: Any, status_id: str) -> Dict | None:
    s = getattr(target, "status", None)
    if not isinstance(s, dict):
        return None
    v = s.get(status_id)
    return v if isinstance(v, dict) else None


def has_status(target: Any, status_id: str) -> bool:
    st = get_status(target, status_id)
    return bool(st and int(st.get("turns", 0) or 0) > 0)


def apply_outgoing_multiplier(target: Any, dmg: float) -> Tuple[float, Dict]:
    notes = {}
    mult = 1.0

    weak = get_status(target, "weak")
    if weak:
        pot = _clamp(float(weak.get("potency", 0.0) or 0.0), 0.0, 0.6)
        mult *= (1.0 - pot)
        notes["weak"] = pot

    freeze = get_status(target, "freeze")
    if freeze:
        pot = _clamp(float(freeze.get("potency", 0.0) or 0.0), 0.0, 0.6)
        mult *= (1.0 - pot)
        notes["freeze"] = pot

    return dmg * mult, notes


def apply_incoming_multiplier(target: Any, dmg: float) -> Tuple[float, Dict]:
    notes = {}
    mult = 1.0

    vulnerable = get_status(target, "vulnerable")
    if vulnerable:
        pot = _clamp(float(vulnerable.get("potency", 0.0) or 0.0), 0.0, 0.8)
        mult *= (1.0 + pot)
        notes["vulnerable"] = pot

    guard = get_status(target, "guard")
    if guard:
        pot = _clamp(float(guard.get("potency", 0.0) or 0.0), 0.0, 0.8)
        mult *= (1.0 - pot)
        notes["guard"] = pot

    return dmg * mult, notes


def tick_statuses(target: Any) -> Dict:
    s = _ensure_status(target)
    total = 0.0
    ticks = {}

    for status_id in ("burn", "bleed"):
        st = s.get(status_id)
        if isinstance(st, dict) and int(st.get("turns", 0) or 0) > 0:
            pot = float(st.get("potency", 0.0) or 0.0)
            if pot > 0:
                hp = float(getattr(target, "hp", 0.0) or 0.0)
                new_hp = max(0.0, hp - pot)
                setattr(target, "hp", new_hp)
                total += pot
                ticks[status_id] = pot

    for status_id, data in list(s.items()):
        if isinstance(data, dict) and int(data.get("turns", 0) or 0) > 0:
            data["turns"] = int(data["turns"]) - 1
            if data["turns"] <= 0:
                s.pop(status_id, None)

    setattr(target, "status", s)
    return {"total_damage": round(total, 2), "ticks": ticks, "status": s}
