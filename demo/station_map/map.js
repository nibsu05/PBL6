"use strict";

const element = (id) => document.getElementById(id);
const rainBins = [
  {limit: 1, label: "<1", color: "#d7edf4"},
  {limit: 10, label: "1–<10", color: "#9ad5df"},
  {limit: 25, label: "10–<25", color: "#50b4bd"},
  {limit: 50, label: "25–<50", color: "#147f92"},
  {limit: 100, label: "50–<100", color: "#355597"},
  {limit: Infinity, label: "≥100", color: "#332552"},
];
const differenceBins = [
  {match: (value) => value <= -50, label: "Thiếu ≥50", color: "#28577a"},
  {match: (value) => value < -10, label: "Thiếu >10 đến <50", color: "#89beda"},
  {match: (value) => value <= 10, label: "Lệch ≤10", color: "#e7eff2"},
  {match: (value) => value < 50, label: "Thừa >10 đến <50", color: "#f0ad73"},
  {match: () => true, label: "Thừa ≥50", color: "#aa451e"},
];
const probabilityBins = [
  {limit: 20, label: "0–<20", color: "#f4ebd8"},
  {limit: 40, label: "20–<40", color: "#efd093"},
  {limit: 60, label: "40–<60", color: "#d89d50"},
  {limit: 80, label: "60–<80", color: "#ac6532"},
  {limit: Infinity, label: "80–100", color: "#742c35"},
];
const rainLayers = {
  lightgbm: {title: "Lượng mưa dự báo · LightGBM", label: "LightGBM", field: "predicted_mm"},
  gfs: {title: "Lượng mưa dự báo · GFS", label: "GFS", field: "gfs_mm"},
  vrain: {title: "Lượng mưa thực đo · Vrain", label: "Vrain", field: "observed_mm"},
};
const privateLayers = ["vrain", "difference"];
const stationSeries = Object.entries(rainLayers).map(([key, info]) => ({...info, key}));
const amount = new Intl.NumberFormat("vi-VN", {maximumFractionDigits: 1});
const percent = new Intl.NumberFormat("vi-VN", {style: "percent", maximumFractionDigits: 1});
const clockTime = new Intl.DateTimeFormat("vi-VN", {
  timeZone: "Asia/Ho_Chi_Minh", hour: "2-digit", minute: "2-digit", hour12: false,
  day: "2-digit", month: "2-digit", year: "numeric",
});
const calendarDate = new Intl.DateTimeFormat("vi-VN", {
  timeZone: "Asia/Ho_Chi_Minh", day: "2-digit", month: "2-digit", year: "numeric",
});
const mapError = element("map-error");
const issueControl = element("issue");
const stationControl = element("station");
const dayButtons = Array.from(document.querySelectorAll("[data-day]"));
const layerButtons = Array.from(document.querySelectorAll("[data-layer]"));
let state;
let map;
let layer;
let markers = new Map();
let refreshing = false;
const narrow = window.matchMedia("(max-width: 680px)");

function add(parent, tag, text, className) {
  const child = document.createElement(tag);
  if (text !== undefined) child.textContent = text;
  if (className) child.className = className;
  parent.append(child);
  return child;
}

function option(select, id, label) {
  const item = add(select, "option", label);
  item.value = id;
}

function localTime(iso) {
  return clockTime.format(new Date(iso));
}

function unitValue(value, unit = " mm", signed = false) {
  return value === null ? "—" : formatAmount(value, signed) + unit;
}

function measurement(point, field) {
  return Number.isFinite(point?.[field]) ? point[field] : null;
}

function difference(point) {
  const prediction = measurement(point, "predicted_mm");
  const observed = measurement(point, "observed_mm");
  return prediction === null || observed === null ? null : prediction - observed;
}

function mapValue(point) {
  if (state.mapLayer === "difference") return difference(point);
  if (state.mapLayer === "probability") {
    const value = measurement(point, "probability_ge50");
    return value === null ? null : value * 100;
  }
  return measurement(point, rainLayers[state.mapLayer].field);
}

function formatAmount(value, signed = false) {
  if (value === null) return "—";
  const rounded = Math.round(Math.abs(value) * 10) / 10;
  const sign = rounded === 0 ? "" : value < 0 ? "−" : signed ? "+" : "";
  return sign + amount.format(rounded);
}

