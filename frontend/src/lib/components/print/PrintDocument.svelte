<script lang="ts">
  // The printed document for a place. Exactly one A4 page (tour sheet) or two (plus detailed
  // forecast); every page is a fixed 210 × 297 mm box, so content never spills onto extra pages.
  import { onMount } from 'svelte';
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
  const pages = $derived(print.mode === 'full' ? 2 : 1);

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
  const range = (r: [number, number] | undefined) => (r && r[1] - r[0] >= 1 ? fill(s.range_models, { lo: num(r[0]), hi: num(r[1]) }) : '');

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
      <span class="brand"><img src="{base}/logo.png" alt="" />{s.brand}</span>
      <span class="doc">{title}<span class="pg">{page}/{pages}</span></span>
    </div>
    <div class="titlerow">
      <div>
        <h1>{place?.name[ui.lang]}</h1>
        <p class="sub">{place?.range[ui.lang]} · {elevSpan}</p>
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

{#snippet footer()}
  <footer>
    <div class="credits">
      <p>{s.disclaimer}</p>
      <p>Weather data by Open-Meteo.com (CC BY 4.0). {data.meta?.source}. Map: © OpenMapTiles © OpenStreetMap contributors (ODbL).</p>
    </div>
    {#if qr}
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

      <div class="stats">
        <div><span class="lbl">{s.stat_new_snow}</span><b>{num(top.next72.snow_cm)}<small> cm</small></b><span class="sm">{range(top.spread?.snow_next72_cm)}</span></div>
        <div><span class="lbl">{s.stat_last24}</span><b>{num(top.past72.snow_24h_cm)}<small> cm</small></b><span class="sm">{s.col_wind} {num(top.past72.wind_24h_max_kmh)} km/h</span></div>
        <div><span class="lbl">{s.stat_wind}</span><b>{@render arrow(top.next72.wind.from)}{num(top.next72.wind.max_kmh)}<small> km/h</small></b><span class="sm">{top.next72.wind.from ? top.next72.wind.from : ''}</span></div>
        <div><span class="lbl">{s.stat_freezing}</span><b>{num(top.next72.freezing_level_min_m)}<small>–{num(top.next72.freezing_level_max_m)} m</small></b><span class="sm">72 h</span></div>
        <div><span class="lbl">{s.stat_temp}</span><b>{num(top.next72.temp_min_c)}<small>…{num(top.next72.temp_max_c)} °C</small></b><span class="sm">{top.elevation} m</span></div>
      </div>

      <PrintMap pic={print.map} labels={points.map((p) => `${p.elevation} m`)} />

      <div class="cols">
        <div>
          <h2>{s.by_elevation}</h2>
          <table>
            <thead><tr><th></th><th>{s.col_snow}</th><th>{s.col_wind}</th><th>°C</th></tr></thead>
            <tbody>
              {#each points as p, i (p.id)}
                <tr>
                  <td><span class="num">{i + 1}</span>{p.elevation} m <small>{p.name[ui.lang]}</small></td>
                  <td>{num(p.next72.snow_cm)} cm</td>
                  <td>{@render arrow(p.next72.wind.from)}{num(p.next72.wind.max_kmh)} {p.next72.wind.from ? p.next72.wind.from : ''}</td>
                  <td>{num(p.next72.temp_min_c)}…{num(p.next72.temp_max_c)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
          <h2>{fill(s.next_days, { elev: top.elevation })}</h2>
          <div class="days">
            {#each days as d (d.date)}
              <div>
                <b>{d.when === 'today' ? s.today : dayLabel(d.date, s.weekdays)}</b>
                <span class="snowv">{d.snow_cm ? `${num(d.snow_cm)} cm` : '–'}</span>
                <span>{d.rain_mm ? `${num(d.rain_mm, 1)} mm` : ''}</span>
                <span>{num(d.temp_min_c)}…{num(d.temp_max_c)} °C</span>
                <span>{@render arrow(d.wind_from)}{num(d.wind_max_kmh)} km/h</span>
              </div>
            {/each}
          </div>
        </div>

        <div class="emergency">
          <h2>{s.sheet_emergency}</h2>
          <p class="n112">112</p>
          <p class="em">{s.sheet_112}</p>
          <p class="say"><b>{s.call_say}</b> {s.call_items.join(' · ')}</p>
          <p class="burial">{s.burial}</p>
          <h3>{s.map_points}</h3>
          <ol>
            {#each points as p (p.id)}
              <li>{p.elevation} m — {coord(p.lat, p.lon)}</li>
            {/each}
          </ol>
          <p class="other">{s.sheet_other}</p>
        </div>
      </div>

      <div class="plan">
        <h2>{s.sheet_plan}</h2>
        <div class="fields">
          <div class="f1">{s.plan_date}</div>
          <div class="f1">{s.plan_start}</div>
          <div class="f1">{s.sheet_turnaround}</div>
          <div class="f1">{s.plan_back}</div>
          <div class="f4">{s.sheet_group}</div>
          <div class="f4">{s.plan_route}</div>
          <div class="f4">{s.sheet_contact}</div>
        </div>
        <p class="gear"><b>{s.gear_title}</b>{#each s.gear_items as g (g)}<span><i></i>{g}</span>{/each}</p>
      </div>

      {@render footer()}
    </section>

    {#if print.mode === 'full'}
      <section class="page">
        {@render header(2, s.doc_forecast, true)}

        {#if hourlyTop}
          <h2>{fill(s.chart_title, { elev: top.elevation })}</h2>
          <PrintChart h={hourlyTop} />
        {/if}

        <h2>{s.matrix_title}</h2>
        <table class="matrix">
          <thead>
            <tr><th></th>{#each points as p, i (p.id)}<th colspan="3" class="grp"><span class="num">{i + 1}</span>{p.elevation} m</th>{/each}</tr>
            <tr><th></th>{#each points as p (p.id)}<th>{s.col_snow}</th><th>{s.col_wind}</th><th>°C</th>{/each}</tr>
          </thead>
          <tbody>
            {#each days as d (d.date)}
              <tr>
                <td>{d.when === 'today' ? s.today : dayLabel(d.date, s.weekdays)}</td>
                {#each points as p (p.id)}
                  {@const pd = p.days.find((x) => x.date === d.date)}
                  <td class="grp">{pd?.snow_cm ? `${num(pd.snow_cm)} cm` : '–'}</td>
                  <td>{num(pd?.wind_max_kmh)} {pd?.wind_from ? pd.wind_from : ''}</td>
                  <td>{num(pd?.temp_min_c)}…{num(pd?.temp_max_c)}</td>
                {/each}
              </tr>
            {/each}
          </tbody>
        </table>

        <div class="cols2">
          <div>
            <h2>{s.signs_title}</h2>
            <ul class="checks">{#each s.signs_items as it (it)}<li><i></i>{it}</li>{/each}</ul>
            <p class="note">{s.signs_note}</p>
          </div>
          <div>
            <h2>{s.notes_title}</h2>
            <div class="lines">{#each Array(7) as _, i (i)}<span></span>{/each}</div>
          </div>
        </div>

        <div class="about">
          <h2>{s.about_title}</h2>
          <p>{fill(s.about_weather, { level: top.wind_level })} {s.consensus_note}</p>
        </div>

        {@render footer()}
      </section>
    {/if}
  </div>
{/if}

<style>
  .print-doc { display: none; }

  @media print {
    .print-doc { display: block; color: #17283a; font: 8.5pt/1.3 system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif; }
    .page {
      width: 210mm; height: 296mm; padding: 9mm 10mm 8mm; box-sizing: border-box; overflow: hidden;
      display: flex; flex-direction: column; gap: 2mm; break-after: page;
    }
    .page:last-child { break-after: auto; }
    p { margin: 0; }
    h2 { font-size: 8.5pt; margin: 0 0 1.2mm; }
    h3 { font-size: 7.5pt; margin: 1.2mm 0 0.4mm; }

    /* Header */
    header { display: grid; gap: 1.1mm; }
    .brandrow { display: flex; justify-content: space-between; align-items: center; padding-bottom: 1.4mm; border-bottom: 0.5mm solid #17283a; }
    .brand { display: flex; align-items: center; gap: 2mm; font-weight: 800; font-size: 10pt; }
    .brand img { width: 9mm; height: auto; }
    .doc { font-weight: 700; font-size: 9pt; display: flex; align-items: center; gap: 2.5mm; }
    .pg { font-weight: 600; color: #5e6b78; }
    .titlerow { display: flex; justify-content: space-between; align-items: flex-end; gap: 6mm; }
    h1 { font-size: 18pt; line-height: 1.05; margin: 0; letter-spacing: -0.01em; }
    .compact h1 { font-size: 14pt; }
    .sub { color: #5e6b78; font-size: 9pt; }
    .meta { text-align: right; font-size: 7.5pt; color: #5e6b78; }
    .status { display: flex; flex-wrap: wrap; gap: 0.6mm 4mm; padding: 1.3mm 2.5mm; border-radius: 1.5mm; background: #e9f1f9; font-weight: 600; font-size: 9pt; }
    .status.attention { background: #fdf5e2; }
    .status.serious { background: #fbe9e7; }
    .concern { display: inline-flex; align-items: center; gap: 1.5mm; }
    .concern small { font-weight: 400; color: #5e6b78; font-size: 7.5pt; }
    .rating { font-size: 7.5pt; font-weight: 700; }

    /* Key figures */
    .stats { display: grid; grid-template-columns: repeat(5, 1fr); border: 0.3mm solid #c9d1da; border-radius: 1.5mm; }
    .stats > div { display: grid; padding: 1.1mm 2.2mm; border-left: 0.3mm solid #c9d1da; }
    .stats > div:first-child { border-left: 0; }
    .lbl { font-size: 7pt; color: #5e6b78; }
    .stats b { font-size: 14pt; line-height: 1.15; display: flex; align-items: baseline; gap: 0.6mm; font-variant-numeric: tabular-nums; }
    .stats b small { font-size: 8pt; font-weight: 600; }
    .stats .sm { font-size: 6.8pt; color: #5e6b78; min-height: 2.6mm; }
    .stats .warrow { width: 3.6mm; height: 3.6mm; align-self: center; }
    .warrow { width: 2.6mm; height: 2.6mm; display: inline-block; vertical-align: -0.4mm; margin-right: 0.6mm; fill: #17283a; }

    /* Conditions + emergency */
    .cols { display: grid; grid-template-columns: 1.05fr 1fr; gap: 5mm; }
    table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
    th { text-align: right; font-weight: 600; font-size: 7pt; color: #5e6b78; padding: 0 1.2mm 0.6mm; border-bottom: 0.3mm solid #17283a; }
    td { text-align: right; padding: 0.7mm 1.2mm; border-bottom: 0.2mm solid #c9d1da; white-space: nowrap; }
    th:first-child, td:first-child { text-align: left; }
    td small { color: #5e6b78; font-size: 7pt; margin-left: 1mm; }
    .num { display: inline-grid; place-items: center; width: 3.6mm; height: 3.6mm; border-radius: 50%; background: #17283a; color: #fff; font-size: 6.5pt; font-weight: 800; margin-right: 1.2mm; vertical-align: 0.1mm; }
    .days { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.5mm; }
    .days > div { display: grid; gap: 0.1mm; padding: 1.1mm 1.6mm; border: 0.25mm solid #c9d1da; border-radius: 1.2mm; font-size: 7.3pt; }
    .days b { font-size: 8pt; }
    .snowv { color: #2468a8; font-weight: 700; font-size: 9pt; }
    .cols h2:not(:first-child) { margin-top: 1.8mm; }

    .emergency { border: 0.5mm solid #17283a; border-radius: 1.8mm; padding: 1.8mm 3mm; }
    .n112 { font-size: 24pt; font-weight: 900; line-height: 1; letter-spacing: 0.02em; }
    .em { font-weight: 700; margin-top: 0.6mm; }
    .say { margin-top: 1mm; font-size: 7.3pt; }
    .burial { margin-top: 1mm; font-size: 7.3pt; padding: 1mm 1.8mm; background: #fbe9e7; border-radius: 1mm; }
    ol { margin: 0; padding-left: 4.5mm; font-size: 7.5pt; font-variant-numeric: tabular-nums; }
    .other { margin-top: 0.8mm; font-size: 7pt; color: #5e6b78; }

    /* Plan */
    .fields { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.5mm; }
    .fields > div { display: block; border: 0.25mm solid #9aa6b2; border-radius: 1mm; padding: 0.6mm 1.5mm; font-size: 6.8pt; color: #5e6b78; height: 7.5mm; }
    .fields .f4 { grid-column: span 4; height: 7mm; }
    .gear { display: flex; flex-wrap: wrap; align-items: center; gap: 1mm 4mm; margin-top: 1.4mm; font-size: 7.5pt; }
    .gear span, .checks li { display: inline-flex; align-items: center; gap: 1.2mm; }
    .gear i, .checks i { width: 3mm; height: 3mm; border: 0.3mm solid #17283a; border-radius: 0.5mm; display: inline-block; flex: none; }

    /* Page 2 */
    .matrix th.grp, .matrix td.grp { border-left: 0.3mm solid #c9d1da; }
    .matrix thead tr:first-child th { text-align: center; color: #17283a; font-size: 8pt; border-bottom: 0; }
    .cols2 { display: grid; grid-template-columns: 1fr 1fr; gap: 6mm; }
    .checks { list-style: none; margin: 0; padding: 0; display: grid; gap: 1.6mm; font-size: 8pt; }
    .note { margin-top: 1.8mm; font-size: 7.5pt; color: #5e6b78; }
    .lines { display: grid; gap: 6.5mm; padding-top: 4mm; }
    .lines span { border-bottom: 0.25mm solid #9aa6b2; }
    .about p { font-size: 7.5pt; color: #5e6b78; }

    /* Footer */
    footer { margin-top: auto; display: flex; justify-content: space-between; align-items: flex-end; gap: 6mm; padding-top: 1.6mm; border-top: 0.3mm solid #c9d1da; }
    .credits { font-size: 6.3pt; color: #5e6b78; display: grid; gap: 0.6mm; }
    .credits p:first-child { color: #17283a; font-weight: 600; }
    .qr { display: grid; justify-items: center; gap: 0.6mm; font-size: 6pt; color: #5e6b78; flex: none; }
    .qr svg { width: 15mm; height: 15mm; }
    .qr path { fill: #17283a; }
  }
</style>
