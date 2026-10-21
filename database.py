from __future__ import annotations
import sqlite3
from pathlib import Path
from decimal import Decimal
import bcrypt

DB_PATH = Path(__file__).resolve().with_name('novasure_claims.db')

def db_connect():
    c=sqlite3.connect(DB_PATH,timeout=30); c.row_factory=sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON'); c.execute('PRAGMA journal_mode=WAL'); c.execute('PRAGMA busy_timeout=30000')
    return c

def init_db():
    with db_connect() as c:
        c.executescript('''
CREATE TABLE IF NOT EXISTS app_users(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT UNIQUE COLLATE NOCASE NOT NULL,display_name TEXT NOT NULL,password_hash TEXT NOT NULL,role TEXT NOT NULL,reserve_authority REAL DEFAULT 0,is_active INTEGER DEFAULT 1,last_login_at TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS claims(id INTEGER PRIMARY KEY AUTOINCREMENT,claim_number TEXT UNIQUE NOT NULL,policy_number TEXT NOT NULL,insured_entity TEXT NOT NULL,claimant_name TEXT NOT NULL,claimant_email TEXT,claimant_phone TEXT,lob TEXT NOT NULL,claim_type TEXT NOT NULL,jurisdiction_state TEXT NOT NULL,incident_date TEXT NOT NULL,reported_date TEXT NOT NULL,status TEXT DEFAULT 'New',priority TEXT DEFAULT 'Medium',incident_location TEXT,incident_narrative TEXT NOT NULL,incurred_reserve REAL DEFAULT 0,assigned_adjuster_id INTEGER,created_by INTEGER NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(assigned_adjuster_id) REFERENCES app_users(id),FOREIGN KEY(created_by) REFERENCES app_users(id));
CREATE TABLE IF NOT EXISTS entities(id INTEGER PRIMARY KEY AUTOINCREMENT,entity_name TEXT NOT NULL,entity_type TEXT NOT NULL,contact_name TEXT,email TEXT,phone TEXT,address TEXT,is_active INTEGER DEFAULT 1,created_by INTEGER NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(created_by) REFERENCES app_users(id));
CREATE TABLE IF NOT EXISTS attachments(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,document_class TEXT NOT NULL,document_type TEXT NOT NULL,lob TEXT NOT NULL,claim_type TEXT NOT NULL,claim_id INTEGER NOT NULL,file_name TEXT NOT NULL,mime_type TEXT NOT NULL,file_bytes BLOB NOT NULL,verification_status TEXT DEFAULT 'Unverified',adjuster_notes TEXT,uploaded_by INTEGER NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(claim_id) REFERENCES claims(id) ON DELETE CASCADE,FOREIGN KEY(uploaded_by) REFERENCES app_users(id));
CREATE TABLE IF NOT EXISTS audit_log(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,action_type TEXT NOT NULL,object_type TEXT NOT NULL,object_id INTEGER,details TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(user_id) REFERENCES app_users(id));
CREATE INDEX IF NOT EXISTS idx_claim_search ON claims(claim_number,policy_number,insured_entity,claimant_name);
''')
        if not c.execute('SELECT 1 FROM app_users WHERE username=?',('admin',)).fetchone():
            h=bcrypt.hashpw(b'pass123',bcrypt.gensalt()).decode()
            c.execute('INSERT INTO app_users(username,display_name,password_hash,role,reserve_authority) VALUES(?,?,?,?,?)',('admin','NovaSure Administrator',h,'Claims Admin',999999999.99))

def _p(p): return tuple(float(x) if isinstance(x,Decimal) else x for x in p)
def one(sql,p=()):
    with db_connect() as c:
        r=c.execute(sql,_p(p)).fetchone(); return dict(r) if r else None
def all(sql,p=()):
    with db_connect() as c: return [dict(r) for r in c.execute(sql,_p(p)).fetchall()]
def run(sql,p=()):
    with db_connect() as c: return int(c.execute(sql,_p(p)).lastrowid or 0)
def validate_login(u,p):
    x=one('SELECT * FROM app_users WHERE username=? COLLATE NOCASE AND is_active=1',(u.strip(),))
    if not x or not bcrypt.checkpw(p.encode(),x['password_hash'].encode()): return None
    run('UPDATE app_users SET last_login_at=CURRENT_TIMESTAMP WHERE id=?',(x['id'],)); x.pop('password_hash',None); return x
def audit(uid,a,o,oid,d=''): run('INSERT INTO audit_log(user_id,action_type,object_type,object_id,details) VALUES(?,?,?,?,?)',(uid,a,o,oid,d))
def users(): return all('SELECT id,username,display_name,role,reserve_authority,is_active,last_login_at,created_at FROM app_users ORDER BY display_name')
def create_user(u,n,p,r,limit):
    if len(p)<8: raise ValueError('Password must be at least 8 characters.')
    try: return run('INSERT INTO app_users(username,display_name,password_hash,role,reserve_authority) VALUES(?,?,?,?,?)',(u.strip(),n.strip(),bcrypt.hashpw(p.encode(),bcrypt.gensalt()).decode(),r,limit))
    except sqlite3.IntegrityError as e: raise ValueError('Username already exists.') from e