function makeLegend() {
  const list = element("legend-items");
  list.replaceChildren();
  const showDifference = state.mapLayer === "difference";
  const showProbability = state.mapLayer === "probability";
  const bins = showDifference ? differenceBins : showProbability ? probabilityBins : rainBins;
  element("legend-title").textContent = showDifference ? "Sai lệch LightGBM − Vrain"
    : showProbability ? "Xác suất dự báo" : "Dải lượng mưa";
  element("legend-unit").textContent = showProbability ? "%" : "mm/24 giờ";
  const note = element("legend-note");
  note.textContent = showDifference ? "Xanh biểu thị dự báo thiếu. Cam biểu thị dự báo thừa."
    : showProbability ? "Khả năng đạt 50 mm trong 24 giờ tại mỗi trạm."
      : "Mỗi điểm biểu thị lượng mưa tại một trạm.";
  for (const bin of bins) {
    const item = add(list, "li");
    add(item, "span", "", "swatch").style.setProperty("--rain", bin.color);
    add(item, "span", bin.label);
  }
  const missing = add(list, "li");
  add(missing, "span", "", "swatch missing");
  add(missing, "span", "Thiếu mẫu");
}

function initMap(stations) {
  if (!window.L) {
    mapError.textContent = "Không tải được bản đồ. Bạn vẫn có thể chọn trạm để đọc số liệu.";
    mapError.hidden = false;
    element("fit-map").disabled = true;
    return;
  }
  map = L.map("map", {zoomControl: false, minZoom: 4});
  L.control.zoom({position: "topright", zoomInTitle: "Phóng to", zoomOutTitle: "Thu nhỏ"}).addTo(map);
  const tiles = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  });
  tiles.on("tileerror", () => {
    mapError.textContent = "Bản đồ nền tải chưa đủ. Điểm trạm vẫn hiển thị đúng vị trí.";
    mapError.hidden = false;
  });
  tiles.on("tileload", () => { mapError.hidden = true; });
  tiles.addTo(map);
  layer = L.layerGroup().addTo(map);
  fitMap(stations);
}

function fitMap(stations = state.data.stations) {
  if (!map) return;
  const left = !narrow.matches && !element("tools-panel").hidden ? 344 : 35;
  map.fitBounds(stations.map(({latitude, longitude}) => [latitude, longitude]), {
    paddingTopLeft: [left, narrow.matches ? 140 : 115],
    paddingBottomRight: [46, narrow.matches ? 163 : 146],
    maxZoom: 12,
    animate: false,
  });
}

function showTools(open, focus = false) {
  element("tools-panel").hidden = !open;
  element("tools-toggle").setAttribute("aria-expanded", String(open));
  if (open && narrow.matches) element("station-panel").hidden = true;
  if (focus) element(open ? "close-tools" : "tools-toggle").focus();
}

function showStation(id, pan = false) {
  state.stationId = id;
  if (narrow.matches) showTools(false);
  element("station-panel").hidden = false;
  renderStation();
  const marker = markers.get(id);
  if (pan && marker) {
    if (narrow.matches) {
      map.setView(marker.getLatLng(), map.getZoom(), {animate: false});
      map.panBy([0, 82], {animate: false});
    } else {
      map.panInside(marker.getLatLng(), {
        paddingTopLeft: [element("tools-panel").hidden ? 55 : 352, 145],
        paddingBottomRight: [350, 160],
      });
    }
  }
  syncUrl();
}

function syncUrl() {
  const url = new URL(window.location.href);
  if (!state.followLatest) url.searchParams.set("issue", state.selectedIssue.id);
  else url.searchParams.delete("issue");
  url.searchParams.set("day", String(state.day));
  if (!element("station-panel").hidden && state.stationId) url.searchParams.set("station", state.stationId);
  else url.searchParams.delete("station");
  if (state.mapLayer !== "lightgbm") url.searchParams.set("layer", state.mapLayer);
  else url.searchParams.delete("layer");
  window.history.replaceState(null, "", url);
}

function currentWindow() {
  return state.selectedIssue.windows.find((window) => window.horizon === state.day);
}

