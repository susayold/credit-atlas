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
  loadFirstObservedTransitionSupport();
  loadFirstEntryRiskSetFeasibility();
  loadHudFhaBenchmark();
  loadNmdbContext();
  loadSurveyReturns();
}
async function loadHudFhaBenchmark(){
  const state=$('hud-fha-state');
  try{
    const response=await fetch('/api/hud-fha-performance',{cache:'no-store',headers:{Accept:'application/json'}});
    const data=await response.json();if(!response.ok)throw new Error(data.error||`HTTP ${response.status}`);
    const adjustment=$('hud-adjustment');
    const dimension=$('hud-subgroup-dimension');
    const dimensionNames={loan_purpose:'Loan purpose',refinance:'Refinance',credit_score:'Origination credit score',fiscal_year_cohort:'Fiscal-year cohort',origination_loan_amount:'Loan amount at origination',property_type:'Property type',purchase_loan_type:'Purchase loan type',down_payment_assistance:'Down payment assistance'};
    const render=()=>{
      const latest=data.latest[adjustment.value];
      $('hud-fha-metrics').replaceChildren(
        metric('Active FHA loans · EOM',n(latest.active_iif_count),'Insurance in Force · Aug 2026'),
        metric('Serious delinquency',dec(latest.serious_delinquency_pct)+'%','90+ days + foreclosure + bankruptcy'),
        metric('90-day delinquency',dec(latest.delinquency_90d_pct)+'%','Excludes foreclosure/bankruptcy processing'),
        metric('In foreclosure',dec(latest.foreclosure_pct)+'%','Portfolio snapshot rate')
      );
      const rows=data.monthly.filter(row=>row.adjustment===adjustment.value).map(row=>[
        row.month,n(row.active_iif_count),dec(row.delinquency_30d_pct)+'%',dec(row.delinquency_60d_pct)+'%',
        dec(row.delinquency_90d_pct)+'%',dec(row.foreclosure_pct)+'%',dec(row.bankruptcy_pct)+'%',
        dec(row.serious_delinquency_pct)+'%'
      ]);
      $('hud-fha-monthly').replaceChildren(table(['Month','Active IIF','30 day','60 day','90 day','Foreclosure','Bankruptcy','Serious delinquency'],rows,[1,2,3,4,5,6,7]));
      const subgroups=data.subgroups.filter(row=>dimension.value==='all'||row.dimension===dimension.value).map(row=>[
        dimensionNames[row.dimension]||row.dimension,row.parent_category||'—',row.category,
        row.iif_count==null?'—':n(row.iif_count),
        row.iif_share_pct==null?'—':dec(row.iif_share_pct)+'%',row.share_denominator||'—',
        row.all_past_due_pct==null?'—':dec(row.all_past_due_pct)+'%',
        dec(row.delinquency_30d_pct)+'%',dec(row.delinquency_60d_pct)+'%',dec(row.delinquency_90plus_pct)+'%',
        dec(row.foreclosure_pct)+'%',dec(row.bankruptcy_pct)+'%',dec(row.serious_delinquency_pct)+'%',
        'p. '+row.source_page
      ]);
      $('hud-fha-subgroups').replaceChildren(table(['Dimension','Parent','Category','IIF count','IIF share','Share basis','All past due','30 day','60 day','90+','Foreclosure','Bankruptcy','Serious delinquency','Source'],subgroups,[3,4,6,7,8,9,10,11,12]));
    };
    adjustment.addEventListener('change',render);dimension.addEventListener('change',render);render();
    state.className='domain-state ok';state.textContent='HUD August 2026 report transcription loaded · 13 monthly observations × NSA/SA · 60 Table 3 rows across eight panels · aggregate only.';
  }catch(error){state.className='domain-state error';state.textContent=`HUD FHA benchmark unavailable: ${error.message}`;}
}
async function loadNmdbContext(){
  const state=$('nmdb-state');
  try{
    const response=await fetch('/api/nmdb-performance',{cache:'no-store',headers:{Accept:'application/json'}});
    const data=await response.json();if(!response.ok)throw new Error(data.error||`HTTP ${response.status}`);
    const seriesChoice=$('nmdb-series'),marketChoice=$('nmdb-market');
    marketChoice.replaceChildren(...data.markets.map(item=>{const option=node('option','',item.name);option.value=item.name;return option;}));
    const seriesLabels={};for(const [key,value] of Object.entries(data.series)){seriesLabels[key]=value.label;}
    const fmtRate=value=>value==null?'—':dec(value)+'%';
    const render=()=>{
      const seriesId=seriesChoice.value,selectedMarket=marketChoice.value,latest=data.latest.filter(row=>row.series_id===seriesId);
      $('nmdb-latest').replaceChildren(...latest.map(row=>metric(row.market,fmtRate(row.value_pct),`${seriesLabels[seriesId]} · ${row.period}${row.suppressed?' · suppressed':''}`)));
      drawNmdbTrend($('nmdb-trend'),data.observations,seriesId,data.markets);
      $('nmdb-caption').textContent=`${seriesLabels[seriesId]} · quarterly national aggregate · ${data.periods[0]} to ${data.periods.at(-1)}. ${data.series[seriesId].description}`;
      const legend=$('nmdb-legend');legend.replaceChildren(...data.markets.map((market,index)=>{const item=node('span','nmdb-legend-item');const swatch=node('i','nmdb-swatch');swatch.style.backgroundColor=nmdbColors[index];item.append(swatch,node('strong','',market.name));return item;}));
      const rows=data.periods.map(period=>{
        const values=new Map(data.observations.filter(row=>row.market===selectedMarket&&row.period===period).map(row=>[row.series_id,row]));
        return [period,...Object.keys(data.series).map(key=>fmtRate(values.get(key)?.value_pct)),...Object.keys(data.series).map(key=>values.get(key)?.suppressed?'Yes':'No')];
      });
      $('nmdb-quarterly').replaceChildren(table(['Quarter','30–60 DPD','90+ DPD','Foreclosure / bankruptcy / DIL','Forbearance','30–60 suppressed','90+ suppressed','Foreclosure suppressed','Forbearance suppressed'],rows));
    };
    seriesChoice.addEventListener('change',render);marketChoice.addEventListener('change',render);render();
    state.className='domain-state ok';state.textContent=`FHFA NMDB aggregate verified · ${data.observations.length.toLocaleString('en-US')} national market-series-quarter rows · ${data.periods[0]}–${data.periods.at(-1)} · source ${data.source.release_date}.`;
  }catch(error){state.className='domain-state error';state.textContent=`NMDB national benchmark unavailable: ${error.message}`;}
}
const nmdbColors=['#118579','#426a85','#7b61a8','#d28a3b'];
function drawNmdbTrend(svg,observations,seriesId,markets){
  svg.replaceChildren();const w=980,h=340,left=64,right=18,top=22,bottom=46,plotW=w-left-right,plotH=h-top-bottom;
  const values=observations.filter(row=>row.series_id===seriesId&&row.value_pct!==null).map(row=>row.value_pct);
  const maximum=Math.max(1,...values),step=maximum<=2?.25:maximum<=5?.5:maximum<=10?1:2,limit=Math.ceil(maximum/step)*step;
  for(let i=0;i<=4;i++){
    const value=limit-i*limit/4,y=top+i*plotH/4;
    const line=document.createElementNS('http://www.w3.org/2000/svg','line');line.setAttribute('x1',left);line.setAttribute('x2',w-right);line.setAttribute('y1',y);line.setAttribute('y2',y);line.setAttribute('class','grid-line');svg.append(line);
    const label=document.createElementNS('http://www.w3.org/2000/svg','text');label.setAttribute('x',left-9);label.setAttribute('y',y+4);label.setAttribute('text-anchor','end');label.setAttribute('class','axis-label');label.textContent=dec(value)+'%';svg.append(label);
  }
  const periods=[...new Set(observations.map(row=>row.period))].sort((a,b)=>Number(a.slice(0,4))-Number(b.slice(0,4))||Number(a.slice(5))-Number(b.slice(5)));
  markets.forEach((market,marketIndex)=>{
    const byPeriod=new Map(observations.filter(row=>row.market===market.name&&row.series_id===seriesId).map(row=>[row.period,row.value_pct]));
    let points=[];for(const period of periods){const value=byPeriod.get(period);if(value==null)continue;const i=periods.indexOf(period);points.push(`${left+i*plotW/(periods.length-1)},${top+plotH-(value/limit)*plotH}`);}
    const path=document.createElementNS('http://www.w3.org/2000/svg','polyline');path.setAttribute('points',points.join(' '));path.setAttribute('class','nmdb-line');path.setAttribute('stroke',nmdbColors[marketIndex]);svg.append(path);
  });
  const every=Math.ceil(periods.length/10);periods.forEach((period,index)=>{if(index%every!==0&&index!==periods.length-1)return;const x=left+index*plotW/(periods.length-1),label=document.createElementNS('http://www.w3.org/2000/svg','text');label.setAttribute('x',x);label.setAttribute('y',h-14);label.setAttribute('text-anchor','middle');label.setAttribute('class','axis-label');label.textContent=period;svg.append(label);});
  svg.setAttribute('aria-label',`${seriesId} rates by mortgage market from ${periods[0]} to ${periods.at(-1)}.`);
}
async function loadDomainAnalysis(){
  try{const r=await fetch('/api/nsmo-domains',{cache:'no-store',headers:{Accept:'application/json'}});const body=await r.json();if(!r.ok)throw new Error(body.error||`HTTP ${r.status}`);renderDomains(body);$('domain-state').className='domain-state ok';$('domain-state').textContent='Aggregates verified against the same PUF SHA-256 as the structural profile.';}
  catch(error){$('domain-state').className='domain-state error';$('domain-state').textContent=`Domain metrics unavailable: ${error.message}`;}
}
async function loadSurveyReturns(){
  const state=$('survey-returns-state');
  try{
    const response=await fetch('/api/nsmo-survey-returns',{cache:'no-store',headers:{Accept:'application/json'}});
    const data=await response.json();if(!response.ok)throw new Error(data.error||`HTTP ${response.status}`);
    const p=data.puf_v70,shift=data.mode_shift;
    $('survey-returns-metrics').replaceChildren(
      metric('Completed surveys · waves 1–46',n(p.surveys_completed_total),`${n(p.waves)} waves in v7.0 PUF`),
      metric('Completed / mailed',`${dec(p.completion_pct_of_mailed)}%`,`${n(p.surveys_mailed)} mailed surveys`),
      metric('Online share of completes',`${dec(p.online_share_pct_of_completed)}%`,`${n(p.online_english)} English · ${n(p.online_spanish)} Spanish`),
      metric('Online share · wave 1 → 46',`${dec(shift.wave_1_online_share_pct)}% → ${dec(shift.wave_46_online_share_pct)}%`,`+${dec(shift.change_percentage_points)} percentage points`)
    );
    const rows=data.waves.map(row=>[
      row.survey_wave,n(row.surveys_mailed),n(row.surveys_delivered),n(row.surveys_completed_total),
      n(row.completed_by_mail),n(row.online_english),n(row.online_spanish),
      `${dec(row.completion_pct_of_mailed)}%`,`${dec(row.online_share_pct_of_completed)}%`,
      row.included_in_nsmo_v70_puf?'PUF v7.0':'Outside PUF'
    ]);
    const view=table(['Wave','Mailed','Delivered','Completed','Mail','Online EN','Online ES','Complete / mailed','Online / completed','Release'],rows,[1,2,3,4,5,6,7,8]);
    view.classList.add('survey-returns-table');$('survey-returns-table').replaceChildren(view);
    const usable=data.usability,excluded=Object.values(usable.exclusions_by_disposition).reduce((a,b)=>a+b,0);
    $('usable-responses-metrics').replaceChildren(
      metric('Usable returns · Table 4',n(usable.usable_responses_table4),`${dec(usable.usable_share_of_returned_pct)}% of completed returns`),
      metric('Rows in PUF v7.0',n(usable.puf_v70_rows_and_tables5_6_2013_2024),'Tables 5–6 · origination 2013–2024'),
      metric('Returned but unusable',n(excluded),'Duplicate/ineligible, Q1 no, breakoff, wrong loan'),
      metric('Usable outside PUF scope',n(usable.usable_table4_minus_puf_scope),`${n(usable.wave_7_remote_rural_scope_gap)} wave 7 · ${n(usable.wave_45_46_origination_scope_gap)} waves 45–46`)
    );
    const usabilityRows=usable.waves.map(row=>[
      row.survey_wave,n(row.surveys_completed_total),n(row.duplicate_or_ineligible),n(row.answered_no_to_q1),
      n(row.did_not_finish_survey),n(row.wrong_loan),n(row.usable_responses_table4),
      n(row.usable_responses_origination_2013_2024_tables5_6),n(row.gap_to_usable_table4)
    ]);
    const usabilityTable=table(['Wave','Returned','Duplicate / ineligible','No to Q1','Did not finish','Wrong loan','Usable · Table 4','Usable · Tables 5/6','Scope gap'],usabilityRows,[1,2,3,4,5,6,7,8]);
    usabilityTable.classList.add('usable-responses-table');$('usable-responses-table').replaceChildren(usabilityTable);
    state.className='domain-state ok';state.textContent='48 waves reconciled to FHFA Table 3 totals · aggregate-only · no respondent or mortgage linkage.';
  }catch(error){state.className='domain-state error';state.textContent=`Survey response-mode table unavailable: ${error.message}`;}
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
    const sameMonthRows=(data.same_month_ambiguity?.snapshot_status_counts_by_vintage_and_baseline_state||[])
      .filter(row=>!years||years(row.origination_year));
    const statusCounts=new Map();
    sameMonthRows.forEach(row=>{
      const key=row.baseline_state;
      const counts=statusCounts.get(key)||{};
      for(const [status,count] of Object.entries(row.snapshot_status_counts_unweighted||{}))counts[status]=(counts[status]||0)+Number(count||0);
      statusCounts.set(key,counts);
    });
    const statusLabel=code=>code==='<BLANK>'?'Blank':code==='A'?'A · history ended':code;
    const ambiguityRows=[...statusCounts.entries()].sort((a,b)=>({C:0,'1':1,'2':2}[a[0]]??9)-({C:0,'1':1,'2':2}[b[0]]??9))
      .flatMap(([baseline,counts])=>Object.entries(counts).sort((a,b)=>a[0].localeCompare(b[0])).map(([status,count])=>[baseline,statusLabel(status),n(count)]));
    const ambiguityTotals={C:0,'1':0,'2':0};
    for(const [baseline,counts] of statusCounts)ambiguityTotals[baseline]=Object.values(counts).reduce((sum,value)=>sum+Number(value||0),0);
    $('same-month-ambiguity-metrics').replaceChildren(
      metric('Baseline C',n(ambiguityTotals.C),'Same-month tied quarterly snapshots'),
      metric('Baseline 30–59 days',n(ambiguityTotals['1']),'Same-month tied quarterly snapshots'),
      metric('Baseline 60–89 days',n(ambiguityTotals['2']),'Same-month tied quarterly snapshots')
    );
    $('same-month-ambiguity-table').replaceChildren(table(['Baseline state','Performance code in tied quarter','Snapshots'],ambiguityRows,[2]));
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
async function loadFirstObservedTransitionSupport(){
  const state=$('transition-support-state');
  try{const response=await fetch('/api/nsmo-first-observed-transition-support',{cache:'no-store',headers:{Accept:'application/json'}});const data=await response.json();if(!response.ok)throw new Error(data.error||`HTTP ${response.status}`);renderFirstObservedTransitionSupport(data);state.className='domain-state ok';state.textContent='Receipt verified against this PUF SHA-256 · aggregate-only · no target labels produced.';}
  catch(error){state.className='domain-state error';state.textContent=`Transition-support view unavailable: ${error.message}`;}
}
function renderFirstObservedTransitionSupport(data){
  const band=$('target-vintage-band'),summary=data.all_vintages,states=['C','1','2'];
  const labels={C:'Current (C)',1:'30–59 days (1)',2:'60–89 days (2)'};
  function draw(){
    const years=band.value==='all'?null:band.value.split('-').map(Number);
    const rows=data.by_origination_vintage_and_source_state.filter(row=>!years||(Number(row.origination_year)>=years[0]&&Number(row.origination_year)<=years[1]));
    const totals=Object.fromEntries(states.map(code=>[code,{repeated:0,unique:0,first:0}]));
    rows.forEach(row=>{const t=totals[row.source_state];t.repeated+=Number(row.repeated_90plus_transition_count);t.unique+=Number(row.unique_mortgages_with_any_90plus_transition);t.first+=Number(row.first_observed_90plus_event_count);});
    $('transition-support-metrics').replaceChildren(...states.map(code=>metric(`${labels[code]} → 90+`,`${n(totals[code].repeated)} / ${n(totals[code].unique)}`,`Transitions lặp / mortgage duy nhất · ${n(totals[code].first)} là first-observed 90+ từ trạng thái này`)));
    $('transition-support-table').replaceChildren(table(['Origination year','State đầu quý','Repeated → 90+','Mortgage duy nhất','First observed 90+'],rows.map(row=>[row.origination_year,labels[row.source_state],n(row.repeated_90plus_transition_count),n(row.unique_mortgages_with_any_90plus_transition),n(row.first_observed_90plus_event_count)]),[2,3,4]));
    $('transition-support-note').textContent=`Trong toàn PUF có ${n(summary.first_observed_90plus_event_count)} mortgage với trạng thái 90+ được quan sát lần đầu trong chuỗi; ${n(summary.first_observed_90plus_event_with_baseline_source_state)} có snapshot trước đó là C/1/2, ${n(summary.first_observed_90plus_event_after_other_adverse_state)} theo sau 7–9, và ${n(summary.first_observed_90plus_event_without_observed_prior)} không có trạng thái quan sát ngay trước đó. Bộ lọc vintage tác động bảng và ba metric theo C/1/2; các tổng partition này luôn là toàn PUF.`;
  }
  band.addEventListener('change',draw);draw();
}
async function loadFirstEntryRiskSetFeasibility(){
  const state=$('first-entry-risk-set-state');
  try{const response=await fetch('/api/nsmo-first-entry-risk-set-feasibility',{cache:'no-store',headers:{Accept:'application/json'}});const data=await response.json();if(!response.ok)throw new Error(data.error||`HTTP ${response.status}`);renderFirstEntryRiskSetFeasibility(data);state.className='domain-state ok';state.textContent='Receipt verified against this PUF SHA-256 · aggregate-only · no target labels produced.';}
  catch(error){state.className='domain-state error';state.textContent=`First-entry risk-set view unavailable: ${error.message}`;}
}
function renderFirstEntryRiskSetFeasibility(data){
  const band=$('target-vintage-band'),entryChoice=$('risk-entry-state');
  const outcomeLabels={observed_90plus:'Observed 90+',competing_adverse_7:'7',competing_adverse_8:'8',competing_adverse_9:'9',termination_competing:'Closed before next quarter',termination_same_month_ambiguous:'Same-month ambiguous',administrative_end:'Administrative end'};
  function draw(){
    const years=band.value==='all'?null:band.value.split('-').map(Number),entry=entryChoice.value;
    const rows=data.by_origination_vintage_and_entry_state_unweighted.filter(row=>(!years||(Number(row.origination_year)>=years[0]&&Number(row.origination_year)<=years[1]))&&(entry==='all'||row.entry_state===entry));
    const entered=rows.reduce((sum,row)=>sum+Number(row.mortgages_entered),0),intervals=rows.reduce((sum,row)=>sum+Number(row.at_risk_quarter_intervals),0);
    const exits={};rows.forEach(row=>Object.entries(row.first_exit_by_class||{}).forEach(([key,value])=>exits[key]=(exits[key]||0)+Number(value||0)));
    const close=Number(exits.termination_competing||0)+Number(exits.termination_same_month_ambiguous||0);
    $('first-entry-risk-set-metrics').replaceChildren(
      metric('Mortgages entering risk set',n(entered),'First eligible post-origination C/1/2 snapshot; one entry per loan'),
      metric('First observed 90+ exits',n(exits.observed_90plus||0),'Observed code 3–6 at the next adjacent snapshot'),
      metric('At-risk quarter intervals',n(intervals),'Unweighted exposure intervals; not independent loans'),
      metric('Termination exits',n(close),'Earlier close plus same-month ambiguous ordering')
    );
    $('first-entry-risk-set-note').textContent=`Competing 7–9 exits: ${n(Number(exits.competing_adverse_7||0)+Number(exits.competing_adverse_8||0)+Number(exits.competing_adverse_9||0))}; administrative end: ${n(exits.administrative_end||0)}. Filtering does not change the definition; the aggregate population entry partition is ${n(data.population_partition_unweighted.entered_risk_set)}.`;
    const tableRows=rows.map(row=>{const x=row.first_exit_by_class||{},other=Number(x.observation_censor_A||0)+Number(x.observation_censor_B||0)+Number(x.observation_censor_K||0)+Number(x.observation_censor_M||0)+Number(x.observation_censor_P||0)+Number(x.observation_censor_Q||0)+Number(x.observation_censor_S||0)+Number(x.observation_censor_blank||0)+Number(x.observation_censor_unknown||0);return [row.origination_year,row.entry_state,n(row.mortgages_entered),n(row.at_risk_quarter_intervals),n(x.observed_90plus||0),n(Number(x.competing_adverse_7||0)+Number(x.competing_adverse_8||0)+Number(x.competing_adverse_9||0)),n(x.termination_competing||0),n(x.termination_same_month_ambiguous||0),n(other),n(x.administrative_end||0)];});
    $('first-entry-risk-set-table').replaceChildren(table(['Origination year','Entry state','Mortgages','Risk intervals','First 90+','Competing 7–9','Closed before next','Same-month ambiguous','Other censor','Admin end'],tableRows,[2,3,4,5,6,7,8,9]));
  }
  band.addEventListener('change',draw);entryChoice.addEventListener('change',draw);draw();
}
function loadDictionary(){
  fetch('/api/nsmo-dictionary',{cache:'no-store',headers:{Accept:'application/json'}}).then(async r=>{const data=await r.json();if(!r.ok)throw new Error(data.error||`HTTP ${r.status}`);renderDictionary(data);}).catch(error=>{$('dictionary-count').textContent=`Không tải được: ${error.message}`;});
}
function renderDictionary(data){
  const labels=new Map();for(const item of data.value_labels){const key=item.format_name.replace(/^\$/,'').toUpperCase();if(!labels.has(key))labels.set(key,[]);labels.get(key).push(item);}
  const coverage=new Map(data.wave_coverage.map(item=>[item.csv_column,item]));
  const itemReviewReady=Array.isArray(data.item_comparability);
  const itemReviewRows=itemReviewReady?data.item_comparability:[];
  const itemReview=new Map(itemReviewRows.map(item=>[item.field,item]));
  const predictorGates=Array.isArray(data.predictor_gates)?data.predictor_gates:[];
  const gatesByField=new Map(predictorGates.map(item=>[item.csv_column,item]));
  const search=$('field-search'),results=$('field-results'),detail=$('field-detail');let selected=null;
  function show(field){selected=field;results.querySelectorAll('button').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.field===field.csv_column)));detail.replaceChildren();
    const title=node('h3','',field.csv_column);detail.append(title,node('p','field-label',field.sas_label||field.codebook_name));
    const wave=coverage.get(field.csv_column),gate=gatesByField.get(field.csv_column);const rows=[['Codebook',`${field.codebook_part} · ${field.codebook_name}`],['Family / timing',`${field.field_family} · ${field.timing_class}`],['Publisher predictor gate',field.predictor_use],['CreditAtlas boundary',gate?.eligibility_bucket||'Feature-gate inventory unavailable'],['Current model approval',gate?.decision_status||'Not available'],['Intended scope',gate?.intended_scope||'Review required'],['Open review before use',gate?.required_review||'Load the latest D02 reference data'],['Wave mentions in codebook',field.survey_wave_ranges||'N/A — supplemental field'],['Observed response waves',wave?.observed_response_waves||'N/A'],['Entirely not asked (SAS -3)',wave?.entirely_not_asked_waves||'None observed'],['Partially not asked (SAS -3)',wave?.partially_not_asked_waves||'None observed'],['Not applicable (SAS -2)',wave?.not_applicable_waves||'None observed'],['Question / condition',[field.survey_question_refs,field.codebook_condition].filter(Boolean).join(' · ')||'No survey question'],['Source location',`${field.printed_page||'—'} (PDF page ${field.pdf_page||'—'})`],['SAS',`${field.sas_format||'No format'} · ${field.sas_length||'—'} · ${field.sas_label||''}`]];
    const dl=document.createElement('dl');for(const [term,value] of rows){dl.append(node('dt','',term),node('dd','',value));}detail.append(dl);
    const review=itemReview.get(field.csv_column);if(review){const box=node('aside','item-review');box.append(node('strong','','Cross-wave comparability'),node('p','',review.assessment));detail.append(box);}else if(!itemReviewReady){const box=node('aside','item-review unavailable');box.append(node('strong','','Cross-wave review unavailable'),node('p','','Dictionary API from the running server does not include the latest item-comparability notes. Restart/reload the local app to apply the current D02 review; the codebook field details remain available.'));detail.append(box);}
    const key=(field.sas_format||'').replace(/^\$/,'').toUpperCase(),items=labels.get(key)||[];if(items.length){detail.append(node('h4','','Giá trị theo SAS format'));const list=document.createElement('ul');list.className='value-labels';for(const item of items)list.append(node('li','',`${item.format_value} → ${item.format_label}`));detail.append(list);}
  }
  function update(){const q=search.value.trim().toLowerCase();const matches=data.fields.filter(f=>[f.csv_column,f.codebook_name,f.sas_label,f.field_family,f.survey_question_refs,f.predictor_use,coverage.get(f.csv_column)?.observed_response_waves,itemReview.get(f.csv_column)?.assessment,gatesByField.get(f.csv_column)?.eligibility_bucket,gatesByField.get(f.csv_column)?.required_review].some(x=>(x||'').toLowerCase().includes(q))).slice(0,100);results.replaceChildren();for(const field of matches){const b=node('button','field-option');b.type='button';b.dataset.field=field.csv_column;b.setAttribute('role','option');b.setAttribute('aria-selected',String(selected?.csv_column===field.csv_column));b.append(node('strong','',field.csv_column),node('small','',field.sas_label||field.codebook_name));b.addEventListener('click',()=>show(field));results.append(b);} const reviewStatus=itemReviewReady?`${data.item_comparability_count} ghi chú so sánh item`:'ghi chú version chưa được server nạp';$('dictionary-count').textContent=`${data.field_count} trường · ${data.wave_coverage_count} biến survey có coverage · ${data.predictor_gate_count||0} feature gates · ${data.approved_feature_count||0} feature đã duyệt · ${reviewStatus} · ${matches.length}${q?' kết quả':' trường đầu'}`;if(!selected&&matches.length)show(matches[0]);}
  search.addEventListener('input',update);update();
}
async function load(){loadDictionary();try{const r=await fetch('/api/nsmo-profile',{cache:'no-store',headers:{Accept:'application/json'}});const body=await r.json();if(!r.ok)throw new Error(body.error||`HTTP ${r.status}`);render(body);}catch(error){$('state').className='state error';$('state').textContent=`D02 NSMO chưa sẵn sàng: ${error.message}. Hoàn tất tải PUF, chạy audit aggregate-only và kiểm tra local receipt; trang không dựng dữ liệu giả.`;}}
load();
