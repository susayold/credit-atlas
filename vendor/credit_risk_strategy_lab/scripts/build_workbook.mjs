// Author with the bundled @oai/artifact-tool runtime. No private rows are exported.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {Workbook, SpreadsheetFile} from '@oai/artifact-tool';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const inputPath=path.resolve(process.argv.slice(2).find(arg=>!arg.startsWith('--')) || path.join(root,'artifacts/private/pipeline-ca9d8efec1e7-workbook-input.json'));
const renderSelection=process.argv.find(arg=>arg.startsWith('--render-sheets='))?.split('=')[1].split(',');
const outputOverride=process.argv.find(arg=>arg.startsWith('--output-directory='))?.split('=').slice(1).join('=');
const inputBytes=await fs.readFile(inputPath);
const data=JSON.parse(inputBytes);
if(data.visibility!=='private'||data.public_release_approved!==false) throw Error('Private payload required');
const digest=b=>createHash('sha256').update(b).digest('hex');
const outputDir=outputOverride?path.resolve(outputOverride):path.join(root,'outputs/01a08025-b938-7313-b1e6-a75f2e46bcdf',data.pipeline_run);
await fs.mkdir(outputDir,{recursive:true});
const workbook=Workbook.create();
const names=['00_ReadMe','01_DataCoverage','02_MetricDictionary','03_Portfolio','04_Vintage','05_Transitions','06_Cure','07_ModelComparison','08_Calibration','09_Strategy','10_Loss','11_ForecastStress','12_Assumptions','13_Checks','14_Sources'];
const sheets=Object.fromEntries(names.map(n=>[n,workbook.worksheets.add(n)]));
const previews=[];
const col=n=>String.fromCharCode(65+n);
const raw=(name,cell,value)=>sheets[name].getRange(cell).values=[[value]];
const formula=(name,cell,value)=>sheets[name].getRange(cell).formulas=[[value]];
function sheet(name,title,headers,rows,widths,note){
  const s=sheets[name], last=col(headers.length-1), end=6+rows.length;
  s.showGridLines=false;
  s.getRange(`A1:${last}${Math.max(end,12)}`).format.font={name:'Arial',size:11,color:'#172B46'};
  s.getRange(`A1:${last}${Math.max(end,12)}`).format.rowHeight=23;
  s.getRange(`A1:${last}${Math.max(end,12)}`).format.verticalAlignment='center';
  raw(name,'A2',title);s.getRange('A2').format.font={name:'Arial',size:16,bold:true};
  raw(name,'A3','PRIVATE RESEARCH - derived observed sample; not approved for publication');
  s.getRange('A3').format.font={name:'Arial',size:11,color:'#9B4313'};
  raw(name,'A4',note);
  s.getRange('A4').format.font={name:'Arial',size:11,italic:true,color:'#475569'};
  s.getRange(`A6:${last}${end}`).values=[headers,...rows];
  s.getRange(`A6:${last}6`).format={fill:'#17365C',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},wrapText:true,rowHeight:38,horizontalAlignment:'center'};
  widths.forEach((w,i)=>s.getRange(`${col(i)}6:${col(i)}${Math.max(end,12)}`).format.columnWidth=w);
  s.getRange(`A7:${last}${end}`).format.horizontalAlignment='left';
  if(rows.length>15)s.freezePanes.freezeRows(6);
  previews.push({name,title,headers,startRow:7,endRow:end,lastColumn:last,note});
  return s;
}
function numeric(name,range,format='#,##0'){
  const r=sheets[name].getRange(range);r.setNumberFormat(format);r.format.horizontalAlignment='right';
}
function gate(name,title,reason,required){
  sheet(name,title,['Item','State','Required evidence'],[
    ['Research output','Unavailable',reason],
    ['Next acceptance condition','Not met',required],
    ['Displayed model / financial results','None','No synthetic values substituted for observed research'],
  ],[36,20,92],'Not delivered. A gate explanation is not a completed analytical module.');
}

