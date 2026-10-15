import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';

// Text stays literal, including source strings that resemble spreadsheet formulas.
const literal=v=>typeof v==='string'&&v.startsWith('=')?"'"+v:v;
const col=n=>{let s='';for(n++;n;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s;return s;};
const [input,output,previewDir]=process.argv.slice(2);
if(!input||!output)throw new Error('Input JSON and output XLSX required');
const report=JSON.parse(await fs.readFile(input,'utf8'));
const wb=Workbook.create();
const names=['Overview','KPI','Data','Reviews'];
const sheets=Object.fromEntries(names.map(n=>[n,wb.worksheets.add(n)]));
const formats={count:'#,##0',share:'0.0000%',USD:'#,##0.00',decimal:'0.000000',declared_cost_units:'#,##0.000000'};
function write(sheet,row,rows){if(!rows.length)return;const width=Math.max(...rows.map(x=>x.length));for(let i=0;i<rows.length;i++)for(let j=0;j<rows[i].length;j++)if(typeof rows[i][j]==='string')sheet.getRange(`${col(j)}${row+i}`).setNumberFormat('@');sheet.getRange(`A${row}:${col(width-1)}${row+rows.length-1}`).values=rows.map(x=>Array.from({length:width},(_,i)=>literal(x[i]??null)));}
function header(sheet,row,labels){write(sheet,row,[labels]);sheet.getRange(`A${row}:${col(labels.length-1)}${row}`).format={fill:'#233E59',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,horizontalAlignment:'center',verticalAlignment:'center',rowHeight:32};}
function base(sheet,title,end,width){sheet.showGridLines=false;sheet.getRange(`A1:${col(width-1)}${end}`).format={font:{name:'Arial',size:10,color:'#24384C'},verticalAlignment:'top',rowHeight:27};sheet.getRange('A2').values=[[title]];sheet.getRange('A2').format.font={name:'Arial',size:16,bold:true,color:'#233E59'};sheet.getRange(`A3:${col(width-1)}3`).format.borders={bottom:{style:'thin',color:'#B6C5D4'}};sheet.getRange(`A1:${col(width-1)}${end}`).format.columnWidth=24;}
const domains=Object.entries(report.kpi_analysis);
const overview=[];
overview.push(['Scope',report.filters.domain,'Basis',report.filters.basis]);
overview.push(['Report read at',new Date(report.read_at)]);
overview.push(['Calculation scope','Browser-derived historical KPI report. Source artifacts verified at export; Excel recalculates comparison deltas only.']);
overview.push(['Units','USD, count, share, decimal and declared cost units remain separate. No combined suite exposure or borrower total.']);
overview.push(['Missing values','Unavailable is distinct from zero. Baseline applies only to KPIs carrying a saved comparison.']);
for(const [d,r] of domains){overview.push([d,r.title]);overview.push(['Population / period',r.scope]);overview.push(['Business KPI count',r.metrics.length,'Quality controls',r.data_quality.metrics.length]);if(r.comparison_control)overview.push(['Baseline control',r.comparison_control.status,'Requested',r.comparison_control.requested,'Resolved',r.comparison_control.resolved_period??'Unavailable']);for(const f of r.findings)overview.push(['Finding',f]);overview.push(['Next investigation',r.next]);overview.push([]);}
base(sheets.Overview,'CreditAtlas KPI analysis',overview.length+5,6);write(sheets.Overview,5,overview);
sheets.Overview.getRange(`A5:A${overview.length+4}`).format.columnWidth=25;
sheets.Overview.getRange(`B5:B${overview.length+4}`).format.columnWidth=110;
sheets.Overview.getRange(`B5:B${overview.length+4}`).format.wrapText=true;
sheets.Overview.getRange(`A5:F${overview.length+4}`).format.rowHeight=42;
sheets.Overview.getRange('B6').setNumberFormat('yyyy-mm-dd hh:mm:ss');
sheets.Overview.tabColor='#233E59';
const metrics=[];
for(const [d,r] of domains)for(const [kind,list] of [['Business',r.metrics],['Quality',r.data_quality.metrics]])for(const m of list){const c=m.comparison;metrics.push([d,kind,m.name,m.unit,m.value??'Unavailable',c?.period??'Unavailable',c?.value??'Unavailable',null,null,c?.absolute_change??'Unavailable',null,m.formula,m.interpretation,kind==="Quality"?r.data_quality.scope:r.scope,r.review_snapshot.evidence_refs.map(x=>x.kind+': '+x.id).join('; ')]);}
base(sheets.KPI,'KPI actuals and comparison calculations',metrics.length+5,15);
header(sheets.KPI,5,['Domain','Type','KPI','Unit','Actual','Baseline period','Baseline actual','Delta (Excel)','Relative delta (Excel)','Delta (app)','Excel minus app','Formula / support (text)','Interpretation','Source scope','Evidence IDs']);write(sheets.KPI,6,metrics);
for(let i=0;i<metrics.length;i++){const row=i+6,u=metrics[i][3],fmt=formats[u]??'0.000000';for(const c of ['E','G','H','J','K'])sheets.KPI.getRange(`${c}${row}`).setNumberFormat(fmt);sheets.KPI.getRange(`I${row}`).setNumberFormat('0.0000%');sheets.KPI.getRange(`H${row}:I${row}`).formulas=[[`=IF(AND(ISNUMBER(E${row}),ISNUMBER(G${row})),E${row}-G${row},"Unavailable")`,`=IF(AND(ISNUMBER(H${row}),ISNUMBER(G${row})),IF(G${row}=0,"Unavailable",H${row}/G${row}),"Unavailable")`]];sheets.KPI.getRange(`K${row}`).formulas=[[`=IF(AND(ISNUMBER(H${row}),ISNUMBER(J${row})),H${row}-J${row},"Unavailable")`]];}
for(const [c,w] of [['A',10],['B',12],['C',48],['D',22],['E',25],['F',23],['G',25],['H',25],['I',25],['J',25],['K',25],['L',58],['M',70],['N',65],['O',65]])sheets.KPI.getRange(`${c}5:${c}${metrics.length+5}`).format.columnWidth=w;
sheets.KPI.getRange(`A6:O${metrics.length+5}`).format.wrapText=true;sheets.KPI.getRange(`A6:O${metrics.length+5}`).format.rowHeight=66;
sheets.KPI.freezePanes.freezeRows(5);sheets.KPI.freezePanes.freezeColumns(3);
sheets.KPI.getRange(`H6:I${metrics.length+5}`).format.font.color='#172B3F';
const data=[];let row=5;const sections=[];
for(const [d,r] of domains)for(const t of [...r.tables,...r.data_quality.tables]){sections.push({row,title:d+' '+t.title,columns:t.columns,rows:t.rows});row+=t.rows.length+4;}
base(sheets.Data,'Supporting source tables',row,10);
for(const s of sections){write(sheets.Data,s.row,[[s.title]]);sheets.Data.getRange(`A${s.row}`).format.font.bold=true;header(sheets.Data,s.row+1,s.columns);write(sheets.Data,s.row+2,s.rows);}
sheets.Data.getRange(`A5:O${row}`).format.columnWidth=29;sheets.Data.getRange(`A5:O${row}`).format.wrapText=true;sheets.Data.getRange(`A5:O${row}`).format.rowHeight=30;
for(const s of sections){sheets.Data.getRange(`A${s.row}:O${s.row}`).format.wrapText=false;for(let i=0;i<s.rows.length;i++){const height=Math.max(30,Math.ceil(Math.max(...s.rows[i].map(x=>String(x??'').length))/28)*14+10);sheets.Data.getRange(`A${s.row+i+2}:O${s.row+i+2}`).format.rowHeight=Math.min(409,height);}}
// Source tables preserve original display/exact strings; numeric KPI inputs are on KPI.
write(sheets.Data,4,[['Source table values retain app display/exact text. Do not treat formatted amounts or ratios here as numeric inputs.']]);
const reviews=[];
for(const record of report.reviews??[])for(const r of record.history??[record.review??record]){reviews.push([r.domain,r.id,r.revision,r.status,r.title,r.owner,r.judgement,r.hypothesis,r.next_action,r.capture?.captured_at??'',r.capture?.snapshot_sha256??'',JSON.stringify(r.capture?.snapshot?.filters??{}),r.capture?.snapshot?.scope??'']);}
base(sheets.Reviews,'Analyst review history',Math.max(7,reviews.length+5),13);header(sheets.Reviews,5,['Domain','Review ID','Revision','Status','Title','Owner','Judgement','Hypothesis','Next action','Captured at','Snapshot digest','Captured filters','Captured scope']);
write(sheets.Reviews,6,reviews.length?reviews:[['No persisted reviews in exported scope']]);
sheets.Reviews.getRange(`A5:M${Math.max(6,reviews.length+5)}`).format.columnWidth=32;sheets.Reviews.getRange(`E6:M${Math.max(6,reviews.length+5)}`).format.wrapText=true;sheets.Reviews.getRange(`A6:M${Math.max(6,reviews.length+5)}`).format.rowHeight=100;sheets.Reviews.freezePanes.freezeRows(5);
let captureRow=Math.max(9,reviews.length+8);
const uniqueCaptures=new Map();
for(const record of report.reviews??[]){const r=record.review??record;if(r.capture)uniqueCaptures.set(r.id,r.capture);}
if(uniqueCaptures.size){write(sheets.Reviews,captureRow++,[['Original immutable KPI captures. These values retain the review capture scope; they may differ from this export.']]);header(sheets.Reviews,captureRow++,['Review ID','Domain','Captured KPI','Unit','Captured actual','Baseline period','Baseline actual','Formula / support','Interpretation']);for(const [id,c] of uniqueCaptures){for(const m of [...c.snapshot.metrics,...c.snapshot.quality_metrics]){write(sheets.Reviews,captureRow,[[id,c.snapshot.domain,m.name,m.unit,m.value??'Unavailable',m.comparison?.period??'Unavailable',m.comparison?.value??'Unavailable',m.formula,m.interpretation]]);for(const k of ['E','G'])sheets.Reviews.getRange(`${k}${captureRow}`).setNumberFormat(formats[m.unit]??'0.000000');captureRow++;}}sheets.Reviews.getRange(`A${reviews.length+8}:M${captureRow}`).format.font={name:'Arial',size:10,color:'#24384C'};sheets.Reviews.getRange(`A${reviews.length+8}:M${captureRow}`).format.wrapText=true;sheets.Reviews.getRange(`A${reviews.length+8}:M${captureRow}`).format.rowHeight=95;}
// Evidence captures belong next to actual inputs, not to a decorative sources sheet.
let evidenceRow=row+2;
for(const capture of report.source_captures??[]){write(sheets.Data,evidenceRow++,[[capture.snapshot.domain+' source verification at '+capture.captured_at]]);for(const source of capture.source_capture)for(const [key,value] of Object.entries(source)){write(sheets.Data,evidenceRow++,[[key,typeof value==='object'?JSON.stringify(value):value]]);}}
if(evidenceRow>row+2){sheets.Data.getRange(`A${row+2}:J${evidenceRow}`).format.font={name:'Arial',size:10};sheets.Data.getRange(`A${row+2}:J${evidenceRow}`).format.rowHeight=50;sheets.Data.getRange(`B${row+2}:B${evidenceRow}`).format.columnWidth=70;sheets.Data.getRange(`B${row+2}:B${evidenceRow}`).format.wrapText=true;}
wb.recalculate();
const checked=[];
for(let i=0;i<metrics.length;i++){const m=metrics[i],row=i+6,vals=sheets.KPI.getRange(`H${row}:K${row}`).values[0];if(typeof m[4]==='number'&&typeof m[6]==='number'){const expected=m[4]-m[6];if(Math.abs(vals[0]-expected)>1e-9)throw new Error('Excel delta mismatch '+row);if(typeof m[9]==='number'&&Math.abs(vals[3])>1e-7)throw new Error('App delta mismatch '+row);checked.push(row);}else if(vals[0]!=='Unavailable')throw new Error('Missing delta became numeric '+row);}
// Recalculation boundary: real zero baseline and missing baseline stay distinct.
const first=checked[0];if(first){const original=sheets.KPI.getRange(`G${first}`).values;sheets.KPI.getRange(`G${first}`).values=[[0]];if(sheets.KPI.getRange(`I${first}`).values[0][0]!=='Unavailable')throw new Error('Zero denominator boundary failed');sheets.KPI.getRange(`G${first}`).values=[['Unavailable']];if(sheets.KPI.getRange(`H${first}`).values[0][0]!=='Unavailable')throw new Error('Missing baseline boundary failed');sheets.KPI.getRange(`G${first}`).values=original;}
wb.recalculate();
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:20}});
await fs.mkdir(path.dirname(output),{recursive:true});
if(previewDir){await fs.mkdir(previewDir,{recursive:true});for(const name of names){const range=name==='KPI'?'A2:K11':name==='Data'?'A2:G13':name==='Reviews'?'A2:I9':'A2:F16';const png=await wb.render({sheetName:name,range,scale:1});await fs.writeFile(path.join(previewDir,name+'.png'),new Uint8Array(await png.arrayBuffer()));}await fs.writeFile(path.join(previewDir,'inspect.json'),JSON.stringify({errors,checked_rows:checked,source_read_at:report.read_at}));}
await (await SpreadsheetFile.exportXlsx(wb)).save(output);
console.log(JSON.stringify({status:'EXPORTED',metrics:metrics.length,comparison_rows:checked.length,sheets:names,output}));
