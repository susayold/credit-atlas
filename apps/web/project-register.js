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
