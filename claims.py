"""Private claims and atomic, owner-confirmed returns."""
import time
from uuid import uuid4
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from activity import notify


class ClaimCreate(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    proof: str = Field(min_length=10, max_length=2000)


class ClaimAction(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    action: Literal['approve', 'reject', 'withdraw', 'confirm_return']
    note: str = Field(default='', max_length=500)
    verified: bool = False


def claims_router(connect, current_user):
    router = APIRouter()

    def detail(db, row, user):
        result = dict(row)
        report = db.execute('SELECT title, custody, owner_id, status FROM reports WHERE id=?', (row['report_id'],)).fetchone()
        result.update(title=report['title'], custody=report['custody'], report_status=report['status'],
                      is_owner=report['owner_id'] == user['id'],
                      claimant_name=db.execute('SELECT display_name FROM users WHERE id=?', (row['claimant_id'],)).fetchone()[0])
        result['events'] = [dict(event) for event in db.execute('SELECT status, note, created_at FROM claim_events WHERE claim_id=? ORDER BY id', (row['id'],))]
        return result

    def record(db, claim_id, actor, status, note):
        now = int(time.time() * 1000)
        db.execute('UPDATE claims SET status=?, note=?, updated_at=? WHERE id=?', (status, note, now, claim_id))
        event = db.execute('INSERT INTO claim_events (claim_id,actor_id,status,note,created_at) VALUES (?,?,?,?,?)',
                   (claim_id, actor, status, note, now))
        claim = db.execute('SELECT c.report_id,c.claimant_id,r.owner_id FROM claims c JOIN reports r ON r.id=c.report_id WHERE c.id=?',(claim_id,)).fetchone()
        recipient = claim['owner_id'] if actor==claim['claimant_id'] else claim['claimant_id']
        labels={'pending':'New claim received','approved':'Your claim was approved','rejected':'Your claim was rejected',
                'withdrawn':'A claim was withdrawn','returned':'Item return confirmed','closed':'Claim closed: item returned to another claimant'}
        notify(db,recipient,f'claim-event:{event.lastrowid}','claim',claim['report_id'],claim_id,labels[status])

    @router.post('/reports/{report_id}/claims', status_code=201)
    def submit(report_id: str, data: ClaimCreate, user=Depends(current_user)):
        with connect() as db:
            db.execute('BEGIN IMMEDIATE')
            report = db.execute('SELECT * FROM reports WHERE id=?', (report_id,)).fetchone()
            if not report:
                raise HTTPException(404, 'Report not found')
            if report['report_type'] != 'found' or not report['owner_id'] or report['owner_id'] == user['id']:
                raise HTTPException(409, 'You cannot claim this report')
            if report['status'] != 'open':
                raise HTTPException(409, 'This item has already been returned')
            existing = db.execute('SELECT * FROM claims WHERE report_id=? AND claimant_id=?', (report_id,user['id'])).fetchone()
            if existing:
                if existing['proof'] == data.proof:
                    return detail(db, existing, user)
                raise HTTPException(409, 'You already submitted a claim for this item. Check My claims.')
            cid, now = str(uuid4()), int(time.time() * 1000)
            db.execute("INSERT INTO claims VALUES (?,?,?,?,'pending','',?,?)", (cid,report_id,user['id'],data.proof,now,now))
            record(db, cid, user['id'], 'pending', '')
            return detail(db, db.execute('SELECT * FROM claims WHERE id=?',(cid,)).fetchone(), user)

    @router.get('/claims')
    def list_claims(user=Depends(current_user)):
        with connect() as db:
            rows = db.execute('''SELECT c.* FROM claims c JOIN reports r ON r.id=c.report_id
                WHERE c.claimant_id=? OR r.owner_id=? ORDER BY c.updated_at DESC, c.id''', (user['id'],user['id'])).fetchall()
            return [detail(db,row,user) for row in rows]

    @router.post('/claims/{claim_id}/actions')
    def act(claim_id: str, data: ClaimAction, user=Depends(current_user)):
        with connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM claims WHERE id=?',(claim_id,)).fetchone()
            if not row:
                raise HTTPException(404,'Claim not found')
            report = db.execute('SELECT * FROM reports WHERE id=?',(row['report_id'],)).fetchone()
            is_owner = report['owner_id'] == user['id']
            if not is_owner and row['claimant_id'] != user['id']:
                raise HTTPException(404,'Claim not found')
            if data.action == 'withdraw':
                if row['claimant_id'] != user['id']:
                    raise HTTPException(403,'Only the claimant can withdraw')
                target = 'withdrawn'
            else:
                if not is_owner:
                    raise HTTPException(403,'Only the report owner can decide or confirm a return')
                if report['custody'] == 'reception' and user['role'] not in {'reception','admin'}:
                    raise HTTPException(403,'Reception access is required')
                target = {'approve':'approved','reject':'rejected','confirm_return':'returned'}[data.action]
            if row['status'] == target:
                return detail(db,row,user)
            if report['status'] != 'open' or row['status'] not in {'pending','approved'}:
                raise HTTPException(409,'This claim can no longer be changed')
            if data.action == 'approve':
                if report['custody'] == 'reception':
                    raise HTTPException(409,'Reception verifies ownership at collection; confirm collection instead')
                if db.execute("SELECT 1 FROM claims WHERE report_id=? AND status='approved' AND id!=?",(report['id'],claim_id)).fetchone():
                    raise HTTPException(409,'Another claim is already approved')
            if data.action == 'confirm_return':
                if not data.verified:
                    raise HTTPException(422,'Confirm that ownership was checked and the item handed over')
                if report['custody'] != 'reception' and row['status'] != 'approved':
                    raise HTTPException(409,'Approve the claim before confirming handover')
                db.execute("UPDATE reports SET status='resolved' WHERE id=?", (report['id'],))
                others = db.execute("SELECT id FROM claims WHERE report_id=? AND id!=? AND status IN ('pending','approved')",(report['id'],claim_id)).fetchall()
                for other in others:
                    record(db,other['id'],user['id'],'closed','Item returned to another claimant')
            record(db,claim_id,user['id'],target,data.note)
            return detail(db,db.execute('SELECT * FROM claims WHERE id=?',(claim_id,)).fetchone(),user)

    return router
