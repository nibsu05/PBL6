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
const hourlyRainBins = [
  {limit: .1, label: "<0,1", color: "#d7edf4"},
  {limit: 1, label: "0,1–<1", color: "#9ad5df"},
  {limit: 5, label: "1–<5", color: "#50b4bd"},
  {limit: 10, label: "5–<10", color: "#147f92"},
  {limit: Infinity, label: "≥10", color: "#355597"},
];
const differenceBins = [
  {match: (value) => value <= -50, label: "Thiếu ≥50", color: "#28577a"},
  {match: (value) => value < -10, label: "Thiếu >10 đến <50", color: "#89beda"},
  {match: (value) => value <= 10, label: "Lệch ≤10", color: "#e7eff2"},
  {match: (value) => value < 50, label: "Thừa >10 đến <50", color: "#f0ad73"},
  {match: () => true, label: "Thừa ≥50", color: "#aa451e"},
];
const hourlyDifferenceBins = [
  {match: (value) => value <= -5, label: "Thiếu ≥5", color: "#28577a"},
  {match: (value) => value < -1, label: "Thiếu >1 đến <5", color: "#89beda"},
  {match: (value) => value <= 1, label: "Lệch ≤1", color: "#e7eff2"},
  {match: (value) => value < 5, label: "Thừa >1 đến <5", color: "#f0ad73"},
  {match: () => true, label: "Thừa ≥5", color: "#aa451e"},
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
  bilstm: {title: "Lượng mưa dự báo · Bi-LSTM R", label: "Bi-LSTM R", field: "bilstm_mm"},
  persistence: {title: "Giữ nguyên mưa giờ vừa đo", label: "Giữ mưa", field: "persistence_mm"},
  gfs: {title: "Lượng mưa dự báo · GFS", label: "GFS", field: "gfs_mm"},
  vrain: {title: "Lượng mưa thực đo · Vrain", label: "Vrain", field: "observed_mm"},
};
const privateLayers = ["vrain", "difference"];
const amount = new Intl.NumberFormat("vi-VN", {maximumFractionDigits: 1});
const hourAmount = new Intl.NumberFormat("vi-VN", {maximumFractionDigits: 2});
const percent = new Intl.NumberFormat("vi-VN", {style: "percent", maximumFractionDigits: 1});
const clockTime = new Intl.DateTimeFormat("vi-VN", {
  timeZone: "Asia/Ho_Chi_Minh", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
  day: "2-digit", month: "2-digit", year: "numeric",
});
const calendarDate = new Intl.DateTimeFormat("vi-VN", {
  timeZone: "Asia/Ho_Chi_Minh", day: "2-digit", month: "2-digit", year: "numeric",
});
const timelineClock = new Intl.DateTimeFormat("vi-VN", {
  timeZone: "Asia/Ho_Chi_Minh", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
});
const mapError = element("map-error");
const issueControl = element("issue");
const stationControl = element("station");
const scopeControl = element("station-scope");
const layerButtons = Array.from(document.querySelectorAll("[data-layer]"));
const viewButtons = Array.from(document.querySelectorAll("[data-view]"));
const {prepareAreas, summarizeArea, simplifyName} = window.PBL6Areas;
const areaPaths = new Map();
const areaCollator = new Intl.Collator("vi");
const hoangSaCode = "20333"; // Offshore and outside the default view of the station network.
let state;
let map;
let layer;
let areaLayer;
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

function hourly() {
  return currentWindow().hours === 1;
}

function periodName(window) {
  return (window.hours === 1 ? "Giờ " : "Ngày ") + window.horizon;
}

function periodUnit() {
  return hourly() ? "mm/1 giờ" : "mm/24 giờ";
}

function forecastModel() {
  return hourly() ? "LightGBM R" : "LightGBM B";
}

function modelLayers() {
  return hourly() ? ["lightgbm", "bilstm", "persistence"] : ["lightgbm", "gfs"];
}

function layerAllowed(key) {
  if (privateLayers.includes(key)) return state.member;
  return modelLayers().includes(key) || (key === "probability" && !hourly());
}

function layerLabel(key) {
  return key === "lightgbm" ? forecastModel() : rainLayers[key].label;
}

function namedStation(id) {
  const station = state.stationById.get(id);
  return station && station.name !== id ? station.name + " · " + id : id;
}

function thresholds() {
  return hourly() ? [.1, 5] : [1, 10];
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
  const divisor = hourly() ? 100 : 10;
  const rounded = Math.round(Math.abs(value) * divisor) / divisor;
  const sign = rounded === 0 ? "" : value < 0 ? "−" : signed ? "+" : "";
  return sign + (hourly() ? hourAmount : amount).format(rounded);
}

function binsFor(kind) {
  if (kind === "probability") return probabilityBins;
  if (kind === "difference") return hourly() ? hourlyDifferenceBins : differenceBins;
  return hourly() ? hourlyRainBins : rainBins;
}

