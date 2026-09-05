import json, os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from .ai import AIServiceError
from .service import WardenService

app=FastAPI(title="Mandate Warrant")
ROOT=Path(__file__).resolve().parents[2]
service=WardenService(os.getenv("WARDEN_DB_PATH",str(ROOT/"data"/"mandate_warrant_runtime.db")))
app.add_middleware(CORSMiddleware,allow_origins=["http://127.0.0.1:5174","http://localhost:5174"],allow_methods=["*"],allow_headers=["*"])
@app.get("/")
def root(): return RedirectResponse(os.getenv("WARDEN_FRONTEND_URL","http://127.0.0.1:5174/"))
@app.get("/api/overview")
def overview(): return service.db.overview()
@app.get("/api/audit")
def audit(): return {"verified":service.db.verify_chain(),"rows":service.db.audit_rows()}
@app.get("/api/policy")
def policy(): return {"text":(ROOT/"data"/"policy_spec.md").read_text(encoding="utf-8")}
@app.get("/api/eval")
def eval_report():
    stored=service.db.latest_eval_run()
    if stored: return stored
    path=ROOT/"eval"/"eval_report.json"
    if not path.exists(): return {"report":None}
    return {"dataset_commit":None,"generated_at":None,"report":json.loads(path.read_text(encoding="utf-8"))}
@app.get("/api/adapter/status")
def adapter_status(): return service.adapter.status()
@app.post("/api/evaluate")
def evaluate(payload:dict):
    try: return service.evaluate(payload)
    except (AIServiceError,ValueError) as error: raise HTTPException(status_code=503 if isinstance(error,AIServiceError) else 422,detail=str(error))
