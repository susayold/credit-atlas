import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook, SpreadsheetFile} from '@oai/artifact-tool';

const [outputPath]=process.argv.slice(2);
if(!outputPath)throw new Error('output-xlsx required');
const wb=Workbook.create();
const control=wb.worksheets.add('AffordabilityControl');
const items=wb.worksheets.add('AffordabilityItems');
for(const [s,last] of [[control,'D'],[items,'H']]){
 s.showGridLines=false;s.getRange(`A1:${last}24`).format.font={name:'Arial',size:11};
 s.getRange(`A1:${last}24`).format.verticalAlignment='center';
 s.getRange(`A1:${last}24`).format.rowHeight=26;
 s.freezePanes.freezeRows(1);
}
const groups=['gross_income','net_income','recurring_expenses','debt_payments','proposed_payments'];
const keys=['case_ref','as_of','currency','scope','scope_ref','members','policy_ref','max_total_dti_fraction','min_monthly_residual',...groups.map(g=>'coverage_'+g)];
control.getRange('A1:B15').values=[['key','value'],...keys.map(k=>[k,k.startsWith('coverage_')?'false':null])];
control.getRange('A1:A15').format.columnWidth=36;control.getRange('B1:B15').format.columnWidth=29;control.getRange('C1:C24').format.columnWidth=3;control.getRange('D1:D24').format.columnWidth=91;
control.getRange('B2:B15').format.fill='#FFF5D9';control.getRange('B2:B15').format.font.color='#0000FF';
control.getRange('B3').setNumberFormat('@');control.getRange('B7').setNumberFormat('0');
control.getRange('B9').setNumberFormat('0.0%');control.getRange('B10').setNumberFormat('#,##0.00');
control.getRange('B5').dataValidation={rule:{type:'list',values:['individual','household']}};
control.getRange('B7').dataValidation={rule:{type:'whole',operator:'between',formula1:1,formula2:100}};
control.getRange('B11:B15').dataValidation={rule:{type:'list',values:['true','false']}};
control.getRange('D1:D24').values=[
 ['Guidance'],['AFFORDABILITY — THÔNG TIN HỒ SƠ'],['Điền ô vàng; giữ nguyên keys và tên sheets.'],
 ['case_ref / scope_ref: mã giả danh; không nhập tên, mật khẩu.'],['as_of: nhập text ISO YYYY-MM-DD, ví dụ định dạng 2026-10-12.'],
 ['currency: một mã tiền tệ ba chữ in hoa, như VND hoặc USD.'],['scope: individual hoặc household; individual có members = 1.'],
 ['policy_ref: mã policy khai báo; không có policy thì giữ trống.'],['max_total_dti_fraction: nhập ngưỡng phần trăm; không có ngưỡng thì để trống.'],
 ['min_monthly_residual: số tiền còn lại tối thiểu theo cùng currency.'],['coverage false: chưa khai báo đầy đủ; không tự chuyển thành zero.'],
 ['Chỉ chọn true sau khi đã nhập đầy đủ nhóm theo phạm vi hồ sơ.'],['Không có dòng và coverage true nghĩa là bạn khai báo known zero.'],
 ['DTI = (existing + proposed monthly payments) / gross monthly income.'],['Residual = net income − expenses − existing payments − proposed payments.'],
 ['Gross và net tách riêng; expenses không gồm các payments đã nhập.'],['File input chỉ nhận values; không nhập formulas hoặc external links.'],
 ['Chọn file trong Retail → Affordability; xem ô nguồn rồi kiểm tra kết quả.'],['Chứng từ và completeness cần được xác minh riêng.'],
 ['Optional sensitivity: thêm đủ 3 keys ở dưới bảng khi cần.'],['gross_income_reduction_fraction và net_income_reduction_fraction: 0–1.'],
 ['extra_monthly_expense: số tiền tăng chi phí hàng tháng, không âm.'],['Không thêm một phần keys sensitivity; để cả nhóm vắng nếu không dùng.'],
 ['Cột Guidance là hướng dẫn, không được dùng làm financial input.']];
