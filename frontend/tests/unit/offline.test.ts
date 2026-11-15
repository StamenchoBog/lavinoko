import { expect, test } from '@playwright/test';
import { previousIssue, missedIssue } from '../../src/lib/format';
import { staleAppCaches } from '../../src/lib/swcache';

// Skopje is UTC+1 in winter: issues at 08:00 and 17:00 local are 07:00 and 16:00 UTC.

test('previousIssue is the latest scheduled issue at or before now', () => {
  expect(previousIssue(new Date('2026-11-15T10:30:00Z')).toISOString()).toBe('2026-11-15T07:00:00.000Z');
  expect(previousIssue(new Date('2026-11-15T06:59:00Z')).toISOString()).toBe('2026-11-14T16:00:00.000Z');
  expect(previousIssue(new Date('2026-11-15T16:00:00Z')).toISOString()).toBe('2026-11-15T16:00:00.000Z');
});

test('missedIssue: forecast issued before the last scheduled issue (after a 1 h grace)', () => {
  const issued = '2026-11-15T07:05:00Z'; // the 08:00 issue
  expect(missedIssue(issued, new Date('2026-11-15T12:00:00Z'))).toBe(false);
  expect(missedIssue(issued, new Date('2026-11-15T16:30:00Z'))).toBe(false); // 17:00 issue still within grace
  expect(missedIssue(issued, new Date('2026-11-15T17:30:00Z'))).toBe(true); // 17:00 issue should be out
});

test('missedIssue: a run published a little before the scheduled hour counts for that issue', () => {
  expect(missedIssue('2026-11-15T06:40:00Z', new Date('2026-11-15T12:00:00Z'))).toBe(false);
});

test('staleAppCaches keeps the current and the newest previous app shell', () => {
  const keys = ['data-v1', 'app-1', 'tiles-v1', 'app-2', 'app-3', 'app-4'];
  expect(staleAppCaches(keys, 'app-4')).toEqual(['app-1', 'app-2']);
  expect(staleAppCaches(['app-3', 'app-4'], 'app-4')).toEqual([]);
  expect(staleAppCaches(['app-4'], 'app-4')).toEqual([]);
});
