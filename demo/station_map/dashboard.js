"use strict";

(() => {
  const {api, send} = window.PBL6Portal;
  const get = (id) => document.getElementById(id);
  const dayButtons = [...document.querySelectorAll("[data-check-day]")];
  const number = new Intl.NumberFormat("vi-VN", {minimumFractionDigits: 2, maximumFractionDigits: 2});
  const percent = new Intl.NumberFormat("vi-VN", {style: "percent", maximumFractionDigits: 0});
  const clock = new Intl.DateTimeFormat("vi-VN", {
    timeZone: "Asia/Ho_Chi_Minh", year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", hour12: false,
  });
  const modelStyles = {
    B: {name: "LightGBM B", color: "var(--series-lightgbm)"},
    GFS: {name: "GFS", color: "var(--series-gfs)"},
    MOS_LONG: {name: "MOS", color: "#ab763e"},
  };
  let verification;
  let day = 1;
  let checking = false;
  let pollAfterProbe;

  function add(parent, tag, value, className) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (value !== undefined) node.textContent = value;
    parent.append(node);
    return node;
  }

  function time(value) {
    return value ? clock.format(new Date(value)) : "Chưa có";
  }

  function notify(message, id = "dashboard-error") {
    get(id).textContent = message;
    get(id).hidden = !message;
  }

  function sourceCard(title, status, label, facts) {
    const card = add(get("source-cards"), "article", undefined, "card source-card");
    const header = add(card, "div", undefined, "source-heading");
    add(header, "h3", title);
    const badge = add(header, "span", label, "status-badge");
    badge.dataset.status = status;
    const list = add(card, "dl", undefined, "source-facts");
    for (const [name, value] of facts) {
      const fact = add(list, "div");
      add(fact, "dt", name);
      add(fact, "dd", value);
    }
  }

  function renderStatus(data) {
    const {gfs, vrain} = data.sources;
    const forecast = data.last_recorded_issue;
    get("source-cards").replaceChildren();
    get("status-refresh").textContent = "Hiển thị lúc " + time(data.checked_at) + " (VN). Bảng tự làm mới mỗi 30 giây.";
    sourceCard("GFS · Khí tượng dự báo", gfs?.status ?? "unknown",
               gfs?.status === "ok" ? (gfs.kind === "decode" ? "Đã tải và giải mã" : "Đủ chỉ mục") :
                 gfs?.status === "error" ? "Lấy dữ liệu lỗi" : "Chưa kiểm tra", [
      ["Lần kiểm tra gần nhất", time(gfs?.checked_at)],
      ["Chu kỳ GFS", time(gfs?.cycle)],
      ["Số trường ở lần kiểm tra", Number.isInteger(gfs?.fields) ? gfs.fields + " / 19" : "Chưa rõ"],
      ["Lần giải mã dữ liệu đầy đủ", data.last_gfs_decode
        ? time(data.last_gfs_decode.checked_at) + " · " + data.last_gfs_decode.stations + " trạm" : "Chưa ghi nhận"],
    ]);
    sourceCard("Vrain · Mưa tại trạm", vrain?.status ?? "unknown",
               vrain?.status === "ok" ? "Có số đo" : vrain?.status === "error"
                 ? (vrain.http_status ? "Lỗi HTTP " + vrain.http_status : "Lấy dữ liệu lỗi")
                 : vrain?.status === "waiting" ? "Chờ số đo" : "Chưa kiểm tra", [
      ["Lần kiểm tra gần nhất", time(vrain?.checked_at)],
      ["Ngày yêu cầu dữ liệu", vrain?.day ?? "Chưa rõ"],
      ["Số trạm có giá trị trả về", vrain?.stations ?? "Chưa rõ"],
      ["Giờ có số đo mới nhất trong lần kiểm tra", time(vrain?.last_hour)],
    ]);
    sourceCard("Lần phát dự báo", forecast ? "ok" : "waiting",
               forecast ? "Có lượt đã ghi" : "Đang phát lại lịch sử", [
      ["Giờ phát theo thiết kế", data.planned_issue_local + " giờ Việt Nam"],
      ["Bản gần nhất ghi trước giờ phát", forecast ? time(forecast.issue_utc) : "Chưa ghi nhận"],
      ...(forecast ? [["Giờ lưu dự báo", time(forecast.recorded_utc)]] : []),
      ["Đối chiếu bản ghi mới với Vrain", forecast ? (forecast.verified ? "Có kết quả" : "Đang chờ") : "Chưa có lượt để chấm"],
      ["Tín hiệu cuối của trình ghi dự báo", time(data.tracker_heartbeat)],
    ]);
    const button = get("source-check");
    button.disabled = data.source_probe_running;
    button.textContent = data.source_probe_running ? "Đang kiểm tra nguồn…" : "Kiểm tra nguồn";
  }

  async function refreshStatus() {
    if (checking) return;
    checking = true;
    try {
      const data = await api("/api/status");
      renderStatus(data);
      notify("", "status-error");
      if (data.source_probe_running) {
        window.clearTimeout(pollAfterProbe);
        pollAfterProbe = window.setTimeout(refreshStatus, 1500);
      } else if (!get("probe-feedback").hidden &&
                 get("probe-feedback").textContent === "Đang hỏi GFS và Vrain…") {
        notify("Đã kiểm tra xong. Xem giờ và kết quả mới ở từng nguồn.", "probe-feedback");
      }
    } catch (error) {
      if (error.status === 401) window.location.replace("/login");
      else notify("Chưa đọc được trạng thái nguồn. Bảng sẽ thử lại.", "status-error");
    } finally {
      checking = false;
    }
  }

  function format(value) {
    return value === null ? "—" : number.format(value);
  }

  function renderIssue() {
    const issue = verification.replay_issues.find(({id}) => id === get("check-issue").value);
    const window = issue.windows.find(({horizon}) => day === horizon);
    get("check-period").textContent = time(window.start_utc) + " → " + time(window.end_utc) + " (VN)";
    const stats = get("check-stats");
    stats.replaceChildren();
    for (const [value, label] of [
      [window.stations + " / " + verification.roster, "trạm đủ số để so"],
      [window.scores[0].over_20, "trạm có sai lệch LightGBM trên 20 mm"],
      [window.heavy_events ? window.hits + " / " + window.heavy_events : "—", "trường hợp mưa ≥50 mm bắt được"],
    ]) {
      const item = add(stats, "div", undefined, "result-stat");
      add(item, "strong", String(value));
      add(item, "span", label);
    }
    const target = get("issue-metrics");
    target.replaceChildren();
    const bestMAE = Math.min(...window.scores.map(({mae}) => mae ?? Infinity));
    const bestRMSE = Math.min(...window.scores.map(({rmse}) => rmse ?? Infinity));
    for (const score of window.scores) {
      const row = add(target, "tr");
      add(row, "th", score.model).scope = "row";
      add(row, "td", format(score.mae), score.mae === bestMAE ? "best" : "");
      add(row, "td", format(score.rmse), score.rmse === bestRMSE ? "best" : "");
      add(row, "td", format(score.bias));
    }
    get("event-detail").textContent = "Mưa ≥50 mm/24 giờ ở ngưỡng báo " + percent.format(window.cutoff) +
      " · Bỏ sót " + window.misses + " · Báo nhầm " + window.false_alarms + ".";
    const params = new URLSearchParams({issue: issue.id, day: String(day)});
    get("open-map").href = "/?" + params;
    get("download-issue").href = "/api/export.csv?" + params;
    for (const button of dayButtons) button.setAttribute("aria-pressed", String(Number(button.dataset.checkDay) === day));
  }

  function renderResearch() {
    const aggregate = verification.retrospective_rmse;
    const max = Math.max(1, ...aggregate.map(({rmse}) => rmse));
    const chart = get("retrospective-chart");
    const key = add(chart, "div", undefined, "chart-key");
    for (const model of Object.values(modelStyles)) {
      const item = add(key, "span");
      add(item, "i").style.setProperty("--series", model.color);
      add(item, "span", model.name);
    }
    const groups = add(chart, "div", undefined, "retrospective-groups");
    for (const horizon of [1, 2, 3]) {
      const group = add(groups, "div", undefined, "rmse-group");
      add(group, "span", "Ngày " + horizon);
      const values = add(group, "div", undefined, "rmse-rows");
      for (const [id, style] of Object.entries(modelStyles)) {
        const metric = aggregate.find((row) => row.horizon === horizon && row.model === id);
        if (!metric) continue;
        const row = add(values, "div", undefined, "rmse-row");
        row.title = style.name + " · ngày " + horizon + " · " + format(metric.rmse) + " mm";
        row.setAttribute("role", "img");
        row.setAttribute("aria-label", row.title);
        const track = add(row, "div", undefined, "chart-track");
        const bar = add(track, "span", undefined, "chart-bar");
        bar.style.setProperty("--series", style.color);
        bar.style.setProperty("--extent", 100 * metric.rmse / max + "%");
        add(row, "span", format(metric.rmse), "chart-number");
      }
    }
    for (const row of verification.feature_holdout) {
      const entry = add(get("feature-results"), "div", undefined, "feature-line");
      add(entry, "span", "Ngày " + row.horizon + " · " + format(row.reference) + " → " + format(row.model));
      add(entry, "strong", "Giảm " + format(-row.difference) + " mm");
    }
  }

  get("source-check").addEventListener("click", async () => {
    get("source-check").disabled = true;
    try {
      await send("/api/source-check");
      notify("Đang hỏi GFS và Vrain…", "probe-feedback");
    } catch (error) {
      if (error.status === 401) window.location.replace("/login");
      else notify(error.message, "probe-feedback");
    } finally {
      await refreshStatus();
    }
  });
  get("check-issue").addEventListener("change", renderIssue);
  for (const button of dayButtons) button.addEventListener("click", () => {
    if (!verification) return;
    day = Number(button.dataset.checkDay);
    renderIssue();
  });

  async function start() {
    refreshStatus();
    window.setInterval(() => {
      if (!document.hidden) refreshStatus();
    }, 30000);
    try {
      verification = await api("/api/verification");
      for (const issue of verification.replay_issues) {
        add(get("check-issue"), "option", time(issue.issue_utc) + " · " + issue.label).value = issue.id;
      }
      renderIssue();
      renderResearch();
    } catch (error) {
      if (error.status === 401) window.location.replace("/login");
      else notify("Chưa đọc được bảng kiểm chứng. Hãy tải lại trang.");
    }
  }

  start();
})();
