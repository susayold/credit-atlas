# D01 — nghiệm thu export schema 2

Audit trên frozen case `d01-a24484b21a21`, pipeline
`pipeline-307c354f3d74`, ngày 15/10/2026. Kiểm tra lại wrapper schema 2 và
report schema 1 nhúng bên trong, không chỉnh sửa report engine đã pin.

## Kết quả

| Phạm vi | Kết quả |
|---|---|
| Filter scopes | 5: all, Relief, non-Relief + reporting range, reporting-year 2020, unavailable year 1900 |
| Outer wrapper | Exact key set, schema 2, private visibility, release false, target/run/filter context khớp frozen case |
| Embedded aggregate report | Required fields/constants khớp report schema 1; table IDs, grain, pipeline and row arrays present |
| Supplements | Quality, episode follow-up, reporting-year transitions; source-case/pipeline and canonical JSON digests pass |
| Lineage | Case receipt, output hashes and method-source hashes reconcile to selected run |
| Scope behavior | 2020 lọc đúng opening year; 1900 trả empty year rows, giữ lifetime comparator; export lặp cùng filters deterministic |
| Privacy | Quét serialization của whole-sample export bằng đủ 50.000 source IDs: 0 match; không identifier/prediction keys |
| Unsupported uses | `metric=PD12`, `use=ECL`, cash-flow override và run khác bị từ chối |

Receipt: `artifacts/private/d01-export-contract-dc182aeaae7e/receipt.json`;
reproducible audit: `scripts/audit_d01_export_contract.py`. Export là nghiên cứu
mô tả sample. D3 CIF, balance transitions và reported loss không được đổi tên
thành PD, ECL hoặc contractual cash flow.

## Sửa contract endpoint

Trước audit, `ResearchService.report` bỏ qua query keys không nhận diện. Một
consumer gửi `metric=ECL` vì vậy nhận report mặc định, không phải lỗi rõ ràng.
Endpoint giờ whitelist `run`, `segment`, `basis`, `horizon`, `from`, `to` và
`transition_year`, đồng thời kiểm tra `run` phải đúng case. Parameter khác bị
từ chối; kiểm tra nằm trong `tests/test_frozen_service.py`.

## Giới hạn

Nghiệm thu covers aggregate descriptive schema/current 2012 report. Chưa có
qualified model output để kiểm chứng model score export. Đây không phải
public-release, licensing, lending-decision hoặc ECL approval.
