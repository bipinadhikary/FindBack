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
            owner, visitor, other, admin = [Client() for _ in range(4)]
            for client, name in [(owner,'finder'),(visitor,'visitor'),(other,'other'),(admin,'admin')]:
                client.register(name)
            with closing(sqlite3.connect(database)) as db, db:
                db.execute("UPDATE users SET role='admin' WHERE id=?",(admin.id,))
            item = dict(report_type='found', title='Blue backpack', category='backpack', description='Synthetic backpack for claims testing', location='Library', date='2026-10-12')
            report = owner.call('/reports',item,201)
            path = f"/reports/{report['id']}/claims"
            proof = {'proof':'There is a hidden purple patch inside.'}
            anon.call('/claims',expected=401)
            anon.call(path,proof,401)
            owner.call(path,proof,409)
            visitor.call(path,proof,403,csrf=False)
            visitor.call(path,{'proof':'short'},422)
            visitor.call(path,dict(proof,claimant_id=owner.id),422)
            first = visitor.call(path,proof,201)
            assert visitor.call(path,proof,201)['id']==first['id']
            visitor.call(path,{'proof':'Different identifying details'},409)
            second = other.call(path,{'proof':'My own private identifying details'},201)
            assert len(visitor.call('/claims'))==1
            assert len(other.call('/claims'))==1
            assert len(owner.call('/claims'))==2
            assert admin.call('/claims')==[]
            assert 'proof' not in visitor.call('/reports/'+report['id'])
            action = f"/claims/{first['id']}/actions"
            for client in [admin,other]:
                client.call(action,{'action':'approve'},404)
            visitor.call(action,{'action':'approve'},403)
            owner.call(action,{'action':'withdraw'},403)
            owner.call(action,{'action':'approve'},403,csrf=False)
            owner.call(action,{'action':'confirm_return','verified':True},409)
            assert owner.call(action,{'action':'approve'})['status']=='approved'
            assert owner.call(action,{'action':'approve'})['status']=='approved'
            owner.call(f"/claims/{second['id']}/actions",{'action':'approve'},409)
            owner.call(action,{'action':'confirm_return'},422)
            assert visitor.call(action,{'action':'withdraw'})['status']=='withdrawn'
            owner.call(action,{'action':'approve'},409)
            winning = f"/claims/{second['id']}/actions"
            owner.call(winning,{'action':'approve'})
            returned = owner.call(winning,{'action':'confirm_return','verified':True})
            assert returned['status']=='returned'
            assert len(returned['events'])==3
            assert owner.call(winning,{'action':'confirm_return','verified':True})['events']==returned['events']
            assert owner.call('/reports/'+report['id'])['status']=='resolved'
            assert all(r['id']!=report['id'] for r in owner.call('/reports?status=open'))
            assert any(r['id']==report['id'] for r in owner.call('/reports?status=resolved'))
            admin.call(path,proof,409)
            other.call(winning,{'action':'withdraw'},409)
            reception = admin.call('/reports',dict(item,custody='reception',collection_location='Library reception'),201)
            c1 = visitor.call(f"/reports/{reception['id']}/claims",proof,201)
            c2 = other.call(f"/reports/{reception['id']}/claims",proof,201)
            route = f"/claims/{c1['id']}/actions"
            admin.call(route,{'action':'approve'},409)
            admin.call(route,{'action':'confirm_return'},422)
            with closing(sqlite3.connect(database)) as db, db:
                db.execute("UPDATE users SET role='user' WHERE id=?",(admin.id,))
            admin.call(route,{'action':'confirm_return','verified':True},403)
            with closing(sqlite3.connect(database)) as db, db:
                db.execute("UPDATE users SET role='reception' WHERE id=?",(admin.id,))
            assert admin.call(route,{'action':'confirm_return','verified':True})['status']=='returned'
            closed = next(c for c in other.call('/claims') if c['id']==c2['id'])
            assert closed['status']=='closed'
            rejected_report = owner.call('/reports',item,201)
            rejected = visitor.call(f"/reports/{rejected_report['id']}/claims",proof,201)
            rejected_route = f"/claims/{rejected['id']}/actions"
            assert owner.call(rejected_route,{'action':'reject','note':'Details do not match'})['status']=='rejected'
            visitor.call(rejected_route,{'action':'withdraw'},409)
            process.terminate(); process.wait(timeout=10); process=start()
            assert next(c for c in other.call('/claims') if c['id']==second['id'])['status']=='returned'
            assert owner.call('/reports/'+report['id'])['status']=='resolved'
            print('PASS: private proof, role checks, CSRF, duplicate claims, approval exclusivity, withdrawal, rejection, finder handover, reception collection, closure, status filters and restart persistence')

        finally:
            process.terminate()
            process.wait(timeout=10)


if __name__ == '__main__':
    run()
