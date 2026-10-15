import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const [input,output,preview]=process.argv.slice(2),r=JSON.parse(await fs.readFile(input,'utf8'));
const wb=Workbook.create(),main=wb.worksheets.add('Maturities'),facts=wb.worksheets.add('Facts');
const col=n=>String.fromCharCode(65+n);
function write(s,row,data){const width=Math.max(...data.map(x=>x.length));for(let i=0;i<data.length;i++)for(let j=0;j<data[i].length;j++)if(typeof data[i][j]==='string')s.getRange(`${col(j)}${row+i}`).setNumberFormat('@');s.getRange(`A${row}:${col(width-1)}${row+data.length-1}`).values=data.map(x=>Array.from({length:width},(_,i)=>typeof x[i]==='string'&&x[i].startsWith('=')?"'"+x[i]:x[i]??null));}
function base(s,title,range){s.showGridLines=false;s.getRange(range).format={font:{name:'Arial',size:10,color:'#24384C'},verticalAlignment:'center',rowHeight:28,columnWidth:24};write(s,2,[[title]]);s.getRange('A2').format.font={name:'Arial',size:16,bold:true,color:'#233E59'};s.getRange('A3:F3').format.borders={bottom:{style:'thin',color:'#B6C5D4'}};}
function header(s,row,labels){write(s,row,[labels]);s.getRange(`A${row}:${col(labels.length-1)}${row}`).format={fill:'#233E59',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},horizontalAlignment:'center',wrapText:true,rowHeight:38};}
const numeric=f=>f.status==='supported'&&Number.isFinite(Number(f.value_exact))?Number(f.value_exact):'Unavailable';
base(main,r.entity.ticker+' principal maturities','A1:F28');main.tabColor='#233E59';
write(main,4,[['CIK',r.filters.cik,'Cutoff',new Date(r.filters.asof)],['Selected filing',r.statement.accession,'Report end',new Date(r.statement.report_date)],['Debt scope',r.filters.debt_scope],['Units','USD principal. Fiscal-year buckets; after-year-five is open ended.']]);main.getRange('D4:D5').setNumberFormat('yyyy-mm-dd');
header(main,8,['Maturity bucket','Principal USD (Excel)','Source status','Share (Excel)','Principal exact text','Share exact text']);
const source=r.buckets.map(b=>[b.bucket,b.field.concept,numeric(b.field),b.field.value_exact??'Unavailable',b.field.status,new Date(b.field.end_date),new Date(r.statement.filing_date),r.statement.accession,JSON.stringify(b.field.evidence),b.definition.label??'Not supplied',b.definition.description??'Not supplied',r.statement.filing_url]);
base(facts,'Selected filing maturity facts','A1:L30');facts.tabColor='#E8DDC7';
write(facts,4,[['Source',`https://data.sec.gov/api/xbrl/companyfacts/CIK${r.filters.cik}.json`]]);
header(facts,5,['Bucket key','Concept','Numeric USD input','Exact USD text','Source status','Report end','Filed','Accession','Candidates JSON','Source label','Source definition','Filing URL']);write(facts,6,source);
facts.getRange('C6:C11').setNumberFormat('#,##0;(#,##0);0');facts.getRange('F6:G11').setNumberFormat('yyyy-mm-dd');facts.getRange('C6:C11').format.font.color='#2451A4';
for(let i=0;i<6;i++){const target=i+9,src=i+6,b=r.buckets[i];write(main,target,[[b.label,null,null,null,b.field.value_exact??'Unavailable',b.share_of_disclosed_schedule_exact??'Unavailable']]);main.getRange(`B${target}:D${target}`).formulas=[[
`=IF(AND('Facts'!E${src}="supported",ISNUMBER('Facts'!C${src})),'Facts'!C${src},"Unavailable")`,
`='Facts'!E${src}`,
`=IF(ISNUMBER($B$18),IF($B$18>0,B${target}/$B$18,"Unavailable"),"Unavailable")`]];}
write(main,16,[['Supported buckets',null],['Supported subtotal USD',null],['Complete six-bucket total USD',null],['First three years / complete total',null],['Schedule status (Excel)',null],['Subtotal definition','Subtotal may be partial. Complete total requires six supported numeric, nonnegative buckets.'],['Interpretation','Principal buckets do not supply interest payment dates, full debt balances, cash available for debt service or DSCR.'],['Numeric precision','Excel floating point. Exact source/derived text retained for reconciliation.'],['Refresh','Export again from verified app scope. Manual source edits require rechecking filing/concept/date scope.']]);
main.getRange('B16:B20').formulas=[[
'=COUNTIFS(C9:C14,"supported")'],[
'=IF(COUNT(B9:B14)>0,SUM(B9:B14),"Unavailable")'],[
'=IF(AND(B16=6,COUNT(B9:B14)=6),IF(MIN(B9:B14)>=0,SUM(B9:B14),"Unavailable"),"Unavailable")'],[
'=IF(ISNUMBER(B18),IF(B18>0,SUM(B9:B11)/B18,"Unavailable"),"Unavailable")'],[
'=IF(AND(COUNT(B9:B14)>0,MIN(B9:B14)<0),"INVALID_NEGATIVE_BUCKET",IF(B16<6,"PARTIAL_DISCLOSED_SCHEDULE",IF(COUNT(B9:B14)<6,"NUMERIC_INPUT_UNAVAILABLE",IF(SUM(B9:B14)=0,"COMPLETE_ZERO_SCHEDULE","COMPLETE_DISCLOSED_SCHEDULE"))))']];
main.getRange('B9:B14').setNumberFormat('#,##0;(#,##0);0');main.getRange('B17:B18').setNumberFormat('#,##0;(#,##0);0');main.getRange('D9:D14').setNumberFormat('0.0000%');main.getRange('B19').setNumberFormat('0.0000%');main.getRange('B9:C14').format.font.color='#287D44';main.getRange('B9:F20').format.horizontalAlignment='right';
for(const [column,width] of [['A',39],['B',46],['C',32],['D',20],['E',34],['F',80]])main.getRange(`${column}1:${column}25`).format.columnWidth=width;
main.getRange('B21:B24').format.wrapText=true;main.getRange('A21:F24').format.rowHeight=58;
for(const [column,width] of [['A',18],['B',95],['C',26],['D',32],['E',28],['F',16],['G',16],['H',28],['I',100],['J',70],['K',100],['L',100]])facts.getRange(`${column}1:${column}30`).format.columnWidth=width;
const evidence=[['Source ID',r.source_id],['Case ID',r.case_id],['Method SHA256',r.method_source_sha256],...Object.entries(r.source_capture),['Selection rule',r.selection_rule]];write(facts,14,evidence);facts.getRange(`A14:B${13+evidence.length}`).format.wrapText=true;facts.getRange(`A14:L${13+evidence.length}`).format.rowHeight=45;
facts.freezePanes.freezeRows(5);facts.freezePanes.freezeColumns(1);main.freezePanes.freezeRows(8);main.freezePanes.freezeColumns(1);
main.getRange('B20').conditionalFormats.add('containsText',{text:'INVALID_NEGATIVE_BUCKET',format:{fill:'#FCE8E6',font:{bold:true,color:'#A12A22'}}});
const compare=(value,exact)=>exact==null?value==='Unavailable':typeof value==='number'&&Math.abs(value-Number(exact))<=1e-10*Math.max(1,Math.abs(Number(exact)));
function verify(){wb.recalculate();for(let i=0;i<6;i++){const values=main.getRange(`B${i+9}:D${i+9}`).values[0];if(!compare(values[0],r.buckets[i].field.value_exact)||!compare(values[2],r.buckets[i].share_of_disclosed_schedule_exact))throw new Error('Bucket formula mismatch '+i);}const s=r.summary;for(const [cell,expected] of [['B17',s.supported_subtotal_exact],['B18',s.disclosed_schedule_total_exact],['B19',s.first_three_years_share_exact]])if(!compare(main.getRange(cell).values[0][0],expected))throw new Error('Schedule formula mismatch '+cell);if(main.getRange('B20').values[0][0]!==s.status)throw new Error('Schedule status mismatch');}
verify();
// Authoring-only dependency checks: all zero, source missing and negative inputs.
const original=facts.getRange('C6:E11').values;
for(const [values,status] of [
 [Array.from({length:6},()=>[0,'0','supported']),'COMPLETE_ZERO_SCHEDULE'],
 [Array.from({length:6},()=>['Unavailable','Unavailable','missing']),'PARTIAL_DISCLOSED_SCHEDULE'],
 [Array.from({length:6},(_,i)=>[i===0?-1:1,String(i===0?-1:1),'supported']),'INVALID_NEGATIVE_BUCKET']]){
 facts.getRange('C6:E11').values=values;wb.recalculate();if(main.getRange('B20').values[0][0]!==status||main.getRange('B19').values[0][0]!=='Unavailable')throw new Error('Boundary dependency failure '+status);
}
facts.getRange('C6:E11').values=original;verify();
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:20},maxChars:2000});
if(preview){await fs.mkdir(preview,{recursive:true});for(const [name,range] of [['Maturities','A2:D24'],['Facts','A2:E11']]){const png=await wb.render({sheetName:name,range,scale:1});await fs.writeFile(path.join(preview,name+'.png'),new Uint8Array(await png.arrayBuffer()));}await fs.writeFile(path.join(preview,'inspect.json'),JSON.stringify(errors));}
await fs.mkdir(path.dirname(output),{recursive:true});await(await SpreadsheetFile.exportXlsx(wb)).save(output);console.log(JSON.stringify({status:'EXPORTED',buckets:6,scope:r.filters,output}));
