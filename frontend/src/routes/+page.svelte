<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { asset } from '$app/paths';
  import { base } from '#lib/paths.ts';
  import MapView from '#lib/components/MapView.svelte';
  import Overview from '#lib/components/Overview.svelte';
  import SourcesPanel from '#lib/components/SourcesPanel.svelte';
  import PrintButton from '#lib/components/PrintButton.svelte';
  import PointInspector from '#lib/components/PointInspector.svelte';
  import TerrainTab from '#lib/components/TerrainTab.svelte';
  import WeatherTab from '#lib/components/WeatherTab.svelte';
  import { missedIssue, nextIssue, skopjeTime } from '#lib/format.ts';
  import { fill } from '#lib/i18n.ts';
  import { currentPlace, data, initContrast, initLang, loadFollowed, print, selectPlace, setContrast, setLang, t, toggleFollow, ui } from '#lib/state.svelte.ts';
  import { loadData } from '#lib/data.ts';
  import { onBeforePrint, onPrintKey } from '#lib/printLoader.ts';

  const dataBase = `${base}/data/`;
  const s = $derived(t());
  const place = $derived(currentPlace());

  onMount(async () => {
    const params = new URLSearchParams(location.search);
    initLang(params);
    initContrast();
    loadFollowed();
    try {
      loadData('sources', 'sources.json').then((d) => (data.sources = d?.sources ?? []));
      const [meta, weather] = await Promise.all([loadData('terrain', 'terrain/metadata.json'), loadData('weather', 'weather.json')]);
      if (!meta) throw new Error('No valid terrain/metadata.json');
      data.meta = meta;
      data.weather = weather;
      if (!weather) ui.tab = 'terrain';
      const wanted = params.get('place');
      if (wanted && data.placesById.has(wanted)) selectPlace(wanted);
      const tab = params.get('tab');
      if (tab === 'terrain') ui.tab = tab;
    } catch (err) {
      ui.error = true;
      console.error(err);
    }
  });

  $effect(() => {
    document.documentElement.lang = ui.lang;
  });

  // Tabs (WAI-ARIA tabs pattern): only the selected tab is in the Tab order; arrows, Home and End
  // move between tabs and select them at once.
  type Tab = typeof ui.tab;
  const tabs = $derived<Tab[]>([...(data.weather ? (['weather'] as const) : []), 'terrain']);
  function tabKey(e: KeyboardEvent) {
    const n = tabs.length;
    const i = tabs.indexOf(ui.tab);
    const next = { ArrowRight: (i + 1) % n, ArrowLeft: (i - 1 + n) % n, Home: 0, End: n - 1 }[e.key];
    const tab = next === undefined ? undefined : tabs[next];
    if (tab === undefined) return;
    e.preventDefault();
    ui.tab = tab;
    tick().then(() => document.getElementById(`tab-${tab}`)?.focus());
  }
  $effect(() => {
    document.documentElement.dataset.contrast = ui.highContrast ? 'high' : 'normal';
  });

  // Offline / stale data notices.
  let online = $state(true);
  const MODEL_NAMES: Record<string, string> = { icon_eu: 'ICON-EU', gfs_seamless: 'GFS', meteofrance_seamless: 'Météo-France' };
  const missingModels = $derived(
    Object.entries(data.weather?.health?.models ?? {}).filter(([, st]) => st !== 'ok').map(([m]) => MODEL_NAMES[m] ?? m)
  );
  let now = $state(Date.now());
  const stale = $derived(data.weather ? now - Date.parse(data.weather.issued_utc) > 24 * 3600e3 : false);
  // From the data's age, not the connection: on a weak signal the browser still says "online".
  const missed = $derived(data.weather ? missedIssue(data.weather.issued_utc, new Date(now)) : false);
  onMount(() => {
    online = navigator.onLine;
    const up = () => (online = true);
    const down = () => (online = false);
    addEventListener('online', up);
    addEventListener('offline', down);
    const clock = setInterval(() => (now = Date.now()), 60e3);
    // The offline worker showed a stored forecast and has now received a newer one.
    const updated = (e: MessageEvent) => {
      if (e.data?.type !== 'data-updated' || !String(e.data.url).endsWith('/data/weather.json')) return;
      loadData('weather', 'weather.json').then((w) => w && (data.weather = w));
    };
    navigator.serviceWorker?.addEventListener('message', updated);
    return () => {
      removeEventListener('online', up);
      removeEventListener('offline', down);
      clearInterval(clock);
      navigator.serviceWorker?.removeEventListener('message', updated);
    };
  });
  // Ask the offline worker to keep the hourly forecasts of followed places.
  $effect(() => {
    const ids = ui.followed;
    if (!data.weather || !navigator.serviceWorker?.controller) return;
    navigator.serviceWorker.controller.postMessage({ type: 'prefetch', urls: ids.map((id) => `${dataBase}hourly/${id}.json`) });
  });

