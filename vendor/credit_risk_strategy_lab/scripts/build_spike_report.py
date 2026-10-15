"""Build a private canonical report payload from verified diagnostic outputs."""
import json
from pathlib import Path
from crsl.source import write_json_new, utc_now

root=Path(__file__).resolve().parents[1]
source_run=root/'artifacts/private/d3167b604110-30526467'
spike=root/'artifacts/private/spike-b451ac1c907c'
result=json.loads((source_run/'result.json').read_text())
data=json.loads((spike/'diagnostics.json').read_text())['tables']
s=result['summary']; e=data['event_support'][0]
title='Freddie Mac 2012 Source Qualification'
blocks=[]
def section(id,heading,body,source='spike'):
    blocks.append({'id':id,'type':'markdown','body':heading+'\n\n'+body, **({'sourceId':source} if source else {})})
section('title','# '+title,'',None)
section('summary','## Kết luận kỹ thuật: đủ để phát triển dữ liệu, chưa đủ để huấn luyện',
    f"Annual sample đã ghép khớp {s['origination_loans']:,} khoản vay với {s['performance_rows']:,} bản ghi tháng. Không có trùng khóa, bản ghi mồ côi hoặc đứt tháng trong khoảng được quan sát. Đây là bằng chứng cho bước canonical/eligibility, không phải phê duyệt model hay publication.", 'ingestion')
section('scope','## Phạm vi và định nghĩa',
    'Một hàng origination là một khoản vay; một hàng performance là khoản vay–tháng. Mẫu acquisition vintage 2012, Release 47; lịch sử quan sát từ tháng 1/2012 đến tháng 3/2026. Một vintage acquisition không đồng nghĩa mọi khoản đều bắt đầu hợp đồng năm đó. D3 ở đây là trạng thái numeric 03–99; first observed D3 chưa phải nhãn default12m. RA được đếm riêng. Số liệu là mô tả mẫu, không suy rộng thành danh mục toàn thị trường.')
section('events','## Có sự kiện tín dụng, nhưng tổn thất có ít quan sát hơn',
    f"Có {e['ever_observed_d3_loans']:,} khoản từng được quan sát ở D3, không khoản nào đã D3 ngay hàng đầu. Có {e['ever_reo_loans']} khoản từng ở RA. Chỉ {e['populated_loss_loans']} khoản có actual_loss; còn {e['eligible_code_without_loss_rows']} hàng thuộc nhóm terminal code 02/03/09/15 nhưng thiếu actual_loss. Không điền thiếu bằng 0. Đây là giới hạn có mức độ cao đối với loss modeling; chưa đủ cơ sở xác nhận nhãn LGD hoặc chọn độ phức tạp mô hình.")
section('coverage','## Lịch sử nhiều năm không thay thế tập kiểm định nhiều vintage',
    'Biểu đồ đếm số khoản có ít nhất một hàng trong từng năm. Các khoản trả hết hoặc kết thúc quan sát làm mẫu còn lại thay đổi; không diễn giải đường này như mức rủi ro tăng/giảm. Năm 2026 chỉ có quý I; không so tổng số dòng năm đó trực tiếp với một năm đầy đủ.')
blocks.append({'id':'coverage-chart','type':'chart','chartId':'coverage'})
section('missing','## Giá trị có mặt trong cột chưa chắc là thông tin sử dụng được',
    'Toàn bộ 50.000 hàng có raw VantageScore = 9999; 17.400 hàng có raw DTI = 999. Vì vậy blank rate bằng 0 không thể được trình bày như complete feature coverage. HARP=Y ở 17.399 khoản, cần phân tầng và kiểm tra liên hệ với thiếu DTI, không tự kết luận nguyên nhân. 43.177 khoản bắt đầu được quan sát ở tuổi 0; 48.080 khoản ở tuổi 0–1. Các khoản còn lại cần eligibility/exclusion rõ ràng để tránh giả lập lịch sử trước acquisition.')
