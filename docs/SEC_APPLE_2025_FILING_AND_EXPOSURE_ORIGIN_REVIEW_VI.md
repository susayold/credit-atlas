# Rà soát nguồn Apple 2025 và nguồn gốc exposure của Freddie cohort

Ngày rà soát: **17/10/2026**. Đây là review provenance cho N02/N03; raw issuer filing artifacts, position rows, full hashes và private receipts vẫn nằm ngoài public repo.

## Apple FY2025 10-K — filing identity đã bind, bản sao issuer chưa byte-match SEC

Ba local artifacts trong private workspace đã được kiểm tra bằng receipt: file tồn tại, kích thước và SHA-256 tính lại khớp receipt, HTTP status ghi nhận là 200. Các receipts quy chúng về Apple Investor Relations và issuer filing ID `18880179`. SEC EDGAR xác nhận canonical filing là Apple Inc. Form 10-K, CIK `0000320193`, accession `0000320193-25-000079`, filed `2025-10-31`, reporting period ended `2025-09-27`.

| Source record | Issuer-hosted object | Kích thước local | SHA-256 prefix | Trạng thái |
|---|---|---:|---|---|
| `apple-2025-10k-issuer-html` | FY2025 Form 10-K HTML | 1,452,459 bytes | `eb08113db1fa` | Local receipt verified; one filing |
| `apple-2025-xbrl-issuer-zip` | Inline XBRL ZIP | 249,062 bytes | `8eda40781011` | Local receipt verified; 1 instance, 155 profiled facts |
| `apple-2025-inline-xbrl-issuer-html` | Issuer-hosted Inline XBRL HTML rendering | 2,673,061 bytes | `da9b4a960f00` | Local receipt verified; same filing ID, not a new filing |

The official [SEC filing index](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/0000320193-25-000079-index.html) lists the EDGAR 10-K as `aapl-20250927.htm` (1,520,208 bytes) and the SEC XBRL ZIP as 399,390 bytes. Both sizes differ from the issuer-hosted local copies, so this review does **not** claim byte parity or that the local XBRL ZIP equals the EDGAR ZIP. The index is used to verify the accession, form and period; the local hashes bind only the exact issuer-hosted artifacts. The [SEC-hosted 10-K](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm) provides the canonical filed report.

The source register now contains three artifact records under one parent group and one SEC accession. They do not represent three releases, independent observations, or a complete Apple filing panel. The existing local debt bridge and XBRL dimensional audit support limited filing-specific analysis only. They do not establish individual debt-series balances, actual payments, a complete coupon/payment calendar, debt service, EAD, DSCR or covenant status. N16 still requires an instrument/facility-level executed term and payment evidence chain. See [Apple XBRL debt dimensions](APPLE_XBRL_DEBT_DIMENSIONS_VI.md) and [issuer financials workflow](SEC_ISSUER_FINANCIALS_WORKFLOW.md).

Rights status remains scoped: the filing is public in EDGAR, but local raw copies are private, the register does not approve redistribution, and software/output reuse still requires attribution, fair-access and applicable third-party review. The SEC accession binding does not itself qualify the debt-service outputs or close N16.

## Exposure imports — Freddie sample UPB, not an owned credit portfolio

The February and March 2026 imports have local `import-complete.json` receipts. For each import, all four output hashes match; all 39/39 upstream lineage hashes in `metadata.json` also match local files. Each import names `Freddie-Mac-2012-annual-sample` as its source namespace and says its amounts are raw UPB loan-month observations, not owned positions, EAD or PD.

The February input has 9,804 rows and the March input has 9,698. Every row is USD, in major units, with `DIRECT_ASSET` representation and a reported amount. PD, LGD and EAD fields are blank throughout. The source sample's cohort key is not a securitization pool; the imports contain no evidence that these loans belong to a lender's owned book or share borrower/group identities suitable for obligor concentration.

Therefore these inputs can support a **sample-level UPB movement/concentration diagnostic** under the Freddie source and rights caveats. They cannot be presented as actual lender exposure, actual EAD, portfolio PD, or empirical ECL. The public project register now calls this a Freddie-sample-derived diagnostic. The P4 exposure workspace, KPI summary/traces, and monitor now label the series as Freddie sample UPB and show the limitation at the top of the workspace. Six targeted Edge checks passed for the workspace title, scope banner, accessibility role, source badge, sample-UPB summary and context text; browser errors were zero. The broader existing browser suite stops at its frozen convergence-evidence preflight with `Convergence receipt changed`, before opening the browser; the frozen receipt was not regenerated. Preserve the raw input privately and require a real owner/source statement, portfolio position key and contract evidence before accepting an actual-book portfolio import.

## Effect on N02 and next actions

- Source register: 123 objects (20 public-suite and 103 supplemental) across the same 17 curated broad families.
- Parent-group binding: 22/27 now have source-object records. Five remain explicitly dispositioned: the Freddie-sample-derived exposure diagnostic without ownership evidence, three derived outputs with upstream source links, and Ginnie production access pending an authenticated payload.
- Capability ledger remains 26/50 (52%). The source binding does not change completion.
- Next: resolve the frozen convergence-receipt mismatch before rerunning the full P4 browser suite; retain Freddie provenance on every export; trace Apple debt KPIs to accession/period/unit and availability; keep SEC-copy parity and reuse gates open. Do not forecast missing balances or fill blank PD/LGD/EAD fields.
