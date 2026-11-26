"""End-to-end HTTP checks using a temporary database and real server restarts."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import sqlite3
import http.cookiejar
import base64
from io import BytesIO
from PIL import Image
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen, build_opener, HTTPCookieProcessor

ROOT = Path(__file__).resolve().parents[1]


def run():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    base = f'http://127.0.0.1:{port}'

    jar = http.cookiejar.CookieJar()
    browser = build_opener(HTTPCookieProcessor(jar))
    csrf = ''

    def request(path, data=None, expected=200, method=None, authenticated=True, headers=None):
        req = Request(base + path, data=json.dumps(data).encode() if data is not None else None,
                      method=method, headers={'Content-Type': 'application/json', 'X-CSRF-Token': csrf, **(headers or {})})
        try:
            response = (browser.open if authenticated else urlopen)(req, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            body = response.read()
            assert response.status == expected, (path, response.status, body)
            if not body:
                return None
            if response.headers.get('Content-Type', '').startswith('image/'):
                return body
            return json.loads(body) if 'application/json' in response.headers.get('Content-Type', '') else body.decode()

    with tempfile.TemporaryDirectory() as folder:
        env = dict(os.environ, FINDBACK_DB_PATH=str(Path(folder) / 'test.sqlite3'))
        with sqlite3.connect(env['FINDBACK_DB_PATH']) as db:
            db.execute('''CREATE TABLE reports (id TEXT PRIMARY KEY, report_type TEXT NOT NULL,
                title TEXT NOT NULL, category TEXT NOT NULL, description TEXT NOT NULL,
                location TEXT NOT NULL, date TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open')''')
            db.execute("INSERT INTO reports VALUES ('legacy', 'found', 'Old headphones', 'headphones', 'Synthetic old report', 'Old desk', '2026-01-01', 'open')")
        db.close()

        def start():
            process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', str(port)], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for _ in range(100):
                try:
                    request('/health')
                    return process
                except (URLError, TimeoutError):
                    if process.poll() is not None:
                        raise RuntimeError('Server exited during startup')
                    time.sleep(.1)
            process.terminate()
            process.wait(timeout=10)
            raise RuntimeError('Server startup timed out')

        process = start()
        try:
            request('/reports', expected=401)
            request('/reports/legacy', expected=401)
            request('/admin/users', expected=401)
            credentials = dict(email='Owner@Example.org', password='Synthetic-test-pass123')
            registration = dict(credentials, display_name='Owner')
            request('/auth/register', dict(registration, role='admin'), 422)
            request('/auth/register', registration, 403, headers={'Origin': 'https://other.example'})
            session = request('/auth/register', registration, 201)
            csrf = session['csrf_token']
            owner = session['user']['id']
            assert session['user']['email'] == 'owner@example.org'
            assert session['user']['role'] == 'user'
            cookie = next(iter(jar))
            assert cookie.has_nonstandard_attr('HttpOnly')
            assert cookie.get_nonstandard_attr('SameSite').lower() == 'strict'
            request('/auth/register', dict(registration, email='owner@example.org'), 409)
            assert request('/reports/legacy')['owner_id'] is None
            request('/admin/users', expected=403)
            request(f'/admin/users/{owner}/role', {'role': 'reception'}, 403, method='PATCH')
            data = dict(report_type='lost', title='Synthetic blue backpack', category='backpack', description='Blue demo backpack with a yellow star', location='Demo library', date='2026-10-12')
            request('/reports', data, 401, authenticated=False)
            request('/reports', data, 403, headers={'X-CSRF-Token': ''})
            request('/reports', dict(data, owner_id='legacy'), 422)
            lost = request('/reports', data, 201)
            assert lost['owner_id'] == owner
            found = request('/reports', dict(data, report_type='found', title='Synthetic found backpack'), 201)
            assert len(request('/reports')) == 3
            assert request('/reports/' + lost['id']) == lost
            assert request('/reports?report_type=lost&category=backpack&q=yellow') == [lost]
            assert request('/reports?category=headphones&q=no-match') == []
            for change in [dict(title='  '), dict(report_type='other'), dict(category='invalid-category'), dict(date='invalid'), dict(date='2999-01-01'), dict(description='short')]:
                request('/reports', dict(data, **change), 422)
            missing = dict(data)
            del missing['location']
            request('/reports', missing, 422)
            request('/reports?category=invalid', expected=422)
            request('/reports/missing', expected=404)
            assert 'report-form' in request('/')
            assert "fetch(url" in request('/static/app.js')
            assert 'font-family' in request('/static/style.css')
            print('PASS: creation, list, detail, combined filters, empty results, validation, 404, frontend assets')
            catalog = json.loads((ROOT / 'static/categories.json').read_text(encoding='utf-8'))
            categories = [item['value'] for group in catalog for item in group['items']]
            assert len(categories) == len(set(categories))
            for value in categories:
                extra = {'custom_category': 'Graduation tassel'} if value == 'other' else {}
                item = request('/reports', dict(data, category=value, **extra), 201)
                assert item in request('/reports?category=' + value.replace(' ', '%20'))
            for extra in [{}, {'custom_category': ''}, {'custom_category': '   '}, {'custom_category': 'x'}, {'custom_category': 'x' * 81}]:
                request('/reports', dict(data, category='other', **extra), 422)
            request('/reports', dict(data, custom_category='Not applicable'), 422)
            custom = request('/reports', dict(data, category='other', custom_category='  Unusual keepsake  '), 201)
            assert custom['custom_category'] == 'Unusual keepsake'
            assert request('/reports?category=other&q=keepsake') == [custom]
            pickup = dict(data, report_type='found', custody='finder', collection_location='Student union desk', pickup_instructions='Meet during opening hours')
            for change in [dict(custody='reception'), dict(collection_location='Desk'), dict(pickup_instructions='Meet here')]:
                request('/reports', dict(data, **change), 422)
            request('/reports', dict(pickup, custody='reception', collection_location=None), 422)
            request('/reports', dict(pickup, custody='reception'), 403)
            uploads = []
            for format in ['JPEG', 'PNG', 'WEBP']:
                output = BytesIO()
                picture = Image.new('RGB', (2000, 100), 'blue')
                exif = Image.Exif()
                exif[270] = 'Private image metadata'
                picture.save(output, format=format, exif=exif)
                uploads.append({'data': base64.b64encode(output.getvalue()).decode()})
            pictured = request('/reports', dict(pickup, photos=uploads), 201)
            assert len(pictured['photos']) == 3
            assert pictured in request('/reports?q=Student%20union%20desk')
            photo_url = pictured['photos'][0]['url']
            request(photo_url, expected=401, authenticated=False)
            request('/reports/missing/photos/' + pictured['photos'][0]['id'], expected=404)
            saved_photo = request(photo_url)
            with Image.open(BytesIO(saved_photo)) as clean:
                assert clean.format == 'JPEG' and max(clean.size) <= 1600
                assert not clean.getexif()
            count_before = len(request('/reports'))
            request('/reports', dict(pickup, photos=uploads + uploads[:1]), 422)
            request('/reports', dict(pickup, photos=[{'data': 'not base64!'}]), 422)
            request('/reports', dict(pickup, photos=[{'data': base64.b64encode(b'<svg></svg>').decode()}]), 422)
            request('/reports', dict(pickup, photos=[uploads[0], {'data': 'bad'}]), 422)
            oversized = base64.b64encode(b'x' * (5 * 1024 * 1024 + 1)).decode()
            request('/reports', dict(pickup, photos=[{'data': oversized}]), 413)
            assert len(request('/reports')) == count_before
            process.terminate()
            process.wait(timeout=10)
            process = start()
            assert request('/reports/' + lost['id']) == lost
            assert request('/reports/' + found['id']) == found
            assert request('/reports/legacy')['owner_id'] is None
            assert request('/reports/legacy')['custom_category'] is None
            assert request('/reports/' + custom['id']) == custom
            assert request('/reports/' + pictured['id']) == pictured
            assert request(photo_url) == saved_photo
            assert request('/reports/legacy')['custody'] is None
            assert request('/reports/legacy')['photos'] == []
            print('PASS: photos, image validation, metadata removal, size limits, atomic creation, protected access, pickup validation and restart persistence')
            print('PASS: all categories, Other validation, custom-type search, persistence, legacy compatibility')
            assert request('/auth/me')['user']['id'] == owner
            print('PASS: both reports survive a real server restart; temporary test database only')
            with sqlite3.connect(env['FINDBACK_DB_PATH']) as db:
                stored = db.execute('SELECT password_hash FROM users WHERE id = ?', (owner,)).fetchone()[0]
                assert credentials['password'] not in stored
                assert db.execute('SELECT token_hash FROM sessions').fetchone()[0] != cookie.value
            db.close()
            old_cookie = cookie.value
            request('/auth/logout', {}, 204)
            request('/auth/me', expected=401)
            request('/auth/me', expected=401, authenticated=False, headers={'Cookie': f'findback_session={old_cookie}'})
            request('/auth/login', dict(credentials, password='Wrong-password123'), 401)
            request('/auth/login', dict(credentials, email='missing@example.org'), 401)
            session = request('/auth/login', credentials)
            csrf = session['csrf_token']
            assert session['user']['id'] == owner
            # Explicit owner-only bootstrap; no automatic admin on first registration.
            subprocess.run([sys.executable, 'scripts/set_admin.py', credentials['email']], cwd=ROOT, env=env, check=True)
            assert request('/auth/me')['user']['role'] == 'admin'
            request('/auth/logout', {}, 204)
            staff_session = request('/auth/register', dict(email='staff@example.net', password='Synthetic-staff-pass123', display_name='Reception'), 201)
            csrf = staff_session['csrf_token']
            staff = staff_session['user']['id']
            staff_cookie = next(iter(jar)).value
            request('/auth/logout', {}, 204)
            session = request('/auth/login', credentials)
            csrf = session['csrf_token']
            assert len(request('/admin/users')) == 2
            request(f'/admin/users/{staff}/role', {'role': 'admin'}, 422, method='PATCH')
            request(f'/admin/users/{owner}/role', {'role': 'user'}, 400, method='PATCH')
            request('/admin/users/missing/role', {'role': 'reception'}, 404, method='PATCH')
            assert request(f'/admin/users/{staff}/role', {'role': 'reception'}, method='PATCH')['role'] == 'reception'
            request('/auth/logout', {}, 204)
            session = request('/auth/login', dict(email='staff@example.net', password='Synthetic-staff-pass123'))
            csrf = session['csrf_token']
            assert session['user']['role'] == 'reception'
            reception_report = request('/reports', dict(pickup, custody='reception', collection_location='Library reception'), 201)
            assert reception_report['custody'] == 'reception'
            assert reception_report['owner_id'] == staff
            assert reception_report in request('/reports?q=Library%20reception')
            request('/admin/users', expected=403)
            request(f'/admin/users/{staff}/role', {'role': 'user'}, 403, method='PATCH')
            with sqlite3.connect(env['FINDBACK_DB_PATH']) as db:
                db.execute('UPDATE sessions SET expires_at = 0')
            db.close()
            request('/auth/me', expected=401)
            for _ in range(10):
                request('/auth/login', dict(email='limited@example.org', password='Wrong-password123'), 401)
            request('/auth/login', dict(email='limited@example.org', password='Wrong-password123'), 429)
            print('PASS: registration, hashing, authentication, CSRF, logout revocation, expiry, admin/reception permissions, throttling, legacy migration')
        finally:
            process.terminate()
            process.wait(timeout=10)


if __name__ == '__main__':
    run()