function binFor(value, kind = state.mapLayer) {
  if (value === null) return null;
  return binsFor(kind).find((bin) => bin.match ? bin.match(value) : value < bin.limit);
}

function makeLegend() {
  const list = element("legend-items");
  list.replaceChildren();
  const showDifference = state.mapLayer === "difference";
  const showProbability = state.mapLayer === "probability";
  const bins = binsFor(state.mapLayer);
  const areaView = state.view === "area";
  element("legend-title").textContent = showDifference ? "Sai lệch " + forecastModel() + " − Vrain"
    : showProbability ? "Xác suất dự báo" : areaView ? "Mưa cao nhất tại trạm" : "Dải lượng mưa";
  element("legend-unit").textContent = showProbability ? "%" : periodUnit();
  const note = element("legend-note");
  note.textContent = showDifference
    ? (areaView ? "Lấy độ lệch lớn nhất tại trạm. Xanh là thiếu, cam là thừa." : "Xanh là dự báo thiếu. Cam là dự báo thừa.")
    : showProbability
      ? (areaView ? "Màu theo xác suất cao nhất trong các trạm thuộc khu vực." : "Khả năng đạt 50 mm trong 24 giờ tại mỗi trạm.")
      : areaView ? "Màu theo trạm có lượng cao nhất trong xã, phường. Vùng xám chưa có số." : "Mỗi điểm biểu thị lượng mưa tại một trạm.";
  for (const bin of bins) {
    const item = add(list, "li");
    add(item, "span", "", "swatch").style.setProperty("--rain", bin.color);
    add(item, "span", bin.label);
  }
  const missing = add(list, "li");
  add(missing, "span", "", "swatch missing");
  add(missing, "span", areaView ? "Chưa có số liệu" : "Thiếu mẫu");
}

function initMap() {
  if (!window.L) {
    mapError.textContent = "Không tải được bản đồ. Bạn vẫn có thể xem bảng khu vực hoặc chọn trạm.";
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
    mapError.textContent = "Bản đồ nền tải chưa đủ. Lớp dự báo vẫn hiển thị.";
    mapError.hidden = false;
  });
  tiles.on("tileload", () => { mapError.hidden = true; });
  tiles.addTo(map);
  layer = L.layerGroup().addTo(map);
  if (state.areas.length) {
    areaLayer = L.geoJSON(state.areas.map(({feature}) => feature), {
      smoothFactor: 1,
      className: "ward-path",
      onEachFeature: (feature, path) => {
        const code = String(feature.properties.code);
        areaPaths.set(code, path);
        path.on("click", () => pickArea(code));
        path.bindTooltip(document.createTextNode(feature.properties.name), {className: "area-tooltip", sticky: true});
      },
    });
    map.attributionControl.addAttribution(
      'Ranh giới <a href="https://www.tinhthanhpho.com/tp-da-nang">tinhthanhpho.com</a> · <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>'
    );
  }
  fitMap();
}

function mapPadding() {
  if (narrow.matches) return {paddingTopLeft: [25, 141], paddingBottomRight: [26, 232]};
  const left = element("tools-panel").hidden ? 35 : 344;
  const right = element("rain-panel").hidden ? 46 : element("rain-panel").offsetWidth + 33;
  return {paddingTopLeft: [left, 116], paddingBottomRight: [right, 198]};
}

function fitMap() {
  if (!map) return;
  const coordinates = state.view === "area"
    ? state.areas.filter(({code}) => code !== hoangSaCode).flatMap(({bounds: [w, s, e, n]}) => [[s, w], [n, e]])
    : state.activeStations.map(({latitude, longitude}) => [latitude, longitude]);
  if (coordinates.length) map.fitBounds(coordinates, {...mapPadding(), maxZoom: 12, animate: false});
}

function showTools(open, focus = false) {
  element("tools-panel").hidden = !open;
  element("tools-toggle").setAttribute("aria-expanded", String(open));
  if (open && narrow.matches) {
    element("station-panel").hidden = true;
    showRain(false);
  }
  if (focus) element(open ? "close-tools" : "tools-toggle").focus();
}

function showRain(open, focus = false) {
  element("rain-panel").hidden = !open;
  element("rain-toggle").setAttribute("aria-expanded", String(open));
  document.querySelector(".map-shell").classList.toggle("rain-open", open);
  if (open) {
    element("station-panel").hidden = true;
    if (narrow.matches) showTools(false);
  }
  if (focus) element(open ? "close-rain" : "rain-toggle").focus();
}

function changeView(view, fit = true) {
  if (state.view === view || (view === "area" && !state.areas.length)) return;
  state.view = view;
  element("station-panel").hidden = true;
  showRain(view === "area" && !narrow.matches);
  renderMapLayer();
  if (fit) fitMap();
  syncUrl();
}

