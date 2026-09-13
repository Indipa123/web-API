import json
import sqlite3
from datetime import datetime,timedelta,timezone
import pytest
from fastapi.testclient import TestClient
from app.db import connect
from app.seed import seed
from app.main import app

@pytest.fixture(scope='module')
def setup(tmp_path_factory):
    import os
    path=tmp_path_factory.mktemp('db')
    os.environ['DATABASE_PATH']=str(path/'solar.db')
    os.environ['CREDENTIALS_PATH']=str(path/'credentials.json')
    os.environ['PROVISIONING_TOKEN']='test-only-provisioning-secret'
    seed()
    tokens=json.loads((path/'credentials.json').read_text())
    with TestClient(app) as client:
        yield client,tokens

def auth(token): return {'Authorization':'Bearer '+token}
def get(setup,path,who='user_1_national',**kwargs):
    c,t=setup
    return c.get('/api/v1'+path,headers={**auth(t[who]),**kwargs.pop('headers',{})},**kwargs)

def test_seed(setup):
    with connect() as db:
        assert [db.execute('SELECT COUNT(*) FROM '+x).fetchone()[0] for x in ['provinces','districts','substations','installations','readings']]==[9,25,25,200,134600]
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
    assert seed() is False

@pytest.mark.parametrize('path',['/provinces','/provinces/1','/provinces/1/districts','/districts/1','/districts/1/grid-substations','/grid-substations/1','/grid-substations/1/installations','/installations/1','/installations/1/overview','/installations/1/last-known-reading','/installations/1/readings','/readings','/districts/1/generation-summary'])
def test_reads_cache(setup,path):
    r=get(setup,path)
    assert r.status_code==200,r.text
    cached=get(setup,path,headers={'If-None-Match':r.headers['etag']})
    assert cached.status_code==304 and cached.content==b''
    assert 'Authorization' in cached.headers['vary']

@pytest.mark.parametrize('path',['/districts/2','/districts/2/grid-substations','/grid-substations/2','/grid-substations/2/installations','/installations/2','/installations/2/overview','/installations/2/last-known-reading','/installations/2/readings','/districts/2/generation-summary'])
def test_district_boundary(setup,path):
    assert get(setup,path,'user_3_district').status_code==404

def test_scope_collections(setup):
    assert get(setup,'/provinces','user_3_district').json()['total']==1
    assert get(setup,'/provinces/1/districts','user_3_district').json()['total']==1
    assert get(setup,'/readings?district_id=2','user_3_district').json()['total']==0
    assert get(setup,'/districts/4','user_2_province').status_code==404
    assert get(setup,'/provinces/1/districts','user_2_province').json()['total']==3

def test_auth(setup):
    c,t=setup
    assert c.get('/api/v1/provinces').status_code==401
    assert c.get('/api/v1/provinces',headers=auth('wrong')).status_code==401
    assert get(setup,'/provinces','installation_1').status_code==403

def test_history(setup):
    r=get(setup,'/installations/1/readings?page_size=2&sort=timestamp').json()
    assert r['total']==673 and len(r['items'])==2 and r['previous'] is None
    c,t=setup
    second=c.get(r['next'],headers=auth(t['user_1_national'])).json()
    assert second['items'][0]['timestamp']>r['items'][-1]['timestamp']
    stamp=r['items'][0]['timestamp']
    assert get(setup,'/readings',params={'start':stamp,'end':stamp,'district_id':1}).json()['total']==8
    assert get(setup,'/readings?page_size=201').status_code==422
    assert get(setup,'/readings?sort=invalid').status_code==422
    assert get(setup,'/readings?start=2026-01-01T00:00:00').status_code==400
    assert get(setup,'/readings?start=2026-02-01T00:00:00Z&end=2026-01-01T00:00:00Z').status_code==400

def test_ingestion(setup):
    c,t=setup
    latest=get(setup,'/installations/1/last-known-reading').json()
    body={'timestamp':datetime.now(timezone.utc).isoformat(),'power_kw':2,'energy_kwh':latest['energy_kwh']+1,'voltage':230}
    for who,iid in [('user_1_national',1),('installation_2',1)]:
        assert c.post(f'/api/v1/installations/{iid}/readings',json=body,headers=auth(t[who])).status_code==403
    r=c.post('/api/v1/installations/1/readings',json=body,headers=auth(t['installation_1']))
    assert r.status_code==201,r.text
    assert c.get(r.headers['location'],headers=auth(t['user_1_national'])).json()==r.json()
    assert c.post('/api/v1/installations/1/readings',json=body,headers=auth(t['installation_1'])).status_code==409
    assert get(setup,'/installations/1/last-known-reading').json()['id']==r.json()['id']
    assert c.put(r.headers['location'],json=body,headers=auth(t['installation_1'])).status_code==405
    assert c.delete(r.headers['location'],headers=auth(t['installation_1'])).status_code==405
    body['timestamp']=(datetime.now(timezone.utc)+timedelta(seconds=1)).isoformat()
    body['energy_kwh']=0
    assert c.post('/api/v1/installations/1/readings',json=body,headers=auth(t['installation_1'])).status_code==409
    body['power_kw']=-1
    assert c.post('/api/v1/installations/1/readings',json=body,headers=auth(t['installation_1'])).status_code==422

def test_db_immutable(setup):
    with connect() as db:
        with pytest.raises(sqlite3.IntegrityError): db.execute('UPDATE readings SET power_kw=0 WHERE id=1')
        with pytest.raises(sqlite3.IntegrityError): db.execute('DELETE FROM readings WHERE id=1')

def test_provisioning(setup):
    c,t=setup
    headers=auth('test-only-provisioning-secret')
    body={'name':'Test installation','meter_id':'TEST-201','capacity_kw':5,'substation_id':1}
    assert c.post('/api/v1/installations',json=body,headers=auth(t['user_1_national'])).status_code==403
    r=c.post('/api/v1/installations',json=body,headers=headers)
    assert r.status_code==201,r.text
    url=r.headers['location']; tag=r.headers['etag']
    assert 'token_hash' not in r.text
    assert c.put(url,json=body,headers=headers).status_code==428
    assert c.put(url,json=body,headers={**headers,'If-Match':'"wrong"'}).status_code==412
    body['name']='Changed'
    updated=c.put(url,json=body,headers={**headers,'If-Match':tag})
    assert updated.status_code==200
    again=c.put(url,json=body,headers={**headers,'If-Match':updated.headers['etag']})
    assert again.json()==updated.json()
    assert c.put(url,json=body,headers={**headers,'If-Match':tag}).status_code==412
    assert c.delete(url,headers=headers).status_code==204
    assert c.delete(url,headers=headers).status_code==204
    assert c.delete('/api/v1/installations/1',headers=headers).status_code==409

def test_errors_and_docs(setup):
    c,t=setup
    for path,headers,code in [('/provinces',{'Accept':'text/html'},406),('/provinces',{'Accept':'application/json;q=0, */*;q=1'},406),('/missing',{},404)]:
        r=get(setup,path,headers=headers)
        assert r.status_code==code
        assert set(r.json()['error'])=={'code','message','detail'}
    assert c.post('/api/v1/installations/1/readings',content='x',headers=auth(t['installation_1'])).status_code==415
    assert c.get('/docs').status_code==200
    spec=c.get('/openapi.json').json()
    assert 'HTTPBearer' in spec['components']['securitySchemes']
    assert 'post' in spec['paths']['/api/v1/installations/{installation_id}/readings']
