# P3.03 — nghiệm thu financial ratio analysis

Đã đóng original P3.03: filing-specific ratio cards, annual levels/deltas, numerator-first bridge với exact inputs/counterfactual/effects/residual, baseline statements, explicit interest-coverage candidate evidence, private JSON và Analysis/Facts Excel. Không thay scope thành issuer PD, EBIT ICR, DSCR hoặc covenant compliance.

## Source và runtime

- 268 ratio cells của67statements:201supported/67unavailable;48trendHTTPscopes và360 supported bridges đối soát Decimal60/Fraction với source fields.
- 60expense-concept/cutoff/window coverage scopes:1545field checks801candidate entries618ratio checks. Cash interest paid/net giữ riêng, không thay expense; missing/ambiguous giữ null, numerator âm không clip.
- Actual trends/coverage browser exports,reload,mobile,outage/recovery PASS. Gaps/concept changes/missing/ambiguous và nonpositive denominators có explicit gates; source-original/amendment/baseline selection đã đối chiếu.

Chi tiết:[P3_RATIO_TREND_AUDIT_VI.md](P3_RATIO_TREND_AUDIT_VI.md).

## Excel

- 36issuer/window/expense scopes,downloaded XLSX SHA khớp immutable server JSON capture; formula/cache/missing-source guard checks PASS.
- Full Facts metadata/candidate completeness,dates/units/accession/source URLs/source-method digests và six-metric summary checks PASS cho cả36workbooks. Receipt:`sec-excel-metadata-audit-74186cf6c79d`.
- Native Excel16 CalculateFullRebuild:73656populatedcells và14040formulas trên36read-only disposable copies PASS; các normalization failures trước được giữ và giải thích trong checkpoint.
- Native input changes:216cases/432reads trên36copies. Blank/text numerator,zero/negative denominator giữUnavailable;zero numerator cho0;negative numerator được giữ. Linked calculation và summary cùng phản ứng đúng;source/copy bytes không lưu thay đổi. Receipt:`native-excel-qa-sec-perturb-9c8189a3d577`.
- Actual UI workbook download,outage recovery và mobile PASS:`sec-workbook-qa-bf5f33ced34f`;43backendtestsPASS.
- Đã xem12native Excel PDF renders:summary,Facts vàcalculation ranges cho bốnissuer. CIK đủleadingzeros,exact text khôngscientific notation trongnative Excel. Artifact Tool preview có lỗi hiển thịnumeric-looking strings ngay cảdirect builder; không dùngpreview đó làm bằng chứngsource mất dữ liệu. Native Text/PDF vàsaved XML giữ đúng giá trị.

PDF exports chỉ đổi PageSetup trongmemory rồiClose(false);original workbook hashes giữ nguyên. Preview copies/PDF/PNG là QA intermediates,không phải thêmmodel hoặc thayactuals.

Chi tiết:[P3_SEC_EXCEL_SCOPE_AUDIT_VI.md](P3_SEC_EXCEL_SCOPE_AUDIT_VI.md). Native visual receipt:`artifacts/private/sec-native-render-20261015/visual-review.json`.

## Giới hạn giữ nguyên

Current SEC API không chứng minh historical publication-byte availability. Annual comparability screen không là universal accounting equivalence;custom/dimensional facts còn thiếu. Operating-income/selected-expense vàreported-OCF/selected-expense làproxies. Excel dùngfloating point và giữ exact source text;edits cần recheck scope/gates,không ghi ngược dữ liệu app.

P3.06memo,P3.07covenants vàP3.08debt schedules còn riêng. Tổng suite sau recorder:20/50=40%;goal100% chưa đạt.
