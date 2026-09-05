from __future__ import annotations
import json
from ..ai import call_claude
from ..models import Claim
SYSTEM="Return JSON only: {merchant_match:boolean,match_confidence:number,reason:string}. Match merchant context. Never authorize."
def match_context(claim: Claim) -> dict:
    result=call_claude(SYSTEM,json.dumps(claim.payload()))
    if not isinstance(result.get("merchant_match"),bool) or not isinstance(result.get("match_confidence"),(int,float)): raise ValueError("Claude context response is malformed")
    return {"merchant_match":result["merchant_match"],"match_confidence":float(result["match_confidence"]),"match_reason":result.get("reason",""),"provider":"claude"}