function renderChart() {
  const chart = element("station-chart");
  chart.replaceChildren();
  const days = state.selectedIssue.windows.map(({horizon, points}) => ({
    horizon, point: points.find((point) => point.station_id === state.stationId),
  }));
  const series = stationSeries.filter(({key}) => state.member || key !== "vrain");
  const values = days.flatMap(({point}) => series.map(({field}) => measurement(point, field)));
  chart.hidden = values.every((value) => value === null);
  if (chart.hidden) return;
  const max = Math.max(10, Math.ceil(Math.max(...values.filter((value) => value !== null)) / 10) * 10);
  add(chart, "figcaption", "So sánh ba ngày");
  const key = add(chart, "div", undefined, "chart-key");
  for (const {label, key: source} of series) {
    const item = add(key, "span");
    add(item, "i").style.setProperty("--series", "var(--series-" + source + ")");
    add(item, "span", label);
  }
  const axis = add(chart, "div", undefined, "chart-axis");
  add(axis, "span", "0");
  add(axis, "span", amount.format(max) + " mm");
  for (const {horizon, point} of days) {
    const day = add(chart, "div", undefined, "chart-day");
    day.setAttribute("aria-current", String(horizon === state.day));
    const dayLabel = "Ngày " + horizon;
    add(day, "span", dayLabel);
    const group = add(day, "div", undefined, "chart-series");
    for (const {label, field, key: source} of series) {
      const value = measurement(point, field);
      const row = add(group, "div", undefined, "chart-row");
      const desc = dayLabel + " · " + label + " · " + (value === null ? "Thiếu mẫu" : formatAmount(value) + " mm/24 giờ");
      row.title = desc;
      row.setAttribute("role", "img");
      row.setAttribute("aria-label", desc);
      const track = add(row, "div", undefined, "chart-track");
      if (value !== null) {
        const bar = add(track, "span", undefined, "chart-bar");
        bar.style.setProperty("--extent", 100 * value / max + "%");
        bar.style.setProperty("--series", "var(--series-" + source + ")");
      }
      add(row, "span", formatAmount(value), "chart-number");
    }
  }
}

function highlightStation() {
  for (const [id, marker] of markers) {
    const chosen = id === state.stationId;
    marker.getElement()?.classList.toggle("chosen", chosen);
    marker.getElement()?.setAttribute("aria-pressed", String(chosen));
    marker.setZIndexOffset(chosen ? 1000 : 0);
  }
}

function renderStation() {
  stationControl.value = state.stationId;
  element("station-title").textContent = "Trạm " + state.stationId;
  element("station-day").textContent = "Ngày " + state.day + " · 24 giờ";
  const link = element("station-verify");
  link.hidden = !state.member || !state.selectedIssue.has_truth;
  link.href = "/dashboard?" + new URLSearchParams({issue: state.selectedIssue.id, day: String(state.day)});
  const point = state.points.get(state.stationId);
  const detail = element("station-detail");
  detail.replaceChildren();
  if (!point) {
    add(detail, "p", "Trạm này thiếu mẫu hợp lệ ở lần phát đã chọn.", "station-missing");
  } else {
    const probability = measurement(point, "probability_ge50");
    const observed = measurement(point, "observed_mm");
    const view = mapValue(point);
    const isProbability = state.mapLayer === "probability";
    const signed = state.mapLayer === "difference";
    const currentLabel = signed ? "Sai lệch LightGBM − Vrain" : isProbability ? "Xác suất mưa ≥50 mm"
      : rainLayers[state.mapLayer].title;
    add(detail, "p", currentLabel, "amount-label");
    const main = add(detail, "p", formatAmount(view, signed), "amount");
    if (view !== null) add(main, "span", isProbability ? " %" : " mm/24 giờ");
    const list = add(detail, "dl");
    const facts = [
      ["lightgbm", "LightGBM B", unitValue(measurement(point, "predicted_mm"))],
      ["gfs", "GFS nguyên bản", unitValue(measurement(point, "gfs_mm"))],
      ["probability", "Xác suất mưa ≥50 mm", probability === null ? "—" : percent.format(probability)],
    ];
    if (state.member) facts.unshift(
      ["vrain", "Vrain thực đo", unitValue(observed)],
      ["difference", "Sai lệch LightGBM − Vrain", unitValue(difference(point), " mm", true)],
    );
    for (const [type, name, value] of facts) {
      if (type === state.mapLayer) continue;
      const pair = add(list, "div");
      add(pair, "dt", name);
      add(pair, "dd", value);
    }
    if (state.member && observed === null) add(detail, "p", "Chưa có số đo đối chiếu cho kỳ này.", "detail-note");
  }
  renderChart();
  highlightStation();
}

