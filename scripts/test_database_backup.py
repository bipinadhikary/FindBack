from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from backup_database import backup


class SnapshotTests(unittest.TestCase):
    def test_complete_snapshot_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'source.sqlite3'
            target = Path(folder) / 'backup.sqlite3'
            with closing(sqlite3.connect(source)) as db, db:
                db.execute('CREATE TABLE users (id TEXT, role TEXT)')
                db.execute("INSERT INTO users VALUES ('owner', 'admin')")
                db.execute('CREATE TABLE reports (id TEXT, owner_id TEXT)')
                db.execute("INSERT INTO reports VALUES ('report', 'owner')")
                db.execute('CREATE TABLE report_photos (id TEXT, image BLOB)')
                db.execute('INSERT INTO report_photos VALUES (?, ?)', ('photo', b'photo-bytes'))
                db.execute('CREATE TABLE messages (id INTEGER, body TEXT)')
                db.execute("INSERT INTO messages VALUES (1, 'Private chat sample')")
                db.execute('CREATE TABLE claims (id TEXT, status TEXT)')
                db.execute("INSERT INTO claims VALUES ('claim', 'returned')")
                db.execute('CREATE TABLE claim_events (claim_id TEXT, status TEXT)')
                db.execute("INSERT INTO claim_events VALUES ('claim', 'returned')")
                db.execute('CREATE TABLE matches (lost_id TEXT, found_id TEXT)')
                db.execute("INSERT INTO matches VALUES ('lost', 'found')")
                db.execute('CREATE TABLE notifications (id INTEGER, read_at INTEGER)')
                db.execute('INSERT INTO notifications VALUES (1, 12345)')
            backup(source, target)
            with closing(sqlite3.connect(target)) as db:
                self.assertEqual(db.execute('SELECT * FROM users').fetchall(), [('owner', 'admin')])
                self.assertEqual(db.execute('SELECT * FROM reports').fetchall(), [('report', 'owner')])
                self.assertEqual(db.execute('SELECT * FROM report_photos').fetchall(), [('photo', b'photo-bytes')])
                self.assertEqual(db.execute('SELECT * FROM messages').fetchall(), [(1, 'Private chat sample')])
                self.assertEqual(db.execute('SELECT * FROM claims').fetchall(), [('claim', 'returned')])
                self.assertEqual(db.execute('SELECT * FROM claim_events').fetchall(), [('claim', 'returned')])
                self.assertEqual(db.execute('SELECT * FROM matches').fetchall(), [('lost', 'found')])
                self.assertEqual(db.execute('SELECT * FROM notifications').fetchall(), [(1, 12345)])
            with self.assertRaises(FileExistsError):
                backup(source, target)


if __name__ == '__main__':
    unittest.main()
