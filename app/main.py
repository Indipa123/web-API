"""Solar API: authenticate first, scope in SQL, then serialize and cache."""
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.exceptions import HTTPException as StarletteHTTPException
from .db import connect, initialize
from . import contracts
from .seed import digest, seed

@asynccontextmanager
async def lifespan(app):
    initialize()
    if os.getenv('AUTO_SEED','false').lower() == 'true':
        seed()
    yield

class ErrorDetail(BaseModel):
    code: str
    message: str
    detail: object = None
class ErrorBody(BaseModel):
    error: ErrorDetail

app = FastAPI(title='SLSEA Solar Generation API (Coursework)',version='1.0.0',
 description='Synthetic solar telemetry. Reader and device credentials are separate. All protected routes use bearer tokens. Times require offsets and are stored in UTC.',
 lifespan=lifespan, responses={n:{'model':ErrorBody} for n in [400,401,403,404,405,406,409,412,415,422,428]})
security = HTTPBearer(auto_error=False)

def fail(status, message, detail=None):
    raise HTTPException(status, {'code':f'HTTP_{status}','message':message,'detail':detail})

@app.exception_handler(StarletteHTTPException)
async def http_error(request, exc):
    body=exc.detail if isinstance(exc.detail,dict) else {'code':f'HTTP_{exc.status_code}','message':str(exc.detail),'detail':None}
    headers=dict(exc.headers or {})
    if exc.status_code==401:
        headers['WWW-Authenticate']='Bearer'
    return JSONResponse({'error':body},status_code=exc.status_code,headers=headers)

@app.exception_handler(RequestValidationError)
async def validation_error(request,exc):
    details=[{'location':list(e['loc']),'message':e['msg'],'type':e['type']} for e in exc.errors()]
    return JSONResponse({'error':{'code':'VALIDATION_ERROR','message':'Request validation failed','detail':details}},status_code=422)

def accepts_json(header):
    matches=[]
    for item in header.split(','):
        bits=item.strip().lower().split(';')
        media=bits[0]
        if media not in ('application/json','application/*','*/*'): continue
        q=1.0
        for bit in bits[1:]:
            if bit.strip().startswith('q='):
                try: q=float(bit.strip()[2:])
                except ValueError: q=0
        matches.append(({'application/json':2,'application/*':1,'*/*':0}[media],q))
    return bool(matches) and max(matches)[1]>0

@app.middleware('http')
async def representation(request,call_next):
    if request.url.path.startswith('/api/'):
        if not accepts_json(request.headers.get('accept','*/*')):
            return JSONResponse({'error':{'code':'HTTP_406','message':'Only application/json is available','detail':None}},status_code=406)
        if request.method in ('POST','PUT','PATCH') and request.headers.get('content-type','').split(';')[0].lower()!='application/json':
            return JSONResponse({'error':{'code':'HTTP_415','message':'Send Content-Type: application/json','detail':None}},status_code=415)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    return response

def principal(auth: HTTPAuthorizationCredentials | None = Depends(security)):
    if auth is None: fail(401,'A bearer credential is required')
    token=auth.credentials
    admin=os.getenv('PROVISIONING_TOKEN','')
    if admin and hmac.compare_digest(token,admin): return {'kind':'provisioner'}
    hashed=digest(token)
    with connect() as db:
        user=db.execute('SELECT * FROM users WHERE token_hash=?',(hashed,)).fetchone()
        if user: return {'kind':'user',**dict(user)}
        device=db.execute('SELECT id FROM installations WHERE token_hash=?',(hashed,)).fetchone()
        if device: return {'kind':'device','installation_id':device['id']}
    fail(401,'Invalid bearer credential')

def reader(p=Depends(principal)):
    if p['kind']!='user': fail(403,'Only SLSEA readers may use this resource')
    return p

def provisioner(p=Depends(principal)):
    if p['kind']!='provisioner': fail(403,'Provisioning credential required')
    return p

# Each read joins upward to enforce jurisdiction before returning data or cache metadata.
JOINS=' FROM installations i JOIN substations s ON s.id=i.substation_id JOIN districts d ON d.id=s.district_id JOIN provinces p ON p.id=d.province_id '
PUBLIC='i.id,i.name,i.meter_id,i.capacity_kw,i.substation_id,i.version'

