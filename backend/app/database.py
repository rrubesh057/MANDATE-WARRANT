from __future__ import annotations
import hashlib, json, sqlite3
from datetime import datetime, timezone

class Database:
    def __init__(self, path="mandate_warrant.db"): self.path=str(path); self.migrate()
    def connection(self):
        c=sqlite3.connect(self.path); c.row_factory=sqlite3.Row; return c
    def migrate(self):
        tables=[
        "CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, received_at TEXT NOT NULL, protocol TEXT NOT NULL, raw_payload TEXT NOT NULL)",
        "CREATE TABLE IF NOT EXISTS normalizations (id INTEGER PRIMARY KEY, request_id TEXT NOT NULL, structured_claim TEXT, confidence REAL, status TEXT NOT NULL, provider TEXT, error TEXT, created_at TEXT NOT NULL)",
        "CREATE TABLE IF NOT EXISTS matches (id INTEGER PRIMARY KEY, request_id TEXT NOT NULL, matched INTEGER, confidence REAL, reason TEXT, status TEXT NOT NULL, provider TEXT, error TEXT, created_at TEXT NOT NULL)",
        "CREATE TABLE IF NOT EXISTS policy_decisions (id INTEGER PRIMARY KEY, request_id TEXT NOT NULL, decision TEXT NOT NULL, policy_code TEXT NOT NULL, reason TEXT NOT NULL, evidence TEXT NOT NULL, policy_version TEXT NOT NULL, created_at TEXT NOT NULL)",
        "CREATE TABLE IF NOT EXISTS repair_proposals (id INTEGER PRIMARY KEY, request_id TEXT NOT NULL, proposal TEXT NOT NULL, eligible INTEGER NOT NULL, revalidation TEXT NOT NULL, provider TEXT, error TEXT, created_at TEXT NOT NULL)",
        "CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, event TEXT NOT NULL, payload TEXT NOT NULL, previous_hash TEXT NOT NULL, entry_hash TEXT NOT NULL)",
        "CREATE TABLE IF NOT EXISTS eval_runs (id INTEGER PRIMARY KEY, dataset_commit TEXT, generated_at TEXT NOT NULL, report TEXT NOT NULL)"]
        c=self.connection()
        try:
            for table in tables: c.execute(table)
            c.commit()
        finally: c.close()
    @staticmethod
    def now(): return datetime.now(timezone.utc).isoformat()
    @staticmethod
    def dump(value): return json.dumps(value,sort_keys=True,separators=(",",":"))
    def _execute(self, sql, params=()):
        c=self.connection()
        try:
            c.execute(sql,params); c.commit()
        finally:
            c.close()
    def insert_request(self,id,protocol,payload):
        self._execute("INSERT INTO requests VALUES(?,?,?,?)",(id,self.now(),protocol,self.dump(payload)))
    def insert_normalization(self,id,claim,confidence,status,provider=None,error=None):
        self._execute("INSERT INTO normalizations(request_id,structured_claim,confidence,status,provider,error,created_at) VALUES(?,?,?,?,?,?,?)",(id,self.dump(claim) if claim else None,confidence,status,provider,error,self.now()))
    def insert_match(self,id,matched,confidence,reason,status,provider=None,error=None):
        self._execute("INSERT INTO matches(request_id,matched,confidence,reason,status,provider,error,created_at) VALUES(?,?,?,?,?,?,?,?)",(id,matched,confidence,reason,status,provider,error,self.now()))
    def insert_decision(self,id,result,version):
        self._execute("INSERT INTO policy_decisions(request_id,decision,policy_code,reason,evidence,policy_version,created_at) VALUES(?,?,?,?,?,?,?)",(id,result.decision,result.policy_code,result.reason,self.dump(result.evidence),version,self.now()))
    def insert_repair(self,id,proposal,eligible,revalidation,provider,error=None):
        self._execute("INSERT INTO repair_proposals(request_id,proposal,eligible,revalidation,provider,error,created_at) VALUES(?,?,?,?,?,?,?)",(id,self.dump(proposal),eligible,self.dump(revalidation),provider,error,self.now()))
    def insert_eval_run(self,dataset_commit,report):
        self._execute("INSERT INTO eval_runs(dataset_commit,generated_at,report) VALUES(?,?,?)",(dataset_commit,self.now(),self.dump(report)))
    def latest_eval_run(self):
        c=self.connection()
        try:
            row=c.execute("SELECT dataset_commit,generated_at,report FROM eval_runs ORDER BY id DESC LIMIT 1").fetchone()
        finally:
            c.close()
        if not row: return None
        return {"dataset_commit":row["dataset_commit"],"generated_at":row["generated_at"],"report":json.loads(row["report"])}
    def append_audit(self,event,payload):
        encoded=self.dump(payload); c=self.connection()
        try:
            last=c.execute("SELECT entry_hash FROM audit_log ORDER BY id DESC LIMIT 1").fetchone(); previous=last[0] if last else "GENESIS"; timestamp=self.now(); entry=hashlib.sha256(f"{previous}|{timestamp}|{event}|{encoded}".encode()).hexdigest()
            c.execute("INSERT INTO audit_log(created_at,event,payload,previous_hash,entry_hash) VALUES(?,?,?,?,?)",(timestamp,event,encoded,previous,entry)); c.commit(); return entry
        finally: c.close()
    def audit_rows(self,limit=50):
        c=self.connection()
        try:
            rows=c.execute("SELECT created_at,event,payload,entry_hash FROM audit_log ORDER BY id DESC LIMIT ?",(limit,)).fetchall()
        finally:
            c.close()
        return [{"created_at":r["created_at"],"event":r["event"],"payload":json.loads(r["payload"]),"entry_hash":r["entry_hash"]} for r in rows]
    def verify_chain(self):
        previous="GENESIS"
        c=self.connection()
        try:
            rows=c.execute("SELECT created_at,event,payload,previous_hash,entry_hash FROM audit_log ORDER BY id").fetchall()
        finally:
            c.close()
        for row in rows:
            if row["previous_hash"]!=previous or row["entry_hash"]!=hashlib.sha256(f"{previous}|{row['created_at']}|{row['event']}|{row['payload']}".encode()).hexdigest(): return False
            previous=row["entry_hash"]
        return True
    def overview(self):
        c=self.connection()
        try:
            total=c.execute("SELECT COUNT(*) FROM policy_decisions").fetchone()[0]; blocked=c.execute("SELECT COUNT(*) FROM policy_decisions WHERE decision='blocked'").fetchone()[0]; repairs=c.execute("SELECT COUNT(*) FROM policy_decisions WHERE decision='repair_required'").fetchone()[0]; eligible=c.execute("SELECT COUNT(*) FROM repair_proposals WHERE eligible=1").fetchone()[0]; proposed=c.execute("SELECT COUNT(*) FROM repair_proposals").fetchone()[0]
        finally:
            c.close()
        return {"requests_evaluated":total,"non_compliant_blocked":blocked,"repair_required":repairs,"repair_success_rate":eligible/proposed*100 if proposed else None,"audit_chain_valid":self.verify_chain()}
