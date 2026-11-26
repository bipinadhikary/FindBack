"""HTTP integration checks against an isolated database and real server."""
from contextlib import closing
import http.cookiejar
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPCookieProcessor
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def run():
    with tempfile.TemporaryDirectory() as folder:
        database = Path(folder) / 'chat.sqlite3'
        env = dict(os.environ, FINDBACK_DB_PATH=str(database))
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        base = f'http://127.0.0.1:{port}'

        class Client:
            def __init__(self):
                self.browser = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
                self.csrf = ''

            def call(self, path, body=None, expected=200, csrf=True):
                request = Request(base + path, data=None if body is None else json.dumps(body).encode(),
                                  headers={'Content-Type': 'application/json', 'X-CSRF-Token': self.csrf if csrf else ''})
                try:
                    response = self.browser.open(request, timeout=10)
                except HTTPError as error:
                    response = error
                with response:
                    raw = response.read()
                    assert response.status == expected, (path, response.status, raw)
                    return json.loads(raw) if raw else None

            def register(self, name):
                session = self.call('/auth/register', {'email': name + '@example.org', 'display_name': name,
                                                       'password': 'Synthetic-password-123'}, 201)
                self.csrf = session['csrf_token']
                self.id = session['user']['id']

        anon = Client()

        def start():
            process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', str(port)],
                                       cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for _ in range(100):
                try:
                    anon.call('/health')
                    return process
                except URLError:
                    if process.poll() is not None:
                        raise RuntimeError('Test server failed to start')
                    time.sleep(.1)
            process.terminate()
            process.wait()
            raise RuntimeError('Test server timed out')

        process = start()
        try:
            owner, visitor, outsider, admin = [Client() for _ in range(4)]
            for client, name in [(owner, 'finder'), (visitor, 'claimant'), (outsider, 'other'), (admin, 'admin')]:
                client.register(name)
            with closing(sqlite3.connect(database)) as db, db:
                db.execute("UPDATE users SET role='admin' WHERE id=?", (admin.id,))
                db.execute("UPDATE users SET role='reception' WHERE id=?", (owner.id,))
            item = dict(report_type='found', title='Blue campus backpack', category='backpack', description='Synthetic backpack for chat tests',
                        location='Library lobby', date='2026-10-12', custody='reception', collection_location='Library reception')
            report = owner.call('/reports', item, 201)
            path = f"/reports/{report['id']}/conversations"
            anon.call('/conversations', expected=401)
            anon.call(path, {}, 401)
            owner.call(path, {}, 409)
            visitor.call(path, {}, 403, csrf=False)
            lost = owner.call('/reports', {k:v for k,v in dict(item, report_type='lost').items() if k not in ('custody','collection_location')}, 201)
            visitor.call(f"/reports/{lost['id']}/conversations", {}, 409)
            conversation = visitor.call(path, {})
            cid = conversation['id']
            assert visitor.call(path, {})['id'] == cid
            second = outsider.call(path, {})['id']
            for client in [outsider, admin]:
                client.call(f'/conversations/{cid}/messages', expected=404)
                client.call(f'/conversations/{cid}/messages', {'body':'intrusion', 'client_id':str(uuid4())}, 404)
                client.call(f'/conversations/{cid}/read', {'last_message_id':0}, 404)
                assert all(row['id'] != cid for row in client.call('/conversations')['conversations'])
            message = {'body':'Is there a yellow star on it?', 'client_id':str(uuid4())}
            visitor.call(f'/conversations/{cid}/messages', message, 403, csrf=False)
            for bad in ['', '   ', 'x' * 2001]:
                visitor.call(f'/conversations/{cid}/messages', dict(message, body=bad), 422)
            visitor.call(f'/conversations/{cid}/messages', dict(message, sender_id=owner.id), 422)
            first = visitor.call(f'/conversations/{cid}/messages', message)
            assert visitor.call(f'/conversations/{cid}/messages', message) == first
            visitor.call(f'/conversations/{cid}/messages', dict(message, body='Changed'), 409)
            assert owner.call('/conversations')['unread_count'] == 1
            assert visitor.call('/conversations')['unread_count'] == 0
            assert owner.call(f'/conversations/{cid}/messages')['messages'] == [first]
            assert owner.call('/conversations')['unread_count'] == 1  # GET never marks read.
            unrelated = outsider.call(f'/conversations/{second}/messages', {'body':'A separate private question', 'client_id':str(uuid4())})
            owner.call(f'/conversations/{cid}/read', {'last_message_id':unrelated['id']}, 422)
            owner.call(f'/conversations/{cid}/read', {'last_message_id':first['id']}, 204)
            owner.call(f'/conversations/{cid}/read', {'last_message_id':0}, 204)
            own_thread = next(row for row in owner.call('/conversations')['conversations'] if row['id'] == cid)
            assert own_thread['unread_count'] == 0
            reply = owner.call(f'/conversations/{cid}/messages', {'body':'Please describe another detail before pickup.', 'client_id':str(uuid4())})
            assert visitor.call('/conversations')['unread_count'] == 1
            assert visitor.call(f'/conversations/{cid}/messages?after_id={first["id"]}')['messages'] == [reply]
            # Exercise pagination and the per-sender rate limit without sleeping.
            for number in range(29):
                visitor.call(f'/conversations/{cid}/messages', {'body':f'Message {number}', 'client_id':str(uuid4())})
            visitor.call(f'/conversations/{cid}/messages', {'body':'Rate limited', 'client_id':str(uuid4())}, 429)
            for batch in range(3):
                with closing(sqlite3.connect(database)) as db, db:
                    db.execute('UPDATE messages SET created_at=0 WHERE sender_id=?', (visitor.id,))
                for number in range(30):
                    visitor.call(f'/conversations/{cid}/messages', {'body':f'Page {batch}-{number}', 'client_id':str(uuid4())})
            page = owner.call(f'/conversations/{cid}/messages')
            assert len(page['messages']) == 100 and page['has_more']
            rest = owner.call(f'/conversations/{cid}/messages?after_id={page["messages"][-1]["id"]}')
            assert len(rest['messages']) == 21 and not rest['has_more']
            with closing(sqlite3.connect(database)) as db, db:
                db.execute("UPDATE reports SET status='resolved' WHERE id=?", (report['id'],))
            assert visitor.call(path, {})['id'] == cid  # Existing chat remains accessible.
            admin.call(path, {}, 409)  # No new chats on resolved reports.
            process.terminate()
            process.wait(timeout=10)
            process = start()
            assert len(owner.call(f'/conversations/{cid}/messages')['messages']) == 100
            assert visitor.call('/conversations')['unread_count'] == 1
            visitor.call('/auth/logout', {}, 204)
            visitor.call(f'/conversations/{cid}/messages', expected=401)
            print('PASS: private threads, separate claimants, no admin bypass, CSRF, idempotency, unread/read cursors, pagination, throttling, restart persistence and logout')
        finally:
            process.terminate()
            process.wait(timeout=10)


if __name__ == '__main__':
    run()
