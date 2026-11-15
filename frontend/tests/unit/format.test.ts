import { expect, test } from '@playwright/test';
import { snowFree } from '../../src/lib/format';
import type { WeatherPoint } from '../../src/lib/types';

const point = (depth: number, past: number, next: number) =>
  ({ now: { model_snow_depth_cm: depth }, past72: { snow_cm: past }, next72: { snow_cm: next } }) as unknown as WeatherPoint;

test('a point with no snow on the ground, none fallen and none forecast is snow-free', () => {
  expect(snowFree(point(0, 0, 0))).toBe(true);
});

test('snow on the ground, fallen in the last 72 h or forecast means it is not snow-free', () => {
  expect(snowFree(point(5, 0, 0))).toBe(false);
  expect(snowFree(point(0, 1, 0))).toBe(false);
  expect(snowFree(point(0, 0, 2))).toBe(false);
});

test('an unknown snow depth is not taken as snow-free', () => {
  expect(snowFree({ ...point(0, 0, 0), now: { model_snow_depth_cm: null } } as unknown as WeatherPoint)).toBe(false);
});
