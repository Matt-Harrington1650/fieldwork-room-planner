"""Append-only local project revisions and reproducible solve records."""
import hashlib,json,sqlite3,uuid
from datetime import datetime,timezone
from pathlib import Path

class Store:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,name TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS revisions(id INTEGER PRIMARY KEY AUTOINCREMENT,project_id TEXT NOT NULL,parent_id INTEGER,created_at TEXT NOT NULL,input_hash TEXT NOT NULL,payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS solves(id TEXT PRIMARY KEY,created_at TEXT NOT NULL,input_hash TEXT NOT NULL,payload TEXT NOT NULL);''')
    def connect(self):return sqlite3.connect(self.path)
    def save(self,p,project_id=None):
        project_id=project_id or str(uuid.uuid4());payload=json.dumps(p.model_dump(),sort_keys=True)
        with self.connect() as db:
            parent=db.execute('SELECT MAX(id) FROM revisions WHERE project_id=?',(project_id,)).fetchone()[0]
            db.execute('INSERT OR REPLACE INTO projects VALUES(?,?)',(project_id,p.name))
            cur=db.execute('INSERT INTO revisions(project_id,parent_id,created_at,input_hash,payload) VALUES(?,?,?,?,?)',
                           (project_id,parent,datetime.now(timezone.utc).isoformat(),hashlib.sha256(payload.encode()).hexdigest(),payload))
            return {'id':project_id,'revision':cur.lastrowid}
    def load(self,project_id):
        with self.connect() as db:
            row=db.execute('SELECT payload FROM revisions WHERE project_id=? ORDER BY id DESC LIMIT 1',(project_id,)).fetchone()
            return json.loads(row[0]) if row else None
    def record_solve(self,result):
        with self.connect() as db:
            db.execute('INSERT INTO solves VALUES(?,?,?,?)',(str(uuid.uuid4()),datetime.now(timezone.utc).isoformat(),result['input_hash'],json.dumps(result)))
