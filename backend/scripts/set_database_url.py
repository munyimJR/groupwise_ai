"""Point backend/.env at a Postgres database (e.g. the Supabase pooler) without typing the password into a file.

    python backend/scripts/set_database_url.py "postgresql://postgres.<ref>:[YOUR-PASSWORD]@<host>:5432/postgres"

The password is read with a hidden prompt, percent-encoded, tested with a real connection, and only then
written to backend/.env as DATABASE_URL (the previous DATABASE_URL line is commented out, not deleted).
"""
from __future__ import annotations

import getpass
import sys
from pathlib import Path
from urllib.parse import quote

import psycopg

ENV = Path(__file__).resolve().parents[1] / ".env"
PLACEHOLDER = "[YOUR-PASSWORD]"


def main() -> int:
    if len(sys.argv) != 2 or PLACEHOLDER not in sys.argv[1]:
        print(__doc__)
        return 2
    password = getpass.getpass("Database password (hidden): ")
    if not password:
        print("No password entered; nothing changed.")
        return 1
    url = sys.argv[1].replace(PLACEHOLDER, quote(password, safe=""))
    try:
        with psycopg.connect(url, connect_timeout=10, prepare_threshold=None) as conn:
            version = conn.execute("select version()").fetchone()[0]
    except Exception as exc:  # report the reason without echoing the password
        print("Connection failed:", str(exc).replace(password, "***").replace(quote(password, safe=""), "***"))
        return 1
    print("Connected:", version.split(",")[0])

    lines = ENV.read_text(encoding="utf-8").splitlines() if ENV.exists() else []
    out = [f"# {line}" if line.startswith("DATABASE_URL=") else line for line in lines]
    out.append(f"DATABASE_URL={url}")
    ENV.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"Saved DATABASE_URL to {ENV}. Restart the API to use it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
