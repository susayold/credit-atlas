# N03 — FHFA PUDB 2025: truy vết công thức từ source đến KPI

**Cập nhật:** 17/10/2026 · **Method card:** `fhfa-pudb-acquisition-composition` · **Source release:** 2025 Enterprise acquisitions, phát hành 24/09/2026.

Tài liệu này đóng formula trace cho các KPI PUDB đang được app và workbook analyst sử dụng. Đây là một phép đo **cơ cấu khoản vay Enterprise đã mua**, không phải mô hình rủi ro tín dụng hay tỷ lệ phê duyệt.

## Chuỗi dữ liệu và consumer

| Bước | Đầu vào / phép biến đổi | Bằng chứng và nơi dùng |
|---|---|---|
| 1. Publisher source | FHFA 2025 Single-Family Census Tract ZIP; 2.093.767 acquisition rows, 66 fields; dictionary và record-count workbook cùng release. | Source register: `fhfa-pudb-2025-sf-census-tract`, `fhfa-pudb-2025-data-dictionary`, `fhfa-pudb-2025-record-counts`. URLs và hash prefixes ở [source release register](data/creditatlas-source-release-register-2026-10-17.json). |
| 2. Validate and profile | Reader kiểm tra ZIP member, header/order, width, unique `record_num_sf_ctf`, acquisition year 2025, census year 2020, Enterprise/purpose/guarantee domains, official row totals; dựng one-field category counts và blank census. | [`src/credit_atlas/fhfa_pudb.py`](../src/credit_atlas/fhfa_pudb.py), `profile_archive()` và private versioned receipt/profile. Key chỉ dùng kiểm chứng; không trả ra API aggregate. |
| 3. Service/API | `ResearchService.fhfa_pudb_profile()` đọc receipt/profile đã xác minh. Hai route không nhận query filter: `/api/fhfa-pudb-profile` và `/api/fhfa-pudb-profile-report`. | [`src/credit_atlas/service.py`](../src/credit_atlas/service.py), [`src/credit_atlas/server.py`](../src/credit_atlas/server.py). Response được đánh dấu `visibility=private`, `public_release_approved=false`. |
| 4. App view | Hiển thị source total, category records và share-of-file theo từng category field; suppression theo ngưỡng 30. Các field category có trong profile đều được render. | [`apps/web/app.js`](../apps/web/app.js), `fhfaPudbPane()`. |
| 5. Analyst workbook | 5 tabs: Overview, Category Mix, Missingness, Data Dictionary, Sources & Methods. Có công thức Excel cho file-share, nonblank-field-share, observed records và missing percentage. Không có loan-level rows. | [`apps/excel/build_fhfa_pudb_analyst_review.mjs`](../apps/excel/build_fhfa_pudb_analyst_review.mjs); workbook lưu trong private `outputs`, không commit. |

## Định nghĩa và công thức

Ký hiệu `N = 2.093.767` là số acquisition rows đã xác minh. Với field `f` và source code `c`, mỗi field được xử lý độc lập; reader trim khoảng trắng ở hai đầu. Giá trị rỗng sau `strip()` được ghi thành category `<BLANK>`.

| Metric | Định nghĩa | Consumer / lưu ý |
|---|---|---|
| Category records | `n(f,c) = count(row_i[f] == c)` sau chuẩn hóa khoảng trắng; với ô rỗng, `c = <BLANK>`. | App, workbook và aggregate profile. Với mỗi field category đã profile, tổng các code counts phải bằng `N`; workbook builder dừng nếu không khớp. |
| Share of file | `100 × n(f,c) / N`. | App UI và workbook `Category Mix` (cột F: `E / $B$3`). Mẫu số là toàn bộ acquisitions; blank là category riêng khi phát sinh. Đây không phải tỷ lệ approval hay default. |
| Nonblank-field records | `known(f) = N − b(f)`, trong đó `b(f)` là số source-empty cells ở field `f`. | Workbook `Category Mix` (cột G). Tử số category không blank; blank category không có nonblank share. |
| Share among known values | `100 × n(f,c) / known(f)` cho `c != <BLANK>`. | Chỉ workbook `Category Mix` (cột H: `E / G`). App hiện hiển thị share-of-file, không hiển thị metric này. |
| Source blanks | `b(f) = count(row_i[f].strip() == "")`. | Profile v4 có entry cho đủ 66 fields, kể cả số 0 tường minh; workbook `Missingness` lấy trực tiếp từ đó. Không tự động đổi code “Not available” của publisher thành blank. |
| Missing percentage | `100 × b(f) / N`. | Workbook `Missingness` (cột F). `Records observed = N − b(f)` (cột E). Không nội suy hoặc điền giá trị. |
| Suppression | Nếu `0 < n < 30`, ẩn count và share tương ứng; với missingness, nếu `0 < b(f) < 30`, ẩn count và missing %. | Áp dụng trong app/workbook để không hiển thị ô nhỏ. Các share nhìn thấy có thể cộng dưới 100% do suppression và làm tròn. Raw aggregate profile vẫn private; không dùng số bị ẩn để suy ra danh tính. |

