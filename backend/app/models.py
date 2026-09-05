from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Literal

Decision = Literal["approved", "blocked", "repair_required"]

@dataclass(frozen=True)
class Claim:
    request_id: str
    protocol: str
    operation: str
    merchant: str
    amount: int
    max_amount: int
    agent_id: str
    delegation_active: bool
    mandate_state: str
    notice_hours: int
    merchant_match: bool
    operations_last_hour: int
    request_nonce: str
    replayed: bool = False

    def payload(self) -> dict:
        return asdict(self)

@dataclass(frozen=True)
class PolicyResult:
    decision: Decision
    reason: str
    policy_code: str
    evidence: dict

    def payload(self) -> dict:
        return asdict(self)
