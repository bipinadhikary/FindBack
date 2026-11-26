"""Create a complete local SQLite snapshot, including accounts and sessions."""
import argparse
import os
from pathlib import Path
import sqlite3


def backup(source, destination):
    # Exclusive creation prevents an existing backup from being overwritten.
    with destination.open('xb'):
        pass
    reader = writer = None
    try:
        reader = sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True)
        writer = sqlite3.connect(destination)
        reader.backup(writer)
        if writer.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise RuntimeError('Backup integrity check failed')
    finally:
        if writer is not None:
            writer.close()
        if reader is not None:
            reader.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[1]
    parser.add_argument('destination', type=Path)
    parser.add_argument('--database', type=Path, default=Path(os.environ.get(
        'FINDBACK_DB_PATH', str(root / 'data' / 'findback.sqlite3'))))
    args = parser.parse_args()
    backup(args.database, args.destination)
    print('Complete SQLite snapshot created and integrity checked.')


if __name__ == '__main__':
    main()
