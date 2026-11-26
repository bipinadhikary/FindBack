"""Explicit server-owner action: promote an existing account, never first-signup admin."""
import argparse
import os
from pathlib import Path
import sqlite3


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('email', help='Existing account belonging to the administrator')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    path = Path(os.environ.get('FINDBACK_DB_PATH', str(root / 'data' / 'findback.sqlite3')))
    db = sqlite3.connect(path.resolve().as_uri() + '?mode=rw', uri=True)
    try:
        with db:
            updated = db.execute("UPDATE users SET role = 'admin' WHERE email = ? COLLATE NOCASE", (args.email.strip(),))
            if updated.rowcount != 1:
                raise SystemExit('Account not found. Register the intended account first.')
        print('Administrator access assigned. Refresh the app to see reception management.')
    finally:
        db.close()


if __name__ == '__main__':
    main()
