import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const [input,output,preview]=process.argv.slice(2);
const doc=JSON.parse(await fs.readFile(input,'utf8')),t=doc.trend,c=doc.coverage;
const wb=Workbook.create(),analysis=wb.worksheets.add('Analysis'),facts=wb.worksheets.add('Facts');
const col=n=>String.fromCharCode(65+n);
function write(s,row,rows){if(!rows.length)return;const width=Math.max(...rows.map(r=>r.length));for(let i=0;i<rows.length;i++)for(let j=0;j<rows[i].length;j++)if(typeof rows[i][j]==='string')s.getRange(`${col(j)}${row+i}`).setNumberFormat('@');s.getRange(`A${row}:${col(width-1)}${row+rows.length-1}`).values=rows.map(r=>Array.from({length:width},(_,i)=>typeof r[i]==='string'&&r[i].startsWith('=')?"'"+r[i]:r[i]??null));}
function base(s,title,end,width){s.showGridLines=false;s.getRange(`A1:${col(width-1)}${end}`).format={font:{name:'Arial',size:10,color:'#24384C'},verticalAlignment:'center',rowHeight:26,columnWidth:22};write(s,2,[[title]]);s.getRange('A2').format.font={name:'Arial',size:16,bold:true,color:'#233E59'};s.getRange(`A3:${col(width-1)}3`).format.borders={bottom:{style:'thin',color:'#B6C5D4'}};}
function header(s,row,labels){write(s,row,[labels]);s.getRange(`A${row}:${col(labels.length-1)}${row}`).format={fill:'#233E59',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,horizontalAlignment:'center',rowHeight:42};}
const factRows=[],registry=new Map();
function source(accession,period,field,value,filingDate,form,url){
 const key=JSON.stringify([accession,field,value]);if(registry.has(key))return registry.get(key);
 const numeric=value.status==='supported'&&Number.isFinite(Number(value.value_exact))?Number(value.value_exact):'Unavailable';
 const row=6+factRows.length;registry.set(key,row);
 factRows.push([field,accession,new Date(period),numeric,value.value_exact??'Unavailable',value.status,value.start_date?new Date(value.start_date):'Instant / unavailable',new Date(value.end_date),value.unit,[...new Set(value.evidence.map(e=>e.taxonomy+':'+e.concept))].join(', ')||'Unavailable',new Date(filingDate),form,url,JSON.stringify(value.evidence),numeric==='Unavailable'?'No numeric input':'Excel floating point; exact text retained']);
 return row;
}
function statementRef(s,field){if(!s)return null;return source(s.accession,s.report_date,field,s.fields[field],s.filing_date,s.form,s.filing_url);}
const rows=[],expected=[];
for(const [key,definition] of Object.entries(t.ratio_definitions))for(const p of t.periods){
 const s=p.statement,prior=p.baseline_statement,r=s?.ratios[key],pr=prior?.ratios[key],comparison=p.comparisons[key],bridge=comparison?.driver_bridge;
 rows.push({period:p.report_date,name:definition.label,unit:definition.unit,baseline:comparison?.baseline_report_date,
 refs:[r?statementRef(s,r.numerator):null,r?statementRef(s,r.denominator):null,pr?statementRef(prior,pr.numerator):null,pr?statementRef(prior,pr.denominator):null],
 status:comparison?.status??p.selection_status,actualStatus:r?.status??p.selection_status,priorStatus:pr?.status??'NO_PRIOR_PERIOD',exact:r?.value_exact,delta:comparison?.absolute_delta_exact,accession:s?.accession,bridge});
 expected.push({actual:r?.value_exact,delta:comparison?.absolute_delta_exact,bridge});
}
for(const [key,label,numerator] of [['operating_income_coverage','Operating income / selected expense','operating_income'],['reported_ocf_coverage','Reported OCF / selected expense','operating_cashflow']])for(const p of c.periods){
 const r=p.ratios[key],url=p.accession?`https://www.sec.gov/Archives/edgar/data/${Number(c.filters.cik)}/${p.accession}-index.html`:'';
 const refs=p.fields[numerator]?[source(p.accession,p.report_date,numerator,p.fields[numerator],p.filing_date,'10-K',url),source(p.accession,p.report_date,'selected_interest_expense',p.fields.interest_expense,p.filing_date,'10-K',url),null,null]:[null,null,null,null];
 // Cash interest remains a source observation, never a substitute expense denominator.
 for(const field of ['interest_paid','interest_paid_net'])if(p.fields[field])source(p.accession,p.report_date,field,p.fields[field],p.filing_date,'10-K',url);
 rows.push({period:p.report_date,name:label,unit:'times',refs,status:'NO_COMPARISON',actualStatus:r.status,priorStatus:'NO_PRIOR_PERIOD',exact:r.value_exact,accession:p.accession});expected.push({actual:r.value_exact});
}
base(analysis,t.entity.ticker+' annual financial analysis',rows.length+18,21);analysis.tabColor='#233E59';
write(analysis,4,[['CIK',t.filters.cik,'Cutoff',new Date(t.filters.asof),'Report periods',Number(t.filters.years)],['Expense concept',c.filters.interest_concept],['Reading','Share deltas/effects are percentage points when expressed as percentages. Coverage uses operating income/reported OCF; EBIT ICR, DSCR and covenants remain unqualified.'],['Attribution','Numerator first, then denominator. Order-dependent arithmetic; no causal interpretation. Source edits require rechecking scope gates.']]);
analysis.getRange('D4').setNumberFormat('yyyy-mm-dd');analysis.getRange('B6:B7').format.columnWidth=80;analysis.getRange('B6:B7').format.wrapText=true;analysis.getRange('A6:U7').format.rowHeight=70;
header(analysis,18,['Report end','Metric','Unit','Baseline end','Current numerator USD','Current denominator USD','Prior numerator USD','Prior denominator USD','Actual (Excel)','Baseline (Excel)','Delta (Excel)','Numerator effect','Denominator effect','Bridge residual','Comparison gate','Actual exact text','Delta exact text','Accession','Actual support','Prior support','Counterfactual N1/D0']);
const matrix=rows.map(r=>[new Date(r.period),r.name,r.unit,r.baseline?new Date(r.baseline):'Unavailable',null,null,null,null,null,null,null,null,null,null,r.status,r.exact??'Unavailable',r.delta??'Unavailable',r.accession??'Unavailable',r.actualStatus,r.priorStatus,null]);write(analysis,19,matrix);
for(let i=0;i<rows.length;i++){
 const row=i+19,r=rows[i];r.refs.forEach((ref,j)=>{if(ref)analysis.getRange(`${col(4+j)}${row}`).formulas=[[`=IF(ISNUMBER('Facts'!D${ref}),'Facts'!D${ref},"Unavailable")`]];else write(analysis,row,[]);if(!ref)analysis.getRange(`${col(4+j)}${row}`).values=[['Unavailable']];});
 const supported=(status,n,d)=>`AND(${status}${row}="supported",ISNUMBER(${n}${row}),ISNUMBER(${d}${row}))`;
 analysis.getRange(`I${row}:N${row}`).formulas=[[
 `=IF(${supported('S','E','F')},IF(F${row}>0,E${row}/F${row},"Unavailable"),"Unavailable")`,
 `=IF(${supported('T','G','H')},IF(H${row}>0,G${row}/H${row},"Unavailable"),"Unavailable")`,
 `=IF(AND(O${row}="COMPARABLE",ISNUMBER(I${row}),ISNUMBER(J${row})),I${row}-J${row},"Unavailable")`,
 `=IF(ISNUMBER(U${row}),U${row}-J${row},"Unavailable")`,
 `=IF(ISNUMBER(U${row}),I${row}-U${row},"Unavailable")`,
 `=IF(AND(ISNUMBER(L${row}),ISNUMBER(M${row})),K${row}-SUM(L${row}:M${row}),"Unavailable")`]];
 analysis.getRange(`U${row}`).formulas=[[`=IF(AND(ISNUMBER(K${row}),ISNUMBER(E${row}),ISNUMBER(H${row})),IF(H${row}>0,E${row}/H${row},"Unavailable"),"Unavailable")`]];
 const fmt=r.unit==='share'?'0.0000%;(0.0000%);0.0000%':'0.000000;(0.000000);0.000000';analysis.getRange(`I${row}:M${row}`).setNumberFormat(fmt);analysis.getRange(`U${row}`).setNumberFormat(fmt);analysis.getRange(`N${row}`).setNumberFormat('0.00E+00');
}
analysis.getRange(`A19:A${rows.length+18}`).setNumberFormat('yyyy-mm-dd');analysis.getRange(`D19:D${rows.length+18}`).setNumberFormat('yyyy-mm-dd');analysis.getRange(`E19:H${rows.length+18}`).setNumberFormat('#,##0;(#,##0);0');analysis.getRange(`E19:H${rows.length+18}`).format.font.color='#287D44';
for(const [column,width] of [['A',15],['B',42],['C',12],['D',15],['E',26],['F',26],['G',26],['H',26],['O',36],['P',65],['Q',65],['R',28],['S',35],['T',35],['U',25]])analysis.getRange(`${column}18:${column}${rows.length+18}`).format.columnWidth=width;
write(analysis,8,[['Latest report end',new Date(t.periods[t.periods.length-1].report_date)]]);analysis.getRange('B8').setNumberFormat('yyyy-mm-dd');
header(analysis,9,['Latest annual metric','Actual','Baseline','Absolute delta']);
const latestRows=[...new Map(rows.map((r,i)=>[r.name,i])).entries()];
for(let i=0;i<latestRows.length;i++){const [name,index]=latestRows[i],sourceRow=index+19,target=i+10,unit=rows[index].unit;write(analysis,target,[[name,null,null,null]]);analysis.getRange(`B${target}:D${target}`).formulas=[[`=I${sourceRow}`,`=J${sourceRow}`,unit==='share'?`=IF(ISNUMBER(K${sourceRow}),K${sourceRow}*100,\"Unavailable\")`:`=K${sourceRow}`]];analysis.getRange(`B${target}:C${target}`).setNumberFormat(unit==='share'?'0.0000%':'0.000000');analysis.getRange(`D${target}`).setNumberFormat(unit==='share'?'0.0000\" pp\"':'0.000000');}
analysis.getRange('A9:A15').format.columnWidth=42;analysis.getRange('B10:D15').format.horizontalAlignment='right';write(analysis,17,[['Detailed calculations and source links']]);
analysis.freezePanes.freezeRows(18);analysis.freezePanes.freezeColumns(2);
base(facts,'Reported SEC facts (USD)',factRows.length+10,15);facts.tabColor='#E8DDC7';
write(facts,4,[['Source',`https://data.sec.gov/api/xbrl/companyfacts/CIK${t.filters.cik}.json`]]);
header(facts,5,['Field','Accession','Report end','Numeric USD input','Exact USD text','Support','Start','End','Unit','Concepts','Filed','Form','Filing URL','Candidates JSON','Numeric convention']);write(facts,6,factRows);
facts.getRange(`D6:D${factRows.length+5}`).setNumberFormat('#,##0;(#,##0);0');for(const column of ['C','G','H','K'])facts.getRange(`${column}6:${column}${factRows.length+5}`).setNumberFormat('yyyy-mm-dd');
for(const [column,width] of [['A',30],['B',28],['D',26],['E',30],['F',25],['J',65],['M',90],['N',100],['O',54]])facts.getRange(`${column}5:${column}${factRows.length+5}`).format.columnWidth=width;
facts.freezePanes.freezeRows(5);facts.freezePanes.freezeColumns(2);
const evidenceRow=factRows.length+8,evidence=[['Source ID',t.source_id],['Case ID',t.case_id],...Object.entries(c.source_capture),['Trend method SHA256',t.method_source_sha256],['Coverage method SHA256',c.method_source_sha256],['Scope rules',t.selection_rule],['Comparison rules',t.comparison_rule],['Expense rule',c.concept_rule]];write(facts,evidenceRow,evidence);facts.getRange(`A${evidenceRow}:B${evidenceRow+evidence.length-1}`).format.wrapText=true;for(let i=0;i<evidence.length;i++)facts.getRange(`A${evidenceRow+i}:B${evidenceRow+i}`).format.rowHeight=Math.max(42,Math.ceil(String(evidence[i][1]).length/28)*14+10);
wb.recalculate();
const close=(value,exact)=>typeof value==='number'&&Math.abs(value-Number(exact))<=1e-10*Math.max(1,Math.abs(Number(exact)));
for(let i=0;i<expected.length;i++){const e=expected[i],values=analysis.getRange(`I${i+19}:N${i+19}`).values[0];if(e.actual!=null){if(!close(values[0],e.actual))throw new Error('Actual formula mismatch '+i);}else if(values[0]!=='Unavailable')throw new Error('Missing actual became zero '+i);if(e.delta!=null&&!close(values[2],e.delta))throw new Error('Delta formula mismatch '+i);if(e.bridge?.status==='SUPPORTED'){if(!close(values[3],e.bridge.numerator_effect_exact)||!close(values[4],e.bridge.denominator_effect_exact)||Math.abs(values[5])>1e-10)throw new Error('Driver formula mismatch '+i);}else if(values[3]!=='Unavailable')throw new Error('Unavailable bridge became numeric '+i);}
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:20},maxChars:2000});
if(preview){await fs.mkdir(preview,{recursive:true});for(const [s,range] of [['Analysis','A2:D15'],['Calculations','I18:N25'],['Facts','A2:F13']]){const image=await wb.render({sheetName:s==='Calculations'?'Analysis':s,range,scale:1});await fs.writeFile(path.join(preview,s+'.png'),new Uint8Array(await image.arrayBuffer()));}await fs.writeFile(path.join(preview,'inspect.json'),JSON.stringify(errors));}
await fs.mkdir(path.dirname(output),{recursive:true});await(await SpreadsheetFile.exportXlsx(wb)).save(output);
console.log(JSON.stringify({status:'EXPORTED',rows:rows.length,facts:factRows.length,output}));
