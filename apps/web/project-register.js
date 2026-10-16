"use strict";

async function projectRegisterWorkspace(container, generation) {
  const register = await api("/api/project-register");
  if (generation !== renderGeneration) return;
  const progress = register.progress;
  $("context-note").textContent = register.datasets.length + " nhóm nguồn · " + register.methods.length + " loại provenance · scope P1–P5";
  $("readiness-badges").replaceChildren(
    badge(progress.completed + "/" + progress.requirements + " yêu cầu trong ledger", "green"),
    badge("D01 R2/R3 đang mở", "amber"), badge("Không phải production approval")
  );
  $("footer-run").textContent = "Register date " + register.as_of + " · completion từ acceptance ledger";

  const intro = card("Một nơi để theo dõi project", "Acceptance, dataset readiness và provenance là ba trạng thái khác nhau.");
  intro.id = "project-register-intro";
  intro.append(note(register.scope_note));
  intro.append(button("Tải register JSON ↓", () => downloadJSON("/api/project-register", "CreditAtlas-Project-Register.json")));
  section(container, intro);

  const completion = grid("four"); completion.id = "project-register-completion";
  completion.append(metric("Toàn CreditAtlas", progress.completed + " / " + progress.requirements, (100 * progress.fraction).toFixed(0) + "% theo 50 capability acceptance"));
  progress.domains.forEach(row => completion.append(metric(row.id, row.completed + " / " + row.requirements, (100 * row.completed / row.requirements).toFixed(0) + "% trong ledger")));
  section(container, completion); container.append(note(progress.acceptance_note));

  const releases = card("D01 · R0–R4", "D01 có release gates riêng; tỷ lệ P2 hoặc tỷ lệ tổng không thể hiện tiến độ modeling.");
  releases.id = "project-register-d01-gates";
  releases.append(table(["Gate", "Trạng thái", "Điều kiện / bằng chứng còn lại"], progress.d01_release_gates.map(row => [row.id + " · " + row.name, row.status, row.evidence])));
  section(container, releases);

  const planProgress = card("Thực hiện plan mới", "Tách các đầu việc đã đưa vào code khỏi những phần còn đang được mở rộng.");
  planProgress.id = "project-register-plan-progress";
  planProgress.append(table(["Task", "Trạng thái", "Đã làm", "Còn lại"], register.current_plan_implementation.map(row => [row.id, row.status, row.scope, row.remaining])));
  section(container, planProgress);

  const dataCard = card("Danh mục dữ liệu", register.datasets.length + " nhóm nguồn được ưu tiên; grain và giới hạn giữ riêng.");
  dataCard.id = "project-register-datasets";
  const dataToolbar = el("div", "toolbar"), query = el("input"), domain = el("select"), status = el("select");
  query.type = "search"; query.placeholder = "Tìm nguồn, kỳ, mục đích hoặc việc tiếp theo"; query.setAttribute("aria-label", "Tìm dataset");
  [["all", "Tất cả domain"], ...[...new Set(register.datasets.flatMap(row => row.domain.split("/")))].sort().map(value => [value, value])].forEach(([value, label]) => { const option = el("option", "", label); option.value = value; domain.append(option); });
  [["all", "Mọi trạng thái"], ...[...new Set(register.datasets.map(row => row.status))].sort().map(value => [value, value])].forEach(([value, label]) => { const option = el("option", "", label); option.value = value; status.append(option); });
  dataToolbar.append(append(el("label", "", "Domain"), domain), append(el("label", "", "Trạng thái"), status), query);
  dataCard.append(dataToolbar); const dataBody = el("div"); dataCard.append(dataBody);
  const renderDatasets = () => {
    const search = query.value.trim().toLocaleLowerCase("vi");
    const rows = register.datasets.filter(row => (domain.value === "all" || row.domain.split("/").includes(domain.value)) && (status.value === "all" || row.status === status.value) && (!search || [row.name, row.domain, row.grain, row.period, row.status, row.access, row.use, row.next].join(" ").toLocaleLowerCase("vi").includes(search)));
    dataBody.replaceChildren(table(["Nguồn / domain", "Grain · kỳ", "Trạng thái", "Quyền truy cập", "Phù hợp và bước tiếp"], rows.map(row => {
      const evidence = el("a", "", "Audit / model card ↗"); evidence.href = "https://github.com/susayold/credit-atlas/blob/main/" + row.evidence; evidence.target = "_blank"; evidence.rel = "noopener noreferrer";
      const publisher = row.publisher ? el("a", "", "Nguồn phát hành ↗") : el("span", "", "Chưa gắn link nhà phát hành");
      if (row.publisher) { publisher.href = row.publisher; publisher.target = "_blank"; publisher.rel = "noopener noreferrer"; }
      return [append(el("div"), el("strong", "", row.name), el("div", "muted-text", row.domain + " · " + row.id), evidence), append(el("div"), el("span", "", row.grain), el("div", "muted-text", row.period)), row.status, append(el("div"), el("span", "", row.access), el("div", "muted-text", "Rights: " + row.rights_review)), append(el("div"), el("span", "", row.use), el("div", "muted-text", row.next), publisher)];
    })));
    dataBody.prepend(para("Đang hiển thị " + number(rows.length) + " / " + number(register.datasets.length) + " nhóm nguồn. Đếm theo grain; không cộng thành unique borrowers."));
  };
  query.addEventListener("input", renderDatasets); domain.addEventListener("change", renderDatasets); status.addEventListener("change", renderDatasets); renderDatasets();
  dataCard.append(note("Data status lấy từ acquisition/audit đã lưu. Nó không chứng minh quyền tái phân phối, unique borrower count hay model readiness. Raw private rows không được đưa vào register."));
  section(container, dataCard);

  const sourceCard = card("Nguồn, release và receipt", register.source_register_scope_note);
  sourceCard.id = "project-register-source-releases";
  const sourceToolbar = el("div", "toolbar"), sourceQuery = el("input");
  sourceQuery.type = "search"; sourceQuery.placeholder = "Tìm source ID, publisher, release, quyền dùng hoặc API";
  sourceQuery.setAttribute("aria-label", "Tìm source release"); sourceToolbar.append(sourceQuery); sourceCard.append(sourceToolbar);
  const sourceBody = el("div"); sourceCard.append(sourceBody);
  const renderSourceRecords = () => {
    const queryText = sourceQuery.value.trim().toLocaleLowerCase("vi");
    const rows = register.source_records.filter(row => !queryText || [
      row.source_id, row.registry_group_id, row.publisher, row.distributor, row.release_label, row.publisher_publication_date,
      row.publication_date_status, row.observed_period_start, row.observed_period_end, row.observed_period_label, row.grain,
      row.source_object_url, row.receipt_reference, row.rights_use_gate, row.rights_review_status, row.receipt_status, row.consumer_trace?.join(" "),
      row.kpi_or_output, row.scope_note
    ].join(" ").toLocaleLowerCase("vi").includes(queryText));
    sourceBody.replaceChildren(table(
      ["Source / nhà phát hành", "Công bố / kỳ quan sát", "Receipt / thời điểm tải", "Grain / đầu ra", "Quyền dùng / consumer"],
      rows.map(row => {
        const link = row.publisher_page_url ? el("a", "", row.distributor ? "Series metadata / distributor ↗" : "Publisher ↗") : el("span", "", "Chưa có link publisher");
        if (row.publisher_page_url) { link.href = row.publisher_page_url; link.target = "_blank"; link.rel = "noopener noreferrer"; }
        const distributorLink = row.distributor_url ? el("a", "muted-text", "Mở series qua distributor ↗") : el("span", "muted-text", "");
        if (row.distributor_url) { distributorLink.href = row.distributor_url; distributorLink.target = "_blank"; distributorLink.rel = "noopener noreferrer"; }
        const objectLink = row.source_object_url ? el("a", "muted-text", "Mở source object ↗") : el("span", "muted-text", "");
        if (row.source_object_url) { objectLink.href = row.source_object_url; objectLink.target = "_blank"; objectLink.rel = "noopener noreferrer"; }
        const publisher = append(el("div"), el("strong", "", row.source_id), el("div", "muted-text", row.publisher),
          row.distributor ? el("div", "muted-text", "Phân phối: " + row.distributor) : el("span", "muted-text", ""), link, distributorLink, objectLink);
        const dates = append(el("div"), el("div", "", "Ngày công bố: " + (row.publisher_publication_date || "chưa xác nhận")),
          el("div", "muted-text", row.publication_date_status),
          el("div", "", "Kỳ quan sát: " + (row.observed_period_label || [row.observed_period_start, row.observed_period_end].filter(Boolean).join(" → ") || "chưa xác định")),
          row.observed_period_label && row.observed_period_start ? el("div", "muted-text", "Date range: " + row.observed_period_start + " → " + row.observed_period_end) : el("span", "muted-text", ""),
          row.snapshot_as_of ? el("div", "muted-text", "Snapshot/as-of: " + row.snapshot_as_of) : el("span", "muted-text", ""));
        const receipt = append(el("div"), el("strong", "", row.receipt_status || "Trạng thái receipt chưa ghi"),
          el("div", "muted-text", row.retrieved_at_utc ? "Tải lúc: " + row.retrieved_at_utc : row.component_retrievals?.length ? "Timestamp tải riêng cho từng component bên dưới." : row.acquisition_started_at_utc ? "Receipt ghi giờ chạy/kiểm tra, không ghi giờ tải từng file." : "Không có timestamp tải trong receipt"),
          row.retrieval_time_range_utc ? el("div", "muted-text", "Thời gian tải từng file: " + row.retrieval_time_range_utc.first + " → " + row.retrieval_time_range_utc.last) : el("span", "muted-text", ""),
          row.acquisition_started_at_utc ? el("div", "muted-text", "Acquisition run bắt đầu: " + row.acquisition_started_at_utc) : el("span", "muted-text", ""),
          row.validation_completed_at_utc ? el("div", "muted-text", "Kiểm tra hoàn tất: " + row.validation_completed_at_utc) : el("span", "muted-text", ""),
          row.receipt_completed_at_utc ? el("div", "muted-text", "Receipt hoàn tất: " + row.receipt_completed_at_utc) : el("span", "muted-text", ""),
          row.native_row_count != null ? el("div", "muted-text", "Rows: " + number(row.native_row_count)) : el("span", "muted-text", ""),
          row.field_count != null ? el("div", "muted-text", "Số trường: " + number(row.field_count)) : el("span", "muted-text", ""),
          row.distinct_lei_count != null ? el("div", "muted-text", "Distinct LEI: " + number(row.distinct_lei_count)) : el("span", "muted-text", ""),
          row.quarantined_row_count != null ? el("div", "muted-text", "Rows quarantined: " + number(row.quarantined_row_count)) : el("span", "muted-text", ""),
          row.publisher_package_generated_at_utc ? el("div", "muted-text", "Publisher package generated at: " + row.publisher_package_generated_at_utc + " (không phải giờ tải) ") : el("span", "muted-text", ""),
          row.publisher_package_last_modified_utc ? el("div", "muted-text", "HTTP package Last-Modified: " + row.publisher_package_last_modified_utc + " (không phải giờ tải) ") : el("span", "muted-text", ""),
          row.sha256_prefix ? el("div", "muted-text", "SHA-256 prefix (content): " + row.sha256_prefix) : el("span", "muted-text", ""),
          row.archive_sha256_prefix ? el("div", "muted-text", "SHA-256 prefix (archive): " + row.archive_sha256_prefix) : el("span", "muted-text", ""),
          el("div", "muted-text", "Ô trống/missing: " + (row.missing_cell_count == null ? "chưa audit/không áp dụng" : number(row.missing_cell_count))),
          row.missing_cell_count_basis ? el("div", "muted-text", row.missing_cell_count_basis) : el("span", "muted-text", ""),
          ...(row.component_retrievals || []).map(item => el("div", "muted-text", item.file + " · tải " + item.retrieved_at_utc)));
        const grain = append(el("div"), el("span", "", row.grain), el("div", "muted-text", row.kpi_or_output || "Chưa gắn KPI/output"));
        const rights = append(el("div"), el("strong", "", row.rights_review_status || "Rights review chưa gắn"),
          el("div", "muted-text", row.rights_use_gate || "Chưa ghi điều kiện sử dụng"),
          ...(row.consumer_trace || []).map(value => el("div", "muted-text", value)),
          row.method_card_ids?.length ? el("div", "muted-text", "Method cards: " + row.method_card_ids.join(", ")) : el("div", "muted-text", "Chưa liên kết method card"));
        return [publisher, dates, receipt, grain, rights];
      })
    ));
    sourceBody.prepend(para("Đang hiển thị " + number(rows.length) + " / " + number(register.source_records.length) + " source records. Ngày công bố và timestamp tải được lưu riêng; null nghĩa là receipt chưa chứng minh được."));
  };
  sourceQuery.addEventListener("input", renderSourceRecords); renderSourceRecords();
  sourceCard.append(note("Đây là crosswalk một phần của N02: receipt private không phát raw rows hoặc full hash; các quyền dùng chưa xác nhận được giữ thành gate. FRED/ALFRED có điều khoản cần rà soát trước khi đưa dữ liệu vào phần mềm hoặc ML."));
  section(container, sourceCard);

  const methods = card("Sổ phương pháp và giả định", "Phân biệt reported, derived, publisher-imputed, preprocessing, model output, scenario và forecast.");
  methods.id = "project-register-methods";
  methods.append(table(["Loại giá trị", "Ví dụ trong project", "Bằng chứng cần lưu", "Không được suy diễn"], register.methods.map(row => [row.name, row.examples, row.required_evidence, row.prohibited_shortcut])));
  methods.append(note("Không có forecast mới trong review ngày 16/10/2026. Imputation và scenario đã có vẫn phải được gắn nhãn theo từng output."));
  methods.append(el("h3", "", "Method cards: công thức, input và giới hạn theo nghiên cứu đã có"));
  register.method_cards.forEach(row => {
    const detail = el("details", "project-method-card"), summary = el("summary", "", row.name + " · " + row.value_type);
    const sourceLinks = row.datasets.map(id => {
      const source = register.datasets.find(item => item.id === id), link = el("a", "", source ? source.name : id);
      link.href = "https://github.com/susayold/credit-atlas/blob/main/" + (source?.evidence || "docs/PROJECT_REVIEW_AND_NEXT_PLAN_2026-10-16_VI.md");
      link.target = "_blank"; link.rel = "noopener noreferrer"; return link;
    });
    const evidence = el("a", "", "Mở method card đầy đủ ↗"); evidence.href = "https://github.com/susayold/credit-atlas/blob/main/" + row.evidence; evidence.target = "_blank"; evidence.rel = "noopener noreferrer";
    detail.append(summary, append(el("div", "project-method-detail"), el("strong", "", "Dataset input"), append(el("div"), ...sourceLinks), el("strong", "", "Target / mục tiêu"), para(row.target), el("strong", "", "Cách tính / protocol"), para(row.method), el("strong", "", "Bằng chứng kiểm định"), para(row.validation), el("strong", "", "Giới hạn"), para(row.limits), evidence));
    methods.append(detail);
  });
  section(container, methods);

  const capabilities = card("50 capability acceptance", "Trạng thái lấy trực tiếp từ ledger; ‘đạt’ chỉ đúng trong scope nghiệm thu đã ghi.");
  capabilities.id = "project-register-capabilities";
  const filters = el("div", "toolbar"), capDomain = el("select"), capState = el("select");
  [["all", "Tất cả domain"], ...progress.domains.map(row => [row.id, row.id])].forEach(([value, label]) => { const option = el("option", "", label); option.value = value; capDomain.append(option); });
  [["all", "Đạt và còn mở"], ["complete", "Đạt trong scope"], ["open", "Còn mở"]].forEach(([value, label]) => { const option = el("option", "", label); option.value = value; capState.append(option); });
  filters.append(append(el("label", "", "Domain"), capDomain), append(el("label", "", "Nghiệm thu"), capState)); capabilities.append(filters);
  const capBody = el("div"); capabilities.append(capBody);
  const renderCapabilities = () => {
    const rows = register.capabilities.filter(row => (capDomain.value === "all" || row.id.startsWith(capDomain.value + ".")) && (capState.value === "all" || (capState.value === "complete") === row.full_completion_proven));
    capBody.replaceChildren(table(["ID", "Domain", "Capability", "Trạng thái ledger", "Điều kiện nghiệm thu", "Bước tiếp theo"], rows.map(row => [row.id, row.id.slice(0, 2), row.title, row.full_completion_proven ? "Đạt trong scope" : "Còn mở · " + row.checkpoint_status, row.acceptance, row.next])));
  };
  capDomain.addEventListener("change", renderCapabilities); capState.addEventListener("change", renderCapabilities); renderCapabilities(); section(container, capabilities);
}
