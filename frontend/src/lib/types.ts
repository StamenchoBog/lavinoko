// Shapes of the JSON files the backend writes to frontend/static/data/. They are generated from
// backend/contract/models.py (`cd backend && uv run python -m contract.generate`); do not define them here.
import type { Flag, Names } from './contract/types.gen';

export type * from './contract/types.gen';

export type Lang = keyof Names;
export type FlagCode = Flag['code'];
/** The flag type for one code, e.g. `FlagOf<'strong_wind'>`. */
export type FlagOf<C extends FlagCode> = Extract<Flag, { code: C }>;
