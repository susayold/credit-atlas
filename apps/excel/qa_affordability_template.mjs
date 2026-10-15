import fs from 'node:fs/promises';
import path from 'node:path';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const [source,output]=process.argv.slice(2);
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(source));
const c=wb.worksheets.getItem('AffordabilityControl'),s=wb.worksheets.getItem('AffordabilityItems');
c.getRange('B2:B15').values=[['qa-case'],['2026-10-12'],['USD'],['individual'],['qa-person'],[1],['qa-policy'],[0.4],[500],...Array.from({length:5},()=>['true'])];
const amounts=[60000,4000,1500,1500,500],groups=['gross_income','net_income','recurring_expenses','debt_payments','proposed_payments'];
s.getRange('A2:F6').values=groups.map((g,i)=>[g,'qa-'+g,amounts[i],i===0?'annual':'monthly',null,null]);
wb.recalculate();await fs.mkdir(path.dirname(output),{recursive:true});
const inspected=await wb.inspect({kind:'table',range:'AffordabilityItems!A1:F6',include:'values,formulas',tableMaxRows:6,tableMaxCols:6});
await fs.writeFile(output+'.inspect.json',JSON.stringify({qaInputsOnly:true,inspection:inspected.ndjson},null,2));
for(const sheet of [c,s]){const image=await wb.render({sheetName:sheet.name,range:sheet===c?'A1:D15':'A1:H8',scale:1,format:'png'});await fs.writeFile(output+'.'+sheet.name+'.png',new Uint8Array(await image.arrayBuffer()));}
await(await SpreadsheetFile.exportXlsx(wb)).save(output);
console.log(JSON.stringify({qaInputsOnly:true,output}));
