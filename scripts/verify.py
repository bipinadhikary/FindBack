"""End-to-end HTTP checks using a temporary database and real server restarts."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def run():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    base = f'http://127.0.0.1:{port}'

    def request(path, data=None, expected=200):
        req = Request(base + path, data=json.dumps(data).encode() if data is not None else None,
                      headers={'Content-Type': 'application/json'})
        try:
            response = urlopen(req, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            body = response.read()
            assert response.status == expected, (path, response.status, body)
            return json.loads(body) if 'application/json' in response.headers.get('Content-Type', '') else body.decode()

    with tempfile.TemporaryDirectory() as folder:
        env = dict(os.environ, FINDBACK_DB_PATH=str(Path(folder) / 'test.sqlite3'))

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
            data = dict(report_type='lost', title='Synthetic blue backpack', category='backpack', description='Blue demo backpack with a yellow star', location='Demo library', date='2026-10-12')
            lost = request('/reports', data, 201)
            found = request('/reports', dict(data, report_type='found', title='Synthetic found backpack'), 201)
            assert len(request('/reports')) == 2
            assert request('/reports/' + lost['id']) == lost
            assert request('/reports?report_type=lost&category=backpack&q=yellow') == [lost]
            assert request('/reports?category=headphones') == []
            for change in [dict(title='  '), dict(report_type='other'), dict(category='wallet'), dict(date='invalid'), dict(date='2999-01-01'), dict(description='short')]:
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
            process.terminate()
            process.wait(timeout=10)
            process = start()
            assert request('/reports/' + lost['id']) == lost
            assert request('/reports/' + found['id']) == found
            print('PASS: both reports survive a real server restart; temporary test database only')
        finally:
            process.terminate()
            process.wait(timeout=10)


if __name__ == '__main__':
    run()
