// Field reports from invited observers. The page uses only ReportStore; the current store is local
// (IndexedDB, test sign-in). Hosting = one more ReportStore implementation (docs/architecture/).
import type { Compass } from './types';

/** Field reports are switched off until the feature is developed further (tab, map pins, loading). */
export const REPORTS_ENABLED = false;

export const KINDS = ['avalanche', 'cracking', 'whumpf', 'drifting', 'new_snow', 'wet_snow', 'other'] as const;
export type Kind = (typeof KINDS)[number];
export const ROLES = ['guide', 'patrol', 'rescue', 'forecaster', 'observer'] as const;
export type Role = (typeof ROLES)[number];

export interface Report {
  id: string;
  created_at: string;
  observed_at: string;
  place_id: string | null;
  lat: number;
  lon: number;
  elevation_m: number | null;
  aspect: Compass | null;
  kinds: Kind[];
  avalanche_size: number | null;
  new_snow_cm: number | null;
  note: string | null;
  photo: string | null; // URL the page can show
  display_role: Role;
  organisation: string | null;
}

export type Draft = Omit<Report, 'id' | 'created_at' | 'photo' | 'display_role' | 'organisation'>;

export interface Observer {
  role: Role;
  organisation: string | null;
}

export interface ReportStore {
  /** Shown in the page so nobody mistakes test data for real reports. */
  readonly mode: 'local' | 'online';
  list(): Promise<Report[]>;
  observer(): Promise<Observer | null>;
  /** Local mode: pick a role. Online mode: send a sign-in link to an invited e-mail. */
  signIn(arg: { role: Role; organisation: string | null } | { email: string }): Promise<void>;
  signOut(): Promise<void>;
  submit(draft: Draft, photo: Blob | null): Promise<void>;
  remove(id: string): Promise<void>;
}

/** Days a report stays visible. */
const REPORT_DAYS = 30;

/**
 * Re-encode a photo as a JPEG of at most 1600 px. Drawing it onto a canvas drops all EXIF data,
 * including the camera's GPS position and device details, before the photo is stored anywhere.
 */
export async function preparePhoto(file: File): Promise<Blob> {
  const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' });
  const scale = Math.min(1, 1600 / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement('canvas');
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  canvas.getContext('2d')!.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();
  return new Promise((resolve, reject) =>
    canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('photo'))), 'image/jpeg', 0.82)
  );
}

// --- Local store: IndexedDB in this browser ------------------------------------------------------

interface StoredReport extends Omit<Report, 'photo'> {
  photo_blob: Blob | null;
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open('lavinoko', 1);
    req.onupgradeneeded = () => req.result.createObjectStore('reports', { keyPath: 'id' });
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function tx<T>(mode: IDBTransactionMode, fn: (s: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  return openDb().then(
    (db) =>
      new Promise<T>((resolve, reject) => {
        const req = fn(db.transaction('reports', mode).objectStore('reports'));
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
      })
  );
}

const OBSERVER_KEY = 'lavinoko.localObserver';
const photoUrls = new Map<string, string>();

const localStore: ReportStore = {
  mode: 'local',
  async list() {
    const rows = await tx<StoredReport[]>('readonly', (s) => s.getAll() as IDBRequest<StoredReport[]>);
    const since = Date.now() - REPORT_DAYS * 864e5;
    return rows
      .filter((r) => Date.parse(r.observed_at) > since)
      .sort((a, b) => b.observed_at.localeCompare(a.observed_at))
      .map(({ photo_blob, ...r }) => {
        if (photo_blob && !photoUrls.has(r.id)) photoUrls.set(r.id, URL.createObjectURL(photo_blob));
        return { ...r, photo: photo_blob ? photoUrls.get(r.id)! : null };
      });
  },
  async observer() {
    try {
      const v = localStorage.getItem(OBSERVER_KEY);
      return v ? (JSON.parse(v) as Observer) : null;
    } catch {
      return null;
    }
  },
  async signIn(arg) {
    if (!('role' in arg)) throw new Error('local mode signs in by role');
    localStorage.setItem(OBSERVER_KEY, JSON.stringify(arg));
  },
  async signOut() {
    localStorage.removeItem(OBSERVER_KEY);
  },
  async submit(draft, photo) {
    const who = await this.observer();
    if (!who) throw new Error('not signed in');
    // Plain copy: reactive (proxied) arrays from the form cannot be stored in IndexedDB as they are.
    const plain = JSON.parse(JSON.stringify(draft)) as Draft;
    const row: StoredReport = {
      ...plain,
      note: draft.note?.trim() || null,
      id: crypto.randomUUID(),
      created_at: new Date().toISOString(),
      display_role: who.role,
      organisation: who.organisation,
      photo_blob: photo
    };
    await tx('readwrite', (s) => s.put(row));
  },
  async remove(id) {
    await tx('readwrite', (s) => s.delete(id));
    const url = photoUrls.get(id);
    if (url) URL.revokeObjectURL(url);
    photoUrls.delete(id);
  }
};

export const store: ReportStore = localStore;
