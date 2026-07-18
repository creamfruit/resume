# AI Dungeon RPG

A single-player dungeon-crawler web game: telegraph-and-response combat, procedural loot with rarity tiers, a rune build system, runecrafting (including amplifier runes), an auction house, and trading. Optional Gemini integration generates high-tier item and enemy flavor; without an API key the game uses deterministic fallbacks.

## Requirements

- Python 3.11+ (developed on 3.14)

## Setup and run (Windows PowerShell)

```powershell
cd RPG
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

cd backend
uvicorn main:app --host 127.0.0.1 --port 8000
```

Then open http://127.0.0.1:8000/game in your browser.

Or, after the venv is set up, just run `.\run.ps1` from the `RPG` folder.

> uvicorn must be started **from the `backend` folder** — the code uses top-level imports (`from models.player import Player`).

## Optional: AI-generated content

Copy `.env.example` to `backend\.env` and set `GEMINI_API_KEY` (a `GOOGLE_API_KEY` works too). Check `GET /ai/status` to confirm it is picked up.

## Tests

```powershell
cd backend
python -m unittest discover -s ..\tests -p "test_*.py" -v
```

## Project layout

- `backend/main.py` — FastAPI app: all HTTP endpoints, serves the frontend at `/game`
- `backend/engine/` — combat core, enemy intent (boss AI), passives, status effects, loot, derived stats
- `backend/models/` — Pydantic domain models (Player, Enemy, Item, Passive, Rune, Auction, Dungeon)
- `backend/services/` — dungeon session, stash/equipment, rune system, auction house, trade hub
- `backend/ai/` — Gemini client, item/enemy designers with strict schemas and fallbacks
- `backend/frontend/` — vanilla JS single-page client (`index.html`, `app.js`, `style.css`)
- `backend/database/` — JSON save files, created at runtime
- `tests/` — unittest suite

See `ARCHITECTURE.md` for a system-by-system inventory.
