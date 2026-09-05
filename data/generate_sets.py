"""Generate deterministic synthetic claims after policy_spec.md exists."""
import json
from pathlib import Path
ROOT=Path(__file__).parent
base={"protocol":"upi_autopay","operation":"modify","merchant":"Cloudflow","amount":8000,"max_amount":10000,"agent_id":"agent","delegation_active":True,"mandate_state":"active","notice_hours":24,"merchant_match":True,"operations_last_hour":0,"request_nonce":"seed"}
def expected(x):
 if not x["delegation_active"] or x["mandate_state"]=="expired" or x.get("replayed") or not x["merchant_match"] or x["operations_last_hour"]>3:return "blocked"
 if x["amount"]>x["max_amount"] or x["notice_hours"]<24:return "repair_required"
 return "approved"
def make(seed):
 cases=[]
 variants=[{}, {"amount":11000},{"notice_hours":0},{"delegation_active":False},{"mandate_state":"expired"},{"merchant_match":False},{"operations_last_hour":4},{"amount":10001},{"notice_hours":23}]
 for i in range(54):
  item=base|variants[i%len(variants)]|{"request_id":f"{seed}-{i+1:03}","request_nonce":f"{seed}-nonce-{i+1}","tier":["obvious-legitimate","obvious-violation","near-miss-legitimate","near-miss-violation"][i%4]}
  item["ground_truth"]=expected(item); cases.append(item)
 return cases
(ROOT/"dev_set.json").write_text(json.dumps(make("dev"),indent=2))
(ROOT/"golden_set.json").write_text(json.dumps(make("golden"),indent=2))
