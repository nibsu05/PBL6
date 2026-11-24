"use strict";

const {strictEqual, deepStrictEqual} = require("node:assert");
const {test} = require("node:test");
global.window = {};
require("../demo/station_map/areas.js");
const {prepareAreas, summarizeArea, simplifyName} = window.PBL6Areas;

test("polygon assignment respects holes, islands and ambiguous boundaries", () => {
  const square = (x1, y1, x2, y2) => [[x1,y1], [x2,y1], [x2,y2], [x1,y2], [x1,y1]];
  const feature = (code, type, coordinates) => ({properties: {code, name: code}, geometry: {type, coordinates}});
  const geo = {features: [
    feature("A", "Polygon", [square(0,0,5,5), square(1,1,2,2)]),
    feature("B", "MultiPolygon", [[square(5,0,6,5)], [square(8,8,9,9)]]),
  ]};
  const stations = [
    ["inside",3,3], ["hole",1.5,1.5], ["shared",5,1], ["island",8.5,8.5], ["out",7,7],
  ].map(([station_id, longitude, latitude]) => ({station_id, longitude, latitude}));
  const {shapes, unmatched} = prepareAreas(geo, stations);
  deepStrictEqual(shapes.map((shape) => shape.stationIds), [["inside"], ["island"]]);
  deepStrictEqual(unmatched, ["hole", "shared", "out"]);
});

test("a dry station is valid and a missing station cannot create rain", () => {
  const area = {stationIds: ["dry", "rainy", "missing", "below"]};
  const points = new Map([["dry", 0], ["rainy", 1], ["below", .99], ["outside", 66]]);
  const summary = summarizeArea(area, points, (value) => value);
  deepStrictEqual([summary.valid, summary.rainy, summary.value, summary.minimum], [3, 1, 1, 0]);
  strictEqual(summarizeArea(area, new Map(), (value) => value).value, null);
});

test("the difference view preserves the sign of the largest error", () => {
  const area = {stationIds: ["under", "over"]};
  const points = new Map([["under", -44], ["over", 10]]);
  strictEqual(summarizeArea(area, points, (value) => value, true).value, -44);
  strictEqual(simplifyName("Đà Nẵng"), "da nang");
});

test("a one-hour display can use an independent rain threshold", () => {
  const area = {stationIds: ["trace", "dry", "missing"]};
  const points = new Map([["trace", .2], ["dry", 0]]);
  strictEqual(summarizeArea(area, points, (value) => value).rainy, 0);
  const hour = summarizeArea(area, points, (value) => value, false, .1);
  deepStrictEqual([hour.rainy, hour.valid, hour.value], [1, 2, .2]);
});
