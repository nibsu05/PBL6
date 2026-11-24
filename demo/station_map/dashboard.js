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
  let updatingResults = false;
  let inboxSignature;
  let checkingInbox = false;
  let pollAfterProbe;
  const query = new URLSearchParams(location.search);
  if ([1, 2, 3].includes(Number(query.get("day")))) day = Number(query.get("day"));

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

  function renderAdminAlerts(data) {
    const signature = JSON.stringify(data);
    if (signature === inboxSignature) return;
    inboxSignature = signature;
    const label = get("admin-unread");
    label.hidden = !data.unread;
    label.textContent = data.unread + " chưa đọc";
    get("alerts-read-all").hidden = !data.unread;
    const list = get("alert-items");
    list.replaceChildren();
    for (const item of data.items) {
      const card = add(list, "article", undefined, "card admin-alert");
      card.dataset.unread = String(!item.read_utc);
      const heading = add(card, "div");
      add(heading, "h3", item.title);
      const when = add(heading, "time", time(item.last_seen_utc) + " (VN)" +
        (item.occurrences > 1 ? " · " + item.occurrences + " lần ghi nhận" : ""));
      when.dateTime = item.last_seen_utc;
      if (!item.read_utc) {
        const button = add(card, "button", "Đã đọc", "action");
        button.type = "button";
        button.addEventListener("click", () => markAlerts({id: item.id}));
      }
      add(card, "p", item.detail);
      add(card, "p", item.action);
    }
    notify(data.items.length ? "" : "Chưa có thông báo.", "alerts-feedback");
  }

  async function refreshAdminAlerts() {
    if (checkingInbox) return;
    checkingInbox = true;
    try {
      renderAdminAlerts(await api("/api/admin/alerts"));
    } catch (error) {
      if (error.status === 401) window.location.replace("/login");
      else notify("Chưa đọc được hộp thông báo. Trang sẽ thử lại.", "alerts-feedback");
    } finally {
      checkingInbox = false;
    }
  }

  async function markAlerts(body) {
    try {
      await send("/api/admin/alerts/read", body);
      await refreshAdminAlerts();
    } catch (error) {
      if (error.status === 401) window.location.replace("/login");
      else notify("Chưa lưu được trạng thái đã đọc. Hãy thử lại.", "alerts-feedback");
    }
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

  function dayJob(job, fallback) {
    if (!job) return fallback;
    const labels = {
      running: "Đang chạy",
      recorded: "Đã lưu trước giờ phát",
      already_recorded: "Đã có bản lưu",
      verified: "Đã đối chiếu",
      pending: "Đang chờ đủ số đo",
      vrain_unavailable: "Dừng vì Vrain chưa trả dữ liệu",
      vrain_18h_pending: "Chờ mưa trạm đến 18:00",
      gfs_unavailable: "Chưa đủ trường GFS",
      outside_forecast_window: "Đã qua khung thu dữ liệu",
      no_due_issue: "Chưa có lượt đến hạn",
      issue_record_error: "Thu hoặc lưu dự báo gặp lỗi",
      job_error: "Lượt chạy gặp lỗi",
      job_timeout: "Lượt chạy đã quá thời gian",
    };
    return (labels[job.reason] ?? labels[job.status] ?? fallback) + " · " + time(job.finished_utc ?? job.started_utc);
  }

  function renderDaily(daily, forecast) {
    const schedule = daily?.schedule;
    const badge = get("schedule-state");
    const disabled = schedule?.task_state === "Disabled";
    badge.textContent = disabled ? "Đã tắt" : schedule ? "Đã đăng ký" : "Chưa đăng ký";
    badge.dataset.status = schedule && !disabled ? "ok" : "waiting";
    const latestProbe = daily?.probe?.finished_utc;
    const collection = daily?.forecast
      ? "Lượt thu gần nhất " + time(daily.forecast.started_utc)
      : latestProbe ? "Đã thử nguồn lúc " + time(latestProbe) : "Chưa chạy theo lịch";
    get("collection-step").textContent = collection;
    get("forecast-step").textContent = dayJob(daily?.forecast,
      forecast ? "Đã ghi " + time(forecast.issue_utc) : "Chưa có dự báo mới");
    get("truth-step").textContent = dayJob(daily?.verify, "Chờ lượt dự báo đầu tiên");
    get("schedule-note").textContent = schedule
      ? "Giờ Việt Nam. Tác vụ chạy khi máy còn bật và tài khoản Windows đang đăng nhập."
      : "Có thể kiểm tra nguồn thủ công. Web hiện đọc các bản dự báo đã lưu trên máy.";
    get("daily-schedule").hidden = false;
  }

  function channelText(channel) {
    if (!channel) return "Chưa kiểm tra";
    if (channel.status === "ok") return channel.stations + " trạm có số";
    if (channel.status === "waiting") return "Chờ số đo";
    return channel.http_status ? "HTTP " + channel.http_status : "Lấy dữ liệu lỗi";
  }

  function renderHourly(hourly) {
    if (!hourly?.schedule && !hourly?.last_recorded) return;
    const {last_recorded: last, last_verified: truth, latest} = hourly;
    const reasons = {
      incomplete_24h_history: "Chờ đủ 24 giờ đo",
      vrain_session: "Phiên Vrain cần làm mới",
      late_source: "Số đo về sau hạn lưu",
      outside_hourly_window: "Chạy sau khung thu",
      hourly_source_or_inference_error: "Thu dữ liệu hoặc suy luận gặp lỗi",
      hourly_job_error: "Lượt chạy gặp lỗi",
    };
    const result = latest ? reasons[latest.reason] ??
      (["recorded", "already_recorded"].includes(latest.status) ? "Đã ghi dự báo" : "Chờ lượt thử") : "Chưa chạy";
    sourceCard("Dự báo 1–6 giờ", hourly.display_enabled ? "ok" : "waiting",
               hourly.display_enabled ? "Đang hiển thị" : "Đang thí điểm", [
      ["Lịch trên máy", hourly.schedule ? "Phút 05 mỗi giờ · lưu trước phút 15" : "Chưa đăng ký"],
      ["Trạng thái lượt gần nhất", result + (latest ? " · " + time(latest.started_utc) : "")],
      ["Mốc dữ liệu", time(last?.issue_utc)],
      ["Giờ nhận Vrain", time(last?.received_utc)],
      ["Giờ ghi dự báo", time(last?.recorded_utc)],
      ["Trạm đủ đầu vào", last ? last.stations + " / " + last.stations_expected : "Chưa ghi nhận"],
      ["Số lượt đã lưu trong 8 ngày", hourly.recent_issues],
      ["Đối chiếu", truth ? time(truth.issue_utc) + " · " + truth.observed_cells + " cặp có thực đo"
                  : last ? "Chờ thực đo đến " + time(last.truth_due_utc) : "Chờ lượt ghi đầu tiên"],
    ]);
  }

  function renderStatus(data) {
    const {gfs, vrain} = data.sources;
    const forecast = data.last_recorded_issue;
    renderDaily(data.daily, forecast);
    get("source-cards").replaceChildren();
    get("status-refresh").textContent = "Trạng thái lúc " + time(data.checked_at) + " (VN). Bảng đọc lại mỗi 30 giây.";
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
      ...(vrain?.channels ? [["Kênh hiện tại", channelText(vrain.channels.modern)],
                            ["Kênh lịch sử", channelText(vrain.channels.legacy)]] : []),
      ...(vrain?.inventory_http_status ? [["Danh mục theo phiên hiện tại",
        vrain.authorized_group ? "HTTP 200 · Có nhóm Đà Nẵng" : "HTTP " + vrain.inventory_http_status]] : []),
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
    ]);
    renderHourly(data.hourly);
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
      refreshAdminAlerts();
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

  function renderErrors(window, issue) {
    const parent = get("issue-errors");
    parent.replaceChildren();
    if (!window.largest_errors.length) {
      add(parent, "p", "Chưa có cặp dự báo và thực đo hợp lệ.", "subtle");
      return;
    }
    for (const item of window.largest_errors) {
      const row = add(parent, "a", undefined, "issue-error");
      row.href = "/?" + new URLSearchParams({
        issue: issue.id, day: String(day), layer: "difference", station: item.station_id,
      });
      add(row, "strong", item.station_id);
      add(row, "span", format(item.predicted_mm) + " dự báo · " + format(item.observed_mm) + " thực đo", "subtle");
      const value = add(row, "strong", (item.error > 0 ? "+" : "") + format(item.error) + " mm", "issue-error-value");
      value.dataset.sign = item.error < 0 ? "under" : "over";
    }
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
    get("event-detail").textContent = window.stations
      ? "Mưa ≥50 mm/24 giờ ở ngưỡng báo " + percent.format(window.cutoff) +
        " · Bỏ sót " + window.misses + " · Báo nhầm " + window.false_alarms + "."
      : "Kỳ này chưa đủ số đo đối chiếu.";
    const params = new URLSearchParams({issue: issue.id, day: String(day)});
    get("open-map").href = "/?" + params;
    get("download-issue").href = "/api/export.csv?" + params;
    renderErrors(window, issue);
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
    for (const row of verification.heavy_amount_variant) {
      const card = add(get("heavy-results"), "div", undefined, "result-stat");
      add(card, "small", "Ngày " + row.horizon);
      add(card, "strong", format(row.baseline) + " → " + format(row.adjusted));
      add(card, "span", "Giảm " + format(-row.change) + " mm trên " + row.cases + " lượt");
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
  get("alerts-read-all").addEventListener("click", () => markAlerts({all: true}));
  for (const button of dayButtons) button.addEventListener("click", () => {
    if (!verification) return;
    day = Number(button.dataset.checkDay);
    renderIssue();
  });

  async function refreshVerification() {
    if (updatingResults || document.hidden) return;
    updatingResults = true;
    try {
      const updated = await api("/api/verification");
      if (JSON.stringify(updated) === JSON.stringify(verification)) return;
      const firstLoad = !verification;
      verification = updated;
      const control = get("check-issue");
      const selection = control.value || query.get("issue");
      control.replaceChildren();
      for (const issue of updated.replay_issues) {
        add(control, "option", time(issue.issue_utc) + (issue.mode === "prospective" ? " · Đã ghi" : " · Phát lại")).value = issue.id;
      }
      if (updated.replay_issues.some(({id}) => id === selection)) control.value = selection;
      renderIssue();
      if (firstLoad) renderResearch();
      notify("");
    } catch (error) {
      if (error.status === 401) window.location.replace("/login");
      else notify("Chưa đọc được bảng kiểm chứng mới. Trang sẽ thử lại.");
    } finally {
      updatingResults = false;
    }
  }

  refreshStatus();
  refreshVerification();
  window.setInterval(() => {
    if (!document.hidden) refreshStatus();
  }, 30000);
  window.setInterval(refreshVerification, 90000);
})();
