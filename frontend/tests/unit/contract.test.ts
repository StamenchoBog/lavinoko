import { readFileSync } from 'node:fs';
import { expect, test } from '@playwright/test';
import { dataNameFor, dataProblem, type DataName } from '../../src/lib/contract/check';
import { responseProblem } from '../../src/lib/swcache';

// The page's check of fetched data against the schema generated from backend/contract/models.py.

const fixture = (file: string) => JSON.parse(readFileSync(new URL(`../fixtures/data/${file}`, import.meta.url), 'utf-8'));
const FILES: [DataName, string][] = [
  ['weather', 'weather.json'],
  ['hourly', 'hourly/korab.json'],
  ['sources', 'sources.json'],
  ['terrain', 'terrain/metadata.json']
];

for (const [name, file] of FILES) {
  test(`the test copy of ${file} passes the check`, () => {
    expect(dataProblem(name, fixture(file))).toBeNull();
  });
}

test('a broken weather file is refused, with where it is broken', () => {
  const w = fixture('weather.json');
  expect(dataProblem('weather', null)).toBe('weather: wrong type');
  expect(dataProblem('weather', { ...w, places: undefined })).toBe('weather.places: wrong type');
  const { issued_utc: _, ...noIssued } = w;
  expect(dataProblem('weather', noIssued)).toBe('weather.issued_utc: missing');
  w.places[0].level = 'extreme';
  expect(dataProblem('weather', w)).toMatch(/^weather\.places\[0\]\.level: "extreme" is not one of/);
});

test('each flag is checked by its code', () => {
  const w = fixture('weather.json');
  const point = w.places[0].points[0];
  point.flags = [{ code: 'strong_wind', level: 'attention', period: 'next', wind_kmh: 60, gust_kmh: null, from: 'W' }];
  expect(dataProblem('weather', w)).toBeNull();
  point.flags = [{ code: 'strong_wind', level: 'attention', period: 'next', snow_cm: 60 }];
  expect(dataProblem('weather', w)).toBe('weather.places[0].points[0].flags[0].wind_kmh: missing');
  point.flags = [{ code: 'avalanche', level: 'serious' }];
  expect(dataProblem('weather', w)).toBe('weather.places[0].points[0].flags[0]: unknown code "avalanche"');
});

test('pairs must have exactly two values; nullable fields accept null only', () => {
  const w = fixture('weather.json');
  w.places[0].center = [21.5];
  expect(dataProblem('weather', w)).toBe('weather.places[0].center: expected 2 items');
  const h = fixture('hourly/korab.json');
  h.points[0].temp_c[3] = null;
  expect(dataProblem('hourly', h)).toBeNull();
  h.points[0].temp_c[3] = '−3';
  expect(dataProblem('hourly', h)).toBe('hourly.points[0].temp_c[3]: wrong type');
});

test('fields the page does not know yet are allowed (a newer backend may add them)', () => {
  expect(dataProblem('weather', { ...fixture('weather.json'), new_field: { any: 1 } })).toBeNull();
});

test('dataNameFor knows which files are checked', () => {
  expect(dataNameFor('/data/weather.json')).toBe('weather');
  expect(dataNameFor('/lavinoko/data/hourly/korab.json')).toBe('hourly');
  expect(dataNameFor('/data/terrain/metadata.json')).toBe('terrain');
  expect(dataNameFor('/data/sources.json')).toBe('sources');
  expect(dataNameFor('/data/basemap/style.json')).toBeNull();
});

test('responseProblem: only a successful, valid answer may replace the stored copy', async () => {
  const url = 'http://localhost/data/weather.json';
  const ok = new Response(JSON.stringify(fixture('weather.json')));
  expect(await responseProblem(ok, url)).toBeNull();
  expect(await ok.json()).toHaveProperty('places'); // the original response is still readable
  expect(await responseProblem(new Response('{"places": [', { status: 200 }), url)).toBe('not JSON');
  expect(await responseProblem(new Response('{}', { status: 200 }), url)).toBe('weather.issued_utc: missing');
  expect(await responseProblem(new Response('', { status: 503 }), url)).toBe('HTTP 503');
  expect(await responseProblem(new Response('{"version": 8}'), 'http://localhost/data/basemap/style.json')).toBeNull();
});