function showStation(id, pan = false) {
  if (!state.stationById.has(id)) return;
  state.stationId = id;
  changeView("station", false);
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
  url.searchParams.set("lead", currentWindow().lead);
  url.searchParams.delete("day");
  if (state.scope === "all") url.searchParams.set("scope", "all");
  else url.searchParams.delete("scope");
  if (state.view === "station" && state.areas.length) url.searchParams.set("view", "station");
  else url.searchParams.delete("view");
  if (state.view === "area" && state.areaCode) url.searchParams.set("area", state.areaCode);
  else url.searchParams.delete("area");
  if (state.historyScope === "recent") url.searchParams.set("history", "recent");
  else url.searchParams.delete("history");
  if (!element("station-panel").hidden && state.stationId) url.searchParams.set("station", state.stationId);
  else url.searchParams.delete("station");
  if (state.mapLayer !== "lightgbm") url.searchParams.set("layer", state.mapLayer);
  else url.searchParams.delete("layer");
  window.history.replaceState(null, "", url);
}

function currentWindow() {
  return state.selectedIssue.windows[state.step - 1];
}

function updateScope() {
  const shared = new Set(state.data.shared_stations);
  const useShared = state.scope === "common" && shared.size > 0;
  scopeControl.options[0].disabled = shared.size === 0;
  scopeControl.options[0].textContent = shared.size ? "Trạm chung · " + shared.size : "Chưa có tập trạm chung";
  scopeControl.value = useShared ? "common" : "all";
  const branch = hourly() ? "hourly" : "daily";
  state.activeStations = state.data.stations.filter(({station_id, [branch]: supported}) =>
    useShared ? shared.has(station_id) : supported);
  const active = new Set(state.activeStations.map(({station_id}) => station_id));
  const signature = state.activeStations.map(({station_id}) => station_id).join(",");
  if (signature === state.scopeSignature) return;
  state.scopeSignature = signature;
  state.areas = state.geometry.shapes.map((area) => ({...area, stationIds: area.stationIds.filter((id) => active.has(id))}));
  state.areaByCode = new Map(state.areas.map((area) => [area.code, area]));
  state.unmatched = state.geometry.unmatched.filter((id) => active.has(id));
  stationControl.replaceChildren();
  option(stationControl, "", "Chọn trạm");
  for (const {station_id} of state.activeStations) option(stationControl, station_id, namedStation(station_id));
}

function vietnamDay(value) {
  // Viet Nam is UTC+7. ISO date keys allow date arithmetic without the browser's local zone.
  return new Date(new Date(value).getTime() + 7 * 3600000).toISOString().slice(0, 10);
}

function shortDate(value) {
  const key = vietnamDay(value);
  return key.slice(8) + "/" + key.slice(5, 7);
}

function latestForStep(data, step) {
  return data.snapshots.find(({windows}) => windows[step - 1].mode !== "missing") ?? data.snapshots[0];
}

function chooseIssue(issue, followLatest = false) {
  state.selectedIssue = followLatest ? latestForStep(state.data, state.step) : issue;
  state.followLatest = followLatest;
  render();
}

function renderHistory() {
  const recent = state.historyScope === "recent";
  const latest = latestForStep(state.data, state.step);
  const now = Date.now();
  const today = vietnamDay(now);
  const anchor = recent ? today : vietnamDay(latest.issue_utc);
  // Use noon UTC for display and jump by whole days in the same fixed time zone.
  const last = new Date(anchor + "T12:00:00Z");
  const days = Array.from({length: 8}, (_, i) => new Date(last.getTime() - (7 - i) * 86400000));
  const byDay = new Map();
  for (const issue of state.data.snapshots) {
    const key = vietnamDay(issue.issue_utc);
    const previous = byDay.get(key);
    if (!previous || (previous.windows[state.step - 1].mode === "missing" &&
                      issue.windows[state.step - 1].mode !== "missing")) byDay.set(key, issue);
  }
  const dates = Array.from(byDay, ([date, {id, mode}]) => [date, id, mode]);
  const signature = JSON.stringify([recent, anchor, state.selectedIssue.id, dates, now >= last.getTime()]);
  if (signature === state.historySignature) return;
  const scopeChanged = state.historyRenderedScope !== state.historyScope;
  state.historySignature = signature;
  state.historyRenderedScope = state.historyScope;

  const rail = element("history-strip");
  const previous = rail.scrollLeft;
  rail.replaceChildren();
  element("history-title").textContent = (recent ? "Theo lịch " : "Lượt đã lưu ") +
    shortDate(days[0]) + "–" + calendarDate.format(last);
  element("history-scope").textContent = recent ? "Lượt đã lưu" : "Ngày gần đây";
  for (const day of days) {
    const key = vietnamDay(day);
    const issue = byDay.get(key);
    const pending = recent && key === today && now < day.getTime();
    const label = issue ? (issue.mode === "prospective" ? "Đã ghi" : "Phát lại")
      : pending ? "Chờ 19h" : "Thiếu bản";
    const button = add(rail, "button", shortDate(day));
    button.type = "button";
    button.dataset.archiveDate = key;
    button.disabled = !issue;
    button.setAttribute("aria-pressed", String(issue?.id === state.selectedIssue.id));
    button.setAttribute("aria-label", calendarDate.format(day) + " · " + label);
    add(button, "small", label);
    if (issue) button.addEventListener("click", () => {
      chooseIssue(state.data.snapshots.find(({id}) => id === issue.id));
      rail.querySelector('[aria-pressed="true"]')?.focus({preventScroll: true});
    });
  }
  rail.scrollLeft = scopeChanged ? rail.scrollWidth : previous;
}

