<script lang="ts">
  // Today and the next days at the selected point, as cards. In the afternoon the planning day is
  // tomorrow, so it is highlighted; in the morning, today.
  import { COMPASS_DEG, num } from '$lib/format';
  import { fill } from '$lib/i18n';
  import { t, ui } from '$lib/state.svelte';
  import type { Day, WeatherPoint } from '$lib/types';

  let { point }: { point: WeatherPoint } = $props();
  const s = $derived(t());
  const days = $derived(point.days.filter((d) => d.when !== 'past').slice(0, 4));
  const th = $derived(ui.weather?.thresholds);

  const skopjeHour = () => Number(new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/Skopje', hour: '2-digit', hour12: false }).format(new Date()));
  const focus = skopjeHour() >= 14 ? 1 : 0;

  /** Weather worth attention on that day, in plain words (same limits as the alerts). */
  function marks(d: Day): string[] {
    if (!th) return [];
    const out = [];
    if (d.snow_cm >= th.heavy_snow_24h_cm) out.push(s.concern.heavy_snow_coming);
    else if (d.snow_cm >= th.drift_snow_24h_cm && (d.wind_max_kmh ?? 0) >= th.drift_wind_kmh) out.push(s.concern.wind_drifting);
    if (d.rain_mm >= th.rain_on_snow_mm && d.freezing_max_m !== null && (d.freezing_max_m ?? 0) > point.elevation) out.push(s.day_rain_high);
    return out;
  }
  const label = (d: Day, i: number) => (i === 0 ? s.today : i === 1 ? s.tomorrow : s.weekdays[new Date(d.date + 'T00:00:00Z').getUTCDay()]);
</script>

<div class="strip" role="list" aria-label={fill(s.days_title, { elev: point.elevation })}>
  {#each days as d, i (d.date)}
    {@const m = marks(d)}
    <div class="day" class:focus={i === focus} class:warn={m.length > 0} role="listitem">
      <span class="name">{label(d, i)}</span>
      <span class="snow" class:zero={!d.snow_cm}>{num(d.snow_cm)}<small>&nbsp;cm</small></span>
      <span class="wind">
        {#if d.wind_from}
          <svg viewBox="0 0 16 16" aria-hidden="true" style="transform: rotate({COMPASS_DEG[d.wind_from] + 180}deg)"><path d="M8 1 13 9H9.5v6h-3V9H3z" /></svg>
        {/if}{num(d.wind_max_kmh)} <small>{d.wind_from ?? ''}</small>
      </span>
      <span class="temp">{num(d.temp_min_c)}…{num(d.temp_max_c)}°</span>
      <span class="fl" title={s.freezing_short}>0° {num(d.freezing_min_m)} m</span>
      {#if m.length}<span class="mark">{m.join(', ')}</span>{/if}
    </div>
  {/each}
</div>

<style>
  .strip { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; }
  .day { display: grid; gap: 1px; padding: 7px 7px 6px; border: 1px solid var(--line); border-radius: 9px; background: #fff; font-variant-numeric: tabular-nums; align-content: start; }
  .day.focus { border-color: var(--ink); box-shadow: inset 0 0 0 1px var(--ink); }
  .day.warn { background: var(--signal-bg); }
  .name { font-size: 12px; font-weight: 700; }
  .snow { font-size: 19px; font-weight: 800; color: var(--glacier); line-height: 1.15; }
  .snow.zero { color: var(--muted); font-weight: 600; }
  .snow small { font-size: 11px; font-weight: 500; }
  .wind { font-size: 12.5px; font-weight: 650; white-space: nowrap; }
  .wind svg { width: 11px; height: 11px; vertical-align: -1px; margin-right: 2px; fill: currentColor; }
  .wind small, .temp, .fl { font-size: 11.5px; color: var(--muted); font-weight: 500; }
  .temp { color: var(--ink); }
  .mark { font-size: 11px; font-weight: 700; color: #8a5a00; line-height: 1.2; margin-top: 2px; }
</style>