def scope(user):
    if user['role']=='province': return 'p.id=?',[user['province_id']]
    if user['role']=='district': return 'd.id=?',[user['district_id']]
    return '1=1',[]

def query(sql,args=()):
    with connect() as db: return [dict(r) for r in db.execute(sql,args).fetchall()]

def one(sql,args=()):
    rows=query(sql,args)
    if not rows: fail(404,'Resource not found in your scope')
    return rows[0]

def installation(iid,user):
    clause,args=scope(user)
    return one('SELECT '+PUBLIC+JOINS+' WHERE i.id=? AND '+clause,[iid,*args])

def etag(data):
    return '"'+hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()+'"'

def respond(request,data,status=200,headers=None):
    tag=etag(data)
    h={'ETag':tag,'Cache-Control':'private, no-cache','Vary':'Authorization, Accept',**(headers or {})}
    values=[x.strip().removeprefix('W/') for x in request.headers.get('if-none-match','').split(',')]
    if request.method in ('GET','HEAD') and ('*' in values or tag in values):
        return Response(status_code=304,headers=h)
    return JSONResponse(data,status_code=status,headers=h)

def collection(request,items):
    return respond(request,{'items':items,'total':len(items)})

@app.get('/health',tags=['Operations'])
def health():
    with connect() as db: db.execute('SELECT 1').fetchone()
    return {'status':'ok'}

@app.get('/api/v1/provinces',response_model=contracts.ProvinceCollection,tags=['Hierarchy'])
def provinces(request:Request,u=Depends(reader)):
    clause,args=scope(u)
    return collection(request,query('SELECT DISTINCT p.* FROM provinces p JOIN districts d ON d.province_id=p.id WHERE '+clause+' ORDER BY p.id',args))

@app.get('/api/v1/provinces/{province_id}',response_model=contracts.Province,tags=['Hierarchy'])
def province(province_id:int,request:Request,u=Depends(reader)):
    clause,args=scope(u)
    return respond(request,one('SELECT DISTINCT p.* FROM provinces p JOIN districts d ON d.province_id=p.id WHERE p.id=? AND '+clause,[province_id,*args]))

@app.get('/api/v1/provinces/{province_id}/districts',response_model=contracts.DistrictCollection,tags=['Hierarchy'])
def districts(province_id:int,request:Request,u=Depends(reader)):
    province(province_id,request,u)
    clause,args=scope(u)
    return collection(request,query('SELECT d.* FROM districts d JOIN provinces p ON p.id=d.province_id WHERE p.id=? AND '+clause+' ORDER BY d.id',[province_id,*args]))

@app.get('/api/v1/districts/{district_id}',response_model=contracts.District,tags=['Hierarchy'])
def district(district_id:int,request:Request,u=Depends(reader)):
    clause,args=scope(u)
    return respond(request,one('SELECT d.* FROM districts d JOIN provinces p ON p.id=d.province_id WHERE d.id=? AND '+clause,[district_id,*args]))

@app.get('/api/v1/districts/{district_id}/grid-substations',response_model=contracts.SubstationCollection,tags=['Hierarchy'])
def substations(district_id:int,request:Request,u=Depends(reader)):
    district(district_id,request,u)
    return collection(request,query('SELECT * FROM substations WHERE district_id=? ORDER BY id',[district_id]))

@app.get('/api/v1/grid-substations/{substation_id}',response_model=contracts.Substation,tags=['Hierarchy'])
def substation(substation_id:int,request:Request,u=Depends(reader)):
    clause,args=scope(u)
    return respond(request,one('SELECT s.* FROM substations s JOIN districts d ON d.id=s.district_id JOIN provinces p ON p.id=d.province_id WHERE s.id=? AND '+clause,[substation_id,*args]))

@app.get('/api/v1/grid-substations/{substation_id}/installations',response_model=contracts.InstallationCollection,tags=['Hierarchy'])
def installations(substation_id:int,request:Request,u=Depends(reader)):
    substation(substation_id,request,u)
    return collection(request,query('SELECT '+PUBLIC+' FROM installations i WHERE substation_id=? ORDER BY id',[substation_id]))

