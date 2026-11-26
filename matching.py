"""Explainable text/date/location matching; no external model or paid service."""
from datetime import date
import json
import re
from fastapi import APIRouter, Depends
from activity import notify

STOP_WORDS = set('a an the and or of for to in on at my i it is was with lost found item this that near campus college university'.split())


def words(value):
    return {word for word in re.findall(r"[^\W_]+", (value or '').casefold()) if len(word)>1 and word not in STOP_WORDS}


def score_pair(lost, found):
    if lost['category'] != found['category']:
        return None
    gap = (date.fromisoformat(found['date']) - date.fromisoformat(lost['date'])).days
    if gap < -1 or gap > 30:
        return None
    if lost['category'] == 'other' and not (words(lost['custom_category']) & words(found['custom_category'])):
        return None
    location_overlap = words(lost['location']) & words(found['location'])
    descriptive_overlap = (words(lost['title']+' '+lost['description']) &
                           words(found['title']+' '+found['description'])) - words(lost['category'])
    if not location_overlap and not descriptive_overlap:
        return None
    score = 30
    reasons = ['Same item category']
    if abs(gap)<=3:
        score += 20; reasons.append('Dates within 3 days')
    elif gap<=14:
        score += 10; reasons.append('Found within 2 weeks')
    else:
        reasons.append('Found within 30 days')
    if location_overlap:
        score += 20; reasons.append('Location shares: '+', '.join(sorted(location_overlap)[:4]))
    if descriptive_overlap:
        score += min(30, len(descriptive_overlap)*10)
        reasons.append('Description shares: '+', '.join(sorted(descriptive_overlap)[:5]))
    return (score,reasons) if score>=55 else None


def sync_matches(db, report):
    if report['status'] != 'open' or not report['owner_id']:
        return
    candidates = db.execute("""SELECT * FROM reports WHERE status='open' AND report_type!=?
        AND category=? AND owner_id IS NOT NULL AND owner_id!=?""",
        (report['report_type'],report['category'],report['owner_id'])).fetchall()
    for candidate in candidates:
        lost, found = (report,candidate) if report['report_type']=='lost' else (candidate,report)
        scored = score_pair(lost,found)
        if scored is None:
            continue
        score,reasons = scored
        inserted = db.execute('INSERT OR IGNORE INTO matches (lost_id,found_id,score,reasons) VALUES (?,?,?,?)',
                             (lost['id'],found['id'],score,json.dumps(reasons)))
        if not inserted.rowcount:
            continue
        match_id = inserted.lastrowid
        for own,other in [(lost,found),(found,lost)]:
            notify(db,own['owner_id'],f'match:{match_id}','match',other['id'],other['id'],
                   'Possible match for '+own['title'],match_id)


def matching_router(connect,current_user):
    router=APIRouter()

    @router.get('/matches')
    def matches(user=Depends(current_user)):
        with connect() as db:
            rows=db.execute("""SELECT m.*,a.title AS lost_title,b.title AS found_title,
                a.owner_id AS lost_owner,a.location AS lost_location,b.location AS found_location,
                a.date AS lost_date,b.date AS found_date
                FROM matches m JOIN reports a ON a.id=m.lost_id JOIN reports b ON b.id=m.found_id
                WHERE a.status='open' AND b.status='open' AND (a.owner_id=? OR b.owner_id=?)
                ORDER BY m.score DESC,m.id DESC""",(user['id'],user['id'])).fetchall()
            result=[]
            for row in rows:
                own='lost' if row['lost_owner']==user['id'] else 'found'
                other='found' if own=='lost' else 'lost'
                result.append({'id':row['id'],'own_report_id':row[own+'_id'],'own_title':row[own+'_title'],
                               'report_id':row[other+'_id'],'title':row[other+'_title'],'report_type':other,
                               'location':row[other+'_location'],'date':row[other+'_date'],
                               'score':row['score'],'reasons':json.loads(row['reasons'])})
            return result
    return router
