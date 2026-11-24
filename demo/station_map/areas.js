"use strict";

// Work in the GeoJSON's WGS84 longitude/latitude order. Boundaries are small
// reference areas in one projection and do not cross the antimeridian.
window.PBL6Areas = (() => {
  function locateRing(ring, x, y) {
    let inside = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [ax, ay] = ring[j];
      const [bx, by] = ring[i];
      if (x >= Math.min(ax, bx) && x <= Math.max(ax, bx) && y >= Math.min(ay, by) && y <= Math.max(ay, by) &&
          Math.abs((bx - ax) * (y - ay) - (by - ay) * (x - ax)) < 1e-14) {
        return 0; // On the boundary
      }
      if ((ay > y) !== (by > y) && x < ax + (y - ay) * (bx - ax) / (by - ay)) inside = !inside;
    }
    return inside ? 1 : -1;
  }

  function covers(polygon, x, y) {
    return locateRing(polygon[0], x, y) >= 0 && polygon.slice(1).every((hole) => locateRing(hole, x, y) !== 1);
  }

  function prepareAreas(geojson, stations) {
    const shapes = geojson.features.map((feature) => {
      const {geometry, properties} = feature;
      const polygons = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates;
      const bounds = [Infinity, Infinity, -Infinity, -Infinity];
      for (const [outline] of polygons) {
        for (const [x, y] of outline) {
          bounds[0] = Math.min(bounds[0], x);
          bounds[1] = Math.min(bounds[1], y);
          bounds[2] = Math.max(bounds[2], x);
          bounds[3] = Math.max(bounds[3], y);
        }
      }
      return {code: String(properties.code), name: properties.name, feature, polygons, bounds, stationIds: []};
    });
    const unmatched = [];
    for (const station of stations) {
      const {longitude: x, latitude: y, station_id: id} = station;
      const matches = shapes.filter(({bounds: [west, south, east, north], polygons}) =>
        x >= west && x <= east && y >= south && y <= north && polygons.some((p) => covers(p, x, y)));
      if (matches.length === 1) matches[0].stationIds.push(id);
      else unmatched.push(id);
    }
    return {shapes, unmatched};
  }

  function summarizeArea(area, points, read, magnitude = false) {
    const readings = area.stationIds.map((id) => ({id, value: read(points.get(id))}));
    const valid = readings.filter(({value}) => Number.isFinite(value));
    const best = valid.reduce((peak, item) => {
      if (!peak || (magnitude ? Math.abs(item.value) > Math.abs(peak.value) : item.value > peak.value)) return item;
      return peak;
    }, null);
    return {readings, valid: valid.length, value: best?.value ?? null,
            minimum: valid.length ? Math.min(...valid.map(({value}) => value)) : null,
            rainy: valid.filter(({value}) => value >= 1).length};
  }

  function simplifyName(value) {
    return value.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase().replace(/đ/g, "d").trim();
  }

  return {prepareAreas, summarizeArea, simplifyName};
})();
