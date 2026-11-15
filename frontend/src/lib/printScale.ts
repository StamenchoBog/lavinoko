// The printed map is at a fixed scale, so 1 cm on paper is always the same ground distance.

/** Map frame on paper, in mm (full content width of an A4 page). */
export const MAP_MM = { width: 190, height: 172 };

/** Map scale of the conditions sheet: 1:25,000 (1 mm on paper = 25 m on the ground). */
export const PRINT_SCALE = 25000;

/** Web Mercator zoom (512-px tiles) at which `widthPx` CSS pixels span `groundWidthM` metres at `lat`. */
export function zoomForGroundWidth(lat: number, widthPx: number, groundWidthM: number): number {
  return Math.log2((40075016.686 * Math.cos((lat * Math.PI) / 180) * widthPx) / (512 * groundWidthM));
}

/**
 * Centre of the printed map, [lon, lat]: the middle of the forecast points, so all of them are on
 * the map (a place's own centre can sit at one end, e.g. a lift base below the summit point).
 * Rounded to 4 decimals (about 10 m).
 */
export function frameCenter(points: [number, number][], fallback: [number, number]): [number, number] {
  if (!points.length) return fallback;
  const mid = (v: number[]) => Math.round(((Math.min(...v) + Math.max(...v)) / 2) * 1e4) / 1e4;
  return [mid(points.map((p) => p[0])), mid(points.map((p) => p[1]))];
}

/** `p`, or `fallback` if it has not settled after `ms`: printing must never wait forever on a stalled request. */
export function withTimeout<T>(p: Promise<T>, ms: number, fallback: T): Promise<T> {
  return Promise.race([p, new Promise<T>((resolve) => setTimeout(() => resolve(fallback), ms))]);
}