const headers=['group','ref','amount','period','evidence_ref','valid_through'];
items.getRange('A1:F6').values=[headers,...groups.map(g=>[g,null,null,null,null,null])];
for(const [col,width] of [['A',28],['B',24],['C',21],['D',23],['E',25],['F',21],['G',3],['H',79]])items.getRange(`${col}1:${col}24`).format.columnWidth=width;
items.getRange('A2:F21').format.fill='#FFF5D9';items.getRange('A2:F21').format.font.color='#0000FF';items.getRange('C2:C21').setNumberFormat('#,##0.00');items.getRange('F2:F21').setNumberFormat('@');
items.getRange('A2:A2501').dataValidation={rule:{type:'list',values:groups}};
items.getRange('D2:D2501').dataValidation={rule:{type:'list',values:['monthly','annual','quarterly','weekly','biweekly','semimonthly']}};
items.getRange('H1:H17').values=[['Guidance'],['AFFORDABILITY — DÒNG THU NHẬP VÀ NGHĨA VỤ'],
 ['Mỗi dòng là một khoản; thêm dòng khi có nhiều khoản trong cùng group.'],['group chọn trong danh sách; ref là mã dòng duy nhất.'],
 ['amount là giá trị gốc không âm, theo currency ở Control.'],['Ô amount trống là missing; nhập 0 chỉ khi thực sự là zero.'],
 ['period là kỳ của amount; app quy đổi về tháng theo convention.'],['monthly ×1; annual ÷12; quarterly ÷3.'],
 ['weekly ×52/12; biweekly ×26/12; semimonthly ×2.'],['evidence_ref là mã chứng từ; trống thì app báo thiếu reference.'],
 ['valid_through dùng text ISO YYYY-MM-DD hoặc để trống.'],['Không cộng cùng một nghĩa vụ vào expenses, debt và proposed.'],
 ['Gross income trước khấu trừ; net income sau khấu trừ.'],['Số lớn hơn 15 chữ số cần text decimal; không dùng dấu phẩy trong text.'],
 ['Tối đa 500 dòng/nhóm và 2.500 dòng/file.'],['Giữ A1:F1; cột G là khoảng trống; cột H chỉ là hướng dẫn.'],
 ['Các dòng hiện tại chưa có số liệu hồ sơ; điền trước khi upload.']];
for(const [s,range] of [[control,'A1:B1'],[items,'A1:F1']])s.getRange(range).format={fill:'#243B53',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},horizontalAlignment:'center',verticalAlignment:'center',rowHeight:30};
control.getRange('D1').format.font.bold=true;control.getRange('D2').format.font={size:14,bold:true};items.getRange('H1').format.font.bold=true;items.getRange('H2').format.font={size:14,bold:true};
wb.recalculate();
await fs.mkdir(path.dirname(outputPath),{recursive:true});
const inspection=await wb.inspect({kind:'table',range:'AffordabilityControl!A1:B15',include:'values,formulas',tableMaxRows:15,tableMaxCols:2});
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:50}});
if(!errors.ndjson.includes('matched 0 entries'))throw new Error(errors.ndjson);
await fs.writeFile(outputPath+'.qa.json',JSON.stringify({inspection:inspection.ndjson,formulaErrors:errors.ndjson,blankCustomerInputs:true},null,2));
for(const s of [control,items]){const preview=await wb.render({sheetName:s.name,range:s===control?'A1:D24':'A1:H21',scale:1,format:'png'});await fs.writeFile(outputPath+'.'+s.name+'.png',new Uint8Array(await preview.arrayBuffer()));}
await (await SpreadsheetFile.exportXlsx(wb)).save(outputPath);
console.log(JSON.stringify({status:'exported',output:outputPath}));
