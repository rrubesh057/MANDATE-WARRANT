import ast, sqlite3, tempfile
from pathlib import Path
from backend.app.database import Database
from backend.app.models import Claim
from backend.app.policy_engine.engine import PolicyEngine
from backend.app.service import WardenService

ROOT=Path(__file__).parents[2]
def claim(**overrides):
    values={"request_id":"test-1","protocol":"upi_autopay","operation":"modify","merchant":"Cloudflow","amount":12000,"max_amount":10000,"agent_id":"agent","delegation_active":True,"mandate_state":"active","notice_hours":24,"merchant_match":True,"operations_last_hour":0,"request_nonce":"n1"};values.update(overrides);return Claim(**values)
def test_policy_engine_has_no_ai_dependency():
    tree=ast.parse((ROOT/'backend/app/policy_engine/engine.py').read_text()); banned={'openai','anthropic','requests','httpx','urllib','socket'}; modules=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Import): modules.extend(a.name for a in node.names)
        if isinstance(node,ast.ImportFrom): modules.append(node.module or '')
    assert not {m.split('.')[0] for m in modules}&banned
def test_repair_requires_same_engine_revalidation():
    with tempfile.TemporaryDirectory() as folder:
        service=WardenService(str(Path(folder)/'audit.db'))
        service_mod=__import__('backend.app.service',fromlist=['normalize','match_context','propose_repair'])
        original_normalize=service_mod.normalize; original_match=service_mod.match_context; original_repair=service_mod.propose_repair
        try:
            service_mod.normalize=lambda payload:(claim(**payload),{"extraction_confidence":0.91,"provider":"test-double"})
            service_mod.match_context=lambda normalized:{"merchant_match":True,"match_confidence":0.93,"match_reason":"test context","provider":"test-double"}
            service_mod.propose_repair=lambda normalized,result:claim(request_id=normalized.request_id,amount=10000,notice_hours=24)
            response=service.evaluate(claim().payload())
        finally:
            service_mod.normalize=original_normalize; service_mod.match_context=original_match; service_mod.propose_repair=original_repair
        assert response["decision"]["decision"]=="repair_required"
        assert response["repair"]["eligible"] is True
        events=[row["event"] for row in service.db.audit_rows()]
        assert "repair_revalidated" in events
def test_audit_tamper_detection():
    with tempfile.TemporaryDirectory() as folder:
        path=str(Path(folder)/'audit.db'); db=Database(path); db.append_audit('one',{'x':1}); db.append_audit('two',{'x':2})
        c=sqlite3.connect(path);c.execute("UPDATE audit_log SET payload='tampered' WHERE id=1");c.commit();c.close();assert db.verify_chain() is False
def test_overview_reflects_empty_database():
    with tempfile.TemporaryDirectory() as folder:
        db=Database(str(Path(folder)/'audit.db'));assert db.overview()=={'requests_evaluated':0,'non_compliant_blocked':0,'repair_required':0,'repair_success_rate':None,'audit_chain_valid':True}
def test_full_schema_exists():
    with tempfile.TemporaryDirectory() as folder:
        db=Database(str(Path(folder)/'audit.db'));c=sqlite3.connect(db.path);tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")};c.close();assert {'requests','normalizations','matches','policy_decisions','repair_proposals','audit_log','eval_runs'}<=tables
