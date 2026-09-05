from __future__ import annotations
import json
from ..ai import call_claude
from ..models import Claim
SYSTEM="Return JSON only: {claim:{request_id,protocol,operation,merchant,amount,max_amount,agent_id,delegation_active,mandate_state,notice_hours,merchant_match,operations_last_hour,request_nonce,replayed},extraction_confidence:number}. Extract facts only; never authorize."
def normalize(payload: dict) -> tuple[Claim, dict]:
    result=call_claude(SYSTEM,json.dumps(payload))
    confidence=result.get("extraction_confidence")
    if not isinstance(confidence,(int,float)): raise ValueError("Claude omitted numeric extraction_confidence")
    return Claim(**result["claim"]),{"extraction_confidence":float(confidence),"provider":"claude"}