sheet('00_ReadMe','Credit Risk Strategy Lab - research workbook',['Topic','Scope'],[
 ['Dataset','Freddie Mac Standard annual sample, origination vintage 2012, Release 47'],
 ['Research population','Funded fixed-rate mortgages. Not a complete application / approval funnel.'],
 ['Evidence class','Derived observed sample. No modeled, scenario or synthetic financial results.'],
 ['Entry landmark','First observed performance month, not necessarily origination month.'],
 ['Version',data.pipeline_run],
 ['Data meaning','Latest-release retrospective analysis. Archival point-in-time availability is unproven.'],
 ['Publication','Private aggregate workbook. No approval to redistribute these results is implied.'],
 ['Missing research','Multi-vintage evaluation, model selection, policy and forecasts are not complete.'],
 ['Rates','Monthly stock prevalence and 12-month label outcomes have different populations.'],
 ['Unavailable cells','n.a. means unavailable, never zero. Do not add monthly balances across periods.'],
 ['Refresh','Regenerate from one completed pipeline and rerun workbook QA. Do not hand-edit a release.'],
 ['Preview','Read-only cached values from this workbook. It is not Excel Online.'],
 ],[30,106],'Sample scope and limitations apply to every sheet.');
sheets['00_ReadMe'].tabColor='#17365C';

sheet('14_Sources','Sources and independent controls',['Source / control','Value','Meaning'],[
 ['Release',data.release,'Freddie Mac Standard Release 47'],
 ['Distinct label loans',data.controls.loans,'COUNT(DISTINCT loan_id), checked against row count'],
 ['Original principal (USD)',data.controls.original_upb_usd,'Sum once per input loan, not a monthly stock sum'],
 ['Reporting months',data.monthly.length,'Distinct source reporting months'],
 ['Pipeline',data.pipeline_run,'All workbook tables use this development pipeline'],
 ['Source landing page',data.source_url,'Official source'],
 ['User guide',data.guide_url,'Official field / event definitions'],
 ],[31,112,67],'Source URLs are public; this workbook contains no loan IDs or private filesystem paths.');
numeric('14_Sources','B7:B10');

sheet('01_DataCoverage','Observation entry coverage',['Entry eligibility','Loans','Original principal (USD)','Share of all loans'],
 data.coverage.map(r=>[r.eligibility_reason,r.loans,r.original_upb_usd,null]),[29,17,28,23],
 'Early entry requires age 0-1 and source / contractual age agreement.');
const covEnd=6+data.coverage.length;
data.coverage.forEach((_,i)=>formula('01_DataCoverage',`D${7+i}`,`=B${7+i}/'14_Sources'!$B$8`));
numeric('01_DataCoverage',`B7:C${covEnd}`);numeric('01_DataCoverage',`D7:D${covEnd}`,'0.00%');
const outcomeStart=covEnd+4;
sheets['01_DataCoverage'].getRange(`A${outcomeStart}:B${outcomeStart+data.outcomes.length}`).values=[['12-month outcome','Loans'],...data.outcomes.map(r=>[r.outcome,r.loans])];
sheets['01_DataCoverage'].getRange(`A${outcomeStart}:B${outcomeStart}`).format={fill:'#17365C',font:{color:'#FFFFFF',bold:true,size:11,name:'Arial'}};
numeric('01_DataCoverage',`B${outcomeStart+1}:B${outcomeStart+data.outcomes.length}`);

sheet('02_MetricDictionary','Monthly metric definitions',['Metric','Unit','Numerator / calculation','Denominator','Interpretation'],
 Object.entries(data.metrics).map(([key,m])=>[key,m.unit,m.formula,m.denominator||'Not a ratio',m.limitation]),[31,13,63,35,94],
 'Grain: reporting month. Evidence: derived observed sample. Zero denominators are unavailable.');

const monthlyRows=data.monthly.map(r=>[new Date(r.period+'T00:00:00Z'),r.active_loans,r.state_usable_active_loans,r.d3_active_loans,
 r.unknown_active_loans,r.missing_active_balance_loans,r.observed_active_upb,r.state_usable_active_upb,
 r.d3_active_upb===null?0:r.d3_active_upb,null,null,r.reported_loans,r.terminal_loans]);
