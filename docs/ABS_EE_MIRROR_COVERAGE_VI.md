# ABS-EE WOART 2025-A — acquisition và coverage bản mirror

ABS-EE definition checkpoint: acquired official GovInfo2025CFR PDF/XML2files403351bytes. P5 field dictionary covers62observed mirror columns with proposed Item3correspondence,coverage and private export. Independent62PDF/XML definitions/coverage PASS,backend8PASS,browser5groups/coverage regression4groupsPASS. SEC specification ZIPHTTP403; XSD/original-filing XML/EX103/current-rule/labels/fidelity/model gates remain false. Counts unchanged. See ABS_EE_FIELD_DEFINITIONS_VI.md.

Checkpoint 11/10/2026. Tab **ABS-EE coverage** của P5 đọc profile aggregate đã pin SHA, không gửi asset identifiers ra browser. API `/api/absee-profile`, export `/api/absee-profile-report`.

## Nguồn đã lấy

- Metadata chính thức: `https://data.sec.gov/submissions/CIK0002046523.json`, identity World Omni Auto Receivables Trust 2025-A; recent filings có22 ABS-EE entries.
- Parquet mirror: `https://huggingface.co/datasets/DenyTranDFW/World_Omni_Auto_Receivables_Trust_2025_A_2046523`; revision `071b897ec737ae05bd5e17be707f46e3d68b6a7c`. Đã lưu API repo, README và11files monthly. Hai files cut-off/hypothetical bị loại khỏi selected monthly set.
- Source `data/private/structured/absee-mirror-f97dcd09916d`:14files/28542411bytes, receipt SHA `482aff4e853f68cdb718c6251fd4355eeea7d96c1cc32bfb8a4449ab443b49f1`. Có nguyên bản Parquet; không có XML gốc.
- Archive index chính thức của accession mới nhất `0001104659-26-111552` thử qua HTTP trả403. Không dùng xác thực hoặc lách restriction. Chưa tải EX102/EX103 từSEC.

## Coverage thực đọc

| Report date | Asset-period rows | Columns | Null/whitespace cells |
|---|---:|---:|---:|
|2025-01-31|45263|57|1045|
|2025-02-28|45263|57|1870|
|2025-03-31|45263|59|91134|
|2025-04-30|45263|61|182907|
|2025-05-31|45263|59|93890|
|2025-06-30|45263|57|6462|
|2025-07-31|45263|59|97591|
|2025-08-31|45263|62|232491|
|2026-02-28|44720|61|190952|
|2026-05-31|41640|57|16523|
|2026-07-31|39755|62|213560|

Tổng488219 asset-period rows; **không phải488219 khoản vay duy nhất**. Tổng28885083 ô ở schema hiện diện,1128425 null/whitespace. Không duplicate composite `(assetTypeNumber,assetNumber)` trong từng kỳ; required-money/date parsing không có invalid records. Chưa xác minh sentinel/semantics của mọi field.

7adjacent month links trongJan–Aug2025,45263matched keys mỗi cặp. Sau đó cómonth distances6/3/2; giữgaps, không suy monthly transition qua những khoảng này. Previous-only543/3080/1885 keys chưa có causal exit labels.

Official report dates chưa có selected mirror:2024-12-31 (cutoff files deliberately excluded),2025-09-30/10-31/11-30/12-31,2026-01-31/03-31/04-30/06-30/08-31. Đây là so recent metadata, không khẳng định đã crawl hết lịch sử SEC.

## Trường dữ liệu và giới hạn

Có origination/loan amount/term/rate, borrower score/verification/PTI/geography, vehicle, balances, scheduled/actual collections, status, recoveries/repossession fields. Schema biến đổi: zeroBalanceCode/date, modificationTypeCode/paymentExtendedNumber vàchargedoffPrincipalAmount chỉ hiện ở một sốfiles. **Absent column không bằng zero**; null optional fields không tự được coi là source defect.

Profile giữ raw `assetTypeNumber`/`currentDelinquencyStatus` distributions. Không tự gọi status làdefault, không tự gánUSD cho raw amount fields khi chưa đọc official schema. Các money sums chỉ là phép cộng chuỗi số trongmirror. Model ready/source fidelity/raw XML flags đều false.

README khaiGPL nhưng thống kê “Parquet files:1” không khớp fileinventory. Metadata/README của mirror không được dùng thay source profiling hay xác nhận redistribution rights. Data giữprivate, public release chưa approved.

## Evidence

- Profile: `artifacts/private/absee-profile-63397e5ebbc6/profile.json`, SHA `94e1e9d5742d04e20cd6203da0d11b7dafe7f18ba7ef517de5588d8c68c13ddd`; receipt structural checks PASS.
- Independent Arrow columnar audit: `artifacts/private/absee-profile-audit-00668467a11d/receipt.json`,488219rows/651missingness checks/99exact money sums PASS. Chỉ đối chiếu localParquet projection, không chứng minh XML fidelity.
- Tests: `artifacts/private/absee-profile-tests-20261011.xml`,5PASS: exact/zero/missing/nonfinite/date/duplicate/sign/scope/pinned-profile mutation/gaps.
- Browser: `artifacts/private/absee-profile-qa-eee5f9a1c959/receipt.json`,4groupsPASS: API/JSON/qualification flags/schema parity, reload/mobile, outage/recovery, noerrors/frozenledger unchanged. Desktop/mobile đã xem.
- Independent audit lần đầu thiếu large-string separator kernel; đã sửa trước khi có PASS receipt, không dùng lần lỗi làm evidence.

## Việc cần làm để đóng capability

1. Lấy XML/schema/EX103 chính thức với quyền truy cập hợp lệ; đối soát original rows/fields/extraction completeness với mirror.
2. Định nghĩa units/status/zero-balance/charge-off semantics; persistent identity và terminal event retention.
3. Bổ sung missing monthly files và chứng minh coverage/availability theo thời gian.
4. Đối soát source pool sums vớiservicer reports theo pool inclusion/cutoff/adjustment đúng.
5. Sau đó mới định nghĩa targets/censoring/temporal splits, qualify forecasts/recovery models vàcashflow integration.

P5.02/P5.03/P5.10 chưa complete. Acquisition mới là tiến bộ về nguồn và coverage; không tăng completion label toàn capability, không thay qualified loan-level panel bằng mirror chưa kiểm chứng.
