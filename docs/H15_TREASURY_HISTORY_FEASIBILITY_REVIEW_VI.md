# H.15 cho phần lịch sử Treasury trước 1990 — đánh giá khả thi

Ngày kiểm tra: **18/10/2026**. Phạm vi: xem H.15 Data Download Program có thể thay các quan sát Treasury constant-maturity trước 1990 hiện lấy từ FRED trong P5 hay không. Đây là kiểm tra khả thi bằng snapshot, chưa phải receipt acquisition production, chưa thay route P5 và không phải xác nhận feature/model.

## Kết luận

H.15 là ứng viên phù hợp để thay FRED làm **kênh phân phối/bản lưu lịch sử chính thức của Board** cho phần Treasury trước 1990. H.15 ghi rõ các chuỗi Treasury constant maturity có nguồn là U.S. Treasury; do đó cần mô tả attribution là `Federal Reserve Board H.15 archive; underlying source: U.S. Treasury`, không gọi đây là một phép đo độc lập hay một phương pháp yield curve thứ hai. Treasury direct vẫn là nguồn chính từ 1990-01-02 trở đi.

Snapshot H.15 khớp Decimal tuyệt đối với FRED trên mọi observation cùng ngày mà cả hai cùng có giá trị, không có mismatch và **không có thêm ngày known trước 1990** so với snapshot FRED hiện có. Vì vậy H.15 không làm tăng coverage dữ liệu. Nó chỉ là ứng viên thay FRED bằng một archive/attribution path khác nếu quyền sử dụng hoặc yêu cầu provenance khiến việc đó cần thiết; chưa đủ để đổi app cho đến khi acquisition parser, receipt/hash verification, rights/attribution metadata, P5 case rebuild và browser/export acceptance cùng pass.

## Nguồn và định nghĩa

Federal Reserve Board H.15 cung cấp daily series qua gói CSV Treasury Constant Maturities gồm 11 tenor. Các series cần cho P5 là:

| H.15 series ID | Mô tả | Ngày bắt đầu có quan sát |
|---|---|---|
| `H15/H15/RIFLGFCY02_N.B` | Treasury 2-year constant maturity, investment basis | 1976-06-01 |
| `H15/H15/RIFLGFCY10_N.B` | Treasury 10-year constant maturity, investment basis | 1962-01-02 |
| `H15/H15/RIFLGFCY30_N.B` | Treasury 30-year constant maturity, investment basis | 1977-02-15 |