section('methods','## Phương pháp và kiểm soát tái lập',
    'Giữ nguyên raw strings; xác minh layout 31/35 cột, key uniqueness, anti-join, khoảng tháng và reconciliation accepted + rejected = input. SQL đếm loan-level riêng với repeated monthly states. Lưu SHA256 của ZIP, staging và code; tạo tập spot-check xếp hạng giả ngẫu nhiên seed 20260910 cộng edge cases. File trajectory chứa ID chỉ nằm private. Notebook chạy lại SQL từ staging, không đọc số báo cáo như chân lý.')
section('limits','## Giới hạn chưa được đóng',
    'Độ tin cậy cao cho số đếm kỹ thuật, chưa đánh giá uncertainty dự báo vì chưa fit model. Latest-release retrospective data không chứng minh strict point-in-time availability. Chưa kiểm tra đầy đủ dấu/công thức và maturity loss, censoring/competing events, field-specific sentinels, hay quyền công bố derived outputs. Không có applicant/reject population hoặc treatment assignment; không suy ra approval rate thật hay causal uplift.')
section('next','## Tiếp theo: khóa cohort trước khi mở model',
    'Tiếp tục B03/B04 với canonical field maps và attrition theo observation entry/HARP; kiểm tra chi tiết 7 loss-missing cases. Mở thêm acquisition samples theo plan: 2006–2011 cho candidate train history, 2014 calibration, 2016 validation, 2018 final OOT. Đây là candidate vintages, chưa phải khóa split; phải dùng ngày thực tế và label maturity để tránh overlap/leakage. Không train/tune trên final OOT trước khi freeze protocol.')
section('questions','## Câu hỏi còn quyết định phạm vi',
    'Sau khi loại late-entry và xử lý competing exits, số D3 trong horizon 12m còn bao nhiêu? Các vintage bổ sung có đủ sự kiện trong từng split không? Loss panel đã trưởng thành và có công thức đối chiếu đủ không? Chỉ khi có bằng chứng mới quyết định model, không tăng scope bằng placeholder.')
sources=[{'id':'ingestion','label':'Annual sample 2012 initial integrity profile',
    'path':'d3167b604110-30526467/result.json'},
    {'id':'spike','label':'Annual sample 2012 event and coverage diagnostics',
     'path':'spike-b451ac1c907c/diagnostics.json','query':{
      'engine':'DuckDB','language':'sql','tables_used':['performance'],
      'sql':"""SELECT SUBSTR(period,1,4) AS calendar_year,
 COUNT(*) AS monthly_rows,
 COUNT(DISTINCT loan_id) AS observed_loans,
 COUNT(*) FILTER (
   WHERE TRY_CAST(delinquency AS INTEGER) BETWEEN 3 AND 99
 ) AS d3_state_rows,
 COUNT(*) FILTER (WHERE TRIM(actual_loss)<>'') AS populated_loss_rows
FROM performance GROUP BY ALL ORDER BY 1""",
      'description':'Annual coverage from sample_perf_2012.txt staging; other diagnostics in crsl.spike and profile_events.sql.',
      'filters':['2012 annual acquisition sample; full available monthly history'],
      'metric_definitions':{'observed_loans':'Distinct loan_id with at least one record in calendar year; not new originations or an at-risk denominator.'}}}]
artifact={'surface':'report','manifest':{'version':1,'surface':'report','title':title,
    'blocks':blocks,'sources':sources,'charts':[{'id':'coverage','type':'line',
      'title':'Khoản vay được quan sát theo năm','description':'Mẫu acquisition 2012; 2026 chỉ đến tháng 3. Đơn vị: khoản vay.',
      'showDescription':True,'dataset':'annual','sourceId':'spike',
      'encodings':{'x':{'field':'calendar_year','type':'ordinal','label':'Năm quan sát'},
                   'y':{'field':'observed_loans','type':'quantitative','label':'Khoản vay','format':'number'}},
      'valueFormat':'number'}]},
    'snapshot':{'version':1,'status':'ready','generatedAt':utc_now(),'datasets':{'annual':data['annual_support']}},
    'sources':sources}
(spike/'artifact.json').write_text(json.dumps(artifact,ensure_ascii=False,indent=2),encoding='utf-8')
print(spike/'artifact.json')
