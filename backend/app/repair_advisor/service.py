from __future__ import annotations
import json
from ..ai import call_claude
from ..models import Claim, PolicyResult
SYSTEM="Return JSON only: {proposal:{same Claim fields}}. Propose the smallest compliant configuration. Never authorize."
def propose_repair(claim: Claim, result: PolicyResult) -> Claim | None:
    if result.decision != "repair_required": return None
    return Claim(**call_claude(SYSTEM,json.dumps({"claim":claim.payload(),"violation":result.payload()}))["proposal"])
