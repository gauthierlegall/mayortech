export const MIN_LON = -4.450;
export const MAX_LON = -4.300;
export const MIN_LAT = 48.310;
export const MAX_LAT = 48.420;

export function projectLonLat(lon, lat) {
  const x = ((lon - MIN_LON) / (MAX_LON - MIN_LON)) * 760 + 70;
  const y = ((MAX_LAT - lat) / (MAX_LAT - MIN_LAT)) * 460 + 60;
  return [Math.round(x * 10) / 10, Math.round(y * 10) / 10];
}

export function unprojectXY(x, y) {
  const lon = ((x - 70) / 760) * (MAX_LON - MIN_LON) + MIN_LON;
  const lat = MAX_LAT - ((y - 60) / 460) * (MAX_LAT - MIN_LAT);
  return [Math.round(lon * 10000) / 10000, Math.round(lat * 10000) / 10000];
}
