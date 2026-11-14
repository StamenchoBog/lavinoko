<script lang="ts">
  import { byHeight, dayLabel, num } from '$lib/format';
  import { fill } from '$lib/i18n';
  import { currentPlace, t, ui } from '$lib/state.svelte';
  import Ladder from './Ladder.svelte';
  import Meteogram from './Meteogram.svelte';
  import DayStrip from './place/DayStrip.svelte';
  import Situation from './place/Situation.svelte';
  const s = $derived(t());
  const place = $derived(currentPlace());
  const point = $derived.by(() => {
    const pts = currentPlace()?.points ?? [];
    return pts.find((p) => p.id === ui.point) ?? byHeight(pts)[0];
  });

</script>

{#if point}
<div class="weather">
  <Situation />

  <section aria-labelledby="days-h">
    <h2 id="days-h">{s.sec_days} <small>{point.elevation} m</small></h2>
    <DayStrip {point} />
  </section>

  <section aria-labelledby="elev-h">
    <h2 id="elev-h">{s.sec_elev}</h2>
    <Ladder period="next72" />
  </section>

  <section aria-labelledby="hourly-h">
    <h2 id="hourly-h">{s.sec_hourly} <small>{point.elevation} m</small></h2>
  {#if place}<Meteogram placeId={place.id} pointId={point.id} />{/if}
    <p class="credit"><a href="https://open-meteo.com/" target="_blank" rel="noopener">{s.credit_weather}</a></p>
  </section>

  <details>
    <summary>{fill(s.days_title, { elev: point.elevation })}</summary>
    <table class="days">
      <thead>
        <tr><th>{s.col_day}</th><th>{s.col_snow} cm</th><th>{s.col_rain} mm</th><th>°C</th><th>{s.col_wind}</th></tr>
      </thead>
      <tbody>
        {#each point.days as d (d.date)}
          <tr class={d.when}>
            <td>{d.when === 'today' ? s.today : dayLabel(d.date, s.weekdays)}</td>
            <td class="snow">{d.snow_cm ? num(d.snow_cm) : ''}</td>
            <td>{d.rain_mm ? num(d.rain_mm, 1) : ''}</td>
            <td>{num(d.temp_min_c)}…{num(d.temp_max_c)}</td>
            <td>{num(d.wind_max_kmh)} {d.wind_from ? d.wind_from : ''}</td>
          </tr>
        {/each}
      </tbody>
    </table>
    <p class="small">
      {fill(s.freezing, { min: num(point.next72.freezing_level_min_m), max: num(point.next72.freezing_level_max_m) })}
    </p>
  </details>

  <details>
    <summary>{s.past72}</summary>
    <Ladder period="past72" />
  </details>

  <details>
    <summary>{s.about_title}</summary>
    <p class="small">{fill(s.about_weather, { level: point.wind_level })}</p>
    <p class="small">{s.consensus_note}</p>
    {#if place}<p class="small">{fill(s.place_sources, place.sources)}</p>{/if}
  </details>

</div>
{/if}

<style>
  .weather { display: grid; gap: 22px; }
  .weather > :global(section) { display: grid; gap: 8px; }
  .weather > :global(details) { margin-top: -14px; }
  h2 { font-size: 15px; margin: 0; display: flex; justify-content: space-between; align-items: baseline; }
  h2 small { font-size: 12px; font-weight: 500; color: var(--muted); }
  .credit { font-size: 12px; margin: 0 0 4px; }
  .agree { display: block; font-style: normal; font-size: 12px; color: var(--muted); }
  .credit a { color: var(--muted); }
  .days { width: 100%; border-collapse: collapse; font-size: 13.5px; font-variant-numeric: tabular-nums; }
  .days th { font-weight: 500; color: var(--muted); font-size: 12px; text-align: right; padding: 2px 4px; }
  .days td { text-align: right; padding: 5px 4px; border-top: 1px solid var(--line); }
  .days th:first-child, .days td:first-child { text-align: left; white-space: nowrap; }
  .days tr.past td { color: var(--muted); }
  .days tr.today td { font-weight: 700; }
  .days td.snow { color: var(--glacier); font-weight: 650; }
</style>
