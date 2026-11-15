<script lang="ts">
  // The printed conditions sheet for a place: page 1 the 1:25,000 map and conditions, page 2 the
  // detail, a field observation box and emergency information. It carries what the system knows
  // into the field; it is not a trip planner. Every page is a fixed 210 × 297 mm box, so content
  // never spills onto extra pages.
  import { onMount } from 'svelte';
  import { asset } from '$app/paths';
  import { base } from '#lib/paths.ts';
  import { byHeight, COMPASS_DEG, dayLabel, nextIssue, num, skopjeTime } from '#lib/format.ts';
  import { fill } from '#lib/i18n.ts';
  import { resetAfterPrint } from '#lib/printing.ts';
  import { currentPlace, data, print, t, ui } from '#lib/state.svelte.ts';
  import type { Compass, Flag } from '#lib/types.ts';
  import LevelBadge from '../LevelBadge.svelte';
  import PrintChart from './PrintChart.svelte';
  import PrintMap from './PrintMap.svelte';

  const s = $derived(t());
  const place = $derived(currentPlace());
  const points = $derived(place ? byHeight(place.points) : []);
  const top = $derived(points[0]);
  const pages = 2;
  const COMPASS = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'] as const;

  const concerns = $derived.by(() => {
    // eslint-disable-next-line svelte/prefer-svelte-reactivity -- built and read inside this $derived, never kept
    const seen = new Map<string, Flag>();
    for (const p of points)
      for (const f of p.flags) {
        const cur = seen.get(f.code);
        if (!cur || (f.level === 'serious' && cur.level !== 'serious')) seen.set(f.code, f);
      }
    return [...seen.values()].sort((a, b) => Number(b.level === 'serious') - Number(a.level === 'serious')).slice(0, 3);
  });

  const days = $derived(top ? top.days.filter((d) => d.when !== 'past').slice(0, 4) : []);
  const hourlyTop = $derived(print.hourly?.find((h) => h.id === top?.id) ?? null);
  const elevSpan = $derived(points[0] ? `${points.at(-1)?.elevation}–${points[0].elevation} m` : '');
  const coord = (lat: number, lon: number) =>
    `${lat.toFixed(5)}° N, ${lon.toFixed(5)}° E`;
  // The range only when it adds something ("Kožuf · Kožuf" says nothing).
  const rangeName = $derived(place && place.range[ui.lang] !== place.name[ui.lang] ? place.range[ui.lang] : '');
  const freezing = $derived(
    top ? `${num(Math.min(...points.map((p) => p.next72.freezing_level_min_m ?? Infinity)))}–${num(Math.max(...points.map((p) => p.next72.freezing_level_max_m ?? -Infinity)))} m` : ''
  );

  let printedAt = $state(skopjeTime(new Date().toISOString()));
  let qr: { size: number; path: string } | null = $state(null);
  let liveUrl = $state('');

  onMount(() => {
    const before = () => (printedAt = skopjeTime(new Date().toISOString()));
    addEventListener('beforeprint', before);
    addEventListener('afterprint', resetAfterPrint);
    return () => {
      removeEventListener('beforeprint', before);
      removeEventListener('afterprint', resetAfterPrint);
    };
  });

  // QR code to the live forecast for this place, so the paper copy always leads to the latest one.
  $effect(() => {
    if (!place) return;
    liveUrl = `${location.origin}${base}/?place=${place.id}&lang=${ui.lang}`;
    const url = liveUrl;
    import('uqr').then(({ encode }) => {
      const { size, data: cells } = encode(url, { ecc: 'M', border: 0 });
      let path = '';
      cells.forEach((row, y) => row.forEach((on, x) => on && (path += `M${x},${y}h1v1h-1z`)));
      if (url === liveUrl) qr = { size, path };
    });
  });
</script>

