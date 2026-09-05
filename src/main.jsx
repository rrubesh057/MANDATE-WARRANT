import React,{useEffect,useMemo,useState}from'react';
import{createRoot}from'react-dom/client';
import'./style.css';

const api=import.meta.env.VITE_API_URL||'http://127.0.0.1:8001';
const empty={
  request_id:'',
  protocol:'upi_autopay',
  operation:'modify',
  merchant:'',
  amount:'',
  max_amount:'',
  agent_id:'',
  delegation_active:true,
  mandate_state:'active',
  notice_hours:'',
  merchant_match:true,
  operations_last_hour:'',
  request_nonce:'',
  replayed:false
};
const approvedCase={
  request_id:'approved-001',
  protocol:'upi_autopay',
  operation:'modify',
  merchant:'Cloudflow',
  amount:8000,
  max_amount:10000,
  agent_id:'agent-17',
  delegation_active:'true',
  mandate_state:'active',
  notice_hours:24,
  merchant_match:'true',
  operations_last_hour:1,
  request_nonce:'nonce-approved-001',
  replayed:'false'
};

function Card({children,className=''}){return <section className={`card ${className}`}>{children}</section>}
function Stat({label,value,note}){return <Card><small>{label}</small><h2>{value??'--'}</h2><span>{note}</span></Card>}
function parsePolicyRules(markdown){
  const explanations={
    'AUTH-SCOPE-01':'Blocks requests when no active delegated agent is authorized to operate the mandate.',
    'AUTH-SCOPE-04':'Requires a repair when the requested debit amount is above the delegated ceiling.',
    'NOTICE-02':'Requires a repair when a mandate modification lacks the minimum 24-hour notice.',
    'STATE-07':'Blocks expired mandates and replayed request nonces before any payment action.',
    'CTX-03':'Blocks requests when the merchant context does not match the delegated policy context.',
    'VELOCITY-01':'Blocks unusually frequent mandate operations for the same customer window.'
  };
  return markdown.split('\n').filter(line=>line.startsWith('| `')).map(line=>{
    const cells=line.split('|').slice(1,-1).map(cell=>cell.trim().replaceAll('`',''));
    return{code:cells[0],condition:cells[1],outcome:cells[2],evidence:cells[3],explanation:explanations[cells[0]]||'Deterministic control from the versioned policy specification.'};
  });
}

