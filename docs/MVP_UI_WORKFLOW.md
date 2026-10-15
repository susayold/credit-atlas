# CreditAtlas MVP — giao diện để xem ngay

Ngày 10/10/2026. Mở http://127.0.0.1:8770/ để vào trang chủ mới.

## Homepage banner rows — bản mới theo yêu cầu

Đã thay grid cards/hero bằng5 workspace banners và4 quick-task banners.
Mỗi banner chiếm toàn bộ chiều ngang, một dòng riêng trên desktop và mobile.
Ảnh nền có chủ đề riêng: card/statement (Retail), nhà ở (Mortgage), office/
industrial buildings (Business), ledger/building portfolio (Portfolio),
layered glass (Structured). Chữ trắng trên gradient navy; ảnh tập trung bên
phải. Quick tasks tái sử dụng ảnh của domain tương ứng. Hero lớn trước đây
được bỏ khỏi layout; ảnh hero cũ giữ trong project như artifact lịch sử.

Built-in imagegen tạo5 assets, đã copy về `apps/web/assets/`:
`credit-retail-banner-v2.png`, `credit-mortgage-banner-v2.png`,
`credit-business-banner-v2.png`, `credit-portfolio-banner-v2.png`,
`credit-structured-banner-v2.png`. Các ảnh chỉ minh họa; không phải data charts.
Server allowlist5 exact asset URLs; không mở directory/file serving tùy ý.

Browser receipt `mvp-ux-qa-4383a5f9da15`: **13 PASS**, gồm full-width/separate-row
geometry,9 loaded background images,5 domain routes, Excel/task search,
mobile390px/menu/reload. Desktop và mobile screenshots đã xem trực quan.
`banner-http-20261010.xml`: **15 tests PASS**. Node syntax check PASS.
Lượt browser trước có một ERR_CONNECTION_REFUSED và giữ failed receipt;
lượt cuối không có unexpected console/page errors. Lượt pytest đầu lỗi setup
do host temp path C: bị chặn; rerun dùng explicit unique D: basetemp đã PASS.

