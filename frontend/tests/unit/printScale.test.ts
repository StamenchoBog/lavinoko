import { expect, test } from '@playwright/test';
import { frameCenter, PRINT_SCALE, withTimeout, zoomForGroundWidth } from '../../src/lib/printScale';

const metresPerPx = (lat: number, z: number) => (40075016.686 * Math.cos((lat * Math.PI) / 180)) / (512 * 2 ** z);

test('zoom 0 shows the equator in one 512 px tile', () => {
  expect(zoomForGroundWidth(0, 512, 40075016.686)).toBeCloseTo(0, 9);
});

test('a 190 mm map at 1:25,000 covers 4750 m across 1500 px', () => {
  const ground = (190 * PRINT_SCALE) / 1000;
  expect(ground).toBe(4750);
  const z = zoomForGroundWidth(41.1, 1500, ground);
  expect(Math.abs(metresPerPx(41.1, z) * 1500 - 4750)).toBeLessThan(0.01);
});

test('twice the ground width is one zoom level lower', () => {
  expect(zoomForGroundWidth(41.1, 1500, 4750) - zoomForGroundWidth(41.1, 1500, 9500)).toBeCloseTo(1, 9);
});

test('the map is centred on the middle of the forecast points', () => {
  expect(frameCenter([[22.2094, 41.1594], [22.205, 41.169], [22.1998, 41.1772]], [22.19, 41.18])).toEqual([22.2046, 41.1683]);
});

test('without points the map is centred on the place', () => {
  expect(frameCenter([], [22.19, 41.18])).toEqual([22.19, 41.18]);
});

test('withTimeout gives the fallback when the promise takes too long', async () => {
  const never = new Promise<string>(() => {});
  expect(await withTimeout(never, 20, 'late')).toBe('late');
  expect(await withTimeout(Promise.resolve('ok'), 1000, 'late')).toBe('ok');
});