function renderPoints() {
  if (!layer) return;
  layer.clearLayers();
  markers = new Map();
  for (const station of state.data.stations) {
    const id = station.station_id;
    const value = mapValue(state.points.get(id));
    const showDifference = state.mapLayer === "difference";
    const showProbability = state.mapLayer === "probability";
    const bands = showProbability ? probabilityBins : rainBins;
    const bin = value === null ? null : showDifference
      ? differenceBins.find(({match}) => match(value))
      : bands.find(({limit}) => value < limit);
    const icon = L.divIcon({
      className: "map-point" + (bin ? "" : " missing"),
      iconSize: [16, 16], iconAnchor: [8, 8],
    });
    const suffix = showProbability ? "%" : " mm";
    const name = id + (bin ? " · " + formatAmount(value, showDifference) + suffix : " · Thiếu mẫu");
    const marker = L.marker([station.latitude, station.longitude], {icon, title: name});
    marker.on("click", () => showStation(id, narrow.matches));
    marker.addTo(layer);
    const node = marker.getElement();
    node.style.setProperty("--rain", bin ? bin.color : "#f0f3f5");
    node.setAttribute("aria-label", name);
    marker.bindTooltip(document.createTextNode(name), {direction: "top", offset: [0, -7]});
    markers.set(id, marker);
  }
}

function highlightList() {
  const signed = state.mapLayer === "difference";
  const suffix = state.mapLayer === "probability" ? "%" : " mm";
  const list = element("scan-stations");
  list.replaceChildren();
  element("scan-title").textContent = signed ? "Sai lệch lớn nhất" : "Giá trị cao nhất";
  const ranked = Array.from(state.points.values(), (point) => [point.station_id, mapValue(point)])
    .filter(([, value]) => value !== null)
    .sort(([, first], [, second]) => Math.abs(second) - Math.abs(first));
  if (!ranked.length) add(list, "li", "Chưa có số cho lớp này.", "source-caption");
  for (const [id, value] of ranked.slice(0, 3)) {
    const button = add(add(list, "li"), "button", undefined, "scan-point");
    button.type = "button";
    add(button, "span", id);
    add(button, "strong", unitValue(value, suffix, signed));
    button.addEventListener("click", () => showStation(id, true));
  }
}

function renderMapLayer() {
  element("map-title").textContent = state.mapLayer === "difference"
    ? "Sai lệch dự báo · LightGBM − Vrain" : state.mapLayer === "probability"
      ? "Xác suất mưa ≥50 mm/24 giờ" : rainLayers[state.mapLayer].title;
  const available = [...state.points.values()].filter((point) => mapValue(point) !== null).length;
  element("coverage").textContent = available + "/" + state.data.stations.length + " trạm có số";
  for (const button of layerButtons) {
    button.setAttribute("aria-pressed", String(button.dataset.layer === state.mapLayer));
  }
  makeLegend();
  highlightList();
  renderPoints();
  highlightStation();
}

function render() {
  const window = currentWindow();
  state.points = new Map(window.points.map((point) => [point.station_id, point]));
  issueControl.value = state.selectedIssue.id;
  const selected = state.selectedIssue;
  const mode = element("map-mode");
  const archived = selected.mode === "prospective" && Date.now() >= new Date(selected.issue_utc).getTime() + 86400000;
  mode.dataset.mode = archived ? "archived" : selected.mode;
  mode.textContent = selected.mode === "historical_replay" ? "Phát lại lịch sử" : archived ? "Dự báo đã lưu" : "Lần phát đã ghi";
  element("mode-date").textContent = calendarDate.format(new Date(selected.issue_utc));
  element("latest-issue").hidden = state.followLatest || selected.id === state.data.snapshots[0].id;
  element("period").textContent = localTime(window.start_utc) + " → " + localTime(window.end_utc) + " (VN)";
  element("issue-meta").textContent = "GFS khởi tạo lúc " + localTime(state.selectedIssue.gfs_init_utc) + " (VN).";
  element("export-forecast").href = "/api/export.csv?" + new URLSearchParams({
    issue: state.selectedIssue.id, day: String(state.day),
  });
  for (const button of dayButtons) button.setAttribute("aria-pressed", String(Number(button.dataset.day) === state.day));
  renderMapLayer();
  if (state.stationId) renderStation();
  syncUrl();
}

async function loadForecasts() {
  const data = await window.PBL6Portal.api("/api/short-range");
  if (data.schema_version !== 1 || data.product !== "short_range" ||
      data.window_hours !== 24 || !data.snapshots.length) throw new Error("Unexpected forecast format");
  return data;
}

