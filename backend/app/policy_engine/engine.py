"""Pure deterministic policy engine. Keep this module dependency-free."""
from __future__ import annotations
from ..models import Claim, PolicyResult

class PolicyEngine:
    version = "UPI-AUTOPAY-2026.08"

    def evaluate(self, claim: Claim) -> PolicyResult:
        if not claim.delegation_active or not claim.agent_id:
            return PolicyResult("blocked", "No active delegated agent can request this mandate operation.", "AUTH-SCOPE-01", {"agent_id": claim.agent_id, "delegation_active": claim.delegation_active})
        if claim.mandate_state == "expired" or claim.replayed:
            return PolicyResult("blocked", "Expired or replayed mandates cannot be operated.", "STATE-07", {"mandate_state": claim.mandate_state, "request_nonce": claim.request_nonce, "replayed": claim.replayed})
        if not claim.merchant_match:
            return PolicyResult("blocked", "Merchant context does not match the delegated policy context.", "CTX-03", {"merchant": claim.merchant, "merchant_match": claim.merchant_match})
        if claim.operations_last_hour > 3:
            return PolicyResult("blocked", "Customer mandate-operation velocity exceeds the permitted limit.", "VELOCITY-01", {"operations_last_hour": claim.operations_last_hour, "limit": 3})
        if claim.amount > claim.max_amount:
            return PolicyResult("repair_required", "Requested amount exceeds the delegated authorization ceiling.", "AUTH-SCOPE-04", {"amount": claim.amount, "max_amount": claim.max_amount})
        if claim.operation == "modify" and claim.notice_hours < 24:
            return PolicyResult("repair_required", "A modified mandate requires a pre-debit notice at least 24 hours before execution.", "NOTICE-02", {"notice_hours": claim.notice_hours, "minimum_hours": 24})
        return PolicyResult("approved", "All applicable deterministic policy controls passed.", "POLICY-PASS", {"policy_version": self.version})