Các phần dưới ghi lịch sử MVP/workbench trước đợt banner rows này.
Chạy server từ `local machine path omitted`:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m credit_atlas.cli serve --port 8770
```

## Trải nghiệm đã triển khai

- Trang chủ mặc định: hero với ảnh AI thật, năm thẻ domain và nút mở nhanh
  Portfolio/Excel hoặc Retail. Các thẻ mở workspace đang dùng dữ liệu thực tế.
- Menu gom theo P1–P5, tự mở nhóm của view đang chọn; nguồn và phạm vi nghiên
  cứu nằm trong mục mở rộng để giảm độ dài trang chủ.
- Nền ivory, sidebar emerald, khoảng cách/type hierarchy, cards, buttons,
  tables, focus states và responsive shell được cập nhật trên ứng dụng.
- Mobile390px: menu mở/đóng bằng nút, chọn view đóng menu; URL và reload giữ
  workspace. Nguồn dài dùng scroll bên trong bảng, không tràn chiều ngang trang.
- Lối vào Portfolio từ trang chủ khi chưa chọn import mở frozen mortgage
  snapshot `exposure-import-57b88e00bedb`, USD, 9.698 observations và reported
  amount915.208.989,12USD. Không dùng workbook mẫu3 dòng làm danh mục demo chính.
  Import đang chọn được giữ khi quay lại trang chủ. Source UPB không mặc định
  là EAD, các risk scenarios tiếp tục giữ nhãn assumptions.
- Catalog trên trang chủ là frozen suite snapshot đang chọn. Số source files
  và native tables thuộc snapshot đó; các study mới đọc ở workspace tương ứng.

## Ảnh và prompt

Built-in image_gen được dùng; không dùng CLI/API fallback. Ảnh cuối:
`apps/web/assets/credit-atlas-world-v1.png` (1774×887, PNG), được copy vào
project và tích hợp bằng `<img>` trong hero. Server phục vụ đúng `image/png`
qua đường dẫn allowlist `/assets/credit-atlas-world-v1.png`.

Prompt cuối:

> Use case: stylized-concept. Asset type: premium credit risk analytics application hero illustration, wide landscape. Create an elegant photorealistic 3D miniature architectural landscape of five connected financial districts on a softly textured warm ivory platform: modern glass bank towers, a residential neighborhood, industrial corporate buildings, portfolio blocks, and structured finance layered translucent forms. A thin emerald illuminated pathway connects them. Deep forest green, jade glass, warm ivory, subtle brushed brass accents, sophisticated restrained editorial financial aesthetic. Isometric elevated view, subjects concentrated on the right two thirds, generous clean ivory negative space on left. Soft studio daylight, refined shadows, realistic materials, no people, no text, no letters, no logos, no watermark, no numeric charts. Designed as a tasteful background art banner for CreditAtlas dashboard, not a screenshot.

Ảnh mang tính minh họa; không chứa metric hoặc dữ liệu mô hình.

## Bằng chứng kiểm tra

`private evidence omitted from public release`: **10 checks PASS**.
Trình duyệt thật mở trang chủ mặc định, tải ảnh, kiểm tra source filter,
mở đủ P1–P5 qua thẻ domain, đọc kết quả frozen Retail/Excel Portfolio,
kiểm tra selected navigation, mobile390px, menu và reload. Không unexpected
console/page errors; consumed holdout ledger không đổi.

Screenshots đã kiểm tra trực quan: `home-desktop.png`, `home-mobile.png`,
`portfolio-desktop.png`, `portfolio-mobile.png`, `retail-desktop.png` trong
folder receipt trên. Desktop1440px, mobile390px.

`private evidence omitted from public release`: **15 tests PASS** cho HTTP boundary,
Excel HTTP và suite snapshot integrity. Node `--check apps/web/app.js` PASS.
Full regression1.098 PASS trước lần redesign này là evidence của phiên bản
trước; không dùng làm bằng chứng full regression của giao diện mới.

Chrome headless của host đã thoát khi launch ở lượt đầu; QA chuyển sang Edge
đang có sẵn. Lượt kế tiếp phát hiện selector trùng với body attribute;
đã đổi body sang `data-active-view` và kiểm tra lại. Hai lượt cuối PASS;
receipt1134f61f4300 kiểm tra bản cuối có catalog thu gọn và danh mục thực9.698 observations.

## Bản workbench sau MVP

Homepage đã thêm4 tác vụ trực tiếp; Retail5 tabs, Portfolio8 tabs, SBA5 tabs,
SEC4 tabs, ABS5 tabs và Market3 tabs. Mortgage có9 workflow routes; loan list
cuộn trong card ở mobile để timeline dễ tiếp cận. Task search xử lý tiếng Việt
có/không dấu, gồm chữ Đ viết hoa. Source scope và selected task giữ trong URL.

`mvp-ux-qa-1fcc1a0657ed`: **13 PASS** trên shell/tasks hiện tại.
`product-workbench-qa-cd84624ad93d`: **14 PASS**, gồm active-tab repeated clicks.
`remaining-domains-qa-aefc83d0ae39`: **7 PASS**, gồm mobile loan list/aria selection.
`task-race-qa-b252361edc23`: **4 PASS** khi trì hoãn actual policy catalog,
rời/quay lại tab trong lúc response pending, kiểm tra không trùng controls,
search `DOC ECL` và ledger không đổi. Delay chỉ thuộc QA; không sửa source data.

[Research, blueprint và nghiệm thu](PRODUCT_UX_RESEARCH_AND_REBUILD.md) là
tài liệu chính cho bản workbench; checkpoint10 PASS phía trên thuộc MVP trước đó.

MVP giao diện không đồng nghĩa toàn bộ50 capabilities hoàn tất hoặc model
được qualified cho quyết định cho vay thực tế. Scope và các gap của suite
tiếp tục nằm trong `FIVE_WORKSPACES_STATUS.md` và kế hoạch năm workspace.
