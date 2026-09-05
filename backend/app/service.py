from __future__ import annotations
from dataclasses import replace
from .database import Database
from .ai import AIServiceError
from .matcher.service import match_context
from .normalizer.service import normalize
from .policy_engine.engine import PolicyEngine
from .repair_advisor.service import propose_repair
from .execution.adapter import RazorpayAdapter

class WardenService:
    def __init__(self, db_path="mandate_warrant.db", adapter: RazorpayAdapter | None = None):
        self.db=Database(db_path); self.engine=PolicyEngine()
        self.adapter=adapter or RazorpayAdapter()
    def evaluate(self, payload: dict) -> dict:
        request_id=payload.get("request_id")
        if not request_id: raise ValueError("request_id is required")
        self.db.insert_request(request_id,payload.get("protocol","unknown"),payload); self.db.append_audit("request_received",{"request_id":request_id})
        try:
            claim,normalization=normalize(payload)
            self.db.insert_normalization(request_id,claim.payload(),normalization["extraction_confidence"],"completed",normalization["provider"]); self.db.append_audit("claim_normalized",{"request_id":request_id})
            context=match_context(claim)
            self.db.insert_match(request_id,context["merchant_match"],context["match_confidence"],context["match_reason"],"completed",context["provider"]); self.db.append_audit("context_matched",{"request_id":request_id})
            claim=replace(claim, merchant_match=context["merchant_match"])
        except (AIServiceError,ValueError) as error:
            self.db.insert_normalization(request_id,None,None,"failed",error=str(error)); self.db.append_audit("ai_pipeline_failed",{"request_id":request_id,"error":str(error)})
            raise
        result=self.engine.evaluate(claim); self.db.insert_decision(request_id,result,self.engine.version); self.db.append_audit("policy_evaluated", {"request_id":request_id, "decision":result.decision, "policy_code":result.policy_code, "evidence":result.evidence})
        repair=None
        if result.decision=="repair_required":
            try:
                proposal=propose_repair(claim,result)
            except (AIServiceError,ValueError) as error:
                self.db.append_audit("repair_advisor_failed",{"request_id":request_id,"error":str(error)})
                raise
            if proposal:
                revalidated=self.engine.evaluate(proposal)
                self.db.insert_repair(request_id,proposal.payload(),revalidated.decision=="approved",revalidated.payload(),"claude"); self.db.append_audit("repair_revalidated", {"request_id":request_id, "proposal":proposal.payload(), "decision":revalidated.decision, "policy_code":revalidated.policy_code})
                repair={"proposal":proposal.payload(),"eligible":revalidated.decision=="approved","revalidation":revalidated.payload()}
        execution=None
        if result.decision=="approved":
            execution=self.adapter.execute_mandate(claim)
            if execution.get("status")=="EXECUTED":
                self.db.append_audit("mandate_executed",{"request_id":request_id,"order_id":execution.get("order_id"),"amount":execution.get("amount"),"currency":execution.get("currency"),"provider":execution.get("provider")})
            elif execution.get("status")=="EXECUTION_FAILED":
                self.db.append_audit("execution_failed",{"request_id":request_id,"error":execution.get("error"),"provider":execution.get("provider")})
        elif result.decision=="blocked":
            execution={"status":"BLOCKED — execution halted by policy control","live":False,"policy_code":result.policy_code}
        elif result.decision=="repair_required":
            execution={"status":"HELD — execution requires repair revalidation","live":False,"policy_code":result.policy_code}
        return {"claim":claim.payload(),"normalization":normalization,"context":context,"decision":result.payload(),"repair":repair,"execution":execution,"audit_verified":self.db.verify_chain()}