sheet('03_Portfolio','Monthly observed portfolio',['Reporting month','Active loans','Usable-state loans','Numeric D3 loans','Unknown-state loans','Missing-balance loans',
 'Known active UPB (USD)','Usable-state UPB (USD)','D3 UPB (USD)','D3 count share','D3 balance share','Reported loans','Terminal loans'],monthlyRows,
 [19,18,20,20,21,22,25,25,23,20,21,19,19],'Stock measures. D3 excludes REO; known-balance share is not a loan-count rate.');
const monthEnd=6+monthlyRows.length;
numeric('03_Portfolio',`A7:A${monthEnd}`,'mmm yyyy');numeric('03_Portfolio',`B7:I${monthEnd}`);numeric('03_Portfolio',`L7:M${monthEnd}`);
for(let r=7;r<=monthEnd;r++){
 formula('03_Portfolio',`J${r}`,`=IF(C${r}>0,D${r}/C${r},"n.a.")`);
 formula('03_Portfolio',`K${r}`,`=IF(H${r}>0,I${r}/H${r},"n.a.")`);
}
numeric('03_Portfolio',`J7:K${monthEnd}`,'0.00%');

const profileRows=data.portfolio_profile?.rows||[];
const profileStart=monthEnd+5;
if(profileRows.length){
 const profileHeaders=['Segment','Dimension','Bucket','Loans','Known UPB loans','Missing UPB loans','Opening UPB (USD)','Segment loans','Count share','Balance share'];
 const profileTableRows=profileRows.map(r=>[r.segment,r.dimension,r.bucket,r.loans,r.known_upb_loans,r.missing_upb_loans,
   r.opening_upb,r.segment_loans,r.count_share,r.balance_share]);
 raw('03_Portfolio',`A${profileStart}`,'Origination portfolio anatomy by Relief segment');
 sheets['03_Portfolio'].getRange(`A${profileStart}`).format.font={name:'Arial',size:14,bold:true,color:'#17365C'};
 raw('03_Portfolio',`A${profileStart+1}`,'Count and opening-principal shares are separate views. Unknown or unavailable buckets remain visible; no customer count is claimed.');
 sheets['03_Portfolio'].getRange(`A${profileStart+1}`).format.font={name:'Arial',size:10,italic:true,color:'#475569'};
 const profileEnd=profileStart+3+profileTableRows.length;
 sheets['03_Portfolio'].getRange(`A${profileStart+3}:J${profileEnd}`).values=[profileHeaders,...profileTableRows];
 sheets['03_Portfolio'].getRange(`A${profileStart+3}:J${profileStart+3}`).format={fill:'#17365C',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,rowHeight:46,horizontalAlignment:'center'};
 [16,22,18,14,17,18,22,17,16,17].forEach((w,i)=>sheets['03_Portfolio'].getRange(`${col(i)}${profileStart+3}:${col(i)}${profileEnd}`).format.columnWidth=w);
 sheets['03_Portfolio'].getRange(`A${profileStart+4}:J${profileEnd}`).format.rowHeight=23;
 numeric('03_Portfolio',`D${profileStart+4}:H${profileEnd}`);
 numeric('03_Portfolio',`I${profileStart+4}:J${profileEnd}`,'0.00%');
 previews.find(p=>p.name==='03_Portfolio').extraTables=[{headers:profileHeaders,rows:profileTableRows,startRow:profileStart+4}];
}

sheet('04_Vintage','Available 12-month labels by vintage',['Origination year','Input loans','Available labels','D3 events','Unavailable labels','D3 / available labels'],
 data.vintage.map(r=>[r.origination_year,r.loans,r.available_labels,r.d3_events,r.unavailable_labels,null]),[21,19,23,18,25,27],
 'Only available vintage(s). Not a multi-vintage comparison or a maturity-adjusted cumulative curve.');
