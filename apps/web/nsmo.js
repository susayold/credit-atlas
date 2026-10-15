const $=(id)=>document.getElementById(id);
const n=(x)=>new Intl.NumberFormat('en-US').format(x??0);
const dec=(x)=>new Intl.NumberFormat('en-US',{maximumFractionDigits:2}).format(x??0);
const pct=(x)=>new Intl.NumberFormat('en-US',{style:'percent',maximumFractionDigits:2}).format(x??0);
function node(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=String(text);return e;}
function table(headers,rows,numeric=[]){const t=document.createElement('table'),head=document.createElement('thead'),hr=document.createElement('tr');headers.forEach(h=>hr.append(node('th','',typeof h==='string'?h:h.label)));head.append(hr);t.append(head);const b=document.createElement('tbody');rows.forEach(row=>{const tr=document.createElement('tr');row.forEach((value,i)=>{const td=node('td',numeric.includes(i)?'num':'',value);tr.append(td);});b.append(tr);});t.append(b);return t;}
function metric(label,value,note){const e=node('article','metric');e.append(node('span','label',label),node('strong','',value),node('small','',note));return e;}
function drawChart(svg,series,label){
  svg.replaceChildren();const w=980,h=340,l=58,r=20,t=22,b=48,iw=w-l-r,ih=h-t-b;
  const values=series.map(x=>x.value),max=Math.max(1,...values),nice=Math.ceil(max/4),limit=nice*4;
  for(let i=0;i<=4;i++){const value=limit-i*nice,y=t+i*ih/4;const line=document.createElementNS('http://www.w3.org/2000/svg','line');line.setAttribute('x1',l);line.setAttribute('x2',w-r);line.setAttribute('y1',y);line.setAttribute('y2',y);line.setAttribute('class','grid-line');svg.append(line);const tx=document.createElementNS('http://www.w3.org/2000/svg','text');tx.setAttribute('x',l-10);tx.setAttribute('y',y+4);tx.setAttribute('text-anchor','end');tx.setAttribute('class','axis-label');tx.textContent=n(value);svg.append(tx);}
  const points=series.map((x,i)=>({x:l+(series.length===1?iw/2:i*iw/(series.length-1)),y:t+ih-(x.value/limit)*ih,...x}));
  const path=document.createElementNS('http://www.w3.org/2000/svg','polyline');path.setAttribute('points',points.map(p=>`${p.x},${p.y}`).join(' '));path.setAttribute('class','series-line');svg.append(path);
  points.forEach((p,i)=>{if(i%Math.ceil(points.length/18)===0||i===points.length-1){const c=document.createElementNS('http://www.w3.org/2000/svg','circle');c.setAttribute('cx',p.x);c.setAttribute('cy',p.y);c.setAttribute('r','4');c.setAttribute('class','series-point');const title=document.createElementNS('http://www.w3.org/2000/svg','title');title.textContent=`${p.quarter}: ${n(p.value)}`;c.append(title);svg.append(c);const tx=document.createElementNS('http://www.w3.org/2000/svg','text');tx.setAttribute('x',p.x);tx.setAttribute('y',h-17);tx.setAttribute('text-anchor','middle');tx.setAttribute('class','axis-label');const qmatch=p.quarter.match(/^(\d{4})-Q([1-4])$/);tx.textContent=qmatch?`${qmatch[1]}Q${qmatch[2]}`:p.quarter.slice(0,4)+'Q'+(Math.floor((Number(p.quarter.slice(5,7))-1)/3)+1);svg.append(tx);}});
  svg.setAttribute('aria-label',`${label}. Counts from ${series[0].quarter} to ${series.at(-1).quarter}.`);
}
function render(profile){
  const sample=profile.sample,perf=profile.performance,weights=profile.analysis_weight;
  const sampleTotal=sample.mortgages;
  $('metrics').replaceChildren(
    metric('Sample mortgages',n(sampleTotal),'FHFA public-use rows · 2013–2024 origins'),
    metric('Quarter-end statuses',n(perf.cell_count),'51 quarterly fields · 2013Q1–2025Q3'),
    metric('Distinct public IDs',n(sample.unique_nonblank_ids),'Unique, nonblank; IDs are not displayed'),
    metric('Weight coverage',pct(weights.valid_n/sampleTotal),`Analysis_Weight · median ${dec(weights.median)}`)
  );
  $('source-link').href=profile.source.source_url;
  $('state').className='state ok';$('state').textContent=`Verified local PUF · ${profile.source.title} · SHA-256 ${profile.source.source_sha256}`;
  const statusChoice=$('status-choice');statusChoice.replaceChildren();perf.status_codes.forEach(s=>{const o=node('option','',`${s.code} · ${s.label}`);o.value=s.code;statusChoice.append(o);});statusChoice.value='C';
  const quarterChoice=$('quarter-choice');quarterChoice.replaceChildren();perf.quarterly_counts.forEach((q,i)=>{const o=node('option','',q.quarter_end);o.value=String(i);quarterChoice.append(o);});quarterChoice.value=String(perf.quarterly_counts.length-1);
  const getCounts=(q)=>q.status_counts||{};
  const codeLabel=(code)=>perf.status_codes.find(x=>x.code===code)?.label||code;
  const draw=()=>{
    const code=statusChoice.value,selected=perf.quarterly_counts[Number(quarterChoice.value)];
    const values=perf.quarterly_counts.map(q=>({quarter:q.quarter_end,value:getCounts(q)[code]||0}));
    drawChart($('trend'),values,`${code} ${codeLabel(code)}`);
    $('trend-caption').textContent=`${code} · ${codeLabel(code)} · unweighted sample mortgages at quarter end`;
    const weighted=selected.status_weight_sums_descriptive_only||{};
    const rows=perf.status_codes.map(s=>{const count=getCounts(selected)[s.code]||0;return [s.code,s.label,n(count),pct(count/sampleTotal),dec(weighted[s.code]||0)];});
    const container=$('quarter-table');container.replaceChildren(table(['Code','Codebook category',{label:'Rows',number:true},{label:'Share of full PUF sample',number:true},{label:'Analysis-weight total · descriptive',number:true}],rows,[2,3,4]));
  };
  statusChoice.addEventListener('change',draw);quarterChoice.addEventListener('change',draw);draw();
  const yearRows=Object.entries(sample.origination_year_counts).sort((a,b)=>Number(a[0])-Number(b[0])).map(([year,count])=>[year,n(count),pct(count/sampleTotal)]);
  $('vintages').replaceChildren(table(['Origination year','Mortgages','Share of full PUF'],yearRows,[1,2]));
  const waveRows=Object.entries(sample.survey_wave_counts).sort((a,b)=>Number(a[0])-Number(b[0])).map(([wave,count])=>[wave,n(count),pct(count/sampleTotal)]);$('survey-waves').replaceChildren(node('h3','','Survey wave representation'),table(['Survey wave','Mortgages','Share of full PUF'],waveRows,[1,2]));
  const ws=$('weight-summary'),weightValues=[['Valid rows',n(weights.valid_n)],['Missing',n(weights.missing)],['Nonpositive',n(weights.nonpositive)],['Minimum',dec(weights.min)],['Median',dec(weights.median)],['Maximum',dec(weights.max)],['Weight sum',dec(weights.sum)],['Survey waves',Object.keys(sample.survey_wave_counts).length]];
  ws.className='weight-summary';ws.replaceChildren(...weightValues.map(([label,value])=>{const e=node('div','mini-stat');e.append(node('span','',label),node('strong','',value));return e;}));
  $('limits').replaceChildren(...profile.limitations.map(x=>node('li','',x)));
  $('disclaimer').textContent=profile.required_fhfa_analysis_disclaimer;
  $('dashboard').hidden=false;$('state').hidden=true;
  loadDomainAnalysis();
  loadTargetFeasibility();
  loadOriginationFeasibility();
}
async function loadDomainAnalysis(){
  try{const r=await fetch('/api/nsmo-domains',{cache:'no-store',headers:{Accept:'application/json'}});const body=await r.json();if(!r.ok)throw new Error(body.error||`HTTP ${r.status}`);renderDomains(body);$('domain-state').className='domain-state ok';$('domain-state').textContent='Aggregates verified against the same PUF SHA-256 as the structural profile.';}
  catch(error){$('domain-state').className='domain-state error';$('domain-state').textContent=`Domain metrics unavailable: ${error.message}`;}
}
function renderDomains(data){
  const term=data.termination,total=term.mortgages,termRows=Object.entries(term.status_counts).map(([code,count])=>[code,term.status_labels[code]||code,n(count),pct(count/total)]);
  const ts=$('termination-summary');ts.replaceChildren(...Object.entries(term.status_counts).map(([code,count])=>metric(code==='1'?'Mortgage open':'Mortgage terminated',n(count),pct(count/total)+' of full PUF')));
  $('termination-table').replaceChildren(table(['Code','Publisher label','Mortgages','Share of full sample'],termRows,[2,3]));
  const perfRows=term.final_quarter_performance_by_termination.map(x=>[x.close_status,x.performance_status,n(x.n_mortgages)]);
  $('termination-table').append(node('h4','','Q3 2025 status by termination flag'),table(['Close status','Performance status','Mortgages'],perfRows,[2]));
  const scoreChoice=$('orig-score-choice');scoreChoice.replaceChildren(...data.origination_scores.map((f,i)=>{const o=node('option','',f.label);o.value=String(i);return o;}));
  const drawOrig=()=>{const f=data.origination_scores[Number(scoreChoice.value)],summary=$('orig-score-summary');summary.className='metric-grid';summary.replaceChildren(metric('Score available',n(f.available_n),pct(f.available_share_of_full_sample)+' of mortgage sample'));const rows=f.categories.map(c=>[c.code,c.label,n(c.n),pct(c.share_of_full_sample),dec(c.weight_sum_descriptive_only)]);$('orig-score-table').replaceChildren(table(['VantageScore bin/code','Publisher label','Mortgages','Share of full sample','Weight sum · descriptive'],rows,[2,3,4]));};scoreChoice.addEventListener('change',drawOrig);drawOrig();
  const attrChoice=$('orig-attribute-choice');attrChoice.replaceChildren(...data.origination_attributes.map((f,i)=>{const o=node('option','',`${f.field} · ${f.label}`);o.value=String(i);return o;}));
  const drawAttribute=()=>{const f=data.origination_attributes[Number(attrChoice.value)],summary=$('orig-attribute-summary'),codeCount=code=>f.categories.find(c=>c.code===code)?.n||0,na=codeCount('-2'),missing=codeCount('-4')+f.blank_n;summary.className='metric-grid';summary.replaceChildren(metric('Applicable / observed',n(f.available_n),pct(f.available_share_of_full_sample)+' of full mortgage sample'),metric('Not applicable',n(na),pct(na/data.termination.mortgages)+' of sample'),metric('Missing / blank',n(missing),pct(missing/data.termination.mortgages)+' of sample'));const rows=f.categories.map(c=>[c.code,c.label,n(c.n),pct(c.share_of_full_sample),dec(c.weight_sum_descriptive_only)]);$('orig-attribute-table').replaceChildren(table(['Code/bin','Publisher label','Mortgages','Share of full sample','Weight sum · descriptive'],rows,[2,3,4]));};attrChoice.addEventListener('change',drawAttribute);drawAttribute();
  const scoreQuarters=data.quarterly_respondent_scores,scoreBand=$('quarter-score-band'),scoreCategories=scoreQuarters[0].categories.filter(c=>!['-2','-4'].includes(c.code));scoreBand.replaceChildren(...scoreCategories.map(c=>{const o=node('option','',`${c.code} · ${c.label}`);o.value=c.code;return o;}));
  const drawScore=()=>{const code=scoreBand.value,series=scoreQuarters.map(q=>({quarter:q.quarter,value:q.categories.find(c=>c.code===code)?.n||0}));drawChart($('score-trend'),series,`Respondent VantageScore 3.0 bin ${code}`);$('score-trend-caption').textContent=`${code} · ${scoreCategories.find(c=>c.code===code)?.label||''} · rows with the selected as-of quarterly score bin`;};scoreBand.addEventListener('change',drawScore);drawScore();
  const frows=data.quarterly_forbearance.map(q=>{const cat=code=>q.categories.find(c=>c.code===code)?.n||0;return [q.quarter,n(cat('1')),n(q.available_n),q.affirmative_share_of_known_responses===null?'—':pct(q.affirmative_share_of_known_responses),q.affirmative_weighted_share_of_known_responses_descriptive_only===null?'—':pct(q.affirmative_weighted_share_of_known_responses_descriptive_only),n(cat('-2')),n(cat('-4')),n(q.blank_n)];});$('forbearance-table').replaceChildren(table(['Quarter','In forbearance','Answered 1/2','Share of answered','Weighted share · descriptive','Not applicable','Missing','Blank'],frows,[1,2,3,4,5,6,7]));
  const pairs=data.observed_state_transitions,pairChoice=$('transition-pair-choice'),basis=$('transition-basis');pairChoice.replaceChildren(...pairs.map((p,i)=>{const o=node('option','',`${p.from_quarter_end} → ${p.to_quarter_end}`);o.value=String(i);return o;}));
  const states=['C','1','2','3','4','5','6','7','8','9'];const drawMatrix=()=>{const p=pairs[Number(pairChoice.value)],weighted=basis.value==='weight',value=x=>weighted?x.weight_sum_descriptive_only:x.n,fromTotals=new Map();for(const x of p.transitions)fromTotals.set(x.from,(fromTotals.get(x.from)||0)+value(x));const byKey=new Map(p.transitions.map(x=>[`${x.from}>${x.to}`,x])),rows=states.map(from=>{const vals=states.map(to=>{const x=byKey.get(`${from}>${to}`);return x?`${weighted?dec(value(x)):n(value(x))} (${pct(value(x)/(fromTotals.get(from)||1))})`:'—';});return [from,...vals,weighted?dec(fromTotals.get(from)||0):n(fromTotals.get(from)||0)];});$('transition-meta').textContent=`${weighted?dec(p.transitions.reduce((a,x)=>a+value(x),0)):n(p.observed_to_observed_n)} observed→observed loan-quarter transitions; administrative/gap transitions are tallied separately (${Object.entries(p.all_pair_observation_classes).map(([k,v])=>`${k}: ${n(v)}`).join(' · ')}). ${weighted?'Analysis-weight sum; descriptive only.':'Unweighted count.'}`;const t=table(['From ↓ / To →',...states,weighted?'Weight total':'Row total'],rows,[...Array(11).keys()].slice(1));t.classList.add('transition-matrix');$('transition-matrix').replaceChildren(t);};pairChoice.addEventListener('change',drawMatrix);basis.addEventListener('change',drawMatrix);drawMatrix();
  $('limits').replaceChildren(...[...document.querySelectorAll('#limits li')].map(x=>x.cloneNode(true)),...data.limitations.map(x=>node('li','',x)));
}
async function loadTargetFeasibility(){
  const state=$('target-feasibility-state');
  try{const r=await fetch('/api/nsmo-target-feasibility',{cache:'no-store',headers:{Accept:'application/json'}});const body=await r.json();if(!r.ok)throw new Error(body.error||`HTTP ${r.status}`);renderTargetFeasibility(body);state.className='domain-state ok';state.textContent='Receipt verified against this PUF SHA-256 · aggregate-only · no target labels produced.';}
  catch(error){state.className='domain-state error';state.textContent=`Target-feasibility view unavailable: ${error.message}`;}
}
function renderTargetFeasibility(data){
  const mode=$('target-anchor-choice'),band=$('target-vintage-band');
  const results=['observed_90plus_event','four_quarters_observed_no_event','observed_other_adverse_state_7','observed_other_adverse_state_8','observed_other_adverse_state_9','termination_competing_censor','termination_same_month_ambiguous','observation_censor_M','observation_censor_S','administratively_short_followup','not_open_at_baseline'];
  const labels={'observed_90plus_event':'Observed 90+','four_quarters_observed_no_event':'No 90+ · four observed quarters','observed_other_adverse_state_7':'Bankruptcy 13','observed_other_adverse_state_8':'Foreclosure / surrender','observed_other_adverse_state_9':'Other adverse disposition','termination_competing_censor':'Termination before next snapshot','termination_same_month_ambiguous':'Termination same-month ambiguity','observation_censor_M':'Archive gap (M)','observation_censor_S':'Suppressed (S)','administratively_short_followup':'Short administrative horizon','not_open_at_baseline':'Closed by baseline'};
  const zero=()=>Object.fromEntries(results.map(k=>[k,0]));
  const merge=(target,source)=>{for(const [key,value] of Object.entries(source||{}))target[key]=(target[key]||0)+Number(value||0);return target;};
  const bandYears=value=>{if(value==='all')return null;const [a,b]=value.split('-').map(Number);return year=>Number(year)>=a&&Number(year)<=b;};
  const numberOf=counts=>Object.values(counts||{}).reduce((a,b)=>a+Number(b||0),0);
  function draw(){
    const one=mode.value==='single',years=bandYears(band.value),rows=one?data.one_landmark_per_mortgage.origination_vintage_rows:data.repeated_landmarks.origination_vintage_rows.filter(x=>x.baseline_state==='C');
    const selected=rows.filter(x=>!years||years(x.origination_year));let totals=zero(),basisTotal=0,uniquePositive=0,uniqueBaseline=0;
    selected.forEach(x=>{const counts=one?x.outcomes_unweighted:x.full_horizon_baseline_snapshots_unweighted;merge(totals,counts);basisTotal+=one?Number(x.unique_mortgage_count):numberOf(counts);if(one)uniquePositive+=Number(counts.observed_90plus_event||0);else{uniqueBaseline+=Number(x.unique_mortgages_with_at_least_one_full_horizon_baseline||0);uniquePositive+=Number(x.unique_mortgages_by_snapshot_outcome_class_nonexclusive?.observed_90plus_event||0);}});
    const censored=totals.termination_competing_censor+totals.termination_same_month_ambiguous+totals.observation_censor_M+totals.observation_censor_S;
    $('target-feasibility-metrics').replaceChildren(
      metric(one?'Unique mortgages · one landmark':'Full-horizon C snapshots',n(basisTotal),one?'One earliest eligible C snapshot per mortgage':'Each quarterly C snapshot is a separate baseline'),
      metric(one?'90+ outcomes · unique mortgages':'90+ outcomes · snapshots',n(totals.observed_90plus_event),one?'One outcome per mortgage in this sizing diagnostic':'Primary observed endpoint candidate · codes 3–6'),
      metric('Four observed quarters · no 90+',n(totals.four_quarters_observed_no_event),'Complete observed window; not a population negative rate'),
      metric('Censored / ambiguous',n(censored),'Termination, same-month ordering, M and S')
    );
    $('target-feasibility-note').textContent=one
      ?`One C landmark per mortgage: earliest C snapshot with four future quarterly snapshots and no known closure by baseline. This avoids repeated rows but is not an origination-date model. ${n(uniquePositive)} observed 90+ outcomes in the selected vintage scope; this is sample support, not PD.`
      :`Repeated C landmarks: ${n(uniqueBaseline)} unique mortgages contribute at least one full-horizon snapshot, with ${n(uniquePositive)} distinct mortgages ever positive across their C landmarks. A loan may be positive at one landmark and negative/censored at another; these supports overlap and are not independent.`;
    const vintageRows=selected.map(x=>{
      const counts=one?x.outcomes_unweighted:x.full_horizon_baseline_snapshots_unweighted;
      const row=[x.origination_year,n(one?x.unique_mortgage_count:numberOf(counts)),n(counts.observed_90plus_event||0),n(counts.four_quarters_observed_no_event||0),n(counts.observed_other_adverse_state_7||0),n(counts.observed_other_adverse_state_8||0),n(counts.observed_other_adverse_state_9||0),n(counts.termination_competing_censor||0),n(counts.termination_same_month_ambiguous||0),n(counts.observation_censor_M||0),n(counts.observation_censor_S||0)];
      if(!one)row.push(n(x.unique_mortgages_with_at_least_one_full_horizon_baseline),n(x.unique_mortgages_by_snapshot_outcome_class_nonexclusive?.observed_90plus_event||0));
      return row;
    });
    const headers=['Origination vintage',one?'Unique mortgages':'Baseline snapshots','Observed 90+','No 90+ · complete 4Q','Code 7','Code 8','Code 9','Terminated before snapshot','Same-month ambiguous','Gap M','Suppressed S'];
    if(!one)headers.push('Unique loans with C baseline','Unique loans ever positive*');
    $('target-vintage-table').replaceChildren(table(headers,vintageRows,[...Array(headers.length-1).keys()].slice(1)));
    if(!one){
      const quarterRows=data.repeated_landmarks.quarter_state_rows.filter(x=>x.baseline_state==='C').map(x=>{const c=x.outcomes_unweighted;return [x.baseline_quarter,x.full_12m_snapshot_horizon_available?'4Q available':'short horizon',n(numberOf(c)),n(c.observed_90plus_event||0),n(c.four_quarters_observed_no_event||0),n(c.termination_competing_censor||0),n(c.termination_same_month_ambiguous||0),n((c.observation_censor_M||0)+(c.observation_censor_S||0)),n(c.administratively_short_followup||0)];});
      $('target-quarter-table').replaceChildren(table(['C baseline quarter','Follow-up support','Snapshots','90+','No 90+ complete','Termination','Same-month ambiguous','M/S','Short horizon'],quarterRows,[2,3,4,5,6,7,8]));
    }else{
      const grouped=new Map();for(const x of data.one_landmark_per_mortgage.landmark_quarter_vintage_rows){if(years&&!years(x.origination_year))continue;const g=grouped.get(x.landmark_quarter)||{n:0,counts:zero()};g.n+=Number(x.unique_mortgage_count);merge(g.counts,x.outcomes_unweighted);grouped.set(x.landmark_quarter,g);}
      const quarterRows=[...grouped.entries()].sort((a,b)=>a[0].localeCompare(b[0])).map(([q,g])=>[q,n(g.n),n(g.counts.observed_90plus_event||0),n(g.counts.four_quarters_observed_no_event||0),n(g.counts.termination_competing_censor||0),n(g.counts.termination_same_month_ambiguous||0),n((g.counts.observation_censor_M||0)+(g.counts.observation_censor_S||0))]);
      $('target-quarter-table').replaceChildren(table(['Earliest eligible C quarter','Unique mortgages','90+','No 90+ complete','Termination','Same-month ambiguous','M/S'],quarterRows,[1,2,3,4,5,6]));
    }
  }
  mode.addEventListener('change',draw);band.addEventListener('change',draw);draw();
}
async function loadOriginationFeasibility(){
  const state=$('origination-feasibility-state');
  try{const r=await fetch('/api/nsmo-origination-feasibility',{cache:'no-store',headers:{Accept:'application/json'}});const body=await r.json();if(!r.ok)throw new Error(body.error||`HTTP ${r.status}`);renderOriginationFeasibility(body);state.className='domain-state ok';state.textContent='Receipt verified against this PUF SHA-256 · aggregate-only · no target labels produced.';}
  catch(error){state.className='domain-state error';state.textContent=`Origination feasibility unavailable: ${error.message}`;}
}
function renderOriginationFeasibility(data){
  const band=$('target-vintage-band');
  const keys=['observed_90plus','all_in_window_snapshots_observed_no_90plus','observed_other_adverse_state_7','observed_other_adverse_state_8','observed_other_adverse_state_9','termination_competing_censor','termination_same_month_ambiguous','observation_censor_K','observation_censor_M','observation_censor_S','administratively_short_followup'];
  const total=counts=>keys.reduce((sum,key)=>sum+Number(counts?.[key]||0),0);
  const label=key=>({
    observed_90plus:'Observed 90+',
    all_in_window_snapshots_observed_no_90plus:'All snapshots observed · no 90+',
    observed_other_adverse_state_7:'Code 7 · bankruptcy',
    observed_other_adverse_state_8:'Code 8 · foreclosure',
    observed_other_adverse_state_9:'Code 9 · other adverse',
    termination_competing_censor:'Closed before next snapshot',
    termination_same_month_ambiguous:'Same-month closure ambiguity',
    observation_censor_K:'K · not yet reported',
    observation_censor_M:'M · archive gap',
    observation_censor_S:'S · suppressed',
    administratively_short_followup:'Administrative short follow-up'
  }[key]||key);
  function draw(){
    const selected=data.outcomes_by_origination_year.filter(row=>{const value=band.value;if(value==='all')return true;const [first,last]=value.split('-').map(Number);return Number(row.origination_year)>=first&&Number(row.origination_year)<=last;});
    const counts={};selected.forEach(row=>{for(const [key,value] of Object.entries(row.outcomes_unweighted||{}))counts[key]=(counts[key]||0)+Number(value||0);});
    const censor=Number(counts.termination_competing_censor||0)+Number(counts.termination_same_month_ambiguous||0)+Number(counts.observation_censor_K||0)+Number(counts.observation_censor_M||0)+Number(counts.observation_censor_S||0)+Number(counts.administratively_short_followup||0);
    const adverse=Number(counts.observed_other_adverse_state_7||0)+Number(counts.observed_other_adverse_state_8||0)+Number(counts.observed_other_adverse_state_9||0);
    $('origination-feasibility-metrics').replaceChildren(
      metric('Mortgages in selected vintage',n(total(counts)),'Unweighted PUF rows; not a population denominator'),
      metric('Observed 90+ snapshots',n(counts.observed_90plus||0),'First observed 90+ code 3–6 in the window'),
      metric('All snapshots observed · no 90+',n(counts.all_in_window_snapshots_observed_no_90plus||0),'No 90+ observed; not proof of event-free history'),
      metric('Censor / ambiguous / short',n(censor),'K/M/S, termination, same-month ambiguity and data-end truncation')
    );
    $('origination-feasibility-note').textContent=`Other adverse states 7–9 remain separate (${n(adverse)}). This sizes observable support only; monthly opening date and quarterly snapshots cannot establish event dates, incidence or PD.`;
    const rows=selected.map(row=>{const c=row.outcomes_unweighted||{};return [row.origination_year,n(total(c)),n(c.observed_90plus||0),n(c.all_in_window_snapshots_observed_no_90plus||0),n(c.observation_censor_K||0),n(c.observation_censor_M||0),n(c.observation_censor_S||0),n(c.termination_competing_censor||0),n(c.termination_same_month_ambiguous||0),n((c.observed_other_adverse_state_7||0)+(c.observed_other_adverse_state_8||0)+(c.observed_other_adverse_state_9||0)),n(c.administratively_short_followup||0)];});
    $('origination-feasibility-table').replaceChildren(table(['Origination year','Mortgages','Observed 90+','No 90+ · observed','K','M','S','Closed before next','Same-month ambiguous','Other adverse 7–9','Short follow-up'],rows,[1,2,3,4,5,6,7,8,9,10]));
  }
  band.addEventListener('change',draw);draw();
}
function loadDictionary(){
  fetch('/api/nsmo-dictionary',{cache:'no-store',headers:{Accept:'application/json'}}).then(async r=>{const data=await r.json();if(!r.ok)throw new Error(data.error||`HTTP ${r.status}`);renderDictionary(data);}).catch(error=>{$('dictionary-count').textContent=`Không tải được: ${error.message}`;});
}
function renderDictionary(data){
  const labels=new Map();for(const item of data.value_labels){const key=item.format_name.replace(/^\$/,'').toUpperCase();if(!labels.has(key))labels.set(key,[]);labels.get(key).push(item);}
  const coverage=new Map(data.wave_coverage.map(item=>[item.csv_column,item]));
  const itemReview=new Map(data.item_comparability.map(item=>[item.field,item]));
  const search=$('field-search'),results=$('field-results'),detail=$('field-detail');let selected=null;
  function show(field){selected=field;results.querySelectorAll('button').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.field===field.csv_column)));detail.replaceChildren();
    const title=node('h3','',field.csv_column);detail.append(title,node('p','field-label',field.sas_label||field.codebook_name));
    const wave=coverage.get(field.csv_column);const rows=[['Codebook',`${field.codebook_part} · ${field.codebook_name}`],['Family / timing',`${field.field_family} · ${field.timing_class}`],['Predictor gate',field.predictor_use],['Wave mentions in codebook',field.survey_wave_ranges||'N/A — supplemental field'],['Observed response waves',wave?.observed_response_waves||'N/A'],['Entirely not asked (SAS -3)',wave?.entirely_not_asked_waves||'None observed'],['Partially not asked (SAS -3)',wave?.partially_not_asked_waves||'None observed'],['Not applicable (SAS -2)',wave?.not_applicable_waves||'None observed'],['Question / condition',[field.survey_question_refs,field.codebook_condition].filter(Boolean).join(' · ')||'No survey question'],['Source location',`${field.printed_page||'—'} (PDF page ${field.pdf_page||'—'})`],['SAS',`${field.sas_format||'No format'} · ${field.sas_length||'—'} · ${field.sas_label||''}`]];
    const dl=document.createElement('dl');for(const [term,value] of rows){dl.append(node('dt','',term),node('dd','',value));}detail.append(dl);
    const review=itemReview.get(field.csv_column);if(review){const box=node('aside','item-review');box.append(node('strong','','Cross-wave comparability'),node('p','',review.assessment));detail.append(box);}
    const key=(field.sas_format||'').replace(/^\$/,'').toUpperCase(),items=labels.get(key)||[];if(items.length){detail.append(node('h4','','Giá trị theo SAS format'));const list=document.createElement('ul');list.className='value-labels';for(const item of items)list.append(node('li','',`${item.format_value} → ${item.format_label}`));detail.append(list);}
  }
  function update(){const q=search.value.trim().toLowerCase();const matches=data.fields.filter(f=>[f.csv_column,f.codebook_name,f.sas_label,f.field_family,f.survey_question_refs,f.predictor_use,coverage.get(f.csv_column)?.observed_response_waves,itemReview.get(f.csv_column)?.assessment].some(x=>(x||'').toLowerCase().includes(q))).slice(0,100);results.replaceChildren();for(const field of matches){const b=node('button','field-option');b.type='button';b.dataset.field=field.csv_column;b.setAttribute('role','option');b.setAttribute('aria-selected',String(selected?.csv_column===field.csv_column));b.append(node('strong','',field.csv_column),node('small','',field.sas_label||field.codebook_name));b.addEventListener('click',()=>show(field));results.append(b);} $('dictionary-count').textContent=`${data.field_count} trường · ${data.wave_coverage_count} biến survey có coverage · ${data.item_comparability_count} ghi chú so sánh item · ${matches.length}${q?' kết quả':' trường đầu'}`;if(!selected&&matches.length)show(matches[0]);}
  search.addEventListener('input',update);update();
}
async function load(){loadDictionary();try{const r=await fetch('/api/nsmo-profile',{cache:'no-store',headers:{Accept:'application/json'}});const body=await r.json();if(!r.ok)throw new Error(body.error||`HTTP ${r.status}`);render(body);}catch(error){$('state').className='state error';$('state').textContent=`D02 NSMO chưa sẵn sàng: ${error.message}. Hoàn tất tải PUF, chạy audit aggregate-only và kiểm tra local receipt; trang không dựng dữ liệu giả.`;}}
load();
