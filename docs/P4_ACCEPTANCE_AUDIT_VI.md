# P4 — rà soát acceptance và sửa Excel precision

Checkpoint 11/10/2026. Phạm vi P4.01/P4.02/P4.06, theo nguyên văn requirements trong `COMPLETION_REQUIREMENTS_50.json`. Không đóng phần mở rộng của plan hoặc chứng nhận portfolio ngân hàng thực.

## Lỗi đã sửa

Ô numeric XLSX `100000000000000.000000000000001` có30chữ số có nghĩa nhưng trước đây được chấp nhận: `Decimal.normalize()` dùng precision của ambient context và có thể làm tròn trước khi đếm digits. Adapter nay đếm exact constructor digits, chỉ bỏ trailing zeros; không dùng arithmetic normalization để đánh giá precision.

Giữ các numeric cells có≤15 significant digits, integer đến24positions/decimal scale≤18 theo contract hiện có; số/ID cần nhiều precision phải nhập text. Zero và trailing zeros hợp lệ được giữ nguyên. Không claim loại bỏ precision loss đã xảy ra trong Excel trước khi lưu file.

POST XLSX trước đây giấu mọi ValueError thành “Invalid research finding”. Route nay hiển thị allowlist fixed messages cho precision/formulas/file-size/row-bound/template sheets, còn lỗi khác trả thông báo Excel chung. Không phản chiếu arbitrary exception text hay private paths.

## Bằng chứng theo từng điều kiện

| ID | Điều kiện trong requirements | Bằng chứng hiện có | Phần chưa đóng |
|---|---|---|---|
|P4.01|≤20MB/50000positions; formula/unsafe precision reject; missing risk không thànhzero|62backend tests gồm exact50000/50001row gate, >20MB, precision boundaries/context, formula-cache reject; browser POST reject và validEXAMPLE intake/private inventory|Mapping theo source/facility/domain templates; full institution intake/ownership qualification; nativeExcel execution chưatest|
|P4.02|Không cộngcross-currency; source observations không làborrower concentration; reportedamount khácEAD|MixedUSD/VND test+browserexample; actual9698observations sourceoverview/concentration/bucket→reviewdraft; 66independent import checks; exactprivateJSON parity|Obligor/group identity, explicitFXpolicy nếuglobaltotals, institution positions vàreviewgovernance|
|P4.06|Missing record không làdefault/payoff; currency migration không làFXP&L; residual rõ|Same-source actual2026Feb→Marbridge; 500independentFractionchecks; syntheticcurrency migration test; browser/export parity vàsource caveats|Disposition reasons, source linkage/borrower identity; actualcashflow attribution khôngqualified|

**Chỉ acceptance subscope có evidence mới.** `full_completion_proven` giữfalse; không bỏ các next-step requirements để tăng tỷ lệ. Checkpoint counts vẫn21/9/12/8.

## Kết quả nguồn thực

Import `exposure-import-57b88e00bedb`:9698observations,141zerobalances,USD915208989.12; riskinputs thiếu =>ELnull. Đây làsource observations, không làowned portfolio.

Bridge `exposure-movement-dbd1ecad612e`:2026-02→2026-03,9698continuing/106opening-only/0closing-only,openingUSD928246113.34→closingUSD915208989.12,continuingchangeUSD-13037124.22,residual0. Opening-only rows trongpair córemovedamount0; biến mất khôngchứngminhpayoff/default.

ValidExcelQA dùngfilemẫu3EXAMPLE positions, tạo `exposure-import-c171213546b1`:USD250000 vàVND1000000; mộtUSDzero; ELnull. Không dùngEXAMPLE để chứngnhận dữliệuportfoliothật.

## Evidence trên đĩa

- `artifacts/private/p4-intake-movement-tests-20261011.xml`:62PASS.
- `artifacts/private/exposure-audit-42ac59e74266/audit-complete.json`:66independentchecksPASS.
- `artifacts/private/exposure-movement-audit-5bc7404496f3/audit-complete.json`:500independentchecksPASS.
- `artifacts/private/p4-acceptance-qa-435791cbf240/receipt.json`:5browsergroupsPASS,source/bucket→draft/export,unsafePOSTreject,validupload/mobile; frozenholdoutledger unchanged. Desktop/mobile screenshots đãxem.
- QA trước thiếurepo root importpath; lần tiếp dùngtimeout ngắn ởcoldReview; lần sau phát hiệngenericPOSTerror. Không dùngcác lần chưaPASS làmnghiệmthu. HeadlessQA cuối dùngTEMP/TMP trênD vàdaemonHTTPthreads để khôngkẹt shutdown sau assertionfailure.

Không chạy/recalculate trongMicrosoftExcel native. Không refit hoặc tune frozenmodels; coldReview chỉ xácminh/replay nghiêncứu đãlưu.
