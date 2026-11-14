<script lang="ts">
  import { onMount } from 'svelte';
  import { base } from '$app/paths';
  import MapView from '$lib/components/MapView.svelte';
  import Overview from '$lib/components/Overview.svelte';
  import ReportsTab from '$lib/components/ReportsTab.svelte';
  import { REPORTS_ENABLED, store } from '$lib/reports';
  import SourcesPanel from '$lib/components/SourcesPanel.svelte';
  import PrintDocument from '$lib/components/print/PrintDocument.svelte';
  import PrintButton from '$lib/components/PrintButton.svelte';
  import PointInspector from '$lib/components/PointInspector.svelte';
  import TerrainTab from '$lib/components/TerrainTab.svelte';
  import WeatherTab from '$lib/components/WeatherTab.svelte';
  import { nextIssue, skopjeTime } from '$lib/format';
  import { fill } from '$lib/i18n';
  import { currentPlace, initLang, loadFollowed, selectPlace, setLang, t, toggleFollow, ui } from '$lib/state.svelte';
  import type { Source, TerrainMeta, Weather } from '$lib/types';

  const dataBase = `${base}/data/`;
  const s = $derived(t());
  const place = $derived(currentPlace());

  onMount(async () => {
    const params = new URLSearchParams(location.search);
    initLang(params);
    loadFollowed();
    try {
      if (REPORTS_ENABLED) {
        store.list().then((r) => (ui.reports = r)).catch(() => {});
        store.observer().then((o) => (ui.observer = o)).catch(() => {});
      }
      fetch(dataBase + 'sources.json').then((r) => r.json()).then((d) => (ui.sources = d.sources as Source[])).catch(() => {});
      const [meta, weather] = await Promise.all([
        fetch(dataBase + 'terrain/metadata.json').then((r) => r.json() as Promise<TerrainMeta>),
        fetch(dataBase + 'weather.json').then((r) => (r.ok ? (r.json() as Promise<Weather>) : null)).catch(() => null)
      ]);
      ui.meta = meta;
      ui.weather = weather;
      if (!weather) ui.tab = 'terrain';
      const wanted = params.get('place');
      if (wanted && weather?.places.some((p) => p.id === wanted)) selectPlace(wanted);
      const tab = params.get('tab');
      if (tab === 'terrain' || (tab === 'reports' && REPORTS_ENABLED)) ui.tab = tab;
    } catch (err) {
      ui.error = true;
      console.error(err);
    }
  });

  $effect(() => {
    document.documentElement.lang = ui.lang;
  });

  // Offline / stale data notices.
  let online = $state(true);
  const MODEL_NAMES: Record<string, string> = { icon_eu: 'ICON-EU', gfs_seamless: 'GFS', meteofrance_seamless: 'Météo-France' };
  const missingModels = $derived(
    Object.entries(ui.weather?.health?.models ?? {}).filter(([, st]) => st !== 'ok').map(([m]) => MODEL_NAMES[m] ?? m)
  );
  const stale = $derived(ui.weather ? Date.now() - Date.parse(ui.weather.issued_utc) > 24 * 3600e3 : false);
  onMount(() => {
    online = navigator.onLine;
    const up = () => (online = true);
    const down = () => (online = false);
    addEventListener('online', up);
    addEventListener('offline', down);
    return () => {
      removeEventListener('online', up);
      removeEventListener('offline', down);
    };
  });
  // Ask the offline worker to keep the hourly forecasts of followed places.
  $effect(() => {
    const ids = ui.followed;
    if (!ui.weather || !navigator.serviceWorker?.controller) return;
    navigator.serviceWorker.controller.postMessage({ type: 'prefetch', urls: ids.map((id) => `${dataBase}hourly/${id}.json`) });
  });

</script>

<svelte:head>
  <title>{place ? `${place.name[ui.lang]} · ${s.brand}` : `${s.brand}: ${s.tagline}`}</title>
</svelte:head>

