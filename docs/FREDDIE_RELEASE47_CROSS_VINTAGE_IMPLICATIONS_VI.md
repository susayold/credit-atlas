# Freddie Mac Release 47 — tác động tới data contract và so sánh vintage

**Đối chiếu:** 2026-10-16. **Phạm vi:** tài liệu Release Notes và Disclosure Changes có hiệu lực tháng 07/2026, bản Standard Dataset. Đây là nghiên cứu schema/version, không phải thêm loan-performance rows.

## Bằng chứng từ publisher

Release Notes ghi Release 47 phát hành ngày 29/07/2026, origination cutoff và performance cutoff cùng là 31/03/2026. Full Volume Standard Dataset được mô tả khoảng **49,21 triệu origination records** và **2,91 tỷ performance records**. Đây là số toàn bộ dataset do Freddie báo cáo, không phải số dòng của annual sample 2012 đang dùng trong D01. Release Notes cũng nêu các thay đổi Release 47, còn Disclosure Changes so sánh trực tiếp tên trường, enum và file layout mới/cũ.

Hai PDF được tải trực tiếp từ Freddie Mac, kiểm tra PDF header và ghi SHA-256 trong receipt private `data/private/mortgage/freddie-public-reference-c88f57796bfd/receipt.json`:

- `release-notes.pdf`, 602.990 bytes, SHA-256 `3e4aee17551a50c60daf5be9c98769d74f05d9bac60e8328314fc3cd6a92ef97`.
- `disclosure-changes-july-2026.pdf`, 182.219 bytes, SHA-256 `e513ccc06fca13880a541442b393a655e1b5904fd1a97e79cf7f56808f1fa2f0`.

## Thay đổi cần xử lý trong cross-vintage contract

| Thành phần | Release 47 ghi nhận | Rủi ro nếu đọc như cùng một schema |
|---|---|---|
| Tên file/field | Standard files đổi sang `orig_YYYYQn.txt` và `perf_YYYYQn.txt`; một số field đổi tên, MI cancellation indicator và servicer chuyển từ origination sang performance | File-name guessing hoặc position-only mapping có thể ghép sai layout |
| Delinquency | `0/1/2/3` được biểu diễn thành `00/01/02/03`; `RA` là REO Acquisition; `XX` là Not Available; giá trị số được cap tại 99 | Mất leading zero; coi 99 là chính xác 99 kỳ; coi `XX` là Current; hiểu `RA` như numeric delinquency |
| Zero-balance reason 96 | Ghi rõ là confirmed underwriting defect hoặc major servicing defect trước credit event | Gộp 96 vào payoff, default, hoặc ordinary missing exit sẽ đổi estimand |
| Loss components | Recoveries/gains mang dấu âm; expenses/losses mang dấu dương. Actual Loss dương, gains âm | Cộng dữ liệu khác version mà không chuẩn hóa dấu có thể đảo chiều loss bridge |
| Modification cost | Cumulative Modification Costs được disclose ở mọi kỳ kể từ modification đầu tiên | Cộng các bản ghi tháng như incremental cost có thể đếm lặp cumulative balance |
| Origination score | Thêm VantageScore 4.0; Classic FICO vẫn là field riêng | Gộp hai score thành một cột/series tạo sai nghĩa và availability |
| Categorical fields | Một số enum/null thay đổi: Number of Borrowers, Seller Name, Super Conforming, Special Eligibility Program, HARP Indicator, Postal Code | Tỷ lệ missing/segment thay đổi có thể chỉ do disclosure policy chứ không phải thay đổi borrower mix |

Release Notes còn ghi R47 thêm origination records 01/10/2025–31/03/2026 và performance tới 31/03/2026; dataset là historical, unaudited và có thể được sửa. Receipt retrieval date không phải ngày công bố dữ liệu.

## Quyết định cho CreditAtlas

1. Giữ nguyên các giá trị raw, chuỗi có leading zero, codebook và release identity trong raw layer. Không tự động `zfill`, đổi dấu hoặc đổi `XX` thành trạng thái hợp lệ.
2. Mỗi vintage cần ghi rõ file release/layout và mapping version; các enum có khác biệt theo thời kỳ phải giữ field `source_vintage`/`source_release` tới canonicalization.
3. Phân biệt phần tử cumulative với dòng phát sinh trước khi tính modification cost; phần tử loss chỉ được cộng sau khi dấu và coverage đối chiếu độc lập với actual-loss source.
4. Không coi codebook R47 là bằng chứng cho release của corpus 2012 hiện có. Corpus đó được user cung cấp; evidence hiện tại xác nhận cấu trúc/semantics trên các giá trị quan sát nhưng **chưa xác thực publisher release/version**.
5. Không fit lại, tạo PD/LGD/ECL, hoặc tính dự phóng trong lượt này. Release 47 là schema evidence, không bổ sung một annual vintage và không mở R2/R3.

## Hành động tiếp theo khi có annual data

- Ghi URL/receipt/hash/file names/cutoff và xác định release trước khi parse.
- Profile nguyên file và so với exact layout cùng release; so field names, positions, enums, missing codes, zero-balance reasons, loss signs và cumulative behavior qua từng vintage.
- Chạy dual-path reconciliation: raw source value → release-specific mapping → canonical value; tổng counts/UPB/loss phải khớp trước và sau mapping, bao gồm unknown categories.
- Đánh giá support/label follow-up sau harmonization; chỉ sau đó cập nhật target feasibility và model gate.

## Nguồn chính thức

- [Freddie Mac Release Notes](https://www.freddiemac.com/fmac-resources/research/pdf/release_notes.pdf), Release 47 section.
- [Disclosure Changes effective July 2026](https://www.freddiemac.com/fmac-resources/research/pdf/disclosure-changes-summary.pdf), pages 1–4.
- [SFLLD data page](https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset), current coverage/access and Release 47 links.