Các category fields là 16 chiều một biến: `enterprise`, `purpose_ctf`, `fed_guarantee_ctf`, `fthb`, `occupancy_sf_ctf`, `lien_status`, `dti_cat`, `same_year_acq`, `preapproval`, `score_borr_model`, `race1_borr`, `ethnicity_borr`, `sex_borr`, `age_borr_cat`, `state_fips`, `tract_rural`. Không tạo cross-tab giữa race/ethnicity, geography, income, DTI, score model hoặc Enterprise; không cộng chồng các chiều như thể chúng là các nhóm loại trừ nhau.

Code label lấy từ [FHFA 2025 data dictionary](https://www.fhfa.gov/document/d/pud/2025-enterprise-pudb-data-dictionary.xlsx). Các code chưa có label giải nghĩa trong UI vẫn hiện mã nguồn gốc; không tự đặt định nghĩa. `same_year_acq` là thời điểm note được phát hành so với năm mua lại; `preapproval` là yêu cầu preapproval được mã hóa trong PUDB, không phải kết quả chấp thuận khoản vay.

## Đối soát và nghiệm thu

- Production audit đã xác minh `2.093.767` rows, `66` columns, unique source keys, không duplicate/malformed rows, toàn bộ acquisition year `2025` và census year `2020`.
- Enterprise totals khớp record-count workbook FHFA: Fannie Mae `987.450` + Freddie Mac `1.106.317` = `2.093.767`.
- Profile v4 ghi blank census đủ 66 fields. Từng category field trong builder phải cộng về đúng `N`; source dictionary được đối chiếu 66 unique header names và thứ tự/hash header.
- Workbook được tạo từ profile/receipt riêng tư; category rows <30 được suppress. File không chứa `record_num_sf_ctf` hoặc các source loan rows. Receipt hiện **không cho phép public release**; profile và workbook không được commit.
- Test server HTTP ngày 17/10 trả `200` cho profile API (`AVAILABLE`, 16 category dimensions, 66 blank-count fields), asset `app.js` (đã có `same_year_acq`, `preapproval` và method link), và workbook download (`37.209` bytes; ZIP có 5 worksheet XML). Đây là route/asset smoke test, không phải browser visual acceptance.
- Automated tests cover parser, private-output route và project register. Browser visual review cùng native Excel desktop open/recalculate vẫn đang chờ nghiệm thu.

## Giới hạn diễn giải

PUDB chỉ mô tả các mortgage loans được Fannie Mae/Freddie Mac mua trong năm 2025. Dataset không phải toàn bộ applicant/denial population; không có monthly payment history, delinquency transition, default, foreclosure, prepayment, realized loss hoặc recovery outcome. Không thể dùng nó để ước lượng PD/LGD, fairness approval, causal impact hay trend lịch sử từ một vintage. `record_num_sf_ctf` là key tuần tự riêng của file; không join sang servicing, HMDA, NMDB, NSMO hoặc D01.

Profile lưu blank counts từng field, nên tổng blanks toàn ma trận có thể tính bằng phép cộng 66 counts; tổng đó không được công bố ở source register. Các counts chính xác, full profile/hash và raw rows ở vùng local-private. Summary công khai chỉ dùng hash prefixes và source metadata được phép.

## Kế tiếp trong N03

PUDB formula trace đã có source field, mẫu số, phép biến đổi, suppression, consumer và giới hạn. N03 toàn dự án vẫn mở: áp dụng cùng chuẩn cho HMDA `action_taken` denominator, NMDB rate/weighted-series calculations, và các KPI khác; lưu rõ publisher value, app-derived value, publisher-imputed field và missing/suppressed state trong từng output.
