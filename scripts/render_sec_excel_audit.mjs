import fs from 'node:fs/promises';
import path from 'node:path';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const [manifestPath,output]=process.argv.slice(2);
const manifest=JSON.parse(await fs.readFile(manifestPath,'utf8'));
await fs.mkdir(output,{recursive:true});const checks=[];
for(const cik of ['0000320193','0000789019','0000037996','0001467858']){
 const s=manifest.scopes.find(s=>s.query.cik===cik&&s.query.years==='5'&&s.query.interest_concept==='InterestExpenseNonoperating');
 const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(path.resolve(s.workbook)));
 for(const [sheet,range,label] of [['Analysis','A2:D15','summary'],['Analysis','I18:N25','calculations'],['Facts','A2:H13','facts']]){
  const blob=await wb.render({sheetName:sheet,range,scale:1});
  await fs.writeFile(path.join(output,cik+'-'+label+'.png'),new Uint8Array(await blob.arrayBuffer()));
 }
 const inspected=await wb.inspect({kind:'table',range:'Analysis!A9:D15',include:'values,formulas',tableMaxRows:7,tableMaxCols:4,maxChars:2500});
 await fs.writeFile(path.join(output,cik+'-inspect.json'),JSON.stringify(inspected));
 checks.push({cik,source:s.workbook,ranges:3});
}
await fs.writeFile(path.join(output,'receipt.json'),JSON.stringify({status:'RENDERED_NEEDS_VISUAL_REVIEW',books:checks},null,2));
console.log(output);
