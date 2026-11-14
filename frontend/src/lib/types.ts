// Shapes of the JSON files the backend writes to frontend/static/data/.

export type Lang = 'mk' | 'en';
export type Names = Record<Lang, string>;
export type Compass = 'N' | 'NE' | 'E' | 'SE' | 'S' | 'SW' | 'W' | 'NW';

export interface Wind {
  max_kmh: number | null;
  gust_max_kmh: number | null;
  from: Compass | null;
  loads: Compass | null;
}

export interface Period {
  snow_cm: number;
  snow_24h_cm: number;
  wind_24h_max_kmh?: number | null;
  temp_24h_min_c?: number | null;
  rain_mm: number;
  temp_min_c: number | null;
  temp_max_c: number | null;
  freezing_level_min_m?: number | null;
  freezing_level_max_m?: number | null;
  wind: Wind;
}

export interface Day {
  date: string;
  when: 'past' | 'today' | 'future';
  snow_cm: number;
  rain_mm: number;
  temp_min_c: number | null;
  temp_max_c: number | null;
  wind_max_kmh: number | null;
  gust_max_kmh: number | null;
  wind_from: Compass | null;
  freezing_min_m: number | null;
  freezing_max_m: number | null;
}

export type Level = 'none' | 'attention' | 'serious';

export interface Flag {
  code: string;
  level: Exclude<Level, 'none'>;
  period?: 'past' | 'next';
  agree?: number; // how many forecast models raise this flag
  models?: number; // out of how many
  [value: string]: unknown;
}

export interface Overnight {
  snow_cm: number;
  rain_mm: number;
  temp_min_c: number | null;
  wind: Wind;
}

export interface WeatherPoint {
  id: string;
  name: Names;
  lon: number;
  lat: number;
  elevation: number;
  wind_level: string;
  past12: Overnight;
  past72: Period;
  next72: Period;
  spread: {
    models: string[];
    snow_next72_cm: [number, number];
    snow_past72_cm: [number, number];
    wind_next72_kmh: [number, number];
  } | null;
  days: Day[];
  flags: Flag[];
}

export interface Place {
  id: string;
  kind: 'resort' | 'touring';
  pilot: boolean;
  name: Names;
  range: Names;
  center: [number, number];
  level: Level;
  sources: { location: string; elevation: string; checked: string };
  headline: {
    elevation: number;
    snow_next72_cm: number;
    snow_past72_cm: number;
    wind_next72: Wind;
    flag_count: number;
  };
  points: WeatherPoint[];
}

export interface Weather {
  issued_utc: string;
  health?: { models: Record<string, string>; consensus: boolean };
  thresholds: Record<string, number>;
  source: string;
  source_url: string;
  places: Place[];
}

export interface TerrainMeta {
  bounds: [number, number, number, number];
  center: [number, number];
  layers: Record<'slope' | 'aspect' | 'relief' | 'contours', { country: string; detail: string }>;
  country_zooms: [number, number];
  detail_zooms: [number, number];
  resolution_m: number;
  source: string;
  slope_legend: { label: string; rgba: number[] }[];
  aspect_legend: { label: Compass; rgb: number[] }[];
  stats: { elevation_min_m: number; elevation_max_m: number };
}

export interface HourlyPoint {
  id: string;
  elevation: number;
  time: string[];
  now_index: number;
  snow_cm: (number | null)[];
  rain_mm: (number | null)[];
  temp_c: (number | null)[];
  wind_kmh: (number | null)[];
  wind_dir: (number | null)[];
  freezing_m: (number | null)[];
}

export interface Source {
  id: string;
  name: string;
  used_for: Names;
  licence: string;
  credit: string;
  url: string;
  terms_url: string;
  checked: string;
}