{#snippet arrow(from: Compass | null)}
  {#if from}
    <svg class="warrow" viewBox="0 0 16 16" aria-hidden="true" style="transform: rotate({COMPASS_DEG[from] + 180}deg)">
      <path d="M8 1 13 9H9.5v6h-3V9H3z" />
    </svg>
  {/if}
{/snippet}

{#snippet header(page: number, title: string, compact: boolean)}
  <header class:compact>
    <div class="brandrow">
      <span class="brand"><img src={asset('logo.png')} alt="" />{s.brand}</span>
      <span class="doc">{title} <span class="pg">{page}/{pages}</span></span>
    </div>
    <div class="titlerow">
      <div>
        <h1>{place?.name[ui.lang]}</h1>
        <p class="sub">{#if rangeName}{rangeName} · {/if}{elevSpan}</p>
      </div>
      <div class="meta">
        <p>{fill(s.issued_short, { issued: data.weather ? skopjeTime(data.weather.issued_utc) : '', next: nextIssue() })}</p>
        <p>{fill(s.printed_at, { time: printedAt })}</p>
      </div>
    </div>
    {#if !compact}
      <div class="status {place?.level}">
        {#if concerns.length}
          {#each concerns as f (f.code)}
            <span class="concern"><LevelBadge level={f.level} />{s.concern[f.code]}{#if f.agree}<small>{fill(s.agree, { n: f.agree, m: f.models })}</small>{/if}</span>
          {/each}
        {:else}
          <span>{s.summary_calm}</span>
        {/if}
      </div>
    {/if}
    <p class="rating">{s.not_rating}</p>
  </header>
{/snippet}

{#snippet footer(full: boolean)}
  <footer>
    <div class="credits">
      <p>{s.disclaimer}</p>
      {#if full}
        <p>Weather data by Open-Meteo.com (CC BY 4.0). {data.meta?.source}. Map: © OpenMapTiles © OpenStreetMap contributors (ODbL).</p>
      {:else}
        <p>{s.credits_short}</p>
      {/if}
    </div>
    {#if !full && qr}
      <div class="qr">
        <svg viewBox="-2 -2 {qr.size + 4} {qr.size + 4}" aria-label={s.qr_label}><rect x="-2" y="-2" width={qr.size + 4} height={qr.size + 4} fill="#fff" /><path d={qr.path} /></svg>
        <span>{s.qr_label}</span>
      </div>
    {/if}
  </footer>
{/snippet}

{#if place && top}
  <div class="print-doc" lang={ui.lang}>
    <section class="page">
      {@render header(1, s.doc_sheet, false)}

      <PrintMap pic={print.map} labels={points.map((p) => `${p.elevation} m`)} />

      <div>
        <h2>{s.by_elevation}</h2>
        <table>
          <thead>
            <tr>
              <th></th><th>{s.stat_new_snow}</th><th>{s.stat_last24}</th><th>{s.stat_wind}</th><th>{s.stat_temp}</th>
            </tr>
          </thead>
          <tbody>
            {#each points as p, i (p.id)}
              <tr>
                <td><span class="num">{i + 1}</span>{p.elevation} m <span class="muted">{p.name[ui.lang]}</span></td>
                <td><b>{num(p.next72.snow_cm)}</b> cm</td>
                <td>{num(p.past72.snow_24h_cm)} cm</td>
                <td>{@render arrow(p.next72.wind.from)}<b>{num(p.next72.wind.max_kmh)}</b> km/h {p.next72.wind.from ?? ''}</td>
                <td>{num(p.next72.temp_min_c)} … {num(p.next72.temp_max_c)} °C</td>
              </tr>
            {/each}
          </tbody>
        </table>
        <p class="tnote">{s.stat_freezing}: <b>{freezing}</b></p>
      </div>

      <p class="emline"><b>112</b> {s.emergency_line}</p>

      {@render footer(false)}
    </section>

    <section class="page">
      {@render header(2, s.doc_forecast, true)}

      {#if hourlyTop}
        <div>
          <h2>{fill(s.chart_title, { elev: top.elevation })}</h2>
          <PrintChart h={hourlyTop} />
        </div>
      {/if}

      <div>
        <h2>{s.matrix_title}</h2>
        <table class="matrix">
          <thead>
            <tr><th></th>{#each points as p, i (p.id)}<th colspan="3" class="grp"><span class="num">{i + 1}</span>{p.elevation} m</th>{/each}</tr>
            <tr><th></th>{#each points as p (p.id)}<th class="grp">{s.col_snow}</th><th>{s.col_wind}</th><th>°C</th>{/each}</tr>
          </thead>
          <tbody>
            {#each days as d (d.date)}
              <tr>
                <td>{d.when === 'today' ? s.today : dayLabel(d.date, s.weekdays)}</td>
                {#each points as p (p.id)}
                  {@const pd = p.days.find((x) => x.date === d.date)}
                  <td class="grp">{pd?.snow_cm ? `${num(pd.snow_cm)} cm` : '–'}</td>
                  <td>{num(pd?.wind_max_kmh)} {pd?.wind_from ?? ''}</td>
                  <td>{num(pd?.temp_min_c)} … {num(pd?.temp_max_c)}</td>
                {/each}
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <div class="cols2">
        <div class="obs">
          <h2>{s.obs_title}</h2>
          <div class="fields">
            <div>{s.obs_when}</div>
            <div>{s.obs_where}</div>
            <div>{s.obs_elev}</div>
            <div class="aspect">{s.obs_aspect}<span>{#each COMPASS as c (c)}<span>{c}</span>{/each}</span></div>
          </div>
          <h3>{s.signs_title}</h3>
          <ul class="checks">{#each s.signs_items as it (it)}<li class="tick"><i></i>{it}</li>{/each}</ul>
          <p class="muted">{s.signs_note}</p>
          <h3>{s.obs_seen}</h3>
          <div class="lines">{#each Array(4) as _, i (i)}<span></span>{/each}</div>
        </div>

        <div class="side">
          <div class="emergency">
            <h2>{s.sheet_emergency}: 112</h2>
            <p>{s.sheet_112}</p>
            <p><b>{s.call_say}</b> {s.call_items.join(' · ')}</p>
            <p class="burial">{s.burial}</p>
            <h3>{s.map_points}</h3>
            <ol>
              {#each points as p (p.id)}
                <li>{p.elevation} m — {coord(p.lat, p.lon)}</li>
              {/each}
            </ol>
            <p class="muted">{s.sheet_other}</p>
          </div>
          <div class="about">
            <h2>{s.about_title}</h2>
            <p class="muted">{fill(s.about_weather, { level: top.wind_level })} {s.consensus_note}</p>
          </div>
        </div>
      </div>

      {@render footer(true)}
    </section>
  </div>
{/if}

<style>
  .print-doc { display: none; }

  /* Swiss-style sheet: one typeface, four sizes (18 / 11 / 9 / 7 pt), flush left, hairline rules,
     a strict 190 mm column. Size follows importance: place, then the weather message, then data. */
  @media print {
    .print-doc {
      display: block; color: #111820;
      font: 9pt/1.3 'Helvetica Neue', Helvetica, Arial, system-ui, sans-serif;
      font-variant-numeric: tabular-nums;
    }
    .page {
      width: 210mm; height: 296mm; padding: 10mm 10mm 8mm; box-sizing: border-box; overflow: hidden;
      display: flex; flex-direction: column; gap: 3mm; break-after: page;
    }
    .page:last-child { break-after: auto; }
    p { margin: 0; }
    h1 { font-size: 18pt; line-height: 1.05; margin: 0; letter-spacing: -0.015em; font-weight: 700; }
    h2 { font-size: 9pt; margin: 0 0 1.2mm; font-weight: 700; }
    h3 { font-size: 9pt; margin: 2.2mm 0 0.8mm; font-weight: 700; }
    .muted, .meta, .pg, .credits, th { color: #5b6672; }
    .meta, .pg, .credits, th, .tnote, .qr span, .fields > div, .checks + .muted { font-size: 7pt; }

    /* Header */
    header { display: grid; gap: 1.6mm; }
    .brandrow { display: flex; justify-content: space-between; align-items: center; padding-bottom: 1.6mm; border-bottom: 0.5mm solid #111820; }
    .brand { display: flex; align-items: center; gap: 2mm; font-weight: 700; }
    .brand img { width: 6mm; height: auto; }
    .doc { font-weight: 700; }
    .titlerow { display: flex; justify-content: space-between; align-items: flex-end; gap: 6mm; }
    .sub { color: #5b6672; }
    .meta { text-align: right; }
    .status { display: flex; flex-wrap: wrap; gap: 0.8mm 5mm; padding: 0.4mm 0 0.4mm 2.5mm; border-left: 1.2mm solid #2468a8; font-size: 11pt; font-weight: 700; }
    .status.attention { border-left-color: #d08a00; }
    .status.serious { border-left-color: #c62828; }
    .concern { display: inline-flex; align-items: center; gap: 1.5mm; }
    .concern small { font-size: 7pt; font-weight: 400; color: #5b6672; }
    .compact h1 { font-size: 11pt; }
    .rating { font-weight: 700; }

    /* Tables: hairlines only */
    table { width: 100%; border-collapse: collapse; }
    th { text-align: right; font-weight: 400; padding: 0 1.5mm 0.8mm; border-bottom: 0.3mm solid #111820; white-space: nowrap; }
    td { text-align: right; padding: 1mm 1.5mm; border-bottom: 0.15mm solid #c3cad2; white-space: nowrap; }
    th:first-child, td:first-child { text-align: left; padding-left: 0; }
    td:first-child .muted { margin-left: 1mm; }
    .num { display: inline-grid; place-items: center; width: 3.8mm; height: 3.8mm; border-radius: 50%; background: #111820; color: #fff; font-size: 7pt; font-weight: 700; margin-right: 1.5mm; vertical-align: 0.2mm; }
    .warrow { width: 2.8mm; height: 2.8mm; display: inline-block; vertical-align: -0.3mm; margin-right: 0.8mm; fill: #111820; }
    .tnote { margin-top: 1mm; }
    .matrix th.grp, .matrix td.grp { border-left: 0.15mm solid #c3cad2; }
    .matrix thead tr:first-child th { text-align: center; color: #111820; font-weight: 700; border-bottom: 0; }

    .emline { padding: 1.4mm 0; border-top: 0.5mm solid #111820; border-bottom: 0.15mm solid #c3cad2; }
    .emline b { font-size: 11pt; margin-right: 2mm; color: #c62828; }

    /* Page 2: observation (left, the larger) | emergency and about (right) */
    .cols2 { display: grid; grid-template-columns: 1.2fr 1fr; gap: 6mm; align-items: start; }
    .obs { border-top: 0.5mm solid #111820; padding-top: 1.6mm; }
    .fields { display: grid; grid-template-columns: 1fr 1fr; gap: 0; border-top: 0.15mm solid #c3cad2; border-left: 0.15mm solid #c3cad2; }
    .fields > div { height: 11mm; box-sizing: border-box; padding: 0.8mm 1.5mm; border-right: 0.15mm solid #c3cad2; border-bottom: 0.15mm solid #c3cad2; }
    .fields .aspect > span { display: flex; justify-content: space-between; margin-top: 1.6mm; color: #111820; font-weight: 700; }
    .checks { list-style: none; margin: 0 0 1mm; padding: 0; display: grid; gap: 1.4mm; }
    .checks li { display: flex; align-items: center; gap: 1.8mm; }
    .checks i { width: 3.2mm; height: 3.2mm; border: 0.3mm solid #111820; display: inline-block; flex: none; }
    .lines { display: grid; gap: 7mm; padding-top: 6mm; }
    .lines span { border-bottom: 0.15mm solid #8a949e; }
    .side { display: grid; gap: 4mm; }
    .emergency { border-top: 0.5mm solid #c62828; padding-top: 1.6mm; display: grid; gap: 1.2mm; }
    .emergency h2 { color: #c62828; }
    .emergency h3 { margin: 0.8mm 0 0; }
    .burial { padding-left: 2mm; border-left: 0.8mm solid #c62828; }
    ol { margin: 0; padding-left: 4.5mm; }
    .about { border-top: 0.15mm solid #c3cad2; padding-top: 1.6mm; }

    /* Footer */
    footer { margin-top: auto; display: flex; justify-content: space-between; align-items: flex-end; gap: 6mm; padding-top: 1.6mm; border-top: 0.15mm solid #c3cad2; }
    .credits { display: grid; gap: 0.6mm; }
    .credits p:first-child { color: #111820; font-weight: 700; }
    .qr { display: grid; justify-items: center; gap: 0.6mm; flex: none; }
    .qr svg { width: 16mm; height: 16mm; }
    .qr path { fill: #111820; }
  }
</style>
