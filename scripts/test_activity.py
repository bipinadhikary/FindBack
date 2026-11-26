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
            owner, visitor, outsider = [Client() for _ in range(3)]
            for client,name in [(owner,'finder'),(visitor,'student'),(outsider,'other')]:
                client.register(name)
            anon.call('/matches',expected=401)
            anon.call('/notifications',expected=401)
            data=dict(report_type='lost',title='Blue backpack with yellow star',category='backpack',description='Blue canvas backpack with yellow star patch',location='Campus library lobby',date='2026-10-12')
            lost=visitor.call('/reports',data,201)
            own_found=visitor.call('/reports',dict(data,report_type='found'),201)
            assert visitor.call('/matches')==[]
            owner.call('/reports',dict(data,report_type='found',category='headphones'),201)
            owner.call('/reports',dict(data,report_type='found',date='2026-11-12'),201)
            assert visitor.call('/matches')==[]
            found=owner.call('/reports',dict(data,report_type='found'),201)
            matches=visitor.call('/matches')
            assert len(matches)==1 and matches[0]['report_id']==found['id']
            assert matches[0]['score']==100 and len(matches[0]['reasons'])==4
            assert len(owner.call('/matches'))==1
            assert outsider.call('/matches')==[]
            feed=visitor.call('/notifications')
            assert feed['unread_count']==1 and feed['notifications'][0]['kind']=='match'
            first_id=feed['notifications'][0]['id']
            outsider.call(f'/notifications/{first_id}/read',{},404)
            visitor.call(f'/notifications/{first_id}/read',{},403,csrf=False)
            visitor.call(f'/notifications/{first_id}/read',{},204)
            assert visitor.call('/notifications')['unread_count']==0
            process.terminate(); process.wait(timeout=10); process=start()
            assert len(visitor.call('/matches'))==1
            assert len(visitor.call('/notifications')['notifications'])==1
            assert visitor.call('/notifications')['unread_count']==0
            conversation=visitor.call(f"/reports/{found['id']}/conversations",{})
            cid=conversation['id']
            message={'body':'PRIVATE message not copied to alerts','client_id':str(uuid4())}
            sent=visitor.call(f'/conversations/{cid}/messages',message)
            visitor.call(f'/conversations/{cid}/messages',message)
            notifications=owner.call('/notifications')['notifications']
            assert len([n for n in notifications if n['kind']=='message'])==1
            assert 'PRIVATE' not in json.dumps(notifications)
            owner.call(f'/conversations/{cid}/read',{'last_message_id':sent['id']},204)
            assert all(n['read_at'] for n in owner.call('/notifications')['notifications'] if n['kind']=='message')
            claim=visitor.call(f"/reports/{found['id']}/claims",{'proof':'PRIVATE proof inside pocket'},201)
            visitor.call(f"/reports/{found['id']}/claims",{'proof':'PRIVATE proof inside pocket'},201)
            assert len([n for n in owner.call('/notifications')['notifications'] if n['kind']=='claim'])==1
            assert 'PRIVATE' not in json.dumps(owner.call('/notifications'))
            route=f"/claims/{claim['id']}/actions"
            owner.call(route,{'action':'approve'})
            owner.call(route,{'action':'approve'})
            assert len([n for n in visitor.call('/notifications')['notifications'] if n['kind']=='claim'])==1
            owner.call(route,{'action':'confirm_return','verified':True})
            assert visitor.call('/matches')==[] and owner.call('/matches')==[]
            assert all(n['kind']!='match' for n in visitor.call('/notifications')['notifications'])
            assert outsider.call('/notifications')['notifications']==[]
            # Pagination, recipient isolation, and read-all high-watermark semantics.
            with closing(sqlite3.connect(database)) as db, db:
                for number in range(55):
                    db.execute("INSERT INTO notifications (recipient_id,event_key,kind,report_id,resource_id,text,created_at) VALUES (?,?,'claim',?,?,?,0)",
                               (visitor.id,'test:'+str(number),found['id'],claim['id'],'Test notice'))
            page=visitor.call('/notifications')
            assert len(page['notifications'])==50 and page['next_before_id']
            older=visitor.call('/notifications?before_id='+str(page['next_before_id']))
            assert older['notifications'] and not ({n['id'] for n in page['notifications']} & {n['id'] for n in older['notifications']})
            through=page['notifications'][0]['id']
            with closing(sqlite3.connect(database)) as db, db:
                db.execute("INSERT INTO notifications (recipient_id,event_key,kind,report_id,resource_id,text,created_at) VALUES (?,'later','claim',?,?,'Later update',0)",
                           (visitor.id,found['id'],claim['id']))
            visitor.call('/notifications/read-all',{'through_id':through},403,csrf=False)
            visitor.call('/notifications/read-all',{'through_id':through},204)
            assert visitor.call('/notifications')['unread_count']==1
            process.terminate(); process.wait(timeout=10); process=start()
            assert visitor.call('/notifications')['unread_count']==1
            assert visitor.call('/matches')==[]
            print('PASS: match rules, same-owner exclusion, reasons, recipient isolation, event deduplication, private-data exclusion, read cursors, pagination, resolved-item removal and restart persistence')

        finally:
            process.terminate()
            process.wait(timeout=10)


if __name__ == '__main__':
    run()