def set_active(i,v): run('UPDATE app_users SET is_active=? WHERE id=?',(1 if v else 0,i))
def adjusters(): return all("SELECT u.id,u.display_name,u.role,COUNT(c.id) active_cases FROM app_users u LEFT JOIN claims c ON c.assigned_adjuster_id=u.id AND c.status NOT IN ('Closed','Denied') WHERE u.is_active=1 AND u.role IN ('Claims Admin','Senior Claims Adjuster','Claims Triage Specialist') GROUP BY u.id ORDER BY active_cases,u.display_name")
def create_claim(d,uid):
    with db_connect() as c:
        c.execute('BEGIN IMMEDIATE'); n=c.execute('SELECT COALESCE(MAX(id),0)+1 FROM claims').fetchone()[0]; num=f'NS-2026-{n:04d}'
        cur=c.execute('''INSERT INTO claims(claim_number,policy_number,insured_entity,claimant_name,claimant_email,claimant_phone,lob,claim_type,jurisdiction_state,incident_date,reported_date,status,priority,incident_location,incident_narrative,incurred_reserve,assigned_adjuster_id,created_by) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(num,d['policy_number'],d['insured_entity'],d['claimant_name'],d.get('claimant_email'),d.get('claimant_phone'),d['lob'],d['claim_type'],d['jurisdiction_state'],str(d['incident_date']),str(d['reported_date']),d.get('status','New'),d.get('priority','Medium'),d.get('incident_location'),d['incident_narrative'],d.get('incurred_reserve',0),d.get('assigned_adjuster_id'),uid)); return int(cur.lastrowid),num
def recent(limit=100): return all('''SELECT c.*,u.display_name assigned_adjuster FROM claims c LEFT JOIN app_users u ON u.id=c.assigned_adjuster_id ORDER BY c.id DESC LIMIT ?''',(limit,))
def search(q='',lob='All',status='All',state='All',priority='All',lo=0,hi=999999999):
    w=['incurred_reserve BETWEEN ? AND ?']; p=[lo,hi]
    if q.strip(): w+=['(claim_number LIKE ? OR policy_number LIKE ? OR insured_entity LIKE ? OR claimant_name LIKE ?)']; p += [f'%{q.strip()}%']*4
    for col,val in [('lob',lob),('status',status),('jurisdiction_state',state),('priority',priority)]:
        if val!='All': w+=[f'{col}=?']; p+=[val]
    return all('SELECT * FROM claims WHERE '+' AND '.join(w)+' ORDER BY id DESC LIMIT 500',p)
def create_entity(d,uid): return run('INSERT INTO entities(entity_name,entity_type,contact_name,email,phone,address,created_by) VALUES(?,?,?,?,?,?,?)',(d['entity_name'],d['entity_type'],d.get('contact_name'),d.get('email'),d.get('phone'),d.get('address'),uid))
def entities(q='',t='All'):
    w=['1=1']; p=[]
    if q.strip(): w+=['(entity_name LIKE ? OR contact_name LIKE ? OR email LIKE ?)']; p += [f'%{q.strip()}%']*3
    if t!='All': w+=['entity_type=?']; p+=[t]
    return all('SELECT * FROM entities WHERE '+' AND '.join(w)+' ORDER BY entity_name',p)
def save_attachment(m,name,mime,b,uid): return run('INSERT INTO attachments(title,document_class,document_type,lob,claim_type,claim_id,file_name,mime_type,file_bytes,uploaded_by) VALUES(?,?,?,?,?,?,?,?,?,?)',(m['title'],m['document_class'],m['document_type'],m['lob'],m['claim_type'],m['claim_id'],name,mime,b,uid))
def attachments(): return all('SELECT a.id,a.title,a.document_class,a.document_type,a.lob,a.claim_type,c.claim_number,a.file_name,a.mime_type,LENGTH(a.file_bytes) file_size,a.verification_status,a.adjuster_notes,a.created_at FROM attachments a JOIN claims c ON c.id=a.claim_id ORDER BY a.id DESC')
def attachment(i): return one('SELECT * FROM attachments WHERE id=?',(i,))
def update_attachment(i,s,n): run('UPDATE attachments SET verification_status=?,adjuster_notes=? WHERE id=?',(s,n,i))
def kpis(): return one("SELECT (SELECT COUNT(*) FROM claims) total_claims,(SELECT COUNT(*) FROM attachments) total_docs,(SELECT COUNT(*) FROM entities WHERE is_active=1) total_entities,(SELECT COUNT(*) FROM app_users WHERE is_active=1) active_users,(SELECT COALESCE(SUM(incurred_reserve),0) FROM claims WHERE status NOT IN ('Closed','Denied')) reserve,(SELECT COUNT(DISTINCT insured_entity) FROM claims) insureds")
def by_lob(): return all('SELECT lob,COUNT(*) claim_count,COALESCE(SUM(incurred_reserve),0) reserve FROM claims GROUP BY lob ORDER BY lob')
