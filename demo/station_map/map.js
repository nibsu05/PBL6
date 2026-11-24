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

function binFor(value, kind = state.mapLayer) {
  if (value === null) return null;
  if (kind === "difference") return differenceBins.find(({match}) => match(value));
  const bins = kind === "probability" ? probabilityBins : rainBins;
  return bins.find(({limit}) => value < limit);
}

function makeLegend() {
  const list = element("legend-items");
  list.replaceChildren();
  const showDifference = state.mapLayer === "difference";
  const showProbability = state.mapLayer === "probability";
  const bins = showDifference ? differenceBins : showProbability ? probabilityBins : rainBins;
  const areaView = state.view === "area";
  element("legend-title").textContent = showDifference ? "Sai lệch LightGBM − Vrain"
    : showProbability ? "Xác suất dự báo" : areaView ? "Mưa cao nhất tại trạm" : "Dải lượng mưa";
  element("legend-unit").textContent = showProbability ? "%" : "mm/24 giờ";
  const note = element("legend-note");
  note.textContent = showDifference
    ? (areaView ? "Lấy độ lệch lớn nhất tại trạm. Xanh là thiếu, cam là thừa." : "Xanh là dự báo thiếu. Cam là dự báo thừa.")
    : showProbability
      ? (areaView ? "Màu theo xác suất cao nhất trong các trạm thuộc khu vực." : "Khả năng đạt 50 mm trong 24 giờ tại mỗi trạm.")
      : areaView ? "Tổng hợp các trạm nằm trong ranh giới. Vùng xám chưa có số." : "Mỗi điểm biểu thị lượng mưa tại một trạm.";
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
    : state.data.stations.map(({latitude, longitude}) => [latitude, longitude]);
  map.fitBounds(coordinates, {...mapPadding(), maxZoom: 12, animate: false});
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
  url.searchParams.set("day", String(state.day));
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
  return state.selectedIssue.windows.find((window) => window.horizon === state.day);
}

function vietnamDay(value) {
  // Viet Nam is UTC+7. ISO date keys allow date arithmetic without the browser's local zone.
  return new Date(new Date(value).getTime() + 7 * 3600000).toISOString().slice(0, 10);
}

function shortDate(value) {
  const key = vietnamDay(value);
  return key.slice(8) + "/" + key.slice(5, 7);
}

function chooseIssue(issue, followLatest = false) {
  state.selectedIssue = issue;
  state.followLatest = followLatest;
  render();
}

