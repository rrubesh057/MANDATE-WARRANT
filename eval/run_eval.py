"""Only this script reads the held-out golden set."""
import json, subprocess, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/"backend"))
from app.database import Database
from app.models import Claim
from app.policy_engine.engine import PolicyEngine

root=Path(__file__).parents[1]
cases=json.loads((root/"data/golden_set.json").read_text(encoding="utf-8"))
engine=PolicyEngine(); matrix=Counter(); per=Counter()
for row in cases:
    expected=row.get("true_label") or row.get("ground_truth")
    payload={key:value for key,value in row.items() if key not in {"tier","true_label","ground_truth","expected_policy_code"}}
    actual=engine.evaluate(Claim(**payload)).decision
    matrix[(expected,actual)]+=1
for label in ("approved","blocked","repair_required"):
    tp=matrix[(label,label)]; fp=sum(matrix[(x,label)] for x in ("approved","blocked","repair_required") if x!=label); fn=sum(matrix[(label,x)] for x in ("approved","blocked","repair_required") if x!=label)
    p=tp/(tp+fp) if tp+fp else 0; r=tp/(tp+fn) if tp+fn else 0; per[label]={"precision":p,"recall":r,"f1":2*p*r/(p+r) if p+r else 0}
try:
    dataset_commit=subprocess.run(["git","log","-n","1","--format=%H","--","data/golden_set.json"],cwd=root,text=True,capture_output=True,check=False).stdout.strip() or None
except Exception:
    dataset_commit=None
report={"cases":len(cases),"metrics":per,"confusion_matrix":{f"{a}->{b}":n for (a,b),n in matrix.items()},"dataset_commit":dataset_commit}
(root/"eval/eval_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
Database(root/"data"/"mandate_warrant_runtime.db").insert_eval_run(dataset_commit,report)
print(json.dumps(report,indent=2))