function App(){
  const[page,setPage]=useState('Overview');
  const[form,setForm]=useState(empty);
  const[overview,setOverview]=useState();
  const[audit,setAudit]=useState([]);
  const[result,setResult]=useState();
  const[error,setError]=useState();
  const[loading,setLoading]=useState(false);
  const[policy,setPolicy]=useState('');
  const[evalRun,setEvalRun]=useState();
  const[adapter,setAdapter]=useState();
  const nav=['Overview','Evaluate Request','Audit Trail','Policy Rulebook','Evaluation Metrics'];
  const required=useMemo(()=>new Set(['request_id','merchant','amount','max_amount','agent_id','notice_hours','operations_last_hour','request_nonce']),[]);

  async function load(){
    try{
      const[o,a,p,e,ad]=await Promise.all([
        fetch(api+'/api/overview'),
        fetch(api+'/api/audit'),
        fetch(api+'/api/policy'),
        fetch(api+'/api/eval'),
        fetch(api+'/api/adapter/status').catch(()=>null)
      ]);
      if(!o.ok||!a.ok||!p.ok||!e.ok)throw Error('Runtime endpoint unavailable.');
      setOverview(await o.json());
      setAudit((await a.json()).rows);
      setPolicy((await p.json()).text);
      setEvalRun(await e.json());
      if(ad&&ad.ok)setAdapter(await ad.json());
    }catch(err){setError(err.message)}
  }

  useEffect(()=>{load()},[]);
  function change(e){setForm({...form,[e.target.name]:e.target.type==='checkbox'?e.target.checked:e.target.value})}
  async function submit(e){
    e.preventDefault();setLoading(true);setError();setResult();
    try{
      const payload={...form,amount:Number(form.amount),max_amount:Number(form.max_amount),notice_hours:Number(form.notice_hours),operations_last_hour:Number(form.operations_last_hour)};
      const response=await fetch(api+'/api/evaluate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
      const body=await response.json();
      if(!response.ok)throw Error(body.detail||'Evaluation failed');
      setResult(body);await load();setPage('Evaluate Request');
    }catch(err){setError(err.message)}
    finally{setLoading(false)}
  }

  const metrics=evalRun?.report?.metrics||{};
  const policyRules=parsePolicyRules(policy);
  return <div className="shell">
    <aside>
      <div className="brand"><span>MW</span><b>Mandate Warrant<small>GOVERNANCE RUNTIME</small></b></div>
      <label>WORKSPACE</label>
      {nav.map(item=><button type="button" className={page===item?'active':''} onClick={()=>setPage(item)} key={item}>{item}</button>)}
      <footer>
        POLICY SET<br/><b>UPI-AUTOPAY-2026.08</b>
        <div className="adapter-status">
          <small>EXECUTION ADAPTER</small>
          <b>{adapter?.configured ? 'Razorpay Test Active' : 'Simulated Only'}</b>
        </div>
      </footer>
    </aside>
    <main>
      <header>
        <div><em>{page.toUpperCase()}</em><h1>Mandate governance console</h1><p>Claude extracts context. Deterministic policy makes the decision. Audit writes are hash chained.</p></div>
      </header>
      {error&&<div className="error">{error}</div>}

      {page==='Overview'&&<>
        <div className="metrics">
          <Stat label="REQUESTS EVALUATED" value={overview?.requests_evaluated} note="SQLite policy decisions"/>
          <Stat label="NON-COMPLIANT BLOCKED" value={overview?.non_compliant_blocked} note="Deterministic blocks"/>
          <Stat label="REPAIR REQUIRED" value={overview?.repair_required} note="Repairable violations"/>
          <Stat label="REPAIR SUCCESS RATE" value={overview?.repair_success_rate==null?null:overview.repair_success_rate.toFixed(1)+'%'} note="Eligible repairs only"/>
        </div>
        <Card><h3>Overview explanation</h3><p>This dashboard only shows live database aggregates. Empty values mean no completed policy decisions have been written to the current runtime database yet.</p></Card>
      </>}

      {page==='Evaluate Request'&&<>
        <Card>
          <div className="head">
            <div>
              <h3>Mandate evaluation</h3>
              <p className="explain">Propose an agent mandate modification or creation for deterministic policy evaluation and Razorpay test execution.</p>
            </div>
            <mark>{adapter?.configured ? 'LIVE RAZORPAY TEST' : 'SIMULATED RUNTIME'}</mark>
          </div>
          <div className="form-actions">
            <button type="button" className="secondary-btn" onClick={()=>setForm({...approvedCase})}>Load Approved Sample</button>
            <button type="button" className="secondary-btn" onClick={()=>setForm(empty)}>Reset Form</button>
          </div>
          <form onSubmit={submit} className="form">
            {Object.entries(form).map(([key,value])=><label key={key}>{key.replaceAll('_',' ')}
              {typeof value==='boolean'?<input name={key} type="checkbox" checked={value} onChange={change}/>:<input required={required.has(key)} name={key} value={value} onChange={change}/>}
            </label>)}
            <button className="primary" disabled={loading}>{loading?'Calling runtime & executing...':'Run policy evaluation & execute'}</button>
          </form>
        </Card>
        {result&&<Card>
          <div className="head"><h3>Decision card</h3><mark>{result.decision.policy_code}</mark></div>
          <div className={'decision '+result.decision.decision}><b>{result.decision.decision.toUpperCase()}</b><p>{result.decision.reason}</p><pre>{JSON.stringify(result.decision.evidence,null,2)}</pre></div>
          <p>Extraction confidence: {result.normalization.extraction_confidence}. Context confidence: {result.context.match_confidence}.</p>
        </Card>}
        {result?.execution&&<Card className="execution">
          <div className="head">
            <div>
              <h3>Execution Dispatch</h3>
              <p className="explain">{result.execution.live ? 'Live Razorpay Test Mode execution via authenticated API adapter' : 'Deterministic execution guard'}</p>
            </div>
            <mark className={result.execution.status==='EXECUTED' ? 'pill-executed' : ''}>
              {result.execution.status==='EXECUTED' ? 'LIVE RAZORPAY TEST' : (result.execution.live ? 'LIVE ADAPTER' : 'POLICY GUARD')}
            </mark>
          </div>
          <div className={'execution-box ' + (result.execution.status==='EXECUTED' ? 'executed' : (result.execution.status.startsWith('BLOCKED') ? 'blocked' : 'held'))}>
            <div className="exec-title">
              <b>{result.execution.status}</b>
              {result.execution.order_id && <code className="exec-order-id">{result.execution.order_id}</code>}
            </div>
            {result.execution.order_id && (
              <div className="exec-grid">
                <div><span>Order ID</span><b>{result.execution.order_id}</b></div>
                <div><span>Authorized Amount</span><b>₹{(result.execution.amount / 100).toLocaleString('en-IN')}</b></div>
                <div><span>Currency</span><b>{result.execution.currency}</b></div>
                <div><span>Provider</span><b>Razorpay Test Mode</b></div>
                <div><span>Receipt Nonce</span><b>{result.execution.receipt}</b></div>
                <div><span>Order State</span><b className="status-badge">{result.execution.order_status}</b></div>
              </div>
            )}
            {result.execution.error && <p className="error" style={{marginTop:'8px',marginBottom:0}}>{result.execution.error}</p>}
          </div>
        </Card>}
        {result?.repair&&<Card className="repair">
          <h3>Closest compliant repair</h3>
          <pre>{JSON.stringify(result.repair.proposal,null,2)}</pre>
          <strong className={result.repair.eligible?'valid':'invalid'}>{result.repair.eligible?'Eligible after deterministic re-validation':'Not eligible after deterministic re-validation'}</strong>
          {result.repair.eligible && (
            <button
              type="button"
              className="apply-repair-btn"
              onClick={() => {
                setForm({...empty, ...result.repair.proposal});
              }}
            >
              Apply Compliant Repair to Form
            </button>
          )}
        </Card>}
      </>}

      {page==='Audit Trail'&&<Card><div className="head"><div><h3>Immutable audit trail</h3><p className="explain">Each row is chained to the row before it. The payload is stored in the database, but hidden here to keep the audit screen focused.</p></div><small>{overview?.audit_chain_valid?'SHA-256 chain verified':'Chain unavailable'}</small></div><table><thead><tr><th>TIME</th><th>EVENT</th><th>HASH</th></tr></thead><tbody>{audit.map((row,index)=><tr key={row.entry_hash||index}><td>{new Date(row.created_at).toLocaleString()}</td><td>{row.event}</td><td>{row.entry_hash.slice(0,18)}...</td></tr>)}</tbody></table></Card>}
      {page==='Policy Rulebook'&&<>
        <Card><div className="head"><div><h3>Versioned policy rulebook</h3><p className="explain">Rules are evaluated top to bottom by the deterministic policy engine. AI can extract or propose; it cannot approve outside these controls.</p></div><small>{policyRules.length} rules</small></div><table><thead><tr><th>CODE</th><th>CONDITION</th><th>OUTCOME</th><th>EVIDENCE</th><th>EXPLANATION</th></tr></thead><tbody>{policyRules.map(rule=><tr key={rule.code}><td><code>{rule.code}</code></td><td>{rule.condition}</td><td><span className={'pill '+rule.outcome.toLowerCase()}>{rule.outcome}</span></td><td><code>{rule.evidence}</code></td><td>{rule.explanation}</td></tr>)}</tbody></table></Card>
        <Card className="approvedCase"><div className="head"><div><h3>Approved case</h3><p className="explain">This case passes because delegation is active, mandate state is valid, merchant matches, velocity is under limit, amount is within ceiling, and notice is at least 24 hours.</p></div><span className="pill approved">APPROVED</span></div><table><thead><tr><th>FIELD</th><th>VALUE</th></tr></thead><tbody>{Object.entries(approvedCase).map(([key,value])=><tr key={key}><td>{key.replaceAll('_',' ')}</td><td><code>{String(value)}</code></td></tr>)}</tbody></table></Card>
      </>}
      {page==='Evaluation Metrics'&&<Card><div className="head"><h3>Evaluation metrics</h3><small>{evalRun?.report?.cases||0} cases</small></div>{evalRun?.report?<><div className="metricRows">{Object.entries(metrics).map(([label,row])=><div key={label}><b>{label}</b><span>P {row.precision.toFixed(2)} / R {row.recall.toFixed(2)} / F1 {row.f1.toFixed(2)}</span></div>)}</div><pre>{JSON.stringify(evalRun.report.confusion_matrix,null,2)}</pre></>:<p>No persisted eval run is available.</p>}</Card>}
    </main>
  </div>
}


createRoot(document.getElementById('root')).render(<App/>);