function renderHistory() {
  const recent = state.historyScope === "recent";
  const latest = state.data.snapshots[0];
  const now = Date.now();
  const today = vietnamDay(now);
  const anchor = recent ? today : vietnamDay(latest.issue_utc);
  // Use noon UTC for display and jump by whole days in the same fixed time zone.
  const last = new Date(anchor + "T12:00:00Z");
  const days = Array.from({length: 8}, (_, i) => new Date(last.getTime() - (7 - i) * 86400000));
  const byDay = new Map();
  for (const issue of state.data.snapshots) {
    const key = vietnamDay(issue.issue_utc);
    if (!byDay.has(key)) byDay.set(key, issue);
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

function chooseDay(day) {
  if (state.day === day) return;
  state.day = day;
  render();
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
    const bin = binFor(value);
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
  const query = simplifyName(element("area-search").value);
  const matches = state.areas.filter((area) => {
    if (query && !simplifyName(area.name).includes(query)) return false;
    const summary = state.forecastAreas.get(area.code);
    return filter === "all" || (filter === "rain" && summary.rainy > 0) ||
      (filter === "10" && summary.value !== null && summary.value >= 10) ||
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
      add(value, "i", undefined, "rain-sample-dot").style.setProperty("--rain", binFor(summary.value, "lightgbm").color);
    }
    add(value, "span", formatAmount(summary.value));
    add(row, "td", summary.valid + "/" + area.stationIds.length);
  }
  const message = element("rain-empty");
  message.hidden = matches.length > 0;
  message.textContent = query ? "Không tìm thấy khu vực trong bộ lọc này."
    : filter === "rain" ? "Kỳ này chưa có trạm nào được dự báo từ 1 mm."
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
    add(description, "p", "Lượng LightGBM cao nhất tại trạm", "area-detail-label");
    add(add(description, "div", formatAmount(summary.value), "area-amount"), "small", "mm/24 giờ");
    add(description, "p", summary.rainy + "/" + summary.valid + " trạm có số dự kiến từ 1 mm.");
    if (summary.valid > 1) add(description, "p",
      "Các trạm dự báo từ " + formatAmount(summary.minimum) + " đến " + formatAmount(summary.value) + " mm.");
    else add(description, "p", "Kỳ này chỉ có số từ một trạm.");
  } else {
    add(description, "p", area.stationIds.length ? "Chưa có dự báo hợp lệ tại trạm cho kỳ này."
      : "Khu vực chưa có trạm trong bộ dữ liệu.");
  }
  if (!summary.readings.length) return;
  add(stations, "p", "Chọn trạm để xem dự báo ba ngày");
  const list = add(stations, "ul", undefined, "area-station-list");
  for (const {id, value} of summary.readings) {
    const button = add(add(list, "li"), "button");
    button.type = "button";
    add(button, "span", id);
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
  state.forecastAreas = new Map(state.areas.map((area) => [
    area.code, summarizeArea(area, state.points, (p) => measurement(p, "predicted_mm")),
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
    " khu vực có số cho kỳ đã chọn. Số khu vực tính theo LightGBM." +
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
    add(button, "span", id);
    add(button, "strong", unitValue(value, suffix, signed));
    button.addEventListener("click", () => showStation(id, true));
  }
}

function renderMapLayer() {
  const byArea = state.view === "area";
  element("map-title").textContent = state.mapLayer === "difference"
    ? "Sai lệch dự báo · LightGBM − Vrain" : state.mapLayer === "probability"
      ? "Xác suất mưa ≥50 mm/24 giờ" : rainLayers[state.mapLayer].title;
  const available = [...state.points.values()].filter((point) => mapValue(point) !== null).length;
  element("coverage").textContent = available + "/" + state.data.stations.length + " trạm có số";
  for (const button of layerButtons) {
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
    state.displayAreas = state.mapLayer === "lightgbm" ? state.forecastAreas
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
  element("rain-period").textContent = "Ngày " + state.day + " · " + element("period").textContent;
  element("issue-meta").textContent = "GFS khởi tạo lúc " + localTime(state.selectedIssue.gfs_init_utc) + " (VN).";
  element("export-forecast").href = "/api/export.csv?" + new URLSearchParams({
    issue: state.selectedIssue.id, day: String(state.day),
  });
  const slider = element("horizon-slider");
  slider.value = state.day;
  slider.setAttribute("aria-valuetext", "Ngày " + state.day + " · " + element("period").textContent);
  for (const button of dayButtons) {
    const h = Number(button.dataset.day);
    const end = state.selectedIssue.windows.find((span) => span.horizon === h).end_utc;
    button.querySelector("small").textContent = shortDate(end);
    button.setAttribute("aria-label", "Ngày " + h + " · Kết thúc " + localTime(end));
    button.setAttribute("aria-pressed", String(h === state.day));
  }
  renderHistory();
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
    if (JSON.stringify(data) === JSON.stringify(state.data)) {
      renderHistory();
      return;
    }
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
    const [data, boundaries] = await Promise.all([
      loadForecasts(),
      window.PBL6Portal.api("/api/areas")
        .then((value) => value.type === "FeatureCollection" ? value : null)
        .catch(() => null),
    ]);
    const matched = boundaries ? prepareAreas(boundaries, data.stations) : {shapes: [], unmatched: []};
    const areaByCode = new Map(matched.shapes.map((area) => [area.code, area]));
    const query = new URLSearchParams(location.search);
    const pinned = data.snapshots.find(({id}) => id === query.get("issue"));
    const selectedIssue = pinned ?? data.snapshots[0];
    const day = [1, 2, 3].includes(Number(query.get("day"))) ? Number(query.get("day")) : 1;
    const stationId = data.stations.find(({station_id}) => station_id === query.get("station"))?.station_id;
    const requestedLayer = layerButtons.find((button) => button.dataset.layer === query.get("layer"))?.dataset.layer;
    const view = matched.shapes.length && !stationId && query.get("view") !== "station" ? "area" : "station";
    const areaCode = view === "area" && areaByCode.has(query.get("area")) ? query.get("area") : null;
    state = {data, selectedIssue, day, stationId, mapLayer: requestedLayer ?? "lightgbm",
             member: data.viewer === "member", followLatest: !pinned,
             historyScope: query.get("history") === "recent" ? "recent" : "saved",
             view, areaCode, areaByCode, areas: matched.shapes, unmatched: matched.unmatched};
    applyViewer();
    fillIssues();
    for (const station of data.stations) option(stationControl, station.station_id, station.station_id);
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
    element("horizon-slider").addEventListener("input", (event) => chooseDay(Number(event.target.value)));
    for (const button of dayButtons) button.addEventListener("click", () => chooseDay(Number(button.dataset.day)));
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
