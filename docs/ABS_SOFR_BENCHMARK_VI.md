# P5 — SOFR nguồn và đối chiếu lãi A-2b

Ngày cập nhật: 11/10/2026. Bổ sung vào P5.05/P5.10; chưa đóng full contractual waterfall hoặc structured valuation.

## Dữ liệu vừa tải bằng HTTP/API

Source `sofr-source-a076d14b0327`, thư mục `data/private/reference-rates`:

- 443 bản ghi SOFRAI từ API New York Fed, effective dates 02/01/2025–09/10/2026. Mỗi bản ghi có SOFR averages 30/90/180 ngày và index; module này dùng average30day.
- Lịch SIFMA U.S. năm 2025 trong archive và năm 2026 trong trang current.
- Trang phương pháp SOFR averages/index và thông báo New York Fed về Good Friday 2026.
- Tổng 5 file, 925.844 bytes; receipt có URL, thời điểm tải, HTTP status, SHA và byte size. Không dùng cookies hoặc phiên đăng nhập.

[New York Fed API](https://markets.newyorkfed.org/api/rates/secured/sofrai/search.json?startDate=2025-01-01&endDate=2026-10-11), [SIFMA archive](https://www.sifma.org/resources/guides-playbooks/us-holiday-archive), [SIFMA current](https://www.sifma.org/resources/general/holiday-schedule).

Receipt hash được pin; API từ chối source/receipt bị sửa. Saved source hiện tại không chứng minh dữ liệu được công bố tại một thời điểm trong quá khứ.

## Quy tắc hợp đồng và phép tính

WOART 2025-A prospectus PDF90–91 đã extract và visual-review; source SHA `dc34695537492fd7f452e3dd735d4938e76eedde87f441e127e94875e708e653`.

1. A-2b dùng compounded average SOFR tenor 30 ngày, khác overnight SOFR và term SOFR.
2. Adjustment date là ngày làm việc chứng khoán Chính phủ Mỹ thứ hai trước ngày bắt đầu kỳ lãi, reference time 15:00 New York.
3. Loại thứ Bảy, Chủ nhật và ngày SIFMA khuyến nghị đóng toàn bộ. Early close vẫn là ngày làm việc. Good Friday 2025 full close; 2026 early close.
4. Nếu average không xuất hiện, điều khoản cho phép giá trị công bố ở ngày làm việc hợp lệ gần nhất trước đó. Code chỉ xử lý fallback khi fixing không có trong nguồn; không lấy giá trị tương lai. Long-gap unsupported bị từ chối.
5. Coupon = max(0, SOFR fraction + 0,0033). Làm tròn tỷ lệ theo precision hợp đồng; base interest = beginning balance × coupon × actual days/360, HALF_UP đến cent.

Calendar parser phân biệt U.S. với U.K./Japan và full với early closes. Có 12 full-close dates năm 2025, 11 năm 2026. Historical unscheduled notices và administrator conforming changes chưa được review đầy đủ.

## Kết quả đối chiếu 20 kỳ

| Phép so | Khớp raw exact | Khớp với tolerance binary nguồn |
|---|---:|---:|
| Reported SOFR so với administrator average | 19/20 | 20/20 |
| Reported coupon so với average + spread/floor | 15/20 | 20/20 |
| Reported interest due so với independent base interest | 20/20 đến cent | 20/20 |

Sai lệch raw rate/coupon còn lại là 4–5×10⁻¹⁸ fraction của XLS numeric caches. Giữ raw values/deltas; tolerance 10⁻¹⁵ fraction được khai báo, nhỏ hơn nhiều precision hợp đồng 10⁻⁷ fraction. Không thay raw values hoặc đổi tolerance để bỏ qua sai lệch kinh tế. 20 kỳ không dùng fallback.

Kỳ đầu: accrual start29/01/2025, counted business dates28/01 và27/01, fixing27/01; average4,33693%, coupon4,66693%; principal110.000.000USD và20 actual days → base interest285.201,28USD.

## App và export

P5 ABS có tab **SOFR nguồn**, dùng chung collection-period selector. Hiển thị accrual/fixing/administrator dates, official/reported SOFR, coupon, interest, exact deltas, source workbook/sheet/row/column, nguồn lịch và phương pháp, PDF pages và limitations.

API `/api/abs-benchmark?view_id=...` trả toàn bộ20 kỳ; thêm `period=YYYY-MM-DD` để chọn kỳ. `/api/abs-benchmark-report` xuất private JSON. Phải dùng verified ABS view; unknown periods/extra filters bị từ chối. Nguồn unavailable không tạo fallback results trong UI.

Existing ABS source/canonical/terms/waterfall/view artifacts không bị rebuild hoặc đổi qualification. Không fit model, không truy cập lại retail final-test predictors.

## Bằng chứng kiểm tra

- `abs-benchmark-tests-20261011.xml`:40 tests PASS gồm module mới và ABS contract/view regression. Có kiểm tra percent/fraction, duplicate/wrong-series/nonfinite rates, full/early-close, missing-rate fallback/future exclusion, source mutation, raw binary differences và material mismatch.
- `abs-benchmark-audit-a9d88282311d`:20 kỳ PASS. Audit không import benchmark module; đếm ngày từ reviewed calendar list độc lập, đọc JSON/Parquet gốc và tính interest bằng Fraction với cent rounding riêng.
- `abs-benchmark-qa-22780656071d`:6 nhóm PASS: API20kỳ, selected UI/JSON parity, period switch, deep-link/mobile, outage/recovery, no browser errors/frozen holdout ledger unchanged.
- `abs-benchmark-source-review-20261011`:PDF90/91 rendered và đã xem.

## Những điều vẫn chưa được chứng minh

Khớp current administrator values không chứng minh bản công bố lúc15:00 mỗi historical fixing, revision lịch sử, absence of administrator conforming changes hoặc absence of unscheduled closures. Không qualify full legal state, benchmark-replacement chain, unpaid carryover, forward collateral cashflows hoặc valuation. P5.05 tiếp tục Có điều kiện, P5.10 Một phần; tỷ lệ50capabilities chưa tăng từ bổ sung này.
