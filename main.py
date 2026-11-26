"""FindBack's local report API, SQLite storage, and static web interface."""

from contextlib import asynccontextmanager, contextmanager
from datetime import date
import os
from pathlib import Path
import sqlite3
import re
import secrets
import time
import json
from enum import Enum
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Request, Response, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from accounts import COOKIE, SESSION_SECONDS, migrate, new_session, password_hash, password_matches, token_hash, public_user
from photos import prepare_photo, MAX_ENCODED_LENGTH
from chat import chat_router
from claims import claims_router
from matching import matching_router, sync_matches
from activity import activity_router

ROOT = Path(__file__).resolve().parent
CATEGORY_GROUPS = json.loads((ROOT / 'static' / 'categories.json').read_text(encoding='utf-8'))
Category = Enum('Category', {item['value'].replace(' ', '_'): item['value']
                            for group in CATEGORY_GROUPS for item in group['items']}, type=str)
DB_PATH = Path(
    os.environ.get("FINDBACK_DB_PATH", str(ROOT / "data" / "findback.sqlite3"))
)


@contextmanager
def connect():
    """Commit successful operations and always close the request's connection."""
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    try:
        with connection:
            yield connection
    finally:
        connection.close()


@asynccontextmanager
async def lifespan(app):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                report_type TEXT NOT NULL,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                location TEXT NOT NULL,
                date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open'
            )
        """)
        migrate(db)
        for report in db.execute("SELECT * FROM reports WHERE status='open' AND report_type='lost' AND owner_id IS NOT NULL").fetchall():
            sync_matches(db, report)
    yield


app = FastAPI(
    title="FindBack",
    description="Campus lost-and-found platform with rule-based matching",
    version="0.1.0",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

# Login and registration also require same-origin JSON to prevent login CSRF.
@app.middleware('http')
async def browser_security(request: Request, call_next):
    if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
        origin = request.headers.get('origin')
        expected_origin = str(request.base_url).rstrip('/')
        if request.headers.get('sec-fetch-site') == 'cross-site' or (origin and origin != expected_origin):
            return JSONResponse({'detail': 'Cross-site request rejected'}, status_code=403)
        if request.headers.get('content-type', '').split(';')[0].strip() != 'application/json':
            return JSONResponse({'detail': 'JSON required'}, status_code=415)
        # Enforce a streamed bound even without a Content-Length header.
        chunks, total = [], 0
        limit = 21 * 1024 * 1024 if request.url.path == '/reports' else 64 * 1024
        async for chunk in request.stream():
            total += len(chunk)
            if total > limit:
                return JSONResponse({'detail': 'Request is too large'}, status_code=413)
            chunks.append(chunk)
        request._body = b''.join(chunks)
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
    return response


def current_user(request: Request):
    token = request.cookies.get(COOKIE, '')
    with connect() as db:
        user = db.execute('''SELECT users.*, sessions.csrf_token FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token_hash = ? AND sessions.expires_at > ?''',
            (token_hash(token), int(time.time()))).fetchone()
    if user is None:
        raise HTTPException(401, 'Please sign in')
    if request.method not in {'GET', 'HEAD', 'OPTIONS'}:
        if not secrets.compare_digest(request.headers.get('x-csrf-token', ''), user['csrf_token']):
            raise HTTPException(403, 'Invalid session verification token')
    return dict(user)


def administrator(user=Depends(current_user)):
    if user['role'] != 'admin':
        raise HTTPException(403, 'Administrator access required')
    return user


app.include_router(chat_router(connect, current_user))
app.include_router(claims_router(connect, current_user))
app.include_router(matching_router(connect, current_user))
app.include_router(activity_router(connect, current_user))


class Credentials(BaseModel):
    model_config = ConfigDict(extra='forbid')
    email: str = Field(max_length=254)
    password: str = Field(min_length=12, max_length=128)

    @field_validator('email')
    @classmethod
    def normalize_email(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
            raise ValueError('Enter a valid email address')
        return value


class Registration(Credentials):
    display_name: str = Field(min_length=1, max_length=80)

    @field_validator('display_name')
    @classmethod
    def normalize_name(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('Enter your name')
        return value


def throttle(request, email):
    ip = request.client.host if request.client else 'unknown'
    buckets = [(token_hash(ip), 60), (token_hash(ip + ':' + email), 10)]
    now = int(time.time())
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('DELETE FROM auth_attempts WHERE attempted_at < ?', (now - 300,))
        for bucket, limit in buckets:
            count = db.execute('SELECT count(*) FROM auth_attempts WHERE bucket = ?', (bucket,)).fetchone()[0]
            if count >= limit:
                raise HTTPException(429, 'Too many attempts. Try again in five minutes.', headers={'Retry-After': '300'})
        db.executemany('INSERT INTO auth_attempts VALUES (?, ?)', [(b, now) for b, _ in buckets])


def signed_in(db, user, response, previous_token=''):
    if previous_token:
        db.execute('DELETE FROM sessions WHERE token_hash = ?', (token_hash(previous_token),))
    token, csrf = new_session(db, user['id'])
    response.set_cookie(COOKIE, token, max_age=SESSION_SECONDS, httponly=True,
                        secure=os.environ.get('FINDBACK_SECURE_COOKIE', '0') == '1',
                        samesite='strict', path='/')
    return {'user': public_user(user), 'csrf_token': csrf}


@app.post('/auth/register', status_code=201)
def register(data: Registration, request: Request, response: Response):
    throttle(request, data.email)
    hashed = password_hash(data.password)
    with connect() as db:
        try:
            db.execute('INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)',
                       (str(uuid4()), data.email, data.display_name, hashed, 'user', int(time.time())))
        except sqlite3.IntegrityError:
            raise HTTPException(409, 'An account with that email already exists') from None
        user = db.execute('SELECT * FROM users WHERE email = ?', (data.email,)).fetchone()
        return signed_in(db, user, response, request.cookies.get(COOKIE, ''))


@app.post('/auth/login')
def login(data: Credentials, request: Request, response: Response):
    throttle(request, data.email)
    with connect() as db:
        user = db.execute('SELECT * FROM users WHERE email = ?', (data.email,)).fetchone()
        # Perform the same expensive hash operation even for unknown email addresses.
        stored = user['password_hash'] if user else 'pbkdf2_sha256$600000$' + '00' * 16 + '$' + '00' * 32
        if not password_matches(data.password, stored) or user is None:
            raise HTTPException(401, 'Incorrect email or password')
        return signed_in(db, user, response, request.cookies.get(COOKIE, ''))


@app.get('/auth/me')
def me(user=Depends(current_user)):
    return {'user': public_user(user), 'csrf_token': user['csrf_token']}


@app.post('/auth/logout', status_code=204)
def logout(request: Request, response: Response, user=Depends(current_user)):
    with connect() as db:
        db.execute('DELETE FROM sessions WHERE token_hash = ?', (token_hash(request.cookies.get(COOKIE, '')),))
    response.delete_cookie(COOKIE, path='/')


@app.get('/admin/users')
def users(user=Depends(administrator)):
    with connect() as db:
        return [public_user(row) for row in db.execute('SELECT * FROM users ORDER BY email')]


class RoleChange(BaseModel):
    model_config = ConfigDict(extra='forbid')
    role: Literal['user', 'reception']


@app.patch('/admin/users/{user_id}/role')
def change_role(user_id: str, data: RoleChange, user=Depends(administrator)):
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        target = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        if target is None:
            raise HTTPException(404, 'Account not found')
        if target['role'] == 'admin':
            raise HTTPException(400, 'Administrator accounts cannot be changed here')
        db.execute('UPDATE users SET role = ? WHERE id = ?', (data.role, user_id))
        return public_user(db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone())


class ReportFields(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    report_type: Literal["lost", "found"]
    title: str = Field(min_length=3, max_length=100)
    category: Category
    custom_category: str | None = Field(default=None, max_length=80)
    description: str = Field(min_length=10, max_length=2000)
    location: str = Field(min_length=2, max_length=200)
    date: date
    custody: Literal['finder', 'reception'] | None = None
    collection_location: str | None = Field(default=None, min_length=2, max_length=200)
    pickup_instructions: str | None = Field(default=None, min_length=2, max_length=500)

    @model_validator(mode='after')
    def validate_custom_category(self):
        if self.category == 'other':
            if not self.custom_category or len(self.custom_category) < 2:
                raise ValueError('For Other, enter an item type (2–80 characters)')
        elif self.custom_category:
            raise ValueError('Custom item type is only allowed for Other')
        else:
            self.custom_category = None
        return self

    @field_validator("date")
    @classmethod
    def validate_date(cls, value):
        if value > date.today():
            raise ValueError("Date cannot be in the future")
        return value


class PhotoUpload(BaseModel):
    model_config = ConfigDict(extra='forbid')
    data: str = Field(min_length=1, max_length=MAX_ENCODED_LENGTH)


class ReportCreate(ReportFields):
    photos: list[PhotoUpload] = Field(default_factory=list, max_length=3)

    @model_validator(mode='after')
    def validate_pickup(self):
        if self.report_type == 'lost':
            if self.custody or self.collection_location or self.pickup_instructions:
                raise ValueError('Pickup details only apply to found items')
        else:
            if self.custody is None:
                self.custody = 'finder'
            if self.custody == 'reception' and not self.collection_location:
                raise ValueError('Reception-held items need a collection location')
        return self


class PhotoInfo(BaseModel):
    id: str
    url: str


class Report(ReportFields):
    id: str
    status: Literal["open", "resolved"] = "open"
    owner_id: str | None = None
    photos: list[PhotoInfo] = Field(default_factory=list)


def report_with_photos(db, row):
    report = dict(row)
    report['photos'] = [
        {'id': photo['id'], 'url': f"/reports/{row['id']}/photos/{photo['id']}"}
        for photo in db.execute('SELECT id FROM report_photos WHERE report_id = ? ORDER BY position', (row['id'],))
    ]
    return report


@app.get("/")
def home():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/reports", response_model=Report, status_code=201)
def create_report(data: ReportCreate, user=Depends(current_user)):
    if data.custody == 'reception' and user['role'] not in {'reception', 'admin'}:
        raise HTTPException(403, 'Only reception staff can post reception-held items')
    # Validate every image before inserting anything, so a failed upload leaves no partial report.
    images = [prepare_photo(photo.data) for photo in data.photos]
    report = Report(id=str(uuid4()), owner_id=user['id'], **data.model_dump(exclude={'photos'}))
    values = report.model_dump(mode="json", exclude={'photos'})
    with connect() as db:
        db.execute("""
            INSERT INTO reports (
                id, report_type, title, category, description, location, date, status, owner_id, custom_category,
                custody, collection_location, pickup_instructions
            ) VALUES (
                :id, :report_type, :title, :category, :description, :location, :date, :status, :owner_id, :custom_category,
                :custody, :collection_location, :pickup_instructions
            )
        """, values)
        for position, image in enumerate(images):
            db.execute('INSERT INTO report_photos VALUES (?, ?, ?, ?)', (str(uuid4()), report.id, position, image))
        sync_matches(db, values)
        return report_with_photos(db, values)


@app.get("/reports", response_model=list[Report])
def list_reports(
    report_type: Literal["lost", "found"] | None = None,
    category: Category | None = None,
    q: str = Query(default="", max_length=200),
    status: Literal['open', 'resolved'] | None = None,
    user=Depends(current_user),
):
    clauses, params = [], []
    for column, value in (("report_type", report_type), ("category", category), ("status", status)):
        if value:
            clauses.append(f"{column} = ?")
            params.append(value)
    if q.strip():
        clauses.append(
            "instr(lower(title || ' ' || description || ' ' || location || ' ' || coalesce(custom_category, '') || ' ' || coalesce(collection_location, '')), lower(?)) > 0"
        )
        params.append(q.strip())
    sql = "SELECT * FROM reports"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    with connect() as db:
        rows = db.execute(sql + " ORDER BY date DESC, rowid DESC", params)
        return [report_with_photos(db, row) for row in rows]


@app.get("/reports/{report_id}", response_model=Report)
def get_report(report_id: str, user=Depends(current_user)):
    with connect() as db:
        row = db.execute(
            "SELECT * FROM reports WHERE id = ?", (report_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Report not found")
        return report_with_photos(db, row)


@app.get('/reports/{report_id}/photos/{photo_id}')
def get_photo(report_id: str, photo_id: str, user=Depends(current_user)):
    with connect() as db:
        photo = db.execute('SELECT image FROM report_photos WHERE id = ? AND report_id = ?',
                           (photo_id, report_id)).fetchone()
    if photo is None:
        raise HTTPException(404, 'Photo not found')
    return Response(content=photo['image'], media_type='image/jpeg',
                    headers={'Content-Disposition': 'inline; filename="item-photo.jpg"'})
