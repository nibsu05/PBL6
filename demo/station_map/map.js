"use strict";

const element = (id) => document.getElementById(id);
const bins = [
  {limit: 1, label: "<1", color: "#d7edf4"},
  {limit: 10, label: "1–<10", color: "#9ad5df"},
  {limit: 25, label: "10–<25", color: "#50b4bd"},
  {limit: 50, label: "25–<50", color: "#147f92"},
  {limit: 100, label: "50–<100", color: "#355597"},
  {limit: Infinity, label: "≥100", color: "#332552"},
];
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

function makeLegend() {
  const list = element("legend-items");
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

function renderStation() {
  stationControl.value = state.stationId;
  const point = state.points.get(state.stationId);
  const detail = element("station-detail");
  detail.replaceChildren();
  if (!point) {
    add(detail, "p", "Trạm này thiếu mẫu hợp lệ ở lần phát đã chọn.", "station-missing");
  } else {
    add(detail, "p", "LightGBM B dự báo", "amount-label");
    const main = add(detail, "p", amount.format(point.predicted_mm), "amount");
    add(main, "span", " mm/24 giờ");
    const list = add(detail, "dl");
    for (const [name, value] of [
      ["Vrain thực đo", amount.format(point.observed_mm) + " mm"],
      ["GFS nguyên bản", amount.format(point.gfs_mm) + " mm"],
      ["Xác suất mưa ≥50 mm", percent.format(point.probability_ge50)],
    ]) {
      const pair = add(list, "div");
      add(pair, "dt", name);
      add(pair, "dd", value);
    }
    add(detail, "p", "Số đo dùng để đối chiếu sau khi khoảng dự báo kết thúc.", "detail-note");
  }
  for (const [id, marker] of markers) {
    const chosen = id === state.stationId;
    marker.getElement()?.classList.toggle("chosen", chosen);
    marker.getElement()?.setAttribute("aria-pressed", String(chosen));
    marker.setZIndexOffset(chosen ? 1000 : 0);
  }
}

function renderPoints() {
  if (!layer) return;
  layer.clearLayers();
  markers = new Map();
  for (const station of state.data.stations) {
    const id = station.station_id;
    const point = state.points.get(id);
    const bin = point && bins.find(({limit}) => point.predicted_mm < limit);
    const icon = L.divIcon({
      className: "map-point" + (point ? "" : " missing"),
      iconSize: [16, 16], iconAnchor: [8, 8],
    });
    const name = id + (point ? " · " + amount.format(point.predicted_mm) + " mm" : " · Thiếu mẫu");
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

function render() {
  const window = currentWindow();
  state.points = new Map(window.points.map((point) => [point.station_id, point]));
  if (!state.stationId) {
    const peak = window.points.reduce((best, point) =>
      (!best || point.predicted_mm > best.predicted_mm) ? point : best, null);
    state.stationId = peak?.station_id ?? state.data.stations[0].station_id;
  }
  element("period").textContent = localTime(window.start_utc) + " → " + localTime(window.end_utc) + " (VN)";
  element("coverage").textContent = state.points.size + " / " + state.data.stations.length + " trạm đủ mẫu";
  element("issue-meta").textContent = "GFS khởi tạo lúc " + localTime(state.selectedIssue.gfs_init_utc) + " (VN).";
  for (const button of dayButtons) button.setAttribute("aria-pressed", String(Number(button.dataset.day) === state.day));
  renderPoints();
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
    state = {data, selectedIssue: data.snapshots[0], day: 1, stationId: null};
    for (const issue of data.snapshots) option(issueControl, issue.id, localTime(issue.issue_utc) + " · " + issue.label);
    for (const station of data.stations) option(stationControl, station.station_id, station.station_id);
    makeLegend();
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
  } catch (error) {
    element("workspace").hidden = true;
    const message = element("load-error");
    message.textContent = "Chưa mở được dữ liệu phát lại. Chạy scripts/close_short_range.py để tạo bản dữ liệu trên máy.";
    message.hidden = false;
    console.error(error);
  }
}

start();
