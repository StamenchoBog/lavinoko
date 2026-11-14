<script lang="ts">
  import { COMPASS_DEG } from '$lib/format';
  import { fill } from '$lib/i18n';
  import { KINDS, preparePhoto, store, type Kind } from '$lib/reports';
  import { t, ui } from '$lib/state.svelte';
  import type { Compass } from '$lib/types';

  let { onDone }: { onDone: (saved: boolean) => void } = $props();
  const s = $derived(t());

  const pad = (n: number) => String(n).padStart(2, '0');
  const nowLocal = () => {
    const d = new Date();
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  };

  let kinds: Kind[] = $state([]);
  let when = $state(nowLocal());
  let elevation: number | null = $state(null);
  let aspect: Compass | null = $state(null);
  let size: number | null = $state(null);
  let newSnow: number | null = $state(null);
  let note = $state('');
  let photo: Blob | null = $state(null);
  let photoPreview: string | null = $state(null);
  let error = $state('');
  let busy = $state(false);

  const ASPECTS = Object.keys(COMPASS_DEG) as Compass[];

  function toggle(k: Kind) {
    kinds = kinds.includes(k) ? kinds.filter((x) => x !== k) : [...kinds, k];
  }

  function useGps() {
    navigator.geolocation?.getCurrentPosition(
      (pos) => (ui.draftPoint = { lat: pos.coords.latitude, lon: pos.coords.longitude }),
      () => {},
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  async function onPhoto(e: Event) {
    const file = (e.currentTarget as HTMLInputElement).files?.[0];
    if (!file) return;
    photo = await preparePhoto(file);
    if (photoPreview) URL.revokeObjectURL(photoPreview);
    photoPreview = URL.createObjectURL(photo);
  }

  /** Nearest place within 10 km, so reports can be listed under a place. */
  function nearestPlace(lat: number, lon: number): string | null {
    let best: { id: string; d: number } | null = null;
    for (const p of ui.weather?.places ?? []) {
      const dx = (p.center[0] - lon) * 111 * Math.cos((lat * Math.PI) / 180);
      const dy = (p.center[1] - lat) * 111;
      const d = Math.hypot(dx, dy);
      if (d < 10 && (!best || d < best.d)) best = { id: p.id, d };
    }
    return best?.id ?? null;
  }

  async function save() {
    const pt = ui.draftPoint;
    if (!kinds.length || !pt) {
      error = s.form_need;
      return;
    }
    busy = true;
    error = '';
    try {
      await store.submit(
        {
          observed_at: new Date(when).toISOString(),
          place_id: nearestPlace(pt.lat, pt.lon),
          lat: Math.round(pt.lat * 1e5) / 1e5,
          lon: Math.round(pt.lon * 1e5) / 1e5,
          elevation_m: elevation,
          aspect,
          kinds,
          avalanche_size: kinds.includes('avalanche') ? size : null,
          new_snow_cm: kinds.includes('new_snow') ? newSnow : null,
          note
        },
        photo
      );
      onDone(true);
    } catch (err) {
      console.error(err);
      error = s.form_error;
    } finally {
      busy = false;
    }
  }
</script>

<form onsubmit={(e) => (e.preventDefault(), save())}>
  <h2>{s.form_title}</h2>

  <fieldset>
    <legend>{s.form_what}</legend>
    <div class="chips">
      {#each KINDS as k (k)}
        <button type="button" class="chip" aria-pressed={kinds.includes(k)} onclick={() => toggle(k)}>{s.kinds[k]}</button>
      {/each}
    </div>
  </fieldset>

  {#if kinds.includes('avalanche')}
    <fieldset>
      <legend>{s.form_size}</legend>
      <div class="chips">
        {#each [1, 2, 3, 4, 5] as n (n)}
          <button type="button" class="chip num" aria-pressed={size === n} onclick={() => (size = size === n ? null : n)}>{n}</button>
        {/each}
      </div>
    </fieldset>
  {/if}

  {#if kinds.includes('new_snow')}
    <label>{s.form_new_snow}<input type="number" min="0" max="300" inputmode="numeric" bind:value={newSnow} /></label>
  {/if}

  <fieldset>
    <legend>{s.form_where}</legend>
    <p class="where" class:set={ui.draftPoint}>
      {ui.draftPoint
        ? fill(s.form_where_set, { lat: ui.draftPoint.lat.toFixed(4), lon: ui.draftPoint.lon.toFixed(4) })
        : s.form_where_hint}
    </p>
    {#if kinds.includes('avalanche')}<p class="small">{s.form_where_avalanche}</p>{/if}
    <button type="button" class="ghost" onclick={useGps}>{s.form_gps}</button>
  </fieldset>

  <div class="row">
    <label>{s.form_when}<input type="datetime-local" bind:value={when} max={nowLocal()} /></label>
    <label>{s.form_elevation}<input type="number" min="0" max="3000" inputmode="numeric" bind:value={elevation} /></label>
  </div>

  <fieldset>
    <legend>{s.form_aspect}</legend>
    <div class="aspects">
      {#each ASPECTS as a (a)}
        <button type="button" class="chip num" aria-pressed={aspect === a} onclick={() => (aspect = aspect === a ? null : a)}>{a}</button>
      {/each}
    </div>
  </fieldset>

  <label>{s.form_note}<textarea rows="3" maxlength="1000" bind:value={note}></textarea></label>

  <label class="photo">{s.form_photo}<input type="file" accept="image/*" capture="environment" onchange={onPhoto} /></label>
  {#if photoPreview}<img src={photoPreview} alt="" />{/if}
  <p class="small">{s.form_photo_note}</p>

  {#if error}<p class="error" role="alert">{error}</p>{/if}
  <div class="actions">
    <button type="submit" class="primary" disabled={busy}>{s.form_send}</button>
    <button type="button" class="ghost" onclick={() => onDone(false)}>{s.form_cancel}</button>
  </div>
</form>

<style>
  form { display: grid; gap: 12px; }
  h2 { font-size: 17px; margin: 0; }
  fieldset { border: 0; padding: 0; margin: 0; }
  legend, label { font-size: 13px; font-weight: 650; color: var(--ink); }
  label { display: grid; gap: 4px; }
  legend { margin-bottom: 6px; }
  input, textarea { font: inherit; font-weight: 400; border: 1px solid var(--line); border-radius: 8px; padding: 8px 10px; background: #fff; width: 100%; }
  .row { display: grid; grid-template-columns: 1.4fr 1fr; gap: 8px; }
  .chips { display: flex; flex-wrap: wrap; gap: 6px; }
  .aspects { display: grid; grid-template-columns: repeat(8, 1fr); gap: 4px; }
  .chip { border: 1px solid var(--line); background: #fff; border-radius: 999px; padding: 6px 11px; font-size: 13.5px; cursor: pointer; }
  .chip.num { border-radius: 8px; padding: 6px 0; min-width: 36px; text-align: center; font-weight: 650; }
  .chip[aria-pressed='true'] { background: var(--ink); border-color: var(--ink); color: #fff; }
  .where { margin: 0 0 6px; font-size: 13.5px; color: var(--muted); padding: 8px 10px; border: 1px dashed var(--line); border-radius: 8px; }
  .where.set { color: var(--ink); border-style: solid; border-color: var(--glacier); background: var(--tint); }
  .ghost { border: 1px solid var(--line); background: #fff; border-radius: 8px; padding: 7px 12px; cursor: pointer; font-size: 13.5px; }
  .primary { border: 0; background: var(--glacier); color: #fff; border-radius: 8px; padding: 10px 16px; font-weight: 700; cursor: pointer; }
  .primary:disabled { opacity: 0.6; }
  .actions { display: flex; gap: 8px; }
  img { max-width: 100%; border-radius: 8px; }
  .error { color: var(--serious); font-size: 13.5px; margin: 0; }
</style>