data.vintage.forEach((_,i)=>formula('04_Vintage',`F${7+i}`,`=IF(C${7+i}>0,D${7+i}/C${7+i},"n.a.")`));
numeric('04_Vintage',`B7:E${6+data.vintage.length}`);numeric('04_Vintage',`F7:F${6+data.vintage.length}`,'0.00%');
const vintageEvidenceRows=data.vintage_evidence?.rows||[];
const vintageEvidenceStart=6+data.vintage.length+4;
if(vintageEvidenceRows.length){
  const vHeaders=['Origination year','Segment','Horizon (months)','Eligible loans','At risk','Observed D3','Prepayment / other exit','Unknown before horizon','Cumulative incidence D3','95% CI lower','95% CI upper','Maturity','CI status'];
  const vRows=vintageEvidenceRows.map(r=>[r.origination_year,r.segment,r.observation_age,r.eligible_loans,r.at_risk,r.observed_d3_count,
    (r.observed_prepayment_count||0)+(r.observed_other_exit_count||0),r.unknown_before_horizon,r.cif_d3,r.ci_lower,r.ci_upper,
    r.maturity_complete?'Complete':'Immature',r.ci_status]);
  raw('04_Vintage',`A${vintageEvidenceStart}`,'Validated observed competing-risk evidence');
  sheets['04_Vintage'].getRange(`A${vintageEvidenceStart}`).format.font={name:'Arial',size:14,bold:true,color:'#17365C'};
  raw('04_Vintage',`A${vintageEvidenceStart+1}`,'Loan-level identifiers are excluded. Cumulative incidence separates D3 from prepayment and other exit. Immature horizons remain unavailable.');
  sheets['04_Vintage'].getRange(`A${vintageEvidenceStart+1}`).format.font={name:'Arial',size:10,italic:true,color:'#475569'};
  const vEnd=vintageEvidenceStart+3+vRows.length;
  sheets['04_Vintage'].getRange(`A${vintageEvidenceStart+3}:M${vEnd}`).values=[vHeaders,...vRows];
  sheets['04_Vintage'].getRange(`A${vintageEvidenceStart+3}:M${vintageEvidenceStart+3}`).format={fill:'#17365C',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,rowHeight:46,horizontalAlignment:'center'};
  [18,20,16,17,15,15,23,23,23,18,18,15,22].forEach((w,i)=>sheets['04_Vintage'].getRange(`${col(i)}${vintageEvidenceStart+3}:${col(i)}${vEnd}`).format.columnWidth=w);
  sheets['04_Vintage'].getRange(`A${vintageEvidenceStart+4}:M${vEnd}`).format.rowHeight=23;
  numeric('04_Vintage',`C${vintageEvidenceStart+4}:H${vEnd}`);
  numeric('04_Vintage',`I${vintageEvidenceStart+4}:K${vEnd}`,'0.000%');
  previews.find(p=>p.name==='04_Vintage').extraTables=[{headers:vHeaders,rows:vRows,startRow:vintageEvidenceStart+4}];
}

sheet('05_Transitions','Adjacent-month state transitions',['Origin state','Destination state','Pair count','Origin pair count','Count probability','Opening UPB (USD)',
 'Missing UPB pairs','Origin known UPB (USD)','Balance probability'],data.transitions.map(r=>[r.origin,r.destination,r.pairs,null,null,r.opening_upb,r.missing_balance_pairs,null,null]),
 [23,27,19,22,23,27,25,29,25],'Repeated loan-month pairs, not independent loans. Missing / nonadjacent next months are excluded.');
const transEnd=6+data.transitions.length;
for(let r=7;r<=transEnd;r++){
 formula('05_Transitions',`D${r}`,`=SUMIFS($C$7:$C$${transEnd},$A$7:$A$${transEnd},A${r})`);
 formula('05_Transitions',`E${r}`,`=IF(D${r}>0,C${r}/D${r},"n.a.")`);
 formula('05_Transitions',`H${r}`,`=SUMIFS($F$7:$F$${transEnd},$A$7:$A$${transEnd},A${r})`);
 formula('05_Transitions',`I${r}`,`=IF(H${r}>0,F${r}/H${r},"n.a.")`);
}
numeric('05_Transitions',`C7:D${transEnd}`);numeric('05_Transitions',`F7:H${transEnd}`);
numeric('05_Transitions',`E7:E${transEnd}`,'0.00%');numeric('05_Transitions',`I7:I${transEnd}`,'0.00%');

