# FHFA NMDB — New originations và Outstanding mortgage aggregates

**Checkpoint:** 16/10/2026. Đây là public aggregate statistics riêng của FHFA,
không phải loan-level performance và không làm tăng số Freddie vintage hay tỷ lệ
hoàn thành D01.

## Dữ liệu đã thu nhận

Tải trực tiếp từ catalog FHFA release **30/09/2026**, không dùng credentials hay
cookies:

| File | Grain / kỳ | Rows | Field | Kết quả kiểm tra |
|---|---|---:|---:|---|
| New Residential Mortgage Statistics — All Geographic Areas, Annual | Geography × market × series × year; 1998–2025 | 3.038.100 | 14 | 3.038.100 khóa duy nhất; 60 series; 26 market labels; 4.980 dòng suppressed; 135.084 VALUE1 và 337.292 VALUE2 trống/`.` |
| Outstanding Residential Mortgage Statistics — All Geographic Areas, Quarterly | Geography × market × series × quarter; 2013Q1–2026Q2 | 535.464 | 14 | 535.464 khóa duy nhất; **37 series**; 4 market labels; không có dòng suppressed; 57.888 VALUE2 trống/`.` |

Hai file bao phủ National, Rural/Non-Rural, Census Region, Census Division và
State. Tất cả kỳ dự kiến đều có mặt và liên tục; header, member name, ZIP CRC,
row width, numeric values, period fields, suppression flag và khóa aggregate
được kiểm tra. Mỗi khóa là `SOURCE × FREQUENCY × SERIESID × GEOLEVEL × GEOID ×
MARKET × PERIOD`; không có ID khoản vay trong các hàng được phục vụ.

## Ý nghĩa trọng số và đơn vị

**Không được trộn VALUE1 và VALUE2.** FHFA mô tả VALUE1 là thống kê được cân
theo số khoản vay; mỗi khoản trong sample đại diện cho 20 khoản thực. Với
originations, VALUE2 được cân theo origination loan amount; với outstanding,
VALUE2 được cân theo unpaid principal balance (UPB) ở cuối quý. Chỉ dùng measure
VALUE2 khi trường đó có trong series; ô trống vẫn là unavailable, không phải 0.
Các cell dựa trên dưới ba khoản vay bị suppress.

Một số đơn vị chính: `TOT_ORIG` là nghìn originations; `TOT_LOANAMT` trong bộ
New là triệu USD; `AVE_LOANAMT` là nghìn USD; `TOT_LOANS` trong bộ Outstanding
là nghìn active mortgages; `TOT_UPB` là tỷ USD. Các tỷ lệ phần trăm giữ nguyên
đơn vị percent. Average VantageScore là Version 3.0. Outstanding `AVE_MTMLTV`
là current mark-to-market LTV, không phải LTV tại origination.

## Quan sát minh họa, đúng theo source geography/market/period

Ở **National / USA / All Mortgages / 2025**, FHFA công bố 4.677 nghìn
originations, tổng loan volume $1.749.642 triệu, average loan amount $374 nghìn,
average contract rate 6,3% theo VALUE1 và 6,2% theo VALUE2. Home-purchase share
là 66,4% theo loan count và 67,1% theo origination volume; refinance tương ứng
33,6% và 32,9%. Average back-end DTI là 39,1% theo VALUE1 và 40,4% theo
VALUE2. Đây là mô tả mix phát hành, không phải PD, approval rate hay performance
outcome.

Ở **National / USA / All Mortgages / 2026Q2**, outstanding stock là 51.426
nghìn active mortgages và $12.399,6 tỷ UPB. Average MTM LTV là 45,1% theo
loan-count weighting và 54,2% theo UPB weighting. Average contract rate at
origination là 4,4% / 4,5%; VantageScore 742 / 743, theo VALUE1 / VALUE2. Market
share theo counts là Government 23,6%, Enterprise 56,9%, Other 19,4%; theo UPB
shares là 22,0%, 52,0%, 26,0%. Các số làm tròn theo source; denominator và
weighted estimand phụ thuộc từng series.

## Giới hạn sử dụng

NMDB là sample đại diện 5% của closed-end, first-lien mortgages được báo lên
credit bureau; đây không phải census. FHFA lưu ý investor mortgages và
manufactured-home loans kém đại diện hơn. New originations là cohort flow theo
account-opening date. Outstanding là stock các khoản active cuối quý, bằng kỳ
trước cộng originations mới trừ payoff/termination. Hai aggregate products có
population/snapshot/weighting khác nhau và không được nối thành loan-level panel.
Không dùng dữ liệu này thay cho payment history, default labels, Freddie R2,
calibration hay validation; không forecast hoặc impute.