<aside class="panel">
  <div class="top">
    <button class="brand" onclick={() => selectPlace(null)} aria-label={s.all_places}>
      <img src="{base}/logo.png" alt="" width="34" height="21" />
      <span><b>{s.brand}</b><small>{s.tagline}</small></span>
    </button>
    <div class="lang" role="group" aria-label="Јазик / Language">
      <button aria-pressed={ui.lang === 'mk'} onclick={() => setLang('mk')}>МК</button>
      <button aria-pressed={ui.lang === 'en'} onclick={() => setLang('en')}>EN</button>
    </div>
  </div>
  {#if place}<button class="back no-print" onclick={() => selectPlace(null)}>‹ {s.all_places}</button>{/if}
  <div class="title">
    <h1>{place ? place.name[ui.lang] : s.country_title}</h1>
    {#if place}
      {@const on = ui.followed.includes(place.id)}
      <div class="actions">
      <button class="follow no-print" aria-pressed={on} onclick={() => toggleFollow(place.id)}>
        <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 1.5l2 4.3 4.6.5-3.4 3.1 1 4.6L8 11.6 3.8 14l1-4.6L1.4 6.3 6 5.8z" /></svg>
        {on ? s.following : s.follow}
      </button>
      <PrintButton />
      </div>
    {/if}
  </div>
  {#if ui.weather && !online}
    <p class="notice offline no-print" role="status">{fill(s.offline, { time: skopjeTime(ui.weather.issued_utc) })}</p>
  {:else if stale && ui.weather}
    <p class="notice stale" role="alert">{fill(s.stale, { time: skopjeTime(ui.weather.issued_utc) })}</p>
  {/if}
  {#if ui.weather?.health && !ui.weather.health.consensus}
    <p class="notice stale" role="alert">{s.no_consensus}</p>
  {:else if ui.weather?.health && missingModels.length}
    <p class="notice offline">{fill(s.model_missing, { models: missingModels.join(', ') })}</p>
  {/if}
  <p class="updated">
    {#if ui.error}{s.load_error}{:else if ui.weather}{fill(s.issued_line, { issued: skopjeTime(ui.weather.issued_utc), next: nextIssue() })}
      <b>{s.not_rating}</b>{/if}
  </p>


  <div class="tabs" role="tablist">
    {#if ui.weather}
      <button role="tab" aria-selected={ui.tab === 'weather'} onclick={() => (ui.tab = 'weather')}>{s.tab_weather}</button>
    {/if}
    <button role="tab" aria-selected={ui.tab === 'terrain'} onclick={() => (ui.tab = 'terrain')}>{s.tab_terrain}</button>
    {#if REPORTS_ENABLED}
      <button role="tab" aria-selected={ui.tab === 'reports'} onclick={() => (ui.tab = 'reports')}>
        {s.tab_reports}{#if ui.reports.length}<span class="count">{ui.reports.length}</span>{/if}
      </button>
    {/if}
  </div>

  {#if ui.tab === 'terrain'}
    <TerrainTab />
  {:else if ui.tab === 'reports' && REPORTS_ENABLED}
    <ReportsTab />
  {:else if place}
    <WeatherTab />
  {:else}
    <Overview />
  {/if}
  <div class="no-print"><SourcesPanel /></div>
</aside>

<!-- After the panel, so keyboard and screen-reader users reach the forecast first. -->
{#if ui.meta}<MapView {dataBase} />{/if}
<PointInspector />

<PrintDocument />

<style>
  :global(:root) {
    --snow: #fafbfc;      /* panel ground */
    --ink: #17283a;       /* text */
    --muted: #5e6b78;     /* secondary text */
    --line: #dce2e8;      /* rules */
    --glacier: #2468a8;   /* snow amounts, selection */
    --tint: #e9f1f9;      /* selected row */
    --signal: #e8a317;    /* things worth attention */
    --signal-bg: #fdf5e2;
    --serious: #b3261e;   /* serious weather (always with symbol + word) */
    --serious-bg: #fbe9e7;
    --rain: #1f9e89;      /* rain bars */
  }
  :global(*) { box-sizing: border-box; }
  :global(html), :global(body) { margin: 0; height: 100%; }
  :global(body) { font: 15px/1.4 system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif; color: var(--ink); background: #dfe5ea; }
  :global(button) { font: inherit; color: inherit; }
  :global(:focus-visible) { outline: 2px solid var(--glacier); outline-offset: 2px; }
  :global(details) { border-top: 1px solid var(--line); }
  :global(details:first-of-type) { margin-top: 10px; }
  :global(summary) { cursor: pointer; padding: 10px 0; font-weight: 600; font-size: 14px; list-style: none; display: flex; justify-content: space-between; }
  :global(summary::-webkit-details-marker) { display: none; }
  :global(summary::after) { content: '+'; color: var(--muted); font-weight: 400; }
  :global(details[open] summary::after) { content: '–'; }
  :global(details > :not(summary)) { margin: 0 0 12px; }
  :global(.small) { font-size: 13px; color: var(--muted); }
  :global(.sr-only) { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
  /* Touch screens: at least 40 px targets. */
  @media (pointer: coarse) {
    .lang button, .tabs button, .follow, .back, :global(.btn), :global(summary) { min-height: 40px; }
    .lang button { min-width: 40px; }
  }

  .panel {
    position: absolute; z-index: 2; top: 12px; left: 12px; width: 368px; max-height: calc(100% - 24px); overflow: auto;
    background: var(--snow); border-radius: 12px; box-shadow: 0 2px 10px #17283a33; padding: 12px 18px 14px;
  }
  .top { display: flex; justify-content: space-between; align-items: center; padding-bottom: 8px; border-bottom: 1px solid var(--line); }
  .brand { display: flex; align-items: center; gap: 8px; border: 0; background: none; padding: 0; cursor: pointer; text-align: left; }
  .brand img { display: block; }
  .brand b { display: block; font-size: 16px; letter-spacing: 0.01em; line-height: 1.1; }
  .brand small { display: block; font-size: 11.5px; color: var(--muted); }
  .back { border: 0; background: none; padding: 8px 0 0; cursor: pointer; color: var(--glacier); font-size: 14px; font-weight: 600; display: block; }
  h1 { font-size: 22px; line-height: 1.15; margin: 6px 0 0; font-weight: 750; letter-spacing: -0.01em; }
  .title { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 6px; }
  .title h1 { flex: 1 1 180px; min-width: 0; }
  .actions { display: flex; gap: 6px; margin-left: auto; }
  .follow { display: inline-flex; align-items: center; gap: 4px; border: 1px solid var(--line); background: #fff; border-radius: 999px; padding: 3px 10px; font-size: 13px; cursor: pointer; white-space: nowrap; }
  .follow svg { width: 14px; height: 14px; fill: none; stroke: var(--ink); stroke-width: 1.4; }
  .follow[aria-pressed='true'] { background: var(--ink); color: #fff; border-color: var(--ink); }
  .follow[aria-pressed='true'] svg { fill: #fff; stroke: #fff; }
  .lang { display: flex; font-size: 13px; }
  .lang button { border: 0; background: none; padding: 4px 6px; cursor: pointer; color: var(--muted); }
  .lang button[aria-pressed='true'] { color: var(--ink); font-weight: 700; text-decoration: underline; text-underline-offset: 3px; }
  .updated { font-size: 12.5px; color: var(--muted); margin: 6px 0 12px; min-height: 2.8em; }
  .updated b { display: block; font-weight: 600; color: var(--ink); }

  .notice { margin: 8px 0 0; padding: 7px 10px; border-radius: 8px; font-size: 13px; font-weight: 600; }
  .notice.offline { background: #eef1f4; color: var(--ink); }
  .notice.stale { background: var(--serious-bg); color: var(--serious); }

  /* Print: a place prints its own A4 document (PrintDocument); the overview prints the panel. */
  @media print {
    @page { size: A4; margin: 0; }
    :global(html), :global(body) { height: auto; background: #fff; }
    :global(body) { print-color-adjust: exact; -webkit-print-color-adjust: exact; }
    :global(.map), :global(.maplibregl-control-container), .lang, .tabs, .updated, :global(.no-print) { display: none !important; }
    :global(body:has(.print-doc)) .panel { display: none !important; }
    .panel { position: static; width: auto; max-height: none; overflow: visible; box-shadow: none; padding: 12mm; border-radius: 0; }
  }
  .tabs { display: flex; gap: 18px; border-bottom: 1px solid var(--line); margin-bottom: 12px; }
  .tabs button { border: 0; background: none; padding: 0 0 8px; cursor: pointer; font-weight: 650; color: var(--muted); border-bottom: 2px solid transparent; margin-bottom: -1px; }
  .tabs button[aria-selected='true'] { color: var(--ink); border-color: var(--ink); }
  .count { display: inline-block; margin-left: 5px; min-width: 18px; padding: 0 5px; border-radius: 9px; background: var(--ink); color: #fff; font-size: 11px; line-height: 18px; text-align: center; }

  @media (max-width: 560px) {
    .panel { top: auto; bottom: 0; left: 0; right: 0; width: auto; max-height: 52%; border-radius: 14px 14px 0 0; padding: 10px 16px 12px; }
  }
</style>