const segmentedRows=data.segmented_transitions?.rows||[];
const segmentedStart=transEnd+5;
if(segmentedRows.length){
 const segmentedHeaders=['Segment','Origin state','Destination state','Pair count','Distinct loans','Opening UPB (USD)','Missing UPB pairs','Origin pair count','Count probability','Balance probability','Sparse cell'];
 const segmentedTableRows=segmentedRows.map(r=>[r.segment,r.origin,r.destination,r.pairs,r.distinct_loans,r.opening_upb,
   r.missing_balance_pairs,r.origin_pairs,r.count_probability,r.balance_probability,r.sparse_cell?'Review':'Supported']);
 raw('05_Transitions',`A${segmentedStart}`,'Validated transitions by Relief segment');
 sheets['05_Transitions'].getRange(`A${segmentedStart}`).format.font={name:'Arial',size:14,bold:true,color:'#17365C'};
 raw('05_Transitions',`A${segmentedStart+1}`,'Aggregate segment evidence. Sparse cells have fewer than 30 distinct loans; no causal program effect is claimed.');
 sheets['05_Transitions'].getRange(`A${segmentedStart+1}`).format.font={name:'Arial',size:10,italic:true,color:'#475569'};
 const segmentedEnd=segmentedStart+3+segmentedTableRows.length;
 sheets['05_Transitions'].getRange(`A${segmentedStart+3}:K${segmentedEnd}`).values=[segmentedHeaders,...segmentedTableRows];
 sheets['05_Transitions'].getRange(`A${segmentedStart+3}:K${segmentedStart+3}`).format={fill:'#17365C',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,rowHeight:46,horizontalAlignment:'center'};
 [16,18,20,15,16,22,18,18,18,19,14].forEach((w,i)=>sheets['05_Transitions'].getRange(`${col(i)}${segmentedStart+3}:${col(i)}${segmentedEnd}`).format.columnWidth=w);
 sheets['05_Transitions'].getRange(`A${segmentedStart+4}:K${segmentedEnd}`).format.rowHeight=23;
 numeric('05_Transitions',`D${segmentedStart+4}:H${segmentedEnd}`);
 numeric('05_Transitions',`I${segmentedStart+4}:J${segmentedEnd}`,'0.00%');
 previews.find(p=>p.name==='05_Transitions').extraTables=[{headers:segmentedHeaders,rows:segmentedTableRows,startRow:segmentedStart+4}];
}

const episodeMeaning={FIRST_OBSERVED_D3:['First observed D3','First observed numeric D3 for a loan'],ONE_MONTH_CURE:['One-month cure','First current observation after an open D3 episode'],SUSTAINED_CURE_CONFIRMED:['Sustained cure confirmed','Confirmed after three consecutive current months'],REDEFAULT_AFTER_SUSTAINED_CURE:['Redefault after sustained cure','D3 after a confirmed sustained cure']};
sheet('06_Cure','Observed episode confirmations',['Event type','Event records','Distinct loans','Definition'],
 data.episodes.map(r=>[episodeMeaning[r.event_type][0],r.event_records,r.distinct_loans,episodeMeaning[r.event_type][1]]),[37,20,20,77],
 'Counts are not cure probabilities. Horizon-specific eligible denominators are not yet implemented.');
numeric('06_Cure',`B7:C${6+data.episodes.length}`);

gate('07_ModelComparison','Model comparison','Missing calibration, validation and test vintages','Approved temporal split and evaluated baseline / challenger');
gate('08_Calibration','Calibration','No validated out-of-time probabilities','Same-population predictions, bins, events and expected events');
gate('09_Strategy','Policy comparison','No evaluated model or approved economic assumptions','Funded-loan baseline, retention and policy constraints');
const loss=data.loss_summary;
const lossRows=[
 ['Reported loss loans',data.loss_reconciliation[0].reported,'Audit population with reported actual loss'],
 ['Incomplete component formulas',data.loss_reconciliation[0].incomplete_formula,'Reported-loss population'],
 ['Loss formula mismatches',data.loss_reconciliation[0].loss_mismatch,'Signed component reconciliation'],
 ['Expense formula mismatches',data.loss_reconciliation[0].expense_mismatch,'Expense component reconciliation'],
 ['Maximum loss residual (USD)',Number(data.loss_reconciliation[0].max_abs_loss_residual_usd),'Source arithmetic difference'],
 ['Resolved terminal loans',loss.terminal_loans,'One earliest loss-code terminal row per loan'],
 ['Unresolved terminal loans',loss.unresolved_terminal_loans,'Not silently treated as zero loss'],
 ['Reported loss sum (USD)',loss.reported_loss_sum_usd,'Observed signed amount; not lender P&L'],
 ['Mean uncapped severity',loss.severity_mean_uncapped,'Absolute reported loss / absolute removal UPB'],
 ['Maximum uncapped severity',loss.severity_max_uncapped,'Values above 100% remain visible'],
 ['Partial component rows',loss.partial_component_rows,'Excluded from complete component bridge'],
 ['Duplicate terminal rows removed',loss.duplicate_terminal_rows_removed,'Prevents repeated cumulative rows'],
 ['B18 loss model gate',loss.gate_status,loss.gate_reasons.join(', ')||'Support and coverage reviewed'],
 ['Expected loss dollars',loss.expected_loss_dollars===null?'Unavailable':loss.expected_loss_dollars,'Not released while B18 gate is blocked'],
 ];
