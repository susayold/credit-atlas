import fs from 'node:fs/promises';
import path from 'node:path';
import {FileBlob,SpreadsheetFile,Workbook} from '@oai/artifact-tool';
const [rootArg,outArg]=process.argv.slice(2);
if(!rootArg||!outArg) throw new Error('usage: build_hmda_dynamic_review.mjs <data-root> <output.xlsx>');
const root=path.resolve(rootArg), output=path.resolve(outArg);
async function latestAggregate(sourceId){
 const artifacts=path.join(root,'artifacts/private'),dirs=await fs.readdir(artifacts,{withFileTypes:true}),matches=[];
 for(const entry of dirs){if(!entry.isDirectory()||!entry.name.startsWith('hmda-national-view-'))continue;
  const folder=path.join(artifacts,entry.name);try{const receipt=JSON.parse(await fs.readFile(path.join(folder,'view-complete.json'),'utf8'));if(receipt.source_id===sourceId&&receipt.status==='VERIFIED_HMDA_NATIONAL_AGGREGATE_VIEW')matches.push({date:receipt.completed_at,file:path.join(folder,'aggregates.json')});}catch{}
 }
 if(!matches.length)throw new Error(`No verified aggregate view found for ${sourceId}`);
 matches.sort((a,b)=>b.date.localeCompare(a.date));return JSON.parse(await fs.readFile(matches[0].file,'utf8'));
}
const dynamic=await latestAggregate('hmda-national-dynamic-2025-20261011');
const snapshot=await latestAggregate('hmda-national-snapshot-2025-9a5e89600e3c');
const receipt=JSON.parse(await fs.readFile(path.join(root,'data/private/hmda/hmda-national-dynamic-2025-20261011/acquisition-complete.json'),'utf8'));
const snapshotReceipt=JSON.parse(await fs.readFile(path.join(root,'data/private/hmda/hmda-national-snapshot-2025-9a5e89600e3c/acquisition-complete.json'),'utf8'));
const sourceBookPath=path.join(root,'data/private/hmda/hmda-national-snapshot-2025-9a5e89600e3c/CreditAtlas-HMDA-National-2025-Audit.xlsx');
const sourceBook=await SpreadsheetFile.importXlsx(await FileBlob.load(sourceBookPath));
const dictionary=sourceBook.worksheets.getItem('Field dictionary').getUsedRange().values;
const wb=Workbook.create();
const overview=wb.worksheets.add('Overview');
const actions=wb.worksheets.add('Action compare');
const breakdown=wb.worksheets.add('Dynamic detail');
const codebook=wb.worksheets.add('Field dictionary');
const sources=wb.worksheets.add('Sources & method');
const navy='#17365D',blue='#D9EAF7',light='#F3F6FA',teal='#DDEBF7',grey='#5B6573';
function base(sheet,cols){sheet.showGridLines=false;sheet.getRange(`A1:${cols}20`).format.font={name:'Arial',size:10,color:'#1F2937'};sheet.getRange(`A1:${cols}20`).format.verticalAlignment='center';}
function header(sheet,range){sheet.getRange(range).format={fill:navy,font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,horizontalAlignment:'center',verticalAlignment:'center',rowHeight:30};}
function title(sheet,range,text){sheet.getRange(range).merge();sheet.getRange(range.split(':')[0]).values=[[text]];sheet.getRange(range).format={fill:navy,font:{name:'Arial',size:15,bold:true,color:'#FFFFFF'},rowHeight:34,verticalAlignment:'center'};}
const snap= snapshot.summary, dyn=dynamic.summary;
base(overview,'F'); overview.getRange('A1:F20').format.columnWidth=24;overview.getRange('A1:A20').format.columnWidth=38;overview.getRange('B1:B20').format.columnWidth=27;overview.getRange('C1:C20').format.columnWidth=28;overview.getRange('D1:D20').format.columnWidth=22;
title(overview,'A1:F1','CreditAtlas · HMDA 2025 release comparison');
overview.getRange('A2:F2').merge();overview.getRange('A2').values=[['Application and underwriting records only. HMDA does not contain repayment/default outcomes; denied share is not PD.']];overview.getRange('A2:F2').format={fill:light,font:{italic:true,color:grey},wrapText:true,rowHeight:32};
overview.getRange('A4:D4').write([['Measure','Snapshot · 2026-06-02','Dynamic · 2026-10-11','Change']]);header(overview,'A4:D4');
const metrics=[
 ['LAR records',snap.records,dyn.records],['Reporting institutions',snap.reporters,dyn.reporters],
 ['Decided applications · actions 1–3',snap.decision_denominator,dyn.decision_denominator],
 ['Denied applications · action 3',snap.denied_numerator,dyn.denied_numerator],
 ['Denied share · difference shown in percentage points',Number(snap.descriptive_denial_rate),Number(dyn.descriptive_denial_rate)],
 ['All public loan-amount interval midpoints · USD',Number(snap.public_amount_sum_usd),Number(dyn.public_amount_sum_usd)],
];
overview.getRange('A5:C10').write(metrics);overview.getRange('D5:D10').formulas=metrics.map((_,i)=>[`=C${i+5}-B${i+5}`]);
overview.getRange('A5:D10').format.rowHeight=24;overview.getRange('B5:D8').format.numberFormat='#,##0';overview.getRange('B9:D9').format.numberFormat='0.0000%';overview.getRange('B10:D10').format.numberFormat='$#,##0;($#,##0);-';
overview.getRange('A12:F12').merge();overview.getRange('A12').values=[['Interpretation: the Dynamic file is an archived point-in-time copy of a weekly mutable source. Differences include submissions/resubmissions and release design; they are not repayment outcomes or borrower-level transitions.']];overview.getRange('A12:F12').format={fill:teal,wrapText:true,rowHeight:56,font:{color:'#1F2937'}};
overview.getRange('A14:B17').write([['Acquisition as of (UTC)','2026-10-11 12:00:30'],['Rows independently reconciled to TS',dyn.records],['Dynamic schema fields',receipt.datasets.lar.profile.columns.length],['Row-quality exception count',0]]);
overview.getRange('A14:A17').format.font={bold:true};overview.getRange('A14:B17').format.rowHeight=23;
overview.freezePanes.freezeRows(4);
base(actions,'F');actions.getRange('A1:F20').format.columnWidth=24;actions.getRange('B1:B20').format.columnWidth=38;title(actions,'A1:F1','HMDA action counts · frozen versus latest captured release');
actions.getRange('A2:F2').merge();actions.getRange('A2').values=[['Same activity year; different publisher release states. Action 3 is denial, not default.']];actions.getRange('A2:F2').format={fill:light,font:{italic:true,color:grey},wrapText:true,rowHeight:30};
actions.getRange('A4:F4').write([['Action','Meaning','Snapshot 2026-06-02','Dynamic 2026-10-11','Difference','Change %']]);header(actions,'A4:F4');
const actionLabels={'1':'Loan originated','2':'Approved, not accepted','3':'Application denied','4':'Withdrawn','5':'Closed for incompleteness','6':'Purchased loan','7':'Preapproval denied','8':'Preapproval approved, not accepted'};
const sm=new Map(snapshot.actions.map(x=>[x.code,x.records])),dm=new Map(dynamic.actions.map(x=>[x.code,x.records]));
const actionRows=Object.keys(actionLabels).map(code=>[code,actionLabels[code],sm.get(code)||0,dm.get(code)||0,null,null]);
actions.getRange('A5:F12').write(actionRows);actions.getRange('E5:F12').formulas=actionRows.map((_,i)=>[`=D${i+5}-C${i+5}`,`=IFERROR(E${i+5}/C${i+5},0)`]);
actions.getRange('A13:B13').write([['TOTAL','All published actions']]);actions.getRange('C13:F13').formulas=[['=SUM(C5:C12)','=SUM(D5:D12)','=D13-C13','=IFERROR(E13/C13,0)']];
actions.getRange('A5:F13').format.rowHeight=23;actions.getRange('C5:E13').format.numberFormat='#,##0;(#,##0);-';actions.getRange('F5:F13').format.numberFormat='0.000%;(0.000%);-';actions.tables.add('A4:F13',true,'HmdaActionCompare');actions.freezePanes.freezeRows(4);
base(breakdown,'G');breakdown.getRange('A1:G20').format.columnWidth=24;title(breakdown,'A1:G1','Dynamic release · complete aggregate breakdowns');
breakdown.getRange('A2:G2').merge();breakdown.getRange('A2').values=[['All buckets from the verified aggregate view. Denied share uses actions 1+2+3; denial-reason rows are action 3 only. Public amount sums use interval midpoint fields.']];breakdown.getRange('A2:G2').format={fill:light,font:{italic:true,color:grey},wrapText:true,rowHeight:38};
breakdown.getRange('A4:G4').write([['Dimension','Category','Records','Decision denominator','Denied numerator','Descriptive denied share','Public amount midpoint sum · USD']]);header(breakdown,'A4:G4');
const flat=[];for(const [dim,rows] of Object.entries(dynamic.breakdowns)){for(const row of rows)flat.push([dim,row.bucket,row.records,row.decision_denominator,row.denied_numerator,row.descriptive_denial_rate==null?null:Number(row.descriptive_denial_rate),row.public_amount_sum_usd==null?null:Number(row.public_amount_sum_usd)]);}
breakdown.getRange(`A5:G${4+flat.length}`).write(flat);breakdown.tables.add(`A4:G${4+flat.length}`,true,'HmdaDynamicBreakdowns');breakdown.getRange(`C5:E${4+flat.length}`).format.numberFormat='#,##0;(#,##0);-';breakdown.getRange(`F5:F${4+flat.length}`).format.numberFormat='0.0000%';breakdown.getRange(`G5:G${4+flat.length}`).format.numberFormat='$#,##0;($#,##0);-';breakdown.freezePanes.freezeRows(4);
base(codebook,'I');codebook.getRange('A1:I120').format.columnWidth=22;codebook.getRange('D1:D120').format.columnWidth=44;codebook.getRange('G1:G120').format.columnWidth=44;codebook.getRange('I1:I120').format.columnWidth=28;title(codebook,'A1:I1','HMDA 2025 · official 99-field codebook');
codebook.getRange('A2:I2').merge();codebook.getRange('A2').values=[['Official 2025 public LAR definitions and categories, copied from the reviewed Snapshot codebook; Dynamic uses the same 99-field schema.']];codebook.getRange('A2:I2').format={fill:light,font:{italic:true,color:grey},wrapText:true,rowHeight:32};
const dictionaryRows=[dictionary[3],...dictionary.slice(4)];dictionaryRows[0][1]='Public LAR field';codebook.getRange(`A4:I${3+dictionaryRows.length}`).write(dictionaryRows);header(codebook,'A4:I4');codebook.tables.add(`A4:I${3+dictionaryRows.length}`,true,'HmdaFieldDictionary');codebook.getRange(`A5:I${3+dictionaryRows.length}`).format.wrapText=true;codebook.getRange(`A5:I${3+dictionaryRows.length}`).format.rowHeight=72;codebook.freezePanes.freezeRows(4);
base(sources,'D');sources.getRange('A1:D30').format.columnWidth=34;sources.getRange('A1:A30').format.columnWidth=28;sources.getRange('B1:B30').format.columnWidth=46;sources.getRange('C1:C30').format.columnWidth=46;sources.getRange('D1:D30').format.columnWidth=58;title(sources,'A1:D1','Sources, release controls and method');
const sourceRows=[
 ['Item','Snapshot / reference','Dynamic capture','Notes'],
 ['Official data page','https://ffiec.cfpb.gov/data-publication/snapshot-national-loan-level-dataset/2025','https://ffiec.cfpb.gov/data-publication/dynamic-national-loan-level-dataset/2025','FFIEC / CFPB; public privacy-modified records.'],
 ['Release status','Frozen 2026-06-02','Captured 2026-10-11 12:00:30 UTC','Dynamic dataset updates weekly; this archived capture is not a final annual vintage.'],
 ['LAR archive SHA-256',snapshotReceipt.datasets.lar.archive.sha256,receipt.datasets.lar.archive_sha256,'Raw archives remain private on D:.'],
 ['Dynamic CSV SHA-256','',receipt.datasets.lar.csv.sha256,'5,120,169,808 uncompressed bytes; pipe-delimited; ZIP CRC verified.'],
 ['Transmittal Sheet','Official dynamic TS ZIP','https://files.ffiec.cfpb.gov/dynamic-data/2025/2025_ts.zip','4,794 unique LEIs; reported LAR total reconciles exactly. Institution row values/tax IDs are excluded.'],
 ['Schema','99 source fields','99 source fields','Header compared; all source values read as text during audit.'],
 ['Decision-rate definition','Action 3 / actions 1+2+3','Action 3 / actions 1+2+3','Descriptive denied share only; not PD, default, delinquency, or repayment performance.'],
 ['Comparison boundary','2025 frozen Snapshot','2025 Dynamic captured 11 Oct 2026','Differences may reflect submission/resubmission and release design; no loan-level matching claimed.'],
 ['Data handling','Private source and aggregate artifacts','Private source and aggregate artifacts','No forecast or imputation; no raw LAR or institution tax identifiers in this workbook.'],
 ['Official field dictionary','https://ffiec.cfpb.gov/documentation/publications/loan-level-datasets/lar-data-fields/','Same 2025 public LAR schema','See Field dictionary tab; source field names/categories retained.'],
];
sources.getRange(`A3:D${2+sourceRows.length}`).write(sourceRows);header(sources,'A3:D3');sources.tables.add(`A3:D${2+sourceRows.length}`,true,'HmdaSources');sources.getRange(`A4:D${2+sourceRows.length}`).format.wrapText=true;sources.getRange(`A4:D${2+sourceRows.length}`).format.rowHeight=42;sources.freezePanes.freezeRows(3);
wb.recalculate();
const actionTotals=actions.getRange('C13:F13').values[0];
if(Number(actionTotals[0])!==snap.records||Number(actionTotals[1])!==dyn.records||Number(actionTotals[2])!==dyn.records-snap.records)
  throw new Error('Action total/delta formulas do not reconcile to verified source counts');
