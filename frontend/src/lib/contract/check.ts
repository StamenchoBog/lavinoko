// Checks a fetched data file against the schema generated from the backend models
// (backend/contract/models.py). Supports exactly the JSON Schema subset the generator emits.
// Fields the schema does not know are allowed: a newer backend may add one before the page knows it.
import { SCHEMA } from './schema.gen';
import type { Roots } from './types.gen';

export interface Node {
  type?: 'string' | 'number' | 'integer' | 'boolean' | 'null' | 'object' | 'array';
  enum?: unknown[];
  const?: unknown;
  $ref?: string;
  anyOf?: Node[];
  oneOf?: Node[];
  discriminator?: { propertyName: string; mapping: Record<string, string> };
  properties?: Record<string, Node>;
  required?: string[];
  additionalProperties?: Node;
  items?: Node;
  prefixItems?: Node[];
}

export interface Schema {
  roots: Record<keyof Roots, string>;
  defs: Record<string, Node>;
}

export type DataName = keyof Roots;

const TYPES: Record<NonNullable<Node['type']>, (v: unknown) => boolean> = {
  string: (v) => typeof v === 'string',
  number: (v) => typeof v === 'number' && Number.isFinite(v),
  integer: (v) => Number.isInteger(v),
  boolean: (v) => typeof v === 'boolean',
  null: (v) => v === null,
  object: (v) => typeof v === 'object' && v !== null && !Array.isArray(v),
  array: Array.isArray
};

/** The first problem found, as "path: reason", or null when the value matches. */
function problem(v: unknown, s: Node, path: string, schema: Schema): string | null {
  if (s.$ref) {
    const def = schema.defs[s.$ref];
    return def ? problem(v, def, path, schema) : `${path}: unknown type ${s.$ref}`;
  }
  if (s.discriminator && TYPES.object(v)) {
    const tag = (v as Record<string, unknown>)[s.discriminator.propertyName];
    const ref = typeof tag === 'string' ? s.discriminator.mapping[tag] : undefined;
    return ref ? problem(v, { $ref: ref }, path, schema) : `${path}: unknown ${s.discriminator.propertyName} ${JSON.stringify(tag)}`;
  }
  const alternatives = s.anyOf ?? s.oneOf;
  if (alternatives) {
    const problems = alternatives.map((alt) => problem(v, alt, path, schema));
    return problems.includes(null) ? null : (problems.find((p) => !p?.endsWith('wrong type')) ?? problems[0] ?? null);
  }
  if (s.type && !TYPES[s.type](v)) return `${path}: wrong type`;
  if ('const' in s && v !== s.const) return `${path}: expected ${JSON.stringify(s.const)}`;
  if (s.enum && !s.enum.includes(v)) return `${path}: ${JSON.stringify(v)} is not one of ${s.enum.join(', ')}`;

  if (Array.isArray(v)) {
    if (s.prefixItems) {
      if (v.length !== s.prefixItems.length) return `${path}: expected ${s.prefixItems.length} items`;
      for (const [i, item] of s.prefixItems.entries()) {
        const p = problem(v[i], item, `${path}[${i}]`, schema);
        if (p) return p;
      }
    } else if (s.items) {
      for (const [i, x] of v.entries()) {
        const p = problem(x, s.items, `${path}[${i}]`, schema);
        if (p) return p;
      }
    }
  } else if (TYPES.object(v)) {
    const o = v as Record<string, unknown>;
    for (const key of s.required ?? []) if (!(key in o)) return `${path}.${key}: missing`;
    for (const [key, x] of Object.entries(o)) {
      const prop = s.properties?.[key] ?? s.additionalProperties;
      if (!prop) continue;
      const p = problem(x, prop, `${path}.${key}`, schema);
      if (p) return p;
    }
  }
  return null;
}

/** Why `data` is not a valid `name` file (e.g. "weather.places[2].level: wrong type"), or null if it is. */
export function dataProblem(name: DataName, data: unknown, schema: Schema = SCHEMA): string | null {
  return problem(data, { $ref: schema.roots[name] }, name, schema);
}

export function isData<N extends DataName>(name: N, data: unknown): data is Roots[N] {
  return dataProblem(name, data) === null;
}

/** Which data file a URL path is, for the files the page checks. */
export function dataNameFor(pathname: string): DataName | null {
  if (pathname.endsWith('/data/weather.json')) return 'weather';
  if (pathname.endsWith('/data/sources.json')) return 'sources';
  if (pathname.endsWith('/data/terrain/metadata.json')) return 'terrain';
  if (/\/data\/hourly\/[^/]+\.json$/.test(pathname)) return 'hourly';
  return null;
}