</script>

<svelte:window onkeydown={onPrintKey} onbeforeprint={onBeforePrint} />

<svelte:head>
  <title>{place ? `${place.name[ui.lang]} · ${s.brand}` : `${s.brand}: ${s.tagline}`}</title>
</svelte:head>

<div class="column">
<!-- Notices about the data sit outside the scrolling panel, so they stay on screen when the panel
     is scrolled (desktop) or hidden behind an open map point (phone). -->
<!-- All "status" (polite): these describe the data and show on every load, so they must not interrupt. -->
<div class="status">
  {#if data.weather && !online}
    <p class="notice offline no-print" role="status">{fill(s.offline, { time: skopjeTime(data.weather.issued_utc) })}</p>
  {:else if stale && data.weather}
    <p class="notice stale" role="status">{fill(s.stale, { time: skopjeTime(data.weather.issued_utc) })}</p>
  {:else if missed && data.weather}
    <p class="notice offline no-print" role="status">{fill(s.missed_issue, { time: skopjeTime(data.weather.issued_utc) })}</p>
  {/if}
  {#if data.weather?.health && !data.weather.health.consensus}
    <p class="notice stale" role="status">{s.no_consensus}</p>
  {:else if data.weather?.health && missingModels.length}
    <p class="notice offline">{fill(s.model_missing, { models: missingModels.join(', ') })}</p>
  {/if}
</div>

<aside class="panel" class:aside={!!ui.inspect}>
  <div class="top">
    <button class="brand" onclick={() => selectPlace(null)} aria-label={s.all_places}>
      <img src={asset('logo.png')} alt="" width="34" height="21" />
      <span><b>{s.brand}</b><small>{s.tagline}</small></span>
    </button>
    <div class="settings">
      <button class="sun" aria-pressed={ui.highContrast} aria-label={s.high_contrast} title={s.high_contrast}
        onclick={() => setContrast(!ui.highContrast)}>
        <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4.5" /><path d="M12 1.5v3M12 19.5v3M1.5 12h3M19.5 12h3M4.6 4.6l2.1 2.1M17.3 17.3l2.1 2.1M4.6 19.4l2.1-2.1M17.3 6.7l2.1-2.1" /></svg>
      </button>
      <div class="lang" role="group" aria-label="Јазик / Language">
        <button aria-pressed={ui.lang === 'mk'} onclick={() => setLang('mk')}>МК</button>
        <button aria-pressed={ui.lang === 'en'} onclick={() => setLang('en')}>EN</button>
      </div>
    </div>
  </div>
  {#if place}
    {@const on = ui.followed.includes(place.id)}
    <!-- Back link and actions share a row, so the place name gets the full width. -->
    <div class="nav no-print">
      <button class="back" onclick={() => selectPlace(null)}>‹ {s.all_places}</button>
      <div class="actions">
        <button class="follow" aria-pressed={on} onclick={() => toggleFollow(place.id)}>
          <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 1.5l2 4.3 4.6.5-3.4 3.1 1 4.6L8 11.6 3.8 14l1-4.6L1.4 6.3 6 5.8z" /></svg>
          {on ? s.following : s.follow}
        </button>
        <PrintButton />
      </div>
    </div>
  {/if}
  <h1>{place ? place.name[ui.lang] : s.country_title}</h1>
  <p class="updated">
    {#if ui.error}{s.load_error}{:else if data.weather}{fill(s.issued_line, { issued: skopjeTime(data.weather.issued_utc), next: nextIssue() })}
      <b>{s.not_rating}</b>{/if}
  </p>


  <div class="tabs" role="tablist" aria-label={s.tabs_label} tabindex="-1" onkeydown={tabKey}>
    {#each tabs as tab (tab)}
      <button role="tab" id="tab-{tab}" aria-selected={ui.tab === tab} aria-controls="tabpanel"
        tabindex={ui.tab === tab ? 0 : -1} onclick={() => (ui.tab = tab)}>
        {#if tab === 'weather'}{s.tab_weather}{:else}{s.tab_terrain}{/if}
      </button>
    {/each}
  </div>

  <div id="tabpanel" role="tabpanel" aria-labelledby="tab-{ui.tab}">
    {#if ui.tab === 'terrain'}
      <TerrainTab />
    {:else if place}
      <WeatherTab />
    {:else}
      <Overview />
    {/if}
  </div>
  <div class="no-print"><SourcesPanel /></div>
</aside>
</div>

<!-- After the panel, so keyboard and screen-reader users reach the forecast first. -->
{#if data.meta}<MapView {dataBase} />{/if}
<PointInspector />

<!-- Loaded with its code on the first print. -->
{#if print.doc}<print.doc />{/if}

<style>
  :global(:root) {
    --snow: #fafbfc;      /* panel ground */
    --ink: #17283a;       /* text */
    --muted: #3d4a57;     /* secondary text (≥ 7:1 on every panel ground: snow glare) */
    --line: #dce2e8;      /* rules */
    --glacier: #0f4c86;   /* snow amounts, links, selection (≥ 7:1) */
    --tint: #e9f1f9;      /* selected row */
    --signal: #b07400;    /* attention symbols (≥ 3:1, WCAG 1.4.11) */
    --attention-ink: #5c3b00; /* attention text (≥ 7:1) */
    --signal-bg: #fdf5e2;
    --serious: #8c1610;   /* serious weather (always with symbol + word; ≥ 7:1) */
    --serious-bg: #fbe9e7;
    --rain: #1f9e89;      /* rain bars */
  }
  /* High contrast for bright snow: pure white ground, no greys, darker rules, heavier text. */
  :global(:root[data-contrast='high']) {
    --snow: #ffffff;
    --ink: #0b1622;
    --muted: #0b1622;
    --line: #5b6773;
    --tint: #dcebfa;
  }
  :global(:root[data-contrast='high'] body) { font-weight: 500; }
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
  /* Touch screens (gloves): at least 48 px targets. */
  @media (pointer: coarse) {
    .brand, .sun, .lang button, .tabs button, .follow, .back, :global(.btn), :global(summary) { min-height: 48px; }
    .lang button, .sun { min-width: 48px; }
  }

  /* Left column (desktop): data notices on top, never scrolled; the panel below scrolls on its own. */
  .column {
    position: absolute; z-index: 2; top: 12px; left: 12px; width: 368px; max-height: calc(100% - 24px);
    display: flex; flex-direction: column; gap: 8px;
    pointer-events: none; /* the gap between the cards belongs to the map */
  }
  .column > * { pointer-events: auto; }
  .status { flex: none; display: flex; flex-direction: column; gap: 6px; }
  .status:not(:has(.notice)) { display: none; }
  .panel {
    min-height: 0; overflow: auto;
    background: var(--snow); border-radius: 12px; box-shadow: 0 2px 10px #17283a33; padding: 12px 18px 14px;
  }
  .top { display: flex; justify-content: space-between; align-items: center; padding-bottom: 8px; border-bottom: 1px solid var(--line); }
  .brand { display: flex; align-items: center; gap: 8px; border: 0; background: none; padding: 0; cursor: pointer; text-align: left; }
  .brand img { display: block; }
  .brand b { display: block; font-size: 16px; letter-spacing: 0.01em; line-height: 1.1; }
  .brand small { display: block; font-size: 11.5px; color: var(--muted); }
  .nav { display: flex; align-items: center; justify-content: space-between; gap: 6px; padding-top: 8px; }
  .back { border: 0; background: none; padding: 0; cursor: pointer; color: var(--glacier); font-size: 14px; font-weight: 600; white-space: nowrap; }
  h1 { font-size: 22px; line-height: 1.15; margin: 6px 0 0; font-weight: 750; letter-spacing: -0.01em; }
  .actions { display: flex; gap: 6px; }
  .follow { display: inline-flex; align-items: center; gap: 4px; border: 1px solid var(--line); background: #fff; border-radius: 999px; padding: 3px 10px; font-size: 13px; cursor: pointer; white-space: nowrap; }
  .follow svg { width: 14px; height: 14px; fill: none; stroke: var(--ink); stroke-width: 1.4; }
  .follow[aria-pressed='true'] { background: var(--ink); color: #fff; border-color: var(--ink); }
  .follow[aria-pressed='true'] svg { fill: #fff; stroke: #fff; }
  .settings { display: flex; align-items: center; gap: 4px; }
  .sun { display: grid; place-items: center; border: 0; background: none; padding: 4px; border-radius: 8px; cursor: pointer; color: var(--muted); }
  .sun svg { width: 20px; height: 20px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; }
  .sun[aria-pressed='true'] { background: var(--ink); color: #fff; }
  .lang { display: flex; font-size: 13px; }
  .lang button { border: 0; background: none; padding: 4px 6px; cursor: pointer; color: var(--muted); }
  .lang button[aria-pressed='true'] { color: var(--ink); font-weight: 700; text-decoration: underline; text-underline-offset: 3px; }
  .updated { font-size: 12.5px; color: var(--muted); margin: 6px 0 12px; min-height: 2.8em; }
  .updated b { display: block; font-weight: 600; color: var(--ink); }

  .notice { margin: 0; padding: 8px 12px; border-radius: 10px; font-size: 13px; font-weight: 600; box-shadow: 0 2px 10px #17283a33; }
  .notice.offline { background: #eef1f4; color: var(--ink); }
  .notice.stale { background: var(--serious-bg); color: var(--serious); }

  /* Print: a place prints its own A4 document (PrintDocument); the overview prints the panel. */
  @media print {
    @page { size: A4; margin: 0; }
    :global(html), :global(body) { height: auto; background: #fff; }
    :global(body) { print-color-adjust: exact; -webkit-print-color-adjust: exact; }
    :global(.map), :global(.maplibregl-control-container), .lang, .tabs, .updated, :global(.no-print) { display: none !important; }
    :global(body:has(.print-doc)) .column { display: none !important; }
    .column { position: static; display: block; width: auto; max-height: none; }
    .status { padding: 12mm 12mm 0; }
    .notice { box-shadow: none; }
    .panel { overflow: visible; box-shadow: none; padding: 12mm; border-radius: 0; }
  }
  .tabs { display: flex; gap: 18px; border-bottom: 1px solid var(--line); margin-bottom: 12px; }
  .tabs button { border: 0; background: none; padding: 0 0 8px; cursor: pointer; font-weight: 650; color: var(--muted); border-bottom: 2px solid transparent; margin-bottom: -1px; }
  .tabs button[aria-selected='true'] { color: var(--ink); border-color: var(--ink); }

  /* Phone: panel and point card are bottom sheets, so the notices go to the top of the screen,
     left of the map buttons, and stay there when the panel gives way to a map point. */
  @media (max-width: 560px) {
    .column { display: contents; }
    .status {
      position: fixed; z-index: 4; top: calc(8px + env(safe-area-inset-top, 0px)); left: 8px; right: 68px;
    }
    .panel.aside { display: none; }
    .panel {
      position: absolute; z-index: 2; bottom: 0; left: 0; right: 0; max-height: 52%;
      border-radius: 14px 14px 0 0; padding: 10px 16px 12px;
    }
  }
</style>
