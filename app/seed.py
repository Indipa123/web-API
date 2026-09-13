"""Synthetic assets, real province/district names; never actual household data."""
import hashlib
import json
import math
import os
import random
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from .db import connect, initialize

GEOGRAPHY = {
 'Western': ['Colombo','Gampaha','Kalutara'],
 'Central': ['Kandy','Matale','Nuwara Eliya'],
 'Southern': ['Galle','Matara','Hambantota'],
 'Northern': ['Jaffna','Kilinochchi','Mannar','Mullaitivu','Vavuniya'],
 'Eastern': ['Batticaloa','Ampara','Trincomalee'],
 'North Western': ['Kurunegala','Puttalam'],
 'North Central': ['Anuradhapura','Polonnaruwa'],
 'Uva': ['Badulla','Monaragala'],
 'Sabaragamuwa': ['Ratnapura','Kegalle']}

def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()

def seed():
    initialize()
    rng = random.Random(6007)
    credentials = {}
    with connect() as db:
        if db.execute('SELECT COUNT(*) FROM provinces').fetchone()[0]:
            return False
        district_id = 0
        for pid, (province, districts) in enumerate(GEOGRAPHY.items(),1):
            db.execute('INSERT INTO provinces VALUES (?,?)',(pid,province))
            for district in districts:
                district_id += 1
                db.execute('INSERT INTO districts VALUES (?,?,?)',(district_id,district,pid))
                db.execute('INSERT INTO substations VALUES (?,?,?)',
                           (district_id,f'{district} Demo Substation',district_id))
        users = [('national',None,None),('province',1,None),('district',None,1),('district',None,2)]
        for uid,(role,pid,did) in enumerate(users,1):
            token = secrets.token_urlsafe(32)
            credentials[f'user_{uid}_{role}'] = token
            db.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?)',
                       (uid,f'Demo {role} reader {uid}',role,pid,did,digest(token)))
        # 673 points include both ends of a full seven-day interval.
        end = datetime.now(timezone.utc).replace(second=0,microsecond=0)
        end -= timedelta(minutes=end.minute % 15)
        start = end - timedelta(days=7)
        for iid in range(1,201):
            sid = ((iid-1)%25)+1
            capacity = round(rng.uniform(3,12),2)
            token = secrets.token_urlsafe(32)
            credentials[f'installation_{iid}'] = token
            db.execute('INSERT INTO installations(id,name,meter_id,capacity_kw,substation_id,token_hash) VALUES (?,?,?,?,?,?)',
                       (iid,f'Synthetic rooftop {iid:03}',f'DEMO-METER-{iid:04}',capacity,sid,digest(token)))
            energy = 1000.0
            rows=[]
            for n in range(673):
                stamp = start+timedelta(minutes=15*n)
                local = stamp+timedelta(hours=5,minutes=30)
                hour = local.hour+local.minute/60
                power = round(capacity*max(0,math.sin(math.pi*(hour-6)/12))*rng.uniform(.65,.95),3) if 6<hour<18 else 0
                energy += power*.25
                rows.append((iid,stamp.isoformat(timespec='microseconds'),power,round(energy,4),round(rng.uniform(225,240),1)))
            db.executemany('INSERT INTO readings(installation_id,timestamp,power_kw,energy_kwh,voltage) VALUES (?,?,?,?,?)',rows)
        path = Path(os.getenv('CREDENTIALS_PATH','data/credentials.json'))
        path.parent.mkdir(parents=True,exist_ok=True)
        with os.fdopen(os.open(path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600),'w') as f:
            json.dump(credentials,f,indent=2)
    return True

if __name__ == '__main__':
    print('Seed created; credentials saved privately.' if seed() else 'Seed already exists; nothing changed.')
