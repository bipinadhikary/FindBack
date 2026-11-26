"""Item conversations: access is limited to the two participants, including for admins."""
import time
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from activity import notify


class MessageCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    body: str = Field(min_length=1, max_length=2000)
    client_id: UUID

    @field_validator('body')
    @classmethod
    def trim_body(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('Enter a message')
        return value


class ReadReceipt(BaseModel):
    model_config = ConfigDict(extra='forbid')
    last_message_id: int = Field(ge=0)


def chat_router(connect, current_user):
    router = APIRouter()

    def participant(db, conversation_id, user):
        row = db.execute('SELECT * FROM conversations WHERE id = ? AND (visitor_id = ? OR owner_id = ?)',
                         (conversation_id, user['id'], user['id'])).fetchone()
        if row is None:
            raise HTTPException(404, 'Conversation not found')
        return row

    def summary(db, row, user):
        other_id = row['owner_id'] if user['id'] == row['visitor_id'] else row['visitor_id']
        other = db.execute('SELECT display_name FROM users WHERE id = ?', (other_id,)).fetchone()
        report = db.execute('SELECT title, custody FROM reports WHERE id = ?', (row['report_id'],)).fetchone()
        cursor = row['visitor_read'] if user['id'] == row['visitor_id'] else row['owner_read']
        latest = db.execute('SELECT body, created_at FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT 1',
                            (row['id'],)).fetchone()
        unread = db.execute('SELECT count(*) FROM messages WHERE conversation_id = ? AND sender_id != ? AND id > ?',
                            (row['id'], user['id'], cursor)).fetchone()[0]
        return {'id': row['id'], 'report_id': row['report_id'], 'title': report['title'],
                'other_name': other['display_name'], 'custody': report['custody'],
                'unread_count': unread, 'last_message': latest['body'] if latest else '',
                'updated_at': latest['created_at'] if latest else row['created_at']}

    @router.post('/reports/{report_id}/conversations')
    def start_conversation(report_id: str, user=Depends(current_user)):
        with connect() as db:
            db.execute('BEGIN IMMEDIATE')
            report = db.execute('SELECT * FROM reports WHERE id = ?', (report_id,)).fetchone()
            if report is None:
                raise HTTPException(404, 'Report not found')
            if report['report_type'] != 'found' or not report['owner_id']:
                raise HTTPException(409, 'This report cannot receive messages')
            if report['owner_id'] == user['id']:
                raise HTTPException(409, 'Use your inbox to reply to people about your item')
            existing = db.execute('SELECT * FROM conversations WHERE report_id = ? AND visitor_id = ?',
                                  (report_id, user['id'])).fetchone()
            if existing:
                return summary(db, existing, user)
            if report['status'] != 'open':
                raise HTTPException(409, 'This report is already resolved')
            cid = str(uuid4())
            db.execute('INSERT INTO conversations (id, report_id, visitor_id, owner_id, created_at) VALUES (?, ?, ?, ?, ?)',
                       (cid, report_id, user['id'], report['owner_id'], int(time.time() * 1000)))
            return summary(db, participant(db, cid, user), user)

    @router.get('/conversations')
    def inbox(user=Depends(current_user)):
        with connect() as db:
            rows = db.execute('SELECT * FROM conversations WHERE visitor_id = ? OR owner_id = ?', (user['id'], user['id'])).fetchall()
            conversations = [summary(db, row, user) for row in rows]
            conversations.sort(key=lambda row: (row['updated_at'], row['id']), reverse=True)
            return {'conversations': conversations, 'unread_count': sum(row['unread_count'] for row in conversations)}

    @router.get('/conversations/{conversation_id}/messages')
    def history(conversation_id: str, after_id: int = Query(default=0, ge=0), user=Depends(current_user)):
        with connect() as db:
            row = participant(db, conversation_id, user)
            messages = db.execute('SELECT id, sender_id, body, client_id, created_at FROM messages WHERE conversation_id = ? AND id > ? ORDER BY id LIMIT 101',
                                  (conversation_id, after_id)).fetchall()
            return {'conversation': summary(db, row, user), 'messages': [dict(m) for m in messages[:100]],
                    'has_more': len(messages) > 100}

    @router.post('/conversations/{conversation_id}/messages')
    def send(conversation_id: str, data: MessageCreate, user=Depends(current_user)):
        with connect() as db:
            db.execute('BEGIN IMMEDIATE')
            participant(db, conversation_id, user)
            existing = db.execute('SELECT id, sender_id, body, client_id, created_at FROM messages WHERE conversation_id = ? AND sender_id = ? AND client_id = ?',
                                  (conversation_id, user['id'], str(data.client_id))).fetchone()
            if existing:
                if existing['body'] != data.body:
                    raise HTTPException(409, 'This message identifier was already used')
                return dict(existing)
            now = int(time.time() * 1000)
            recent = db.execute('SELECT count(*) FROM messages WHERE sender_id = ? AND created_at > ?', (user['id'], now - 60_000)).fetchone()[0]
            if recent >= 30:
                raise HTTPException(429, 'Please wait a minute before sending more messages', headers={'Retry-After': '60'})
            cursor = db.execute('INSERT INTO messages (conversation_id, sender_id, body, client_id, created_at) VALUES (?, ?, ?, ?, ?)',
                                (conversation_id, user['id'], data.body, str(data.client_id), now))
            conversation = participant(db, conversation_id, user)
            recipient = conversation['owner_id'] if conversation['visitor_id']==user['id'] else conversation['visitor_id']
            notify(db,recipient,f'message:{cursor.lastrowid}','message',conversation['report_id'],conversation_id,'New private message about an item')
            return dict(db.execute('SELECT id, sender_id, body, client_id, created_at FROM messages WHERE id = ?', (cursor.lastrowid,)).fetchone())

    @router.post('/conversations/{conversation_id}/read', status_code=204)
    def mark_read(conversation_id: str, data: ReadReceipt, user=Depends(current_user)):
        with connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = participant(db, conversation_id, user)
            if data.last_message_id and not db.execute('SELECT 1 FROM messages WHERE id = ? AND conversation_id = ?', (data.last_message_id, conversation_id)).fetchone():
                raise HTTPException(422, 'Read position does not belong to this conversation')
            column = 'visitor_read' if user['id'] == row['visitor_id'] else 'owner_read'
            db.execute(f'UPDATE conversations SET {column} = MAX({column}, ?) WHERE id = ?', (data.last_message_id, conversation_id))
            db.execute("""UPDATE notifications SET read_at=COALESCE(read_at,?) WHERE recipient_id=? AND kind='message'
                AND resource_id=? AND event_key IN (SELECT 'message:' || id FROM messages WHERE conversation_id=? AND id<=?)""",
                (int(time.time()*1000),user['id'],conversation_id,conversation_id,data.last_message_id))

    return router
