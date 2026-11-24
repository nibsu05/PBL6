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
const rainLayers = {
  lightgbm: {title: "Lượng mưa dự báo · LightGBM", label: "LightGBM", field: "predicted_mm"},
  gfs: {title: "Lượng mưa dự báo · GFS", label: "GFS", field: "gfs_mm"},
  vrain: {title: "Lượng mưa thực đo · Vrain", label: "Vrain", field: "observed_mm"},
};
const stationSeries = Object.entries(rainLayers).map(([key, info]) => ({...info, key}));
const amount = new Intl.NumberFormat("vi-VN", {maximumFractionDigits: 1});
const percent = new Intl.NumberFormat("vi-VN", {style: "percent", maximumFractionDigits: 1});
const clockTime = new Intl.DateTimeFormat("vi-VN", {
  timeZone: "Asia/Ho_Chi_Minh", hour: "2-digit", minute: "2-digit", hour12: false,
  day: "2-digit", month: "2-digit", year: "numeric",
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

function measurement(point, field) {
  return Number.isFinite(point?.[field]) ? point[field] : null;
}

function difference(point) {
  const prediction = measurement(point, "predicted_mm");
  const observed = measurement(point, "observed_mm");
  return prediction === null || observed === null ? null : prediction - observed;
}

function mapValue(point) {
  return state.mapLayer === "difference" ? difference(point) : measurement(point, rainLayers[state.mapLayer].field);
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
  const bins = showDifference ? differenceBins : rainBins;
  element("legend-title").textContent = showDifference ? "Sai lệch LightGBM − Vrain" : "Dải lượng mưa";
  const note = element("legend-note");
  note.hidden = !showDifference;
  note.textContent = showDifference ? "Xanh biểu thị dự báo thiếu. Cam biểu thị dự báo thừa." : "";
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
    element("map").hidden = true;
    return;
  }
  map = L.map("map", {scrollWheelZoom: false, minZoom: 4});
  const tiles = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  });
  tiles.on("tileerror", () => {
    mapError.textContent = "Bản đồ nền tải chưa đủ. Điểm trạm vẫn hiển thị đúng vị trí.";
    mapError.hidden = false;
  });
  tiles.addTo(map);
  layer = L.layerGroup().addTo(map);
  map.fitBounds(stations.map(({latitude, longitude}) => [latitude, longitude]), {
    padding: [26, 26], maxZoom: 11,
  });
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
  const values = days.flatMap(({point}) => stationSeries.map(({field}) => measurement(point, field)));
  chart.hidden = values.every((value) => value === null);
  if (chart.hidden) return;
  const max = Math.max(10, Math.ceil(Math.max(...values.filter((value) => value !== null)) / 10) * 10);
  add(chart, "figcaption", "So sánh ba ngày");
  const key = add(chart, "div", undefined, "chart-key");
  for (const {label, key: source} of stationSeries) {
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
    for (const {label, field, key: source} of stationSeries) {
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
  const point = state.points.get(state.stationId);
  const detail = element("station-detail");
  detail.replaceChildren();
  if (!point) {
    add(detail, "p", "Trạm này thiếu mẫu hợp lệ ở lần phát đã chọn.", "station-missing");
  } else {
    add(detail, "p", "LightGBM B dự báo", "amount-label");
    const main = add(detail, "p", formatAmount(measurement(point, "predicted_mm")), "amount");
    add(main, "span", " mm/24 giờ");
    const list = add(detail, "dl");
    for (const [name, value] of [
      ["Vrain thực đo", formatAmount(measurement(point, "observed_mm")) + " mm"],
      ["GFS nguyên bản", formatAmount(measurement(point, "gfs_mm")) + " mm"],
      ["Sai lệch LightGBM − Vrain", formatAmount(difference(point), true) + " mm"],
      ["Xác suất mưa ≥50 mm", percent.format(point.probability_ge50)],
    ]) {
      const pair = add(list, "div");
      add(pair, "dt", name);
      add(pair, "dd", value);
    }
    add(detail, "p", "Số đo dùng để đối chiếu sau khi khoảng dự báo kết thúc.", "detail-note");
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
    const bin = value === null ? null : showDifference
      ? differenceBins.find(({match}) => match(value))
      : rainBins.find(({limit}) => value < limit);
    const icon = L.divIcon({
      className: "map-point" + (bin ? "" : " missing"),
      iconSize: [16, 16], iconAnchor: [8, 8],
    });
    const name = id + (bin ? " · " + formatAmount(value, showDifference) + " mm" : " · Thiếu mẫu");
    const marker = L.marker([station.latitude, station.longitude], {icon, title: name});
    marker.on("click", () => {
      state.stationId = id;
      renderStation();
    });
    marker.addTo(layer);
    const node = marker.getElement();
    node.style.setProperty("--rain", bin ? bin.color : "#f0f3f5");
    node.setAttribute("aria-label", name);
    marker.bindTooltip(document.createTextNode(name), {direction: "top", offset: [0, -7]});
    markers.set(id, marker);
  }
}

function renderMapLayer() {
  element("map-title").textContent = state.mapLayer === "difference"
    ? "Sai lệch dự báo · LightGBM − Vrain" : rainLayers[state.mapLayer].title;
  const available = [...state.points.values()].filter((point) => mapValue(point) !== null).length;
  element("coverage").textContent = available + " / " + state.data.stations.length + " trạm đủ mẫu";
  for (const button of layerButtons) {
    button.setAttribute("aria-pressed", String(button.dataset.layer === state.mapLayer));
  }
  makeLegend();
  renderPoints();
  highlightStation();
}

function render() {
  const window = currentWindow();
  state.points = new Map(window.points.map((point) => [point.station_id, point]));
  if (!state.stationId) {
    const peak = window.points.reduce((best, point) =>
      (!best || point.predicted_mm > best.predicted_mm) ? point : best, null);
    state.stationId = peak?.station_id ?? state.data.stations[0].station_id;
  }
  element("period").textContent = localTime(window.start_utc) + " → " + localTime(window.end_utc) + " (VN)";
  element("issue-meta").textContent = "GFS khởi tạo lúc " + localTime(state.selectedIssue.gfs_init_utc) + " (VN).";
  for (const button of dayButtons) button.setAttribute("aria-pressed", String(Number(button.dataset.day) === state.day));
  renderMapLayer();
  renderStation();
}

async function start() {
  try {
    const response = await fetch("/api/short-range");
    if (!response.ok) throw new Error("Snapshot unavailable");
    const data = await response.json();
    if (data.schema_version !== 1 || data.mode !== "historical_replay" ||
        data.product !== "short_range" || data.window_hours !== 24 || !data.snapshots.length) {
      throw new Error("Unexpected forecast format");
    }
    state = {data, selectedIssue: data.snapshots[0], day: 1, stationId: null, mapLayer: "lightgbm"};
    for (const issue of data.snapshots) option(issueControl, issue.id, localTime(issue.issue_utc) + " · " + issue.label);
    for (const station of data.stations) option(stationControl, station.station_id, station.station_id);
    element("workspace").hidden = false;
    initMap(data.stations);
    render();
    issueControl.addEventListener("change", () => {
      state.selectedIssue = data.snapshots.find((issue) => issue.id === issueControl.value);
      render();
    });
    stationControl.addEventListener("change", () => {
      state.stationId = stationControl.value;
      renderStation();
      if (map && markers.has(state.stationId)) map.panInside(markers.get(state.stationId).getLatLng());
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
      });
    }
  } catch (error) {
    element("workspace").hidden = true;
    const message = element("load-error");
    message.textContent = "Chưa mở được dữ liệu phát lại. Chạy scripts/close_short_range.py để tạo bản dữ liệu trên máy.";
    message.hidden = false;
    console.error(error);
  }
}

start();