@app.get('/api/v1/installations/{installation_id}',response_model=contracts.Installation,tags=['Installations'])
def get_installation(installation_id:int,request:Request,u=Depends(reader)):
    return respond(request,installation(installation_id,u))

@app.get('/api/v1/installations/{installation_id}/overview',response_model=contracts.Overview,tags=['Installations'])
def overview(installation_id:int,request:Request,u=Depends(reader)):
    item=installation(installation_id,u)
    related=one('SELECT p.name AS province,d.name AS district,s.name AS substation'+JOINS+' WHERE i.id=?',[installation_id])
    readings=query('SELECT * FROM readings WHERE installation_id=? ORDER BY timestamp DESC LIMIT 1',[installation_id])
    return respond(request,{'installation':item,'hierarchy':related,'last_known_reading':readings[0] if readings else None})

@app.get('/api/v1/installations/{installation_id}/last-known-reading',response_model=contracts.Reading,tags=['Readings'])
def latest(installation_id:int,request:Request,u=Depends(reader)):
    installation(installation_id,u)
    return respond(request,one('SELECT * FROM readings WHERE installation_id=? ORDER BY timestamp DESC LIMIT 1',[installation_id]))

def timestamp(value):
    if value.tzinfo is None or value.utcoffset() is None: fail(400,'Timestamps must include a UTC offset')
    return value.astimezone(timezone.utc).isoformat(timespec='microseconds')

class HistoryQuery:
    def __init__(self, page:int=Query(1,ge=1),page_size:int=Query(50,ge=1,le=200),
                 sort:Literal['timestamp','-timestamp']='-timestamp',
                 start:datetime|None=None,end:datetime|None=None,
                 province_id:int|None=None,district_id:int|None=None,substation_id:int|None=None):
        self.page,self.page_size,self.sort=page,page_size,sort
        self.start=timestamp(start) if start else None
        self.end=timestamp(end) if end else None
        if self.start and self.end and self.start>self.end: fail(400,'start must be before or equal to end')
        self.filters={'p.id':province_id,'d.id':district_id,'s.id':substation_id}

def history(request,u,q,iid=None):
    clause,args=scope(u)
    clauses=[clause]
    for column,value in q.filters.items():
        if value is not None: clauses.append(column+'=?'); args.append(value)
    if iid is not None: clauses.append('i.id=?'); args.append(iid)
    if q.start: clauses.append('r.timestamp>=?'); args.append(q.start)
    if q.end: clauses.append('r.timestamp<=?'); args.append(q.end)
    base=JOINS+' JOIN readings r ON r.installation_id=i.id WHERE '+' AND '.join(clauses)
    direction='ASC' if q.sort=='timestamp' else 'DESC'
    # One transaction gives count and rows the same snapshot during concurrent ingestion.
    with connect() as db:
        db.execute('BEGIN')
        count=db.execute('SELECT COUNT(*)'+base,args).fetchone()[0]
        rows=[dict(x) for x in db.execute('SELECT r.*'+base+f' ORDER BY r.timestamp {direction},r.id {direction} LIMIT ? OFFSET ?',[*args,q.page_size,(q.page-1)*q.page_size])]
    def link(page):
        # Relative links work correctly behind HTTPS reverse proxies.
        url=request.url.include_query_params(page=page)
        return url.path+'?'+url.query
    return respond(request,{'items':rows,'total':count,'page':q.page,'page_size':q.page_size,
                            'next':link(q.page+1) if q.page*q.page_size<count else None,
                            'previous':link(q.page-1) if q.page>1 else None})

@app.get('/api/v1/readings',response_model=contracts.ReadingPage,tags=['Readings'])
def all_readings(request:Request,q:HistoryQuery=Depends(),u=Depends(reader)):
    return history(request,u,q)

@app.get('/api/v1/installations/{installation_id}/readings',response_model=contracts.ReadingPage,tags=['Readings'])
def scoped_readings(installation_id:int,request:Request,q:HistoryQuery=Depends(),u=Depends(reader)):
    installation(installation_id,u)
    return history(request,u,q,installation_id)

