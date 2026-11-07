"""Almacenamiento compartido con control de concurrencia (CAS)."""
from __future__ import annotations
import json, os, sqlite3
from urllib.parse import quote
import requests
from game import initial_state, apply_action

class BusyError(Exception): pass

class SQLiteStore:
    def __init__(self,path='data/game.sqlite3'):
        os.makedirs(os.path.dirname(path) or '.',exist_ok=True)
        self.path=path
        with self._con() as con:
            con.execute('CREATE TABLE IF NOT EXISTS game_rooms (room_id TEXT PRIMARY KEY, version INTEGER NOT NULL, snapshot TEXT NOT NULL)')
    def _con(self):
        con=sqlite3.connect(self.path,timeout=10)
        con.execute('PRAGMA journal_mode=WAL')
        return con
    def read(self,room):
        with self._con() as c:
            row=c.execute('SELECT version,snapshot FROM game_rooms WHERE room_id=?',(room,)).fetchone()
            if row is None:
                c.execute('INSERT OR IGNORE INTO game_rooms VALUES (?,?,?)',(room,0,json.dumps(initial_state())))
                row=c.execute('SELECT version,snapshot FROM game_rooms WHERE room_id=?',(room,)).fetchone()
            return int(row[0]),json.loads(row[1])
    def commit(self,room,version,snapshot,action_id):
        with self._con() as c:
            c.execute('BEGIN IMMEDIATE')
            cur=c.execute('UPDATE game_rooms SET version=version+1,snapshot=? WHERE room_id=? AND version=?',
                          (json.dumps(snapshot,ensure_ascii=False),room,version))
            return cur.rowcount==1
    def apply(self,room,action):
        for _ in range(12):
            version,s=self.read(room)
            if action['id'] in s.get('applied_ids',[]):return version,s
            new=apply_action(s,action)
            new['applied_ids']=(s.get('applied_ids',[])+[action['id']])[-300:]
            if self.commit(room,version,new,action['id']):return version+1,new
        raise BusyError('Conflicto por varias acciones simultáneas. Actualiza y reintenta.')

class SupabaseStore:
    def __init__(self,url,key):
        self.base=url.rstrip('/')+'/rest/v1'
        self.session=requests.Session()
        self.headers={'apikey':key,'Content-Type':'application/json','Accept':'application/json'}
        if not key.startswith('sb_secret_'):
            self.headers['Authorization']='Bearer '+key
    def _call(self,method,uri,body=None,headers=None):
        h={**self.headers,**(headers or {})}
        resp=self.session.request(method,self.base+uri,headers=h,json=body,timeout=12)
        if resp.status_code>=400:raise RuntimeError('Supabase HTTP '+str(resp.status_code)+': '+resp.text[:350])
        return resp.json() if resp.content else None
    def read(self,room):
        path='/game_rooms?room_id=eq.'+quote(room,safe='')+'&select=version,snapshot'
        obj=self._call('GET',path)
        if not obj:
            self._call('POST','/game_rooms',[{'room_id':room,'version':0,'snapshot':initial_state()}],
                       headers={'Prefer':'resolution=ignore-duplicates,return=minimal'})
            obj=self._call('GET',path)
        if not obj:raise RuntimeError('Sala no creada. Ejecuta schema.sql en Supabase.')
        return int(obj[0]['version']),obj[0]['snapshot']
    def apply(self,room,action):
        for _ in range(12):
            version,s=self.read(room)
            if action['id'] in s.get('applied_ids',[]):return version,s
            new=apply_action(s,action)
            new['applied_ids']=(s.get('applied_ids',[])+[action['id']])[-300:]
            ok=self._call('POST','/rpc/game_commit',{'p_room_id':room,'p_expected_version':version,
                                                     'p_snapshot':new,'p_event_id':action['id']})
            if ok is None:raise RuntimeError('game_commit no existe; ejecutar schema.sql')
            if int(ok)>=0:return int(ok),new
        raise BusyError('Conflicto de escritura. Comprueba actividad y reintenta.')

def create_store(config):
    url=config.get('SUPABASE_URL') or os.environ.get('SUPABASE_URL')
    key=(config.get('SUPABASE_SECRET_KEY') or os.environ.get('SUPABASE_SECRET_KEY') or
         config.get('SUPABASE_SERVICE_ROLE_KEY') or os.environ.get('SUPABASE_SERVICE_ROLE_KEY'))
    if url and key:return SupabaseStore(url,key),True
    return SQLiteStore(),False