function chooseStep(step) {
  if (state.step === step) return;
  state.step = step;
  if (state.followLatest) state.selectedIssue = latestForStep(state.data, step);
  render();
}

function renderChart() {
  const chart = element("station-chart");
  chart.replaceChildren();
  const windows = state.selectedIssue.windows.filter((window) => window.hours === currentWindow().hours)
    .map((window) => ({...window, point: window.points.find((point) => point.station_id === state.stationId)}));
  const keys = state.member ? [...modelLayers(), "vrain"] : modelLayers();
  const series = keys.map((key) => ({key, field: rainLayers[key].field, label: layerLabel(key)}));
  const values = windows.flatMap(({point}) => series.map(({field}) => measurement(point, field)));
  chart.hidden = values.every((value) => value === null);
  if (chart.hidden) return;
  const tick = hourly() ? 1 : 10;
  const max = Math.max(tick, Math.ceil(Math.max(...values.filter((value) => value !== null)) / tick) * tick);
  add(chart, "figcaption", hourly() ? "So sánh mưa từng giờ" : "So sánh mưa mỗi ngày");
  const key = add(chart, "div", undefined, "chart-key");
  for (const {label, key: source} of series) {
    const item = add(key, "span");
    add(item, "i").style.setProperty("--series", "var(--series-" + source + ")");
    add(item, "span", label);
  }
  const axis = add(chart, "div", undefined, "chart-axis");
  add(axis, "span", "0");
  add(axis, "span", amount.format(max) + " " + periodUnit());
  for (const window of windows) {
    const {point} = window;
    const day = add(chart, "div", undefined, "chart-day");
    day.setAttribute("aria-current", String(window.lead === currentWindow().lead));
    const dayLabel = periodName(window);
    add(day, "span", dayLabel);
    const group = add(day, "div", undefined, "chart-series");
    for (const {label, field, key: source} of series) {
      const value = measurement(point, field);
      const row = add(group, "div", undefined, "chart-row");
      const desc = dayLabel + " · " + label + " · " + (value === null ? "Thiếu mẫu" : formatAmount(value) + " " + periodUnit());
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
  const window = currentWindow();
  stationControl.value = state.stationId;
  element("station-title").textContent = namedStation(state.stationId);
  element("station-day").textContent = periodName(window) + " · " + window.hours + " giờ";
  const link = element("station-verify");
  link.hidden = !state.member || hourly() || !window.has_truth;
  link.href = "/dashboard?" + new URLSearchParams({issue: state.selectedIssue.id, day: String(window.horizon)});
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
    const currentLabel = signed ? "Sai lệch " + forecastModel() + " − Vrain" : isProbability ? "Xác suất mưa ≥50 mm"
      : layerLabel(state.mapLayer);
    add(detail, "p", currentLabel, "amount-label");
    const main = add(detail, "p", formatAmount(view, signed), "amount");
    if (view !== null) add(main, "span", isProbability ? " %" : " " + periodUnit());
    const list = add(detail, "dl");
    const facts = modelLayers().map((key) => [key, layerLabel(key), unitValue(measurement(point, rainLayers[key].field))]);
    if (!hourly()) facts.push(
      ["probability", "Xác suất mưa ≥50 mm", probability === null ? "—" : percent.format(probability)]);
    if (state.member) facts.unshift(
      ["vrain", "Vrain thực đo", unitValue(observed)],
      ["difference", "Sai lệch " + forecastModel() + " − Vrain", unitValue(difference(point), " mm", true)],
    );
    for (const [type, name, value] of facts) {
      if (type === state.mapLayer) continue;
      const pair = add(list, "div");
      add(pair, "dt", name);
      add(pair, "dd", value);
    }
    if (state.member && observed === null) add(detail, "p", "Chưa có số đo đối chiếu cho kỳ này.", "detail-note");
    if (hourly() || window.lead === "d1") showOverlap(detail);
  }
  renderChart();
  highlightStation();
}

function showOverlap(detail) {
  const forecasts = state.selectedIssue.windows.slice(0, 7).map(({points}) =>
    measurement(points.find(({station_id}) => station_id === state.stationId), "predicted_mm"));
  if (!forecasts.every(Number.isFinite)) return;
  const [day] = forecasts.slice(-1);
  const hours = forecasts.slice(0, 6).reduce((total, value) => total + value, 0);
  const panel = add(detail, "details", undefined, "period-overlap");
  add(panel, "summary", "Đối chiếu sáu giờ đầu và Ngày 1");
  add(panel, "p", "Cộng sáu dự báo giờ của LightGBM R được " + hourAmount.format(hours) +
    " mm. LightGBM B dự báo " + hourAmount.format(day) + " mm cho 24 giờ từ cùng mốc phát.");
  if (hours - day > 1) add(panel, "p", "Hai mô hình dự báo độc lập. Tổng sáu giờ ở lượt này cao hơn dự báo Ngày 1.");
}

function renderPoints() {
  if (!layer) return;
  layer.clearLayers();
  markers = new Map();
  for (const station of state.activeStations) {
    const id = station.station_id;
    const value = mapValue(state.points.get(id));
    const showDifference = state.mapLayer === "difference";
    const showProbability = state.mapLayer === "probability";
    const bin = binFor(value);
    const icon = L.divIcon({
      className: "map-point" + (bin ? "" : " missing"),
      iconSize: [16, 16], iconAnchor: [8, 8],
    });
    const suffix = showProbability ? "%" : " mm";
    const name = namedStation(id) + (bin ? " · " + formatAmount(value, showDifference) + suffix : " · Thiếu mẫu");
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

function updateAreaPaths() {
  if (!areaLayer || !map) return;
  for (const area of state.areas) {
    const path = areaPaths.get(area.code);
    const summary = state.displayAreas.get(area.code);
    const color = binFor(summary.value)?.color ?? "#bac6cd";
    const selected = state.areaCode === area.code;
    path.setStyle({
      color: selected ? "#123d4e" : "#3f6171", weight: selected ? 2.7 : 0.8,
      fillColor: color, fillOpacity: summary.valid ? .75 : .30,
      dashArray: summary.valid ? "" : "3 3",
    });
    if (selected) path.bringToFront();
    const tip = document.createElement("div");
    add(tip, "strong", area.name);
    const suffix = state.mapLayer === "probability" ? "%" : " mm";
    const amount = summary.valid ? unitValue(summary.value, suffix, state.mapLayer === "difference") + " · " +
      summary.valid + "/" + area.stationIds.length + " trạm" : "Chưa có số liệu";
    add(tip, "small", amount);
    path.setTooltipContent(tip);
  }
}

function renderRainRows() {
  const rows = element("rain-rows");
  rows.replaceChildren();
  const filter = element("area-filter").value;
  const [wet, heavy] = thresholds();
  const query = simplifyName(element("area-search").value);
  const matches = state.areas.filter((area) => {
    if (query && !simplifyName(area.name).includes(query)) return false;
    const summary = state.forecastAreas.get(area.code);
    return filter === "all" || (filter === "rain" && summary.rainy > 0) ||
      (filter === "heavy" && summary.value !== null && summary.value >= heavy) ||
      (filter === "data" && summary.valid > 0) || (filter === "missing" && !summary.valid);
  }).sort((a, b) => (state.forecastAreas.get(b.code).value ?? -1) -
    (state.forecastAreas.get(a.code).value ?? -1) || areaCollator.compare(a.name, b.name));
  for (const area of matches) {
    const summary = state.forecastAreas.get(area.code);
    const row = add(rows, "tr");
    const name = add(add(row, "td"), "button", area.name, "rain-place");
    name.type = "button";
    name.dataset.area = area.code;
    name.addEventListener("click", () => pickArea(area.code));
    const value = add(row, "td");
    if (summary.valid) {
      add(value, "i", undefined, "rain-sample-dot").style.setProperty("--rain", binFor(summary.value, state.listLayer).color);
    }
    add(value, "span", formatAmount(summary.value));
    add(row, "td", summary.valid + "/" + area.stationIds.length);
  }
  const message = element("rain-empty");
  message.hidden = matches.length > 0;
  message.textContent = query ? "Không tìm thấy khu vực trong bộ lọc này."
    : filter === "rain" ? "Kỳ này chưa có trạm nào được dự báo từ " + formatAmount(wet) + " mm."
      : "Không có khu vực phù hợp với bộ lọc.";
}

function renderAreaDetail() {
  const area = state.areaByCode.get(state.areaCode);
  element("rain-list-view").hidden = Boolean(area);
  element("area-detail").hidden = !area;
  if (!area) return;

  element("area-title").textContent = area.name;
  const description = element("area-description");
  const stations = element("area-stations");
  description.replaceChildren();
  stations.replaceChildren();
  const summary = state.forecastAreas.get(area.code);
  if (summary.valid) {
    add(description, "p", layerLabel(state.listLayer) + " · lượng cao nhất tại trạm", "area-detail-label");
    add(add(description, "div", formatAmount(summary.value), "area-amount"), "small", periodUnit());
    add(description, "p", summary.rainy + "/" + summary.valid + " trạm có số dự kiến từ " +
      formatAmount(thresholds()[0]) + " mm.");
    if (summary.valid > 1) add(description, "p",
      "Các trạm dự báo từ " + formatAmount(summary.minimum) + " đến " + formatAmount(summary.value) + " mm.");
    else add(description, "p", "Kỳ này chỉ có số từ một trạm.");
  } else {
    add(description, "p", area.stationIds.length ? "Chưa có dự báo hợp lệ tại trạm cho kỳ này."
      : "Khu vực chưa có trạm trong bộ dữ liệu.");
  }
  if (!summary.readings.length) return;
  add(stations, "p", "Chọn trạm để xem các hạn của trạm");
  const list = add(stations, "ul", undefined, "area-station-list");
  for (const {id, value} of summary.readings) {
    const button = add(add(list, "li"), "button");
    button.type = "button";
    add(button, "span", namedStation(id));
    add(button, "strong", unitValue(value));
    button.addEventListener("click", () => showStation(id, true));
  }
}

function pickArea(code) {
  state.areaCode = code;
  showRain(true);
  renderAreaDetail();
  updateAreaPaths();
  const path = areaPaths.get(code);
  if (path) {
    if (narrow.matches) {
      map.panInside(path.getBounds().getCenter(), {paddingTopLeft: [26, 151], paddingBottomRight: [26, 300]});
    } else {
      map.fitBounds(path.getBounds(), {...mapPadding(), maxZoom: 11, animate: false});
    }
  }
  element("back-to-rain").focus({preventScroll: true});
  syncUrl();
}

function renderAreaPanel() {
  const [wet, heavy] = thresholds();
  state.listLayer = modelLayers().includes(state.mapLayer) ? state.mapLayer : "lightgbm";
  const field = rainLayers[state.listLayer].field;
  element("area-unit").textContent = periodUnit();
  element("area-heavy-filter").textContent = "Từ " + formatAmount(heavy) + " mm";
  element("area-note").textContent = "Bảng " + layerLabel(state.listLayer) + " · có mưa từ " +
    formatAmount(wet) + " " + periodUnit() + " tại ít nhất một trạm.";
  state.forecastAreas = new Map(state.areas.map((area) => [
    area.code, summarizeArea(area, state.points, (p) => measurement(p, field), false, wet),
  ]));
  const sources = [...state.forecastAreas.values()];
  const withData = sources.filter((item) => item.valid > 0).length;
  const withRain = sources.filter((item) => item.rainy > 0).length;
  element("rain-count").textContent = withRain;
  const summary = element("rain-overview");
  summary.replaceChildren();
  add(summary, "strong", withRain + " khu vực có tín hiệu mưa");
  add(summary, "span", " · " + withData + "/" + state.areas.length + " khu vực có số");
  element("area-coverage").textContent = withData + "/" + state.areas.length +
    " khu vực có số theo " + layerLabel(state.listLayer) + "." +
    (state.unmatched.length ? " Có " + state.unmatched.length + " trạm chưa ghép được ranh giới." : "");
  renderRainRows();
  renderAreaDetail();
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
    add(button, "span", namedStation(id));
    add(button, "strong", unitValue(value, suffix, signed));
    button.addEventListener("click", () => showStation(id, true));
  }
}

function renderMapLayer() {
  const byArea = state.view === "area";
  element("map-title").textContent = state.mapLayer === "difference"
    ? "Sai lệch · " + forecastModel() + " − Vrain" : state.mapLayer === "probability"
      ? "Xác suất mưa ≥50 mm/24 giờ" : state.mapLayer === "lightgbm"
        ? "Lượng mưa dự báo · " + forecastModel() : rainLayers[state.mapLayer].title;
  const available = state.activeStations.filter(({station_id}) => mapValue(state.points.get(station_id)) !== null).length;
  const count = available + "/" + state.activeStations.length + " trạm có số";
  element("coverage").textContent = count;
  element("period-note").textContent = count + " · " + periodUnit() +
    (state.scope === "common" && state.data.shared_stations.length ? " · Trạm chung" : "") +
    (currentWindow().lead === "d1" ? " · Tính từ giờ phát" : "");
  for (const button of layerButtons) {
    button.hidden = !layerAllowed(button.dataset.layer);
    if (button.dataset.layer === "lightgbm") button.textContent = forecastModel();
    button.setAttribute("aria-pressed", String(button.dataset.layer === state.mapLayer));
  }
  for (const button of viewButtons) {
    button.setAttribute("aria-pressed", String(button.dataset.view === state.view));
    button.disabled = button.dataset.view === "area" && state.areas.length === 0;
  }
  element("station-scan").hidden = byArea;
  element("station-lookup").hidden = byArea;
  const areaStatus = element("area-coverage");
  areaStatus.hidden = !byArea && state.areas.length > 0;
  if (!state.areas.length) areaStatus.textContent = "Chưa có ranh giới khu vực. Bạn có thể xem theo trạm.";
  element("rain-toggle").hidden = state.areas.length === 0;
  element("fit-map").textContent = byArea ? "Xem toàn vùng" : "Xem các trạm";
  makeLegend();
  if (state.areas.length) renderAreaPanel();
  if (byArea) {
    layer?.clearLayers();
    markers = new Map();
    state.displayAreas = state.mapLayer === state.listLayer ? state.forecastAreas
      : new Map(state.areas.map((area) => [
        area.code, summarizeArea(area, state.points, mapValue, state.mapLayer === "difference"),
      ]));
    if (areaLayer) {
      areaLayer.addTo(map);
      updateAreaPaths();
    }
  } else {
    if (areaLayer) areaLayer.remove();
    highlightList();
    renderPoints();
    highlightStation();
  }
}

function renderIssueStatus() {
  const window = currentWindow();
  const selected = state.selectedIssue;
  const mode = element("map-mode");
  const archived = window.mode === "prospective" && Date.now() >= new Date(window.end_utc).getTime();
  mode.dataset.mode = archived ? "archived" : window.mode;
  mode.textContent = window.mode === "missing" ? "Chưa có dự báo" :
    window.mode === "historical_replay" ? "Phát lại lịch sử" : archived ? "Dự báo đã lưu" : "Lần phát đã ghi";
  element("mode-date").textContent = localTime(selected.issue_utc);
  element("latest-issue").hidden = state.followLatest;
  element("issue-meta").textContent = window.mode === "missing" ? "Lượt này chưa có dữ liệu cho hạn đã chọn." :
    window.recorded_utc ? "Mốc dữ liệu " + localTime(selected.issue_utc) +
      " · Công bố " + localTime(window.recorded_utc) + " (VN)." :
    hourly() ? "Phát lại từ 24 giờ mưa Vrain." :
      selected.gfs_init_utc ? "GFS khởi tạo lúc " + localTime(selected.gfs_init_utc) + " (VN)." : "Dự báo lượng mưa ngày.";
}

function render() {
  const window = currentWindow();
  updateScope();
  const active = new Set(state.activeStations.map(({station_id}) => station_id));
  state.points = new Map(window.points.filter(({station_id}) => active.has(station_id))
    .map((point) => [point.station_id, point]));
  if (!layerAllowed(state.mapLayer)) state.mapLayer = "lightgbm";
  issueControl.value = state.selectedIssue.id;
  renderIssueStatus();
  element("period").textContent = localTime(window.start_utc) + " → " + localTime(window.end_utc) + " (VN)";
  element("rain-period").textContent = periodName(window) + " · " + element("period").textContent;
  const csv = element("export-forecast");
  csv.hidden = !state.member || window.mode === "missing";
  csv.href = "/api/export-forecast.csv?" + new URLSearchParams({
    issue: state.selectedIssue.id, lead: window.lead, scope: scopeControl.value,
  });
  const slider = element("horizon-slider");
  slider.value = state.step;
  slider.setAttribute("aria-valuetext", periodName(window) + " · " + element("period").textContent);
  for (const [i, button] of [...element("period-steps").children].entries()) {
    const issue = state.followLatest ? latestForStep(state.data, i + 1) : state.selectedIssue;
    const span = issue.windows[i];
    const missing = span.mode === "missing";
    button.dataset.missing = String(missing);
    button.querySelector("small").textContent = missing ? "Thiếu" :
      span.hours === 1 ? timelineClock.format(new Date(span.end_utc)) : shortDate(span.end_utc);
    button.setAttribute("aria-label", periodName(span) + " · Kết thúc " + localTime(span.end_utc) +
      (missing ? " · Chưa có dự báo" : ""));
    button.setAttribute("aria-pressed", String(i + 1 === state.step));
  }
  renderHistory();
  renderMapLayer();
  if (state.stationId) renderStation();
  syncUrl();
}

async function loadForecasts() {
  const data = await window.PBL6Portal.api("/api/forecast");
  if (data.schema_version !== 1 || data.product !== "station_forecast" ||
      !data.snapshots.length || !data.snapshots.every(({windows}) => windows.length === 9)) {
    throw new Error("Unexpected forecast format");
  }
  return data;
}

function applyViewer() {
  element("monitor-link").hidden = !state.member;
  if (!state.member) {
    element("account-link").hidden = false;
    element("account-name").hidden = true;
    element("sign-out").hidden = true;
  }
}

function fillIssues() {
  issueControl.replaceChildren();
  for (const issue of state.data.snapshots) {
    const label = issue.mode === "prospective" ? "Lần phát đã ghi" : "Phát lại";
    option(issueControl, issue.id, localTime(issue.issue_utc) + " · " + label);
  }
}

async function refreshForecasts() {
  if (refreshing || document.hidden || !state) return;
  refreshing = true;
  try {
    const data = await loadForecasts();
    if (JSON.stringify(data) === JSON.stringify(state.data)) {
      renderIssueStatus();
      renderHistory();
      return;
    }
    if (state.boundaries && JSON.stringify(data.stations) !== JSON.stringify(state.data.stations)) {
      state.geometry = prepareAreas(state.boundaries, data.stations);
      state.scopeSignature = null;
    }
    state.data = data;
    state.stationById = new Map(data.stations.map((station) => [station.station_id, station]));
    state.member = data.viewer === "member";
    state.selectedIssue = (state.followLatest ? null :
      data.snapshots.find(({issue_utc}) => issue_utc === state.selectedIssue.issue_utc)) ?? latestForStep(data, state.step);
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
    const [data, boundaries] = await Promise.all([
      loadForecasts(),
      window.PBL6Portal.api("/api/areas")
        .then((value) => value.type === "FeatureCollection" ? value : null)
        .catch(() => null),
    ]);
    const geometry = boundaries ? prepareAreas(boundaries, data.stations) : {shapes: [], unmatched: []};
    const query = new URLSearchParams(location.search);
    const pinned = data.snapshots.find(({id}) => id === query.get("issue"));
    const firstIssue = pinned ?? data.snapshots[0];
    const legacy = ["1", "2", "3"].includes(query.get("day")) ? "d" + query.get("day") : null;
    const indexed = firstIssue.windows.findIndex(({lead}) => lead === (query.get("lead") ?? legacy));
    const step = Math.max(1, 1 + (indexed >= 0 ? indexed : firstIssue.windows.findIndex(({mode}) => mode !== "missing")));
    const selectedIssue = pinned ?? latestForStep(data, step);
    const stationId = data.stations.find(({station_id}) => station_id === query.get("station"))?.station_id;
    const requestedLayer = layerButtons.find((button) => button.dataset.layer === query.get("layer"))?.dataset.layer;
    const view = geometry.shapes.length && !stationId && query.get("view") !== "station" ? "area" : "station";
    const areaCode = view === "area" && geometry.shapes.some(({code}) => code === query.get("area")) ? query.get("area") : null;
    const scope = query.get("scope") === "all" || (stationId && !data.shared_stations.includes(stationId)) ? "all" : "common";
    state = {data, selectedIssue, step, stationId, scope, mapLayer: requestedLayer ?? "lightgbm",
             member: data.viewer === "member", followLatest: !pinned,
             historyScope: query.get("history") === "recent" ? "recent" : "saved",
             view, areaCode, boundaries, geometry,
             stationById: new Map(data.stations.map((station) => [station.station_id, station]))};
    applyViewer();
    fillIssues();
    updateScope();
    for (const [i, window] of selectedIssue.windows.entries()) {
      const title = window.hours === 1 ? window.horizon + "h" : periodName(window);
      const button = add(element("period-steps"), "button", title);
      button.type = "button";
      button.dataset.lead = window.lead;
      add(button, "small", "");
      button.addEventListener("click", () => chooseStep(i + 1));
    }
    element("map-loading").hidden = true;
    element("workspace").hidden = false;
    showTools(!narrow.matches && view === "station");
    showRain(view === "area" && (!narrow.matches || Boolean(areaCode)));
    element("map-legend").open = !narrow.matches;
    initMap();
    render();
    if (stationId) showStation(stationId, true);
    if (areaCode) pickArea(areaCode);
    issueControl.addEventListener("change", () => {
      chooseIssue(state.data.snapshots.find((issue) => issue.id === issueControl.value));
    });
    scopeControl.addEventListener("change", () => {
      state.scope = scopeControl.value;
      render();
    });
    element("latest-issue").addEventListener("click", () => {
      chooseIssue(state.data.snapshots[0], true);
    });
    element("history-scope").addEventListener("click", () => {
      state.historyScope = state.historyScope === "recent" ? "saved" : "recent";
      renderHistory();
      syncUrl();
    });
    element("open-station").addEventListener("click", () => showStation(stationControl.value, true));
    element("fit-map").addEventListener("click", () => fitMap());
    element("tools-toggle").addEventListener("click", () => showTools(element("tools-panel").hidden, true));
    element("close-tools").addEventListener("click", () => showTools(false, true));
    for (const button of viewButtons) {
      button.addEventListener("click", () => changeView(button.dataset.view));
    }
    element("rain-toggle").addEventListener("click", () => {
      const open = element("rain-panel").hidden;
      if (open && state.view !== "area") changeView("area");
      showRain(open, true);
    });
    element("close-rain").addEventListener("click", () => showRain(false, true));
    element("back-to-rain").addEventListener("click", () => {
      const last = state.areaCode;
      state.areaCode = null;
      renderAreaDetail();
      updateAreaPaths();
      element("rain-rows").querySelector('[data-area="' + last + '"]')?.focus({preventScroll: true});
      syncUrl();
    });
    element("area-search").addEventListener("input", renderRainRows);
    element("area-filter").addEventListener("change", renderRainRows);
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
      else if (!element("rain-panel").hidden) showRain(false, true);
    });
    element("horizon-slider").addEventListener("input", (event) => chooseStep(Number(event.target.value)));
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
