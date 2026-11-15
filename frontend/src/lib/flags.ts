import { num } from './format';
import { fill, type Strings } from './i18n';
import type { Flag } from './types';

/** Identifies a flag within one point: the same code can be raised for the past and the next 72 h. */
export const flagKey = (f: Flag): string => ('period' in f ? `${f.code}:${f.period}` : f.code);

/** The sentence for a weather flag, with its numbers ("Heavy snow coming: 28 cm in 72 hours"). */
export function flagText(f: Flag, s: Strings): string {
  const v: Record<string, unknown> = { ...f };
  for (const k of ['snow_cm', 'wind_kmh', 'rain_mm', 'temp_max_c']) if (k in v) v[k] = num(v[k] as number);
  return fill(s.flags[f.code], v);
}