sheet('10_Loss','Observed loss accounting and B18 gate',['Check','Loans / USD','Interpretation'],lossRows,[38,23,92],
 'Source signs and missingness are preserved. One terminal row per loan is used for descriptive aggregation. No expected-loss dollars are claimed.');
numeric('10_Loss','B7:B14');numeric('10_Loss','B15','0.00%');numeric('10_Loss','B16','0.00%');numeric('10_Loss','B17:B18');
gate('11_ForecastStress','Forecast and stress','No qualified macro / forecast or stress experiment','Origin-specific inputs, backtests and explicit scenario assumptions');

sheet('12_Assumptions','Research protocol settings',['Setting','Value','Meaning'],[
 ['Label horizon (months)',12,'t+1 through t+12 after entry landmark'],
 ['Early entry age (months)','0-1','Source and contractual ages must agree'],
 ['Prepayment estimand','D3 before prepayment','Prepayment negative only for this endpoint'],
 ['Other exits','Unavailable label','Not automatically negative'],
 ['Sustained cure (months)',3,'Confirmation is not backdated'],
 ['Missing or gap before outcome','Unavailable label','Later gaps do not erase an already observed outcome'],
 ['Source vintage meaning','Origination year','Not acquisition year'],
 ['Publication approval','Not approved','Private development workbook only'],
 ],[40,31,74],'Protocol metadata, not editable scenario drivers. Change configuration and regenerate to revise.');

sheet('13_Checks','Workbook reconciliations',['Check','Difference','Tolerance','Result'],[
 ['Eligibility count reconciliation',null,0,null],
 ['Eligibility principal (USD)',null,0.01,null],
 ['Outcome count reconciliation',null,0,null],
 ['Monthly reported = active + terminal',null,0,null],
 ['Vintage loan reconciliation',null,0,null],
 ],[47,22,20,20],'Independent review. No business result depends on these cells.');
formula('13_Checks','B7',`=SUM('01_DataCoverage'!B7:B${covEnd})-'14_Sources'!B8`);
formula('13_Checks','B8',`=SUM('01_DataCoverage'!C7:C${covEnd})-'14_Sources'!B9`);
formula('13_Checks','B9',`=SUM('01_DataCoverage'!B${outcomeStart+1}:B${outcomeStart+data.outcomes.length})-'14_Sources'!B8`);
formula('13_Checks','B10',`=SUM('03_Portfolio'!L7:L${monthEnd})-SUM('03_Portfolio'!B7:B${monthEnd})-SUM('03_Portfolio'!M7:M${monthEnd})`);
formula('13_Checks','B11',`=SUM('04_Vintage'!B7:B${6+data.vintage.length})-'14_Sources'!B8`);
for(let r=7;r<=11;r++)formula('13_Checks',`D${r}`,`=IF(ABS(B${r})<=C${r},"PASS","FAIL")`);
numeric('13_Checks','B7:C11','#,##0.00');
sheets['13_Checks'].getRange('D7:D11').conditionalFormats.add('containsText',{text:'FAIL',format:{fill:'#FEE2E2',font:{color:'#991B1B',bold:true}}});

