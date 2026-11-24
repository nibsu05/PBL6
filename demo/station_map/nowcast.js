"use strict";

const element = id => document.getElementById(`nowcast-${id}`);
const vnOptions = {timeZone: "Asia/Ho_Chi_Minh", hourCycle: "h23"};
const clock = new Intl.DateTimeFormat("vi-VN", {...vnOptions, hour: "2-digit", minute: "2-digit"});
const date = new Intl.DateTimeFormat("vi-VN", {...vnOptions, day: "2-digit", month: "2-digit", year: "numeric"});
const number = new Intl.NumberFormat("vi-VN", {maximumFractionDigits: 2});
const hourMs = 3600000;
let archive, issue, mode, picked, map, markers;
let lead = 1;

function color(q) {
  if (q == null) return "#9ca9ad";
  if (q >= 10) return "#9b304b";
  if (q >= 5) return "#cc7525";
  if (q >= 1) return "#137ca4";
  if (q >= .1) return "#60b9cf";
  return "#c2dce3";
}

function hourEnd(h) {
  return new Date(Date.parse(issue.issue_time) + h * hourMs);
}

function windowLabel(h, full = false) {
  const a = hourEnd(h - 1), b = hourEnd(h);
  const boundary = date.format(a) !== date.format(b);
  const onset = full ? `${clock.format(a)} ${date.format(a)}` : clock.format(a);
  const stop = full || boundary ? `${clock.format(b)} ${date.format(b)}` : clock.format(b);
  return `${onset} → ${stop}`;
}

function node(tag, text) {
  const value = document.createElement(tag);
  if (text != null) value.textContent = text;
  return value;
}

function mm(q) {
  return q == null ? "Thiếu dữ liệu" : `${number.format(q)} mm`;
}

function selection(id, zoom) {
  picked = id;
  const station = archive.stations.find(s => s.id === id);
  if (zoom && map) map.panTo([station.lat, station.lon]);
  render();
}

function renderList() {
  const find = element("search").value.trim().toLocaleLowerCase("vi");
  const minimum = Number(element("filter").value);
  const list = element("list");
  const entries = archive.stations.map(station => ({
    station,
    amount: issue.by_station[station.id]?.forecasts[mode][lead - 1] ?? null,
  }));
  let available = 0;
  for (const {amount} of entries) if (amount != null) available += 1;
  element("coverage").textContent = `${available}/${entries.length} trạm có số`;
  const fragment = document.createDocumentFragment();
  entries.sort((a, b) => (b.amount ?? -1) - (a.amount ?? -1) || a.station.name.localeCompare(b.station.name, "vi"));
  for (const {station, amount} of entries) {
    if (find && !`${station.name} ${station.id}`.toLocaleLowerCase("vi").includes(find)) continue;
    if (minimum > 0 && (amount == null || amount < minimum)) continue;
    const li = node("li");
    const button = node("button");
    button.type = "button";
    button.setAttribute("aria-pressed", String(picked === station.id));
    const label = node("span", station.name);
    label.append(node("small", station.id));
    const rainfall = node("strong", mm(amount));
    rainfall.className = "amount";
    button.append(label, rainfall);
    button.addEventListener("click", () => selection(station.id, true));
    li.append(button);
    fragment.append(li);
  }
  if (!fragment.childElementCount) fragment.append(node("li", "Không có trạm phù hợp bộ lọc."));
  list.replaceChildren(fragment);
}