function applyViewer() {
  for (const button of layerButtons) {
    if (privateLayers.includes(button.dataset.layer)) button.hidden = !state.member;
  }
  if (!state.member && privateLayers.includes(state.mapLayer)) state.mapLayer = "lightgbm";
  element("monitor-link").hidden = !state.member;
  element("export-forecast").hidden = !state.member;
  if (!state.member) {
    element("account-link").hidden = false;
    element("account-name").hidden = true;
    element("sign-out").hidden = true;
  }
}

function fillIssues() {
  issueControl.replaceChildren();
  for (const issue of state.data.snapshots) {
    const label = issue.mode === "prospective" ? "Lần phát đã ghi" : issue.label;
    option(issueControl, issue.id, calendarDate.format(new Date(issue.issue_utc)) + " · " + label);
  }
}

async function refreshForecasts() {
  if (refreshing || document.hidden || !state) return;
  refreshing = true;
  try {
    const data = await loadForecasts();
    if (JSON.stringify(data) === JSON.stringify(state.data)) return;
    state.data = data;
    state.member = data.viewer === "member";
    state.selectedIssue = (state.followLatest ? null : data.snapshots.find(({id}) => id === state.selectedIssue.id)) ?? data.snapshots[0];
    applyViewer();
    fillIssues();
    render();
  } catch {
    // Keep the last accessible snapshot during a transient request failure.
  } finally {
    refreshing = false;
  }
}

async function start() {
  try {
    const data = await loadForecasts();
    const query = new URLSearchParams(location.search);
    const pinned = data.snapshots.find(({id}) => id === query.get("issue"));
    const selectedIssue = pinned ?? data.snapshots[0];
    const day = [1, 2, 3].includes(Number(query.get("day"))) ? Number(query.get("day")) : 1;
    const stationId = data.stations.find(({station_id}) => station_id === query.get("station"))?.station_id;
    const requestedLayer = layerButtons.find((button) => button.dataset.layer === query.get("layer"))?.dataset.layer;
    state = {data, selectedIssue, day, stationId, mapLayer: requestedLayer ?? "lightgbm",
             member: data.viewer === "member", followLatest: !pinned};
    applyViewer();
    fillIssues();
    for (const station of data.stations) option(stationControl, station.station_id, station.station_id);
    element("map-loading").hidden = true;
    element("workspace").hidden = false;
    showTools(!narrow.matches);
    element("map-legend").open = !narrow.matches;
    initMap(data.stations);
    render();
    if (stationId) showStation(stationId, true);
    issueControl.addEventListener("change", () => {
      state.followLatest = false;
      state.selectedIssue = state.data.snapshots.find((issue) => issue.id === issueControl.value);
      render();
    });
    element("latest-issue").addEventListener("click", () => {
      state.followLatest = true;
      state.selectedIssue = state.data.snapshots[0];
      render();
    });
    element("open-station").addEventListener("click", () => showStation(stationControl.value, true));
    element("fit-map").addEventListener("click", () => fitMap());
    element("tools-toggle").addEventListener("click", () => showTools(element("tools-panel").hidden, true));
    element("close-tools").addEventListener("click", () => showTools(false, true));
    const closeStation = () => {
      element("station-panel").hidden = true;
      markers.get(state.stationId)?.getElement()?.focus({preventScroll: true});
      syncUrl();
    };
    element("close-station").addEventListener("click", closeStation);
    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      if (!element("station-panel").hidden) closeStation();
      else if (!element("tools-panel").hidden) showTools(false, true);
    });
    for (const button of dayButtons) {
      button.addEventListener("click", () => {
        state.day = Number(button.dataset.day);
        render();
      });
    }
    for (const button of layerButtons) {
      button.addEventListener("click", () => {
        state.mapLayer = button.dataset.layer;
        renderMapLayer();
        if (state.stationId) renderStation();
        syncUrl();
      });
    }
    window.setInterval(refreshForecasts, 90000);
    document.addEventListener("visibilitychange", refreshForecasts);
  } catch (error) {
    element("map-loading").hidden = true;
    element("workspace").hidden = true;
    const message = element("load-error");
    message.textContent = "Chưa mở được dữ liệu dự báo. Hãy tải lại trang.";
    message.hidden = false;
    console.error(error);
  }
}

start();
