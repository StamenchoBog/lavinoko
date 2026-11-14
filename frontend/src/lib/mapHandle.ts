// Lets the page ask the map for a print picture without passing the MapLibre instance around.

/** A graticule line: its value in degrees and its position as a fraction of the picture (0..1). */
export interface GridLine {
  value: number;
  at: number;
}

export interface MapPicture {
  url: string;
  /** Picture size in CSS pixels (its aspect ratio matches the print frame). */
  width: number;
  height: number;
  /** Ground distance across the full picture width, for the scale bar. */
  widthMeters: number;
  /** Grid spacing in degrees. */
  step: number;
  lons: GridLine[];
  lats: GridLine[];
  /** Requested points, as fractions of the picture; null when outside it. */
  points: ({ x: number; y: number } | null)[];
}

export interface SnapshotRequest {
  /** Output size in CSS pixels; rendered at this size on every device. */
  width: number;
  height: number;
  points: [number, number][];
}

export const mapHandle: { snapshot: ((req: SnapshotRequest) => Promise<MapPicture | null>) | null } = { snapshot: null };