function renderDetail() {
  const panel = element("detail");
  if (!picked) {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  const station = archive.stations.find(s => s.id === picked);
  const detail = issue.by_station[picked];
  element("station").textContent = `${station.name} · ${station.id}`;
  const slot = element("station-hours");
  if (!detail) {
    slot.replaceChildren(node("p", "Trạm thiếu cửa sổ quan trắc đủ 24 giờ cho lượt này."));
    return;
  }
  const table = node("table");
  const header = table.createTHead().insertRow();
  for (const name of ["Khoảng giờ VN", "Dự báo", ...(detail.observed ? ["Vrain đã đo"] : [])]) {
    const th = node("th", name);
    th.scope = "col";
    header.append(th);
  }
  const records = table.createTBody();
  for (const h of archive.lead_hours) {
    const row = records.insertRow();
    if (h === lead) row.className = "selected";
    for (const value of [windowLabel(h), mm(detail.forecasts[mode][h - 1]),
      ...(detail.observed ? [mm(detail.observed[h - 1])] : [])]) {
      row.insertCell().textContent = value;
    }
  }
  slot.replaceChildren(table);
}

function renderMap() {
  if (!markers) return;
  markers.clearLayers();
  for (const station of archive.stations) {
    const amount = issue.by_station[station.id]?.forecasts[mode][lead - 1] ?? null;
    const point = L.circleMarker([station.lat, station.lon], {
      color: station.id === picked ? "#092d3a" : "#fff", weight: station.id === picked ? 3 : 1.5,
      radius: station.id === picked ? 8 : 6, fillColor: color(amount), fillOpacity: .95,
    }).addTo(markers);
    point.bindTooltip(node("span", `${station.name} · ${mm(amount)}`));
    point.on("click", () => selection(station.id, false));
  }
}

function render() {
  element("slider").value = lead;
  element("lead").textContent = `Giờ ${lead}/6`;
  element("window").textContent = `${windowLabel(lead, true)} (VN)`;
  const buttons = archive.lead_hours.map(h => {
    const button = node("button", clock.format(hourEnd(h)));
    button.type = "button";
    button.setAttribute("aria-label", `Giờ ${h}, kết thúc lúc ${clock.format(hourEnd(h))}`);
    button.setAttribute("aria-pressed", String(h === lead));
    button.addEventListener("click", () => {
      lead = h;
      render();
      element("hours").children[h - 1].focus();
    });
    return button;
  });
  element("hours").replaceChildren(...buttons);
  renderMap();
  renderList();
  renderDetail();
}

function startMap() {
  if (!window.L) {
    const message = element("map-message");
    message.hidden = false;
    message.textContent = "Bản đồ nền chưa tải được. Có thể xem dự báo trong danh sách trạm.";
    return;
  }
  map = L.map(element("map"), {scrollWheelZoom: true});
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18, attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(map);
  markers = L.layerGroup().addTo(map);
  map.fitBounds(archive.stations.map(s => [s.lat, s.lon]), {padding: [32, 60], maxZoom: 11});
}

async function load() {
  const accountRequest = fetch("/api/account").then(response => response.json()).catch(() => ({}));
  const response = await fetch("/api/nowcast-replay");
  if (!response.ok) throw new Error("Replay unavailable");
  archive = await response.json();
  issue = archive.issues.at(-1);
  mode = archive.default_method;
  const account = await accountRequest;
  if (account.username) {
    element("account").textContent = "Theo dõi";
    element("account").href = "/dashboard";
  }
  const dropdown = element("issue");
  archive.issues.forEach((row, i) => {
    dropdown.add(new Option(`${date.format(new Date(row.issue_time))} · ${clock.format(new Date(row.issue_time))}`, i));
  });
  dropdown.value = archive.issues.length - 1;
  dropdown.addEventListener("change", () => { issue = archive.issues[Number(dropdown.value)]; render(); });
  const methods = element("method");
  Object.entries(archive.methods).forEach(([key, label]) => methods.add(new Option(label, key)));
  methods.value = mode;
  methods.addEventListener("change", () => { mode = methods.value; render(); });
  element("slider").addEventListener("input", event => { lead = Number(event.target.value); render(); });
  element("close").addEventListener("click", () => { picked = undefined; render(); });
  element("search").addEventListener("input", renderList);
  element("filter").addEventListener("change", renderList);
  element("status").textContent = "Các lượt đã lưu từ mưa trạm Vrain. Mỗi màu biểu thị lượng mưa trong một giờ tại trạm.";
  element("controls").hidden = false;
  startMap();
  render();
}

load().catch(() => {
  element("status").textContent = "Chưa đọc được lượt dự báo cực ngắn trên máy này.";
});
