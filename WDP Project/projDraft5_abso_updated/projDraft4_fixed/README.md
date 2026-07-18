# Re:Connect SG (prototype)

## Run locally

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the server:

```bash
python run.py
```

Open the site:
- http://127.0.0.1:3000

## Database

- SQLite database file is created at `instance/reconnect.db`.
- Signup saves a new user in the `users` table.
- Onboarding saves the selected options in the `user_settings` table under the key `onboarding`.

## Notes

- This is a prototype. Sessions are stored in a signed cookie.
- If you delete `instance/reconnect.db`, the database will be recreated on the next run.

## Backups

Run:

```bash
python scripts/backup_databases.py --source instance --dest backups
```

This creates a timestamped folder with copies of all `.db` files.

## CI

GitHub Actions CI is defined in `.github/workflows/ci.yml` and runs:
- `python -m py_compile run.py`
- `pytest -q`
