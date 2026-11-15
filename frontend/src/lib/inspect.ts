// Point inspector: terrain and live weather at any tapped point (for rescuers and route checks).
// Fetched live from Open-Meteo (same terms as the forecast); needs a connection.

export interface Terrain {
  elevation: number;
  slope: number; // degrees
  aspect: string | null; // compass direction the slope faces
}

export interface HourRow {
  time: string;
  temp: number | null;
  precip: number | null;
  snow: number | null;
  wind: number | null;
  gust: number | null;
  dir: number | null;
  cloud: number | null;
  visibility: number | null; // metres
}

const COMPASS = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
// The elevation service uses the 90 m Copernicus DEM: neighbours must lie in other cells, so ≈100 m apart.
// The slope is therefore the average over ~200 m around the point.
const STEP = 0.0009;

/** Elevation of the point and its 8 neighbours (Copernicus DEM via Open-Meteo); slope and aspect from them. */
export async function terrainAt(lat: number, lon: number): Promise<Terrain> {
  const lats: number[] = [];
  const lons: number[] = [];
  for (const dy of [1, 0, -1]) for (const dx of [-1, 0, 1]) {
    lats.push(+(lat + dy * STEP).toFixed(6));
    lons.push(+(lon + dx * STEP).toFixed(6));
  }
  const r = await fetch(`https://api.open-meteo.com/v1/elevation?latitude=${lats.join(',')}&longitude=${lons.join(',')}`);
  if (!r.ok) throw new Error('elevation');
  const z = (await r.json()).elevation as number[] | undefined;
  if (!z || z.length !== 9 || z.some((v) => typeof v !== 'number')) throw new Error('elevation');
  const [z0, z1, z2, z3, z4, z5, z6, z7, z8] = z as [number, number, number, number, number, number, number, number, number];
  const dyM = STEP * 111320;
  const dxM = STEP * 111320 * Math.cos((lat * Math.PI) / 180);
  // Horn's method on the 3×3 window (rows north→south, columns west→east).
  const dzdx = (z2 + 2 * z5 + z8 - (z0 + 2 * z3 + z6)) / (8 * dxM);
  const dzdn = (z0 + 2 * z1 + z2 - (z6 + 2 * z7 + z8)) / (8 * dyM);
  const slope = (Math.atan(Math.hypot(dzdx, dzdn)) * 180) / Math.PI;
  const aspectDeg = ((Math.atan2(-dzdx, -dzdn) * 180) / Math.PI + 360) % 360;
  return { elevation: Math.round(z4), slope, aspect: slope < 5 ? null : (COMPASS[Math.round(aspectDeg / 45) % 8] ?? null) };
}

/** The next 12 hours at the point and its real elevation: what matters for going in on foot or by helicopter. */
export async function weatherAt(lat: number, lon: number, elevation: number): Promise<HourRow[]> {
  const vars = 'temperature_2m,precipitation,snowfall,wind_speed_10m,wind_gusts_10m,wind_direction_10m,cloud_cover,visibility';
  const r = await fetch(
    `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&elevation=${elevation}` +
      `&hourly=${vars}&forecast_hours=13&timezone=Europe%2FSkopje`
  );
  if (!r.ok) throw new Error('weather');
  const h = (await r.json()).hourly;
  return h.time.map((t: string, i: number) => ({
    time: t.slice(11, 16),
    temp: h.temperature_2m[i],
    precip: h.precipitation[i],
    snow: h.snowfall[i],
    wind: h.wind_speed_10m[i],
    gust: h.wind_gusts_10m[i],
    dir: h.wind_direction_10m[i],
    cloud: h.cloud_cover[i],
    visibility: h.visibility[i]
  }));
}

export function toDms(v: number, pos: string, neg: string): string {
  const a = Math.abs(v);
  const d = Math.floor(a);
  const m = Math.floor((a - d) * 60);
  const s = ((a - d) * 60 - m) * 60;
  return `${d}°${String(m).padStart(2, '0')}′${s.toFixed(1).padStart(4, '0')}″ ${v >= 0 ? pos : neg}`;
}

export const compassOf = (deg: number | null) => (deg === null ? '' : COMPASS[Math.round(deg / 45) % 8]);
