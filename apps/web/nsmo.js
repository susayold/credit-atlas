const $=(id)=>document.getElementById(id);
const n=(x)=>new Intl.NumberFormat('en-US').format(x??0);
const dec=(x)=>new Intl.NumberFormat('en-US',{maximumFractionDigits:2}).format(x??0);
const pct=(x)=>new Intl.NumberFormat('en-US',{style:'percent',maximumFractionDigits:2}).format(x??0);
function node(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=String(text);return e;}
function table(headers,rows,numeric=[]){const t=document.createElement('table'),head=document.createElement('thead'),hr=document.createElement('tr');headers.forEach(h=>hr.append(node('th','',h)));head.append(hr);t.append(head);const b=document.createElement('tbody');rows.forEach(row=>{const tr=document.createElement('tr');row.forEach((value,i)=>{const td=node('td',numeric.includes(i)?'num':'',value);tr.append(td);});b.append(tr);});t.append(b);return t;}
function metric(label,value,note){const e=node('article','metric');e.append(node('span','label',label),node('strong','',value),node('small','',note));return e;}
function drawChart(svg,series,label){
  svg.replaceChildren();const w=980,h=340,l=58,r=20,t=22,b=48,iw=w-l-r,ih=h-t-b;
  const values=series.map(x=>x.value),max=Math.max(1,...values),nice=Math.ceil(max/4),limit=nice*4;
  for(let i=0;i<=4;i++){const value=limit-i*nice,y=t+i*ih/4;const line=document.createElementNS('http://www.w3.org/2000/svg','line');line.setAttribute('x1',l);line.setAttribute('x2',w-r);line.setAttribute('y1',y);line.setAttribute('y2',y);line.setAttribute('class','grid-line');svg.append(line);const tx=document.createElementNS('http://www.w3.org/2000/svg','text');tx.setAttribute('x',l-10);tx.setAttribute('y',y+4);tx.setAttribute('text-anchor','end');tx.setAttribute('class','axis-label');tx.textContent=n(value);svg.append(tx);}
  const points=series.map((x,i)=>({x:l+(series.length===1?iw/2:i*iw/(series.length-1)),y:t+ih-(x.value/limit)*ih,...x}));
  const path=document.createElementNS('http://www.w3.org/2000/svg','polyline');path.setAttribute('points',points.map(p=>`${p.x},${p.y}`).join(' '));path.setAttribute('class','series-line');svg.append(path);
  points.forEach((p,i)=>{if(i%Math.ceil(points.length/18)===0||i===points.length-1){const c=document.createElementNS('http://www.w3.org/2000/svg','circle');c.setAttribute('cx',p.x);c.setAttribute('cy',p.y);c.setAttribute('r','4');c.setAttribute('class','series-point');const title=document.createElementNS('http://www.w3.org/2000/svg','title');title.textContent=`${p.quarter}: ${n(p.value)}`;c.append(title);svg.append(c);const tx=document.createElementNS('http://www.w3.org/2000/svg','text');tx.setAttribute('x',p.x);tx.setAttribute('y',h-17);tx.setAttribute('text-anchor','middle');tx.setAttribute('class','axis-label');tx.textContent=p.quarter.slice(0,4)+'Q'+(Math.floor((Number(p.quarter.slice(5,7))-1)/3)+1);svg.append(tx);}});
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
  $('vintages').replaceChildren(table(['Origination year',{label:'Mortgages',number:true},{label:'Share of full PUF',number:true}],yearRows,[1,2]));
  const ws=$('weight-summary'),weightValues=[['Valid rows',n(weights.valid_n)],['Missing',n(weights.missing)],['Nonpositive',n(weights.nonpositive)],['Minimum',dec(weights.min)],['Median',dec(weights.median)],['Maximum',dec(weights.max)],['Weight sum',dec(weights.sum)],['Survey waves',Object.keys(sample.survey_wave_counts).length]];
  ws.className='weight-summary';ws.replaceChildren(...weightValues.map(([label,value])=>{const e=node('div','mini-stat');e.append(node('span','',label),node('strong','',value));return e;}));
  $('limits').replaceChildren(...profile.limitations.map(x=>node('li','',x)));
  $('disclaimer').textContent=profile.required_fhfa_analysis_disclaimer;
  $('dashboard').hidden=false;$('state').hidden=true;
}
function loadDictionary(){
  fetch('/api/nsmo-dictionary',{cache:'no-store',headers:{Accept:'application/json'}}).then(async r=>{const data=await r.json();if(!r.ok)throw new Error(data.error||`HTTP ${r.status}`);renderDictionary(data);}).catch(error=>{$('dictionary-count').textContent=`Không tải được: ${error.message}`;});
}
function renderDictionary(data){
  const labels=new Map();for(const item of data.value_labels){const key=item.format_name.replace(/^\$/,'').toUpperCase();if(!labels.has(key))labels.set(key,[]);labels.get(key).push(item);}
  const search=$('field-search'),results=$('field-results'),detail=$('field-detail');let selected=null;
  function show(field){selected=field;results.querySelectorAll('button').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.field===field.csv_column)));detail.replaceChildren();
    const title=node('h3','',field.csv_column);detail.append(title,node('p','field-label',field.sas_label||field.codebook_name));
    const rows=[['Codebook',`${field.codebook_part} · ${field.codebook_name}`],['Family / timing',`${field.field_family} · ${field.timing_class}`],['Predictor gate',field.predictor_use],['Survey wave',field.survey_wave_ranges||'N/A — supplemental field'],['Question / condition',[field.survey_question_refs,field.codebook_condition].filter(Boolean).join(' · ')||'No survey question'],['Source location',`${field.printed_page||'—'} (PDF page ${field.pdf_page||'—'})`],['SAS',`${field.sas_format||'No format'} · ${field.sas_length||'—'} · ${field.sas_label||''}`]];
    const dl=document.createElement('dl');for(const [term,value] of rows){dl.append(node('dt','',term),node('dd','',value));}detail.append(dl);
    const key=(field.sas_format||'').replace(/^\$/,'').toUpperCase(),items=labels.get(key)||[];if(items.length){detail.append(node('h4','','Giá trị theo SAS format'));const list=document.createElement('ul');list.className='value-labels';for(const item of items)list.append(node('li','',`${item.format_value} → ${item.format_label}`));detail.append(list);}
  }
  function update(){const q=search.value.trim().toLowerCase();const matches=data.fields.filter(f=>[f.csv_column,f.codebook_name,f.sas_label,f.field_family,f.survey_question_refs,f.predictor_use].some(x=>(x||'').toLowerCase().includes(q))).slice(0,100);results.replaceChildren();for(const field of matches){const b=node('button','field-option');b.type='button';b.dataset.field=field.csv_column;b.setAttribute('role','option');b.setAttribute('aria-selected',String(selected?.csv_column===field.csv_column));b.append(node('strong','',field.csv_column),node('small','',field.sas_label||field.codebook_name));b.addEventListener('click',()=>show(field));results.append(b);} $('dictionary-count').textContent=`${data.field_count} trường · ${data.value_label_count} nhãn giá trị · ${matches.length}${q?' kết quả':' trường đầu'}`;if(!selected&&matches.length)show(matches[0]);}
  search.addEventListener('input',update);update();
}
async function load(){loadDictionary();try{const r=await fetch('/api/nsmo-profile',{cache:'no-store',headers:{Accept:'application/json'}});const body=await r.json();if(!r.ok)throw new Error(body.error||`HTTP ${r.status}`);render(body);}catch(error){$('state').className='state error';$('state').textContent=`D02 NSMO chưa sẵn sàng: ${error.message}. Hoàn tất tải PUF, chạy audit aggregate-only và kiểm tra local receipt; trang không dựng dữ liệu giả.`;}}
load();