workbook.recalculate();
const value=(name,cell)=>sheets[name].getRange(cell).values[0][0];
function near(actual,expected,label){if(typeof actual!=='number'||Math.abs(actual-expected)>1e-9)throw Error(`${label}: ${actual} != ${expected}`);}
data.monthly.forEach((r,i)=>{
 if(r.d3_count_share!==null)near(value('03_Portfolio',`J${i+7}`),r.d3_count_share,`monthly count ${i}`);
 if(r.d3_balance_share!==null)near(value('03_Portfolio',`K${i+7}`),r.d3_balance_share,`monthly balance ${i}`);
});
data.transitions.forEach((r,i)=>near(value('05_Transitions',`E${i+7}`),r.count_probability,`transition ${i}`));
raw('03_Portfolio','C7',0);workbook.recalculate();
if(value('03_Portfolio','J7')!=='n.a.')throw Error('Zero denominator hidden');
raw('03_Portfolio','C7',100);raw('03_Portfolio','D7',5);workbook.recalculate();
near(value('03_Portfolio','J7'),0.05,'changed numerator / denominator');
raw('03_Portfolio','C7',data.monthly[0].state_usable_active_loans);raw('03_Portfolio','D7',data.monthly[0].d3_active_loans);
workbook.recalculate();
for(let r=7;r<=11;r++)if(value('13_Checks',`D${r}`)!=='PASS')throw Error(`Workbook check ${r} failed`);
const scan=await workbook.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:100},maxChars:3000});
await fs.writeFile(path.join(outputDir,'formula-scan.ndjson'),scan.ndjson);

const previewPayload={visibility:'private',public_release_approved:false,pipeline_run:data.pipeline_run,filename:'Credit-Risk-Strategy-Lab-Private.xlsx',sheets:[]};
for(const p of previews){
 const s=sheets[p.name];
 const tableRows=s.getRange(`A${p.startRow}:${p.lastColumn}${p.endRow}`).values;
 const extraTables=p.name==='01_DataCoverage'?[{headers:['12-month outcome','Loans'],rows:s.getRange(`A${outcomeStart+1}:B${outcomeStart+data.outcomes.length}`).values,startRow:outcomeStart+1}]:p.extraTables||[];
 previewPayload.sheets.push({...p,rows:tableRows,extraTables});
 if(renderSelection&&!renderSelection.includes(p.name))continue;
 const renderLast=p.name==='02_MetricDictionary'?'E':p.lastColumn;
  const lastRow=p.name==='01_DataCoverage'?outcomeStart+data.outcomes.length:p.name==='03_Portfolio'&&profileRows.length?profileStart+3+profileRows.length:p.name==='04_Vintage'&&vintageEvidenceRows.length?vintageEvidenceStart+3+vintageEvidenceRows.length:p.name==='05_Transitions'&&segmentedRows.length?segmentedStart+3+segmentedRows.length:Math.min(p.endRow,20);
 const img=await workbook.render({sheetName:p.name,range:`A1:${renderLast}${lastRow}`,scale:1,format:'png'});
 await fs.writeFile(path.join(outputDir,p.name+'.png'),new Uint8Array(await img.arrayBuffer()));
 console.log(`Rendered ${p.name}`);
}
const file=await SpreadsheetFile.exportXlsx(workbook);
const filename=previewPayload.filename;
await file.save(path.join(outputDir,filename));
previewPayload.sha256=digest(await fs.readFile(path.join(outputDir,filename)));
previewPayload.sheets.sort((a,b)=>names.indexOf(a.name)-names.indexOf(b.name));
await fs.writeFile(path.join(outputDir,'preview.json'),JSON.stringify(previewPayload,null,2));
await fs.writeFile(path.join(outputDir,'registry.json'),JSON.stringify({pipeline_run:data.pipeline_run,visibility:'private',public_release_approved:false,
 filename,sha256:previewPayload.sha256,input_sha256:digest(inputBytes),preview_sha256:digest(await fs.readFile(path.join(outputDir,'preview.json'))),
  sheet_count:names.length,monthly_rows:data.monthly.length,transition_rows:data.transitions.length,segmented_transition_rows:segmentedRows.length,portfolio_profile_rows:profileRows.length,artifact_engine_recalculation:true,native_excel_verified:false},null,2));
console.log(`Exported ${filename}; private only. Native Excel verification not performed.`);