@app.get('/api/v1/installations/{installation_id}/readings/{reading_id}',response_model=contracts.Reading,tags=['Readings'])
def reading(installation_id:int,reading_id:int,request:Request,u=Depends(reader)):
    installation(installation_id,u)
    return respond(request,one('SELECT * FROM readings WHERE id=? AND installation_id=?',[reading_id,installation_id]))

class ReadingInput(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    timestamp:datetime
    power_kw:float=Field(ge=0)
    energy_kwh:float=Field(ge=0)
    voltage:float=Field(gt=0,le=1000)
    @field_validator('timestamp')
    @classmethod
    def aware(cls,value):
        if value.tzinfo is None or value.utcoffset() is None: raise ValueError('Include a UTC offset')
        if value>datetime.now(timezone.utc)+timedelta(minutes=5): raise ValueError('Timestamp is too far in the future')
        return value

@app.post('/api/v1/installations/{installation_id}/readings',response_model=contracts.Reading,status_code=201,tags=['Ingestion'],
 responses={201:{'description':'Reading created; Location identifies its resource','headers':{'Location':{'schema':{'type':'string'}}}}})
def ingest(installation_id:int,body:ReadingInput,request:Request,p=Depends(principal)):
    if p['kind']!='device' or p['installation_id']!=installation_id: fail(403,'A meter may only append readings to its own installation')
    stamp=timestamp(body.timestamp)
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        # Validate both neighbors, so late arrivals cannot break cumulative energy order.
        before=db.execute('SELECT energy_kwh FROM readings WHERE installation_id=? AND timestamp<? ORDER BY timestamp DESC LIMIT 1',[installation_id,stamp]).fetchone()
        after=db.execute('SELECT energy_kwh FROM readings WHERE installation_id=? AND timestamp>? ORDER BY timestamp LIMIT 1',[installation_id,stamp]).fetchone()
        if (before and body.energy_kwh<before[0]) or (after and body.energy_kwh>after[0]): fail(409,'Cumulative energy would contradict neighboring readings','Meter resets require a separate future design.')
        try:
            cur=db.execute('INSERT INTO readings(installation_id,timestamp,power_kw,energy_kwh,voltage) VALUES (?,?,?,?,?)',
                           [installation_id,stamp,body.power_kw,body.energy_kwh,body.voltage])
        except sqlite3.IntegrityError: fail(409,'A reading already exists for this installation and timestamp')
        item=dict(db.execute('SELECT * FROM readings WHERE id=?',[cur.lastrowid]).fetchone())
    return respond(request,item,201,{'Location':f'/api/v1/installations/{installation_id}/readings/{item["id"]}'})

class InstallationInput(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    name:str=Field(min_length=1,max_length=150)
    meter_id:str=Field(min_length=1,max_length=100)
    capacity_kw:float=Field(gt=0,le=10000)
    substation_id:int=Field(gt=0)

@app.post('/api/v1/installations',response_model=contracts.CreatedInstallation,status_code=201,tags=['Provisioning'])
def create_installation(body:InstallationInput,request:Request,p=Depends(provisioner)):
    token=secrets.token_urlsafe(32)
    with connect() as db:
        try:
            cur=db.execute('INSERT INTO installations(name,meter_id,capacity_kw,substation_id,token_hash) VALUES (?,?,?,?,?)',
                           [body.name,body.meter_id,body.capacity_kw,body.substation_id,digest(token)])
        except sqlite3.IntegrityError: fail(409,'Meter ID must be unique and substation must exist')
        item=dict(db.execute('SELECT '+PUBLIC+' FROM installations i WHERE id=?',[cur.lastrowid]).fetchone())
    return JSONResponse({'installation':item,'device_token':token},status_code=201,
                        headers={'Location':f'/api/v1/installations/{item["id"]}','Cache-Control':'no-store','ETag':etag(item)})

@app.put('/api/v1/installations/{installation_id}',response_model=contracts.Installation,tags=['Provisioning'])
def replace_installation(installation_id:int,body:InstallationInput,request:Request,p=Depends(provisioner)):
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT '+PUBLIC+' FROM installations i WHERE id=?',[installation_id]).fetchone()
        if not row: fail(404,'Installation not found')
        current=dict(row)
        if not request.headers.get('if-match'): fail(428,'Supply the current ETag in If-Match')
        if etag(current) not in [v.strip() for v in request.headers['if-match'].split(',')]: fail(412,'Installation changed; retrieve its current ETag')
        if any(current[k]!=v for k,v in body.model_dump().items()):
            try:
                db.execute('UPDATE installations SET name=?,meter_id=?,capacity_kw=?,substation_id=?,version=version+1 WHERE id=?',
                           [body.name,body.meter_id,body.capacity_kw,body.substation_id,installation_id])
            except sqlite3.IntegrityError: fail(409,'Meter ID must be unique and substation must exist')
        item=dict(db.execute('SELECT '+PUBLIC+' FROM installations i WHERE id=?',[installation_id]).fetchone())
    return respond(request,item)

@app.delete('/api/v1/installations/{installation_id}',status_code=204,tags=['Provisioning'])
def delete_installation(installation_id:int,p=Depends(provisioner)):
    with connect() as db:
        try: db.execute('DELETE FROM installations WHERE id=?',[installation_id])
        except sqlite3.IntegrityError: fail(409,'Cannot delete an installation with immutable reading history')
    return Response(status_code=204)

@app.get('/api/v1/districts/{district_id}/generation-summary',response_model=contracts.Summary,tags=['Summaries'])
def summary(district_id:int,request:Request,u=Depends(reader)):
    district(district_id,request,u)
    now=datetime.now(timezone.utc)
    midnight=now.astimezone(ZoneInfo('Asia/Colombo')).replace(hour=0,minute=0,second=0,microsecond=0)
    start=timestamp(midnight)
    cutoff=timestamp(now-timedelta(minutes=30))
    ids=query('SELECT i.id'+JOINS+' WHERE d.id=?',[district_id])
    power=energy=0.0
    fresh=complete=0
    with connect() as db:
        db.execute('BEGIN')
        for item in ids:
            iid=item['id']
            latest_row=db.execute('SELECT * FROM readings WHERE installation_id=? AND timestamp<=? ORDER BY timestamp DESC LIMIT 1',[iid,timestamp(now)]).fetchone()
            baseline=db.execute('SELECT * FROM readings WHERE installation_id=? AND timestamp<=? ORDER BY timestamp DESC LIMIT 1',[iid,start]).fetchone()
            if latest_row and latest_row['timestamp']>=cutoff:
                power+=latest_row['power_kw']; fresh+=1
            if latest_row and baseline and latest_row['timestamp']>=start:
                energy+=latest_row['energy_kwh']-baseline['energy_kwh']; complete+=1
    # Power excludes readings older than 30 minutes; energy is an interval estimate.
    return respond(request,{'district_id':district_id,'local_date':midnight.date().isoformat(),
      'timezone':'Asia/Colombo','fresh_power_kw':round(power,3),'estimated_today_energy_kwh':round(energy,4),
      'installation_count':len(ids),'fresh_installation_count':fresh,'stale_or_missing_count':len(ids)-fresh,
      'energy_covered_installation_count':complete,'freshness_minutes':30,
      'energy_method':'latest cumulative value minus last value at/before local midnight; boundary gaps are approximate'})


def documented_openapi():
    from fastapi.openapi.utils import get_openapi
    if app.openapi_schema:
        return app.openapi_schema
    schema=get_openapi(title=app.title,version=app.version,description=app.description,routes=app.routes)
    for path, operations in schema['paths'].items():
        for method,operation in operations.items():
            if method=='get' and path.startswith('/api/'):
                operation.setdefault('parameters',[]).append({'name':'If-None-Match','in':'header','required':False,'schema':{'type':'string'},'description':'ETag from a previous response; a match returns 304 with no body.'})
                operation['responses']['304']={'description':'Not modified; empty response body'}
                operation['responses']['200'].setdefault('headers',{})['ETag']={'schema':{'type':'string'},'description':'Representation fingerprint'}
            if method=='put':
                operation.setdefault('parameters',[]).append({'name':'If-Match','in':'header','required':True,'schema':{'type':'string'},'description':'Current installation ETag; stale values fail with 412.'})
            if method=='post':
                operation['responses']['201'].setdefault('headers',{})['Location']={'schema':{'type':'string'},'description':'Relative URI of the created resource'}
    app.openapi_schema=schema
    return schema

app.openapi=documented_openapi
