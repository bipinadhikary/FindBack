"""Password hashing and persistent, revocable sessions. No external auth service."""
import hashlib
import hmac
import secrets
import time

SESSION_SECONDS = 7 * 24 * 3600
COOKIE = 'findback_session'


def password_hash(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 600_000)
    return f'pbkdf2_sha256$600000${salt}${digest.hex()}'


def password_matches(password, stored):
    _, iterations, salt, expected = stored.split('$')
    actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), int(iterations))
    return hmac.compare_digest(actual.hex(), expected)


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def migrate(db):
    db.execute('''CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE COLLATE NOCASE,
        display_name TEXT NOT NULL, password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user' CHECK(role IN ('user','reception','admin')),
        created_at INTEGER NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS sessions (
        token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
        csrf_token TEXT NOT NULL, expires_at INTEGER NOT NULL)''')
    db.execute('CREATE INDEX IF NOT EXISTS session_user ON sessions(user_id)')
    db.execute('''CREATE TABLE IF NOT EXISTS auth_attempts (
        bucket TEXT NOT NULL, attempted_at INTEGER NOT NULL)''')
    db.execute('CREATE INDEX IF NOT EXISTS auth_attempt_bucket ON auth_attempts(bucket, attempted_at)')
    columns = {row['name'] for row in db.execute('PRAGMA table_info(reports)')}
    if 'owner_id' not in columns:
        db.execute('ALTER TABLE reports ADD COLUMN owner_id TEXT REFERENCES users(id)')
    if 'custom_category' not in columns:
        db.execute('ALTER TABLE reports ADD COLUMN custom_category TEXT')
    for column in ('custody', 'collection_location', 'pickup_instructions'):
        if column not in columns:
            db.execute(f'ALTER TABLE reports ADD COLUMN {column} TEXT')
    db.execute('''CREATE TABLE IF NOT EXISTS report_photos (
        id TEXT PRIMARY KEY, report_id TEXT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
        position INTEGER NOT NULL, image BLOB NOT NULL,
        UNIQUE(report_id, position))''')
    db.execute('''CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY, report_id TEXT NOT NULL REFERENCES reports(id),
        visitor_id TEXT NOT NULL REFERENCES users(id), owner_id TEXT NOT NULL REFERENCES users(id),
        visitor_read INTEGER NOT NULL DEFAULT 0, owner_read INTEGER NOT NULL DEFAULT 0,
        created_at INTEGER NOT NULL, UNIQUE(report_id, visitor_id),
        CHECK(visitor_id != owner_id))''')
    db.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id TEXT NOT NULL REFERENCES conversations(id),
        sender_id TEXT NOT NULL REFERENCES users(id), body TEXT NOT NULL,
        client_id TEXT NOT NULL, created_at INTEGER NOT NULL,
        UNIQUE(conversation_id, sender_id, client_id))''')
    db.execute('CREATE INDEX IF NOT EXISTS message_conversation ON messages(conversation_id, id)')
    db.execute('CREATE INDEX IF NOT EXISTS message_sender_time ON messages(sender_id, created_at)')
    db.execute('CREATE INDEX IF NOT EXISTS conversation_owner ON conversations(owner_id)')
    db.execute('CREATE INDEX IF NOT EXISTS conversation_visitor ON conversations(visitor_id)')
    db.execute('''CREATE TABLE IF NOT EXISTS claims (
        id TEXT PRIMARY KEY, report_id TEXT NOT NULL REFERENCES reports(id),
        claimant_id TEXT NOT NULL REFERENCES users(id), proof TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('pending','approved','rejected','withdrawn','returned','closed')),
        note TEXT NOT NULL DEFAULT '', created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
        UNIQUE(report_id, claimant_id))''')
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS one_approved_claim ON claims(report_id) WHERE status='approved'")
    db.execute('CREATE INDEX IF NOT EXISTS claims_claimant ON claims(claimant_id)')
    db.execute('''CREATE TABLE IF NOT EXISTS claim_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, claim_id TEXT NOT NULL REFERENCES claims(id),
        actor_id TEXT NOT NULL REFERENCES users(id), status TEXT NOT NULL,
        note TEXT NOT NULL, created_at INTEGER NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT, lost_id TEXT NOT NULL REFERENCES reports(id),
        found_id TEXT NOT NULL REFERENCES reports(id), score INTEGER NOT NULL, reasons TEXT NOT NULL,
        UNIQUE(lost_id,found_id))''')
    db.execute('CREATE INDEX IF NOT EXISTS report_matching ON reports(status,category,report_type)')
    db.execute('''CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT, recipient_id TEXT NOT NULL REFERENCES users(id),
        event_key TEXT NOT NULL, kind TEXT NOT NULL, report_id TEXT NOT NULL REFERENCES reports(id),
        resource_id TEXT NOT NULL, text TEXT NOT NULL, match_id INTEGER REFERENCES matches(id),
        created_at INTEGER NOT NULL, read_at INTEGER, UNIQUE(recipient_id,event_key))''')
    db.execute('CREATE INDEX IF NOT EXISTS notification_recipient ON notifications(recipient_id,id)')
    db.execute('PRAGMA user_version = 6')


def new_session(db, user_id):
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    db.execute('DELETE FROM sessions WHERE expires_at <= ?', (int(time.time()),))
    db.execute('INSERT INTO sessions VALUES (?, ?, ?, ?)',
               (token_hash(token), user_id, csrf, int(time.time()) + SESSION_SECONDS))
    return token, csrf


def public_user(row):
    return {key: row[key] for key in ('id', 'email', 'display_name', 'role')}
