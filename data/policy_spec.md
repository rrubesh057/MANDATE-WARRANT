# Mandate Warrant Policy Specification

**Policy version:** `UPI-AUTOPAY-2026.08`  
**Status:** Demo policy model. It is not a substitute for NPCI or merchant legal requirements.

## Deterministic rules

| Code | Condition | Outcome | Evidence |
|---|---|---|---|
| `AUTH-SCOPE-01` | An active, delegated agent is present. | BLOCK | `agent_id`, `delegation_active` |
| `AUTH-SCOPE-04` | Requested amount is no greater than delegated maximum. | REPAIR_REQUIRED | `amount`, `max_amount` |
| `NOTICE-02` | A modified mandate has a pre-debit notice scheduled at least 24 hours before execution. | REPAIR_REQUIRED | `notice_hours` |
| `STATE-07` | Mandate is neither expired nor replayed. | BLOCK | `mandate_state`, `request_nonce` |
| `CTX-03` | Merchant context is an approved semantic match. | BLOCK | `merchant_match` |
| `VELOCITY-01` | No more than 3 mandate operations occur for a customer in the last hour. | BLOCK | `operations_last_hour` |

The closest compliant repair is limited to lowering an over-limit amount to the delegated ceiling and/or scheduling a 24-hour notice. Repairs never alter authorization, merchant context, state, or velocity. The same policy engine must validate every repair.
