import json
import os
import time
import uuid

from utils.validators import validate_item_payload

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRADE_FILE = os.path.join(BASE_DIR, "database", "trade_requests.json")
TRADE_TTL_SEC = 48 * 60 * 60


def _normalize_account(account: str) -> str:
    cleaned = "".join(ch for ch in str(account or "").strip().lower() if ch.isalnum() or ch in ("_", "-"))
    return cleaned or "default"


def _load_rows() -> list[dict]:
    if not os.path.exists(TRADE_FILE):
        return []
    try:
        with open(TRADE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [row for row in data if isinstance(row, dict)]
    except Exception:
        return []
    return []


def _save_rows(rows: list[dict]) -> None:
    os.makedirs(os.path.dirname(TRADE_FILE), exist_ok=True)
    with open(TRADE_FILE, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=True)


def all_requests() -> list[dict]:
    return _load_rows()


def list_requests(account: str) -> dict:
    account_id = _normalize_account(account)
    rows = _load_rows()
    inbox = []
    outbox = []
    history = []
    for row in sorted(rows, key=lambda x: int(x.get("updated_at", x.get("created_at", 0)) or 0), reverse=True):
        sender = _normalize_account(row.get("sender", ""))
        target = _normalize_account(row.get("target", ""))
        if sender == account_id and str(row.get("status", "pending")) == "pending":
            outbox.append(row)
        elif target == account_id and str(row.get("status", "pending")) == "pending":
            inbox.append(row)
        elif sender == account_id or target == account_id:
            history.append(row)
    accepted = sum(1 for row in history if str(row.get("status", "")) == "accepted")
    declined = sum(1 for row in history if str(row.get("status", "")) == "declined")
    cancelled = sum(1 for row in history if str(row.get("status", "")) == "cancelled")
    expired = sum(1 for row in history if str(row.get("status", "")) == "expired")
    return {
        "inbox": inbox[:12],
        "outbox": outbox[:12],
        "history": history[:16],
        "summary": {
            "pending_inbox": len(inbox),
            "pending_outbox": len(outbox),
            "accepted": accepted,
            "declined": declined,
            "cancelled": cancelled,
            "expired": expired,
            "completed": accepted + declined + cancelled + expired,
        },
    }


def create_request(
    sender: str,
    target: str,
    item_payloads: list[dict],
    gold_offer: int,
    gold_request: int,
    requested_items: list[dict] | None = None,
    note: str = "",
) -> dict:
    sender_id = _normalize_account(sender)
    target_id = _normalize_account(target)
    now = int(time.time())

    offered_items = []
    for payload in list(item_payloads or []):
        try:
            offered_items.append(validate_item_payload(payload).model_dump() if hasattr(validate_item_payload(payload), "model_dump") else validate_item_payload(payload).dict())
        except Exception:
            continue

    requested_payloads = []
    for payload in list(requested_items or []):
        try:
            requested_payloads.append(validate_item_payload(payload).model_dump() if hasattr(validate_item_payload(payload), "model_dump") else validate_item_payload(payload).dict())
        except Exception:
            continue

    row = {
        "id": uuid.uuid4().hex[:12],
        "sender": sender_id,
        "target": target_id,
        "status": "pending",
        "offered_items": offered_items,
        "requested_items": requested_payloads,
        "gold_offer": int(max(0, gold_offer or 0)),
        "gold_request": int(max(0, gold_request or 0)),
        "note": str(note or "")[:180],
        "created_at": now,
        "updated_at": now,
        "expires_at": now + int(TRADE_TTL_SEC),
    }
    rows = _load_rows()
    rows.append(row)
    _save_rows(rows)
    return row


def get_request(trade_id: str) -> dict | None:
    tid = str(trade_id or "").strip()
    if not tid:
        return None
    for row in _load_rows():
        if str(row.get("id", "")) == tid:
            return row
    return None


def update_request(trade_id: str, **changes) -> dict | None:
    tid = str(trade_id or "").strip()
    if not tid:
        return None
    rows = _load_rows()
    for row in rows:
        if str(row.get("id", "")) != tid:
            continue
        row.update(changes)
        row["updated_at"] = int(time.time())
        _save_rows(rows)
        return row
    return None