const deniedRow=actions.getRange('C7:F7').values[0];
if(Number(deniedRow[2])!==dm.get('3')-sm.get('3')) throw new Error('Action 3 change formula failed');
const errorScan=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:100},maxChars:3000});
if(!errorScan.ndjson.includes('matched 0 entries')) throw new Error('Formula error scan failed: '+errorScan.ndjson);
const formulaCheck=await wb.inspect({kind:'region',sheetId:'Overview',range:'A4:D10',maxChars:3000});
await fs.mkdir(path.dirname(output),{recursive:true});
const qa={sheets:(await wb.inspect({kind:'sheet',include:'id,name',maxChars:3000})).ndjson,formulaErrors:errorScan.ndjson,formulaCheck:formulaCheck.ndjson,breakdownRows:flat.length,actionTotals:{snapshot:snap.records,dynamic:dyn.records},dictionaryRows:dictionary.length-3};
await fs.writeFile(output+'.qa.json',JSON.stringify(qa,null,2));
for(const s of wb.worksheets.items){const range=s.name==='Dynamic detail'?'A1:G25':s.name==='Field dictionary'?'A1:I20':s.name==='Sources & method'?'A1:D15':s.name==='Action compare'?'A1:F16':'A1:F18';const preview=await wb.render({sheetName:s.name,range,scale:1,format:'png'});await fs.writeFile(output+'.'+s.name.replaceAll(' ','_')+'.png',new Uint8Array(await preview.arrayBuffer()));}
const xlsx=await SpreadsheetFile.exportXlsx(wb);await xlsx.save(output);
console.log(JSON.stringify({status:'exported',output,breakdownRows:flat.length,formulaErrors:errorScan.ndjson,dictionaryRows:dictionary.length-3}));