H.15 nói các giá trị là yields trên Treasury actively traded issues, adjusted to constant maturities; footnote ghi `Source: U.S. Treasury`. H.15 publication là daily release; ngày nghỉ thị trường có thể xuất hiện như ngày không có observation hoặc được đánh dấu `ND`, và phải được giữ theo nghĩa nguồn. [H.15 current release](https://www.federalreserve.gov/releases/h15/), [H.15 package metadata](https://www.federalreserve.gov/datadownload/Review.aspx?filetype=csv&from=&label=include&lastObs=&layout=seriescolumn&rel=H15&series=bf17364827e38702b42a58cf8eaa3f78&to=&type=package).

Board thông báo gỡ chức năng Build Your Package trong tuần **09/11/2026** để chuẩn bị cho việc nghỉ DDP; người dùng được chỉ sang FRED hoặc XML của release. Việc thay đổi này không xóa H.15 historical role nhưng khiến downloader production không nên phụ thuộc riêng vào BYP/CSV package builder. Cần kiểm tra release XML/ZIP như fallback hoặc đóng source version, parser contract và retrieval receipt trước khi dựa vào refresh lâu dài. [Board DDP announcement](https://www.federalreserve.gov/releases/h15/), [H.15 XML download](https://www.federalreserve.gov/releases/h15/data/FRB_h15_xml.zip).

## Snapshot feasibility và đối chiếu

Tải gói H.15 CSV trực tiếp từ Federal Reserve Board ngày 18/10/2026 cho phép xác nhận HTTP 200, content type `text/csv`, kích thước **1,008,476 bytes**, **16,903 ngày** từ 1962-01-02 đến 2026-10-15. Hash của file feasibility private trên D: là `a40e6f897dc6da5f6ff37a748873b5f29f00745b2b876c22a6f13fe719d47fb2`. File này chưa có acquisition receipt production và chưa được đưa vào P5.

| Chuỗi | H.15 known trước 1990 | FRED known trước 1990 | Common-known / exact Decimal | Mismatch | H.15-only known dates |
|---|---:|---:|---:|---:|---:|
| 2Y | 3,387 (1976-06-01–1989-12-29) | 3,387 | 3,387/3,387 | 0 | 0 |
| 10Y | 6,979 (1962-01-02–1989-12-29) | 6,979 | 6,979/6,979 | 0 | 0 |
| 30Y | 3,209 (1977-02-15–1989-12-29) | 3,209 | 3,209/3,209 | 0 | 0 |

Trên phần ngày chung có Treasury direct kể từ 1990-01-02, H.15 khớp **9,203/9,203** giá trị 2Y, **9,203/9,203** giá trị 10Y và **8,209/8,209** giá trị 30Y, không mismatch. H.15 package hiện kết thúc 2026-10-15, trong khi Treasury direct snapshot hiện tại đến 2026-10-16; vì vậy H.15 không thay thế tranche Treasury mới nhất.

Đây là snapshot value parity, không xác nhận equality của publication vintage/revision timing hay quyền sử dụng của FRED. Parser phải coi `ND`, blank và ngày không có row là trạng thái missing khác nhau, không chuyển chúng thành zero; ví dụ H.15 đánh dấu 1990-01-01 và 2002-02-18 là `ND`. 30Y discontinuation 18/02/2002–08/02/2006 vẫn là missing theo H.15/Treasury; không dùng hệ số 20Y và không nội suy.

## Rights, attribution và quyết định phát hành

Federal Reserve Board disclaimer nói thông tin trên website Board nhìn chung thuộc public domain, có thể sao chép/phân phối nếu không có chỉ dấu khác và cần citation Board. Cùng lúc, H.15 đánh dấu underlying source là Treasury. Vì thế quyết định vận hành ở tranche này là:

- Có thể tiếp tục ingestion **private/internal** từ Board H.15, ghi rõ Board là host/distributor và U.S. Treasury là underlying source.
- Raw CSV, normalized panel, receipt và output tiếp tục nằm ở private D:; chưa đưa raw numbers vào GitHub/public app chỉ dựa trên snapshot parity.
- Public code có thể ghi endpoint/series IDs/schema/hash metadata, nhưng không kèm raw file. Bất kỳ public redistribution/third-party API use nào vẫn cần ghi rõ use-case decision và attribution review theo cả Board và Treasury.
- Không coi H.15 là independent replication của Treasury. Giá trị căn bản được Treasury tạo; H.15 là historical access path và comparator chính thức.

Nguồn rights chính: [Federal Reserve Board disclaimer](https://www.federalreserve.gov/disclaimer.htm), [H.15 current release and Treasury source footnote](https://www.federalreserve.gov/releases/h15/). Đây là kết luận sử dụng thận trọng cho dự án, không phải ý kiến pháp lý.

## Tích hợp cần làm để đóng tranche

1. Chỉ tiến hành receipt-bound historical migration nếu rights/use review xác định có lợi ích rõ để rời FRED; H.15 không tăng coverage dữ liệu.
2. Nếu được chọn, viết downloader giới hạn host `www.federalreserve.gov`, URL/package, content type, kích thước, schema, series IDs, ngày và số decimal; raw payload giữ private.
3. Tạo receipt gồm retrieval timestamp, URL, release date, exact SHA-256, script hash, normalized hash, row counts và missing summary. Parser phải phân biệt blank, `ND` và ngày không có row; không tự quy tất cả về zero.
4. Parity acceptance: H.15/FRED pre-1990 common-known values **0 mismatch**; H.15/Treasury direct common-known **0 mismatch**; không có H.15-only known dates trong snapshot pre-1990; kiểm discontinued 30Y window.
5. Nếu route được đổi, dựng P5 private case/view mới, kiểm case receipt và row-level `source_id`/hash, API-vs-JSON, date filters, UI attribution, source-native missingness và Excel/CSV/JSON export; kiểm browser desktop/mobile và không console errors.
6. Giữ mọi FRED receipt cũ làm comparator/audit trail, không xóa hoặc sửa lại lịch sử. Kiểm tra DDP→XML fallback trước khi dựa vào refresh lâu dài.

Không fit, backtest hay tạo macro feature trong tranche này. Treasury/H.15 par yields vẫn chỉ là descriptive market context; snapshot không có event-time vintage.