Raw ZIP, profile và immutable receipts ở private D:
`D:\data\Codex\credit-atlas\data\private\public-context\fhfa-nmdb-composition-b969a703b532\`.
ZIP SHA-256: New annual
`ecc0c10dd6d4d0d73f364e2825329be96c83ca2ad75036f1638dbc69714d1c3e`; Outstanding
quarterly `97654803149dccf3e33aab5a5a746b870feac88c66395e1fffd5ec8ac8e6c1fd`.
Independent current-method audit receipt:
`D:\data\Codex\credit-atlas\data\private\public-context\fhfa-nmdb-composition-reaudit-6861c8916759\receipt.json`.

Acquisition/profile code: [`acquire_fhfa_nmdb_mortgage_statistics.py`](../scripts/acquire_fhfa_nmdb_mortgage_statistics.py).
Focused tests: 3 pass. Re-audit an existing private download:

```powershell
python scripts/acquire_fhfa_nmdb_mortgage_statistics.py `
  --root D:\data\Codex\credit-atlas `
  --source-dir D:\data\Codex\credit-atlas\data\private\public-context\fhfa-nmdb-composition-b969a703b532
```

Official sources: [FHFA NMDB Aggregate Statistics catalog](https://www.fhfa.gov/data/nmdb)
and [Data Dictionary and Technical Notes dated 26/06/2026](https://www.fhfa.gov/document/d/nmdb/nmdb-aggregate-statistics-data-dictionary-technical-notes-2026q1.pdf).

## Mart, API, app và Excel — 17/10/2026

Đã dựng mart canonical trong private workspace tại
`D:\data\Codex\credit-atlas\data\derived\fhfa-nmdb-market-statistics\market-statistics.parquet`.
Mart có 3.573.564 hàng: 3.038.100 New annual và 535.464 Outstanding quarterly.
Receipt mart gắn SHA-256 của hai ZIP, CSV member, source receipt và parquet; đối soát
cho kết quả 4.980 hàng New suppressed, 135.084/337.292 hàng New thiếu VALUE1/VALUE2,
57.888 hàng Outstanding thiếu VALUE2, không có ô số không parse được. VALUE raw
được giữ cả chuỗi nguồn lẫn numeric nullable; không phát sinh forecast hoặc imputation.

**Đính chính:** profile nguồn chứa 37, không phải 38, Outstanding series IDs. Workbook
reference vì vậy có 60 New + 37 Outstanding định nghĩa series. Đếm 38 trong bảng
acquisition cũ là sai.

API code mới cung cấp catalog theo product và report theo geography, market, series,
measure và năm. Workspace P2 có đường dẫn riêng `?view=nmdb`; có biểu đồ theo thời gian,
KPI kỳ mới nhất, delta chỉ giữa hai kỳ liền kề có giá trị, bảng suppression/missing,
và export Excel theo đúng filter. Workbook reference
`apps/excel/templates/CreditAtlas-NMDB-Market-Statistics.xlsx` dùng scope National / USA /
All Mortgages để có thể mở ngay trong Excel: 1.680 annual observations + 1.998 quarterly
observations, latest KPIs, codebook 97 series và quality/lineage. Workbook này không chứa
toàn bộ 3,57 triệu hàng; export theo filter đưa các hàng kỳ đã chọn vào file riêng.

Trọng số được giới hạn theo FHFA Appendix B/C: New `TOT_ORIG`, `TOT_LOANAMT` và
Outstanding `TOT_LOANS`, `PCT_LOANS`, `TOT_UPB`, `PCT_UPB`, `TOT_LOANAMT`, `AVE_PAYMENT`
chỉ dùng VALUE1 theo dictionary. Với series khác, VALUE2 được mô tả rõ là origination
amount weighting (New) hoặc quarter-end UPB weighting (Outstanding). Raw VALUE2 vẫn
được giữ để trace khi FHFA có xuất ô đó, nhưng không hiện như một estimand được chọn cho
series VALUE1-only.

**Trạng thái:** mart đã dựng và reconciled. Ngày 17/10, live API trả đúng product counts,
series counts và 28 năm New / 54 quý Outstanding trong hai query mẫu; endpoint từ chối
VALUE2 cho Outstanding `TOT_UPB`. Hai dynamic workbook exports và workbook tham chiếu đều
tải HTTP 200. Cấu trúc export đã được đối chiếu: chart dùng cột Selected value và nhãn kỳ
dạng text. Browser visual acceptance và mở/tính lại trong Excel desktop chưa làm; N06 vẫn
mở cho hai bước đó. Không thay đổi completion flag 26/50.
