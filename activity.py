"""Persistent in-app notifications. Payloads omit private messages and claim proof."""
import time
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field


def notify(db, recipient, event_key, kind, report_id, resource_id, text, match_id=None):
    if not recipient:
        return
    db.execute('''INSERT OR IGNORE INTO notifications
        (recipient_id,event_key,kind,report_id,resource_id,text,match_id,created_at)
        VALUES (?,?,?,?,?,?,?,?)''',
        (recipient,event_key,kind,report_id,resource_id,text,match_id,int(time.time()*1000)))


VISIBLE = """(n.kind != 'match' OR EXISTS (
    SELECT 1 FROM matches m JOIN reports a ON a.id=m.lost_id JOIN reports b ON b.id=m.found_id
    WHERE m.id=n.match_id AND a.status='open' AND b.status='open'))"""


class ReadAll(BaseModel):
    model_config = ConfigDict(extra='forbid')
    through_id: int = Field(ge=0)


def activity_router(connect, current_user):
    router = APIRouter()

    @router.get('/notifications')
    def notifications(before_id: int | None = Query(default=None, ge=1), user=Depends(current_user)):
        with connect() as db:
            args = [user['id']]
            before = ''
            if before_id is not None:
                before = ' AND n.id < ?'
                args.append(before_id)
            rows = db.execute(f'''SELECT n.id,n.kind,n.report_id,n.resource_id,n.text,n.created_at,n.read_at
                FROM notifications n WHERE n.recipient_id=? AND {VISIBLE}{before}
                ORDER BY n.id DESC LIMIT 51''',args).fetchall()
            unread = db.execute(f'SELECT count(*) FROM notifications n WHERE n.recipient_id=? AND n.read_at IS NULL AND {VISIBLE}',(user['id'],)).fetchone()[0]
            return {'notifications':[dict(row) for row in rows[:50]], 'unread_count':unread,
                    'next_before_id':rows[49]['id'] if len(rows)>50 else None}

    @router.post('/notifications/read-all', status_code=204)
    def mark_all(data: ReadAll, user=Depends(current_user)):
        with connect() as db:
            db.execute('UPDATE notifications SET read_at=? WHERE recipient_id=? AND id<=? AND read_at IS NULL',
                       (int(time.time()*1000),user['id'],data.through_id))

    @router.post('/notifications/{notification_id}/read', status_code=204)
    def mark_one(notification_id: int, user=Depends(current_user)):
        with connect() as db:
            row = db.execute('SELECT id FROM notifications WHERE id=? AND recipient_id=?',(notification_id,user['id'])).fetchone()
            if row is None:
                raise HTTPException(404,'Notification not found')
            db.execute('UPDATE notifications SET read_at=COALESCE(read_at,?) WHERE id=?',(int(time.time()*1000),notification_id))

    return router
