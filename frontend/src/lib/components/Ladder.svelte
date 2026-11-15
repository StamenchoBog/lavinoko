<script lang="ts">
  import WindArrow from './WindArrow.svelte';
  // One row per forecast point, summit on top, like the mountain itself.
  import { byHeight, num } from '#lib/format.ts';
  import { fill } from '#lib/i18n.ts';
  import { currentPlace, t, ui } from '#lib/state.svelte.ts';
  import type { WeatherPoint } from '#lib/types.ts';

  let { period, caption = '' }: { period: 'past72' | 'next72'; caption?: string } = $props();

  const points = $derived(byHeight(currentPlace()?.points ?? []));
  // Freezing level (lowest over the period) drawn as a line between the points at its height.
  const fl = $derived.by(() => {
    const top = points[0];
    const lo = top?.next72.freezing_level_min_m, hi = top?.next72.freezing_level_max_m;
    return period === 'next72' && lo != null && hi != null ? { lo, hi } : null;
  });
  const s = $derived(t());

  function select(p: WeatherPoint) {
    ui.point = p.id;
  }
</script>

<table>
  {#if caption}<caption>{caption}</caption>{/if}
  <thead>
    <tr><th><span class="sr-only">{s.col_point}</span></th><th>{s.col_snow}</th><th>{s.col_wind}</th><th>{s.col_temp}</th></tr>
  </thead>
  <tbody>
    {#each points as p, i (p.id)}
      {@const d = p[period]}
      {#if fl && fl.lo > p.elevation && (i === 0 || fl.lo <= (points[i - 1]?.elevation ?? Infinity))}
        <tr class="fl" aria-hidden="true"><td colspan="4"><span>{fill(s.fl_row, { lo: num(fl.lo), hi: num(fl.hi) })}</span></td></tr>
      {/if}
      {@const rng = p.spread ? (period === 'next72' ? p.spread.snow_next72_cm : p.spread.snow_past72_cm) : null}
      <tr
        tabindex="0"
        aria-selected={p.id === ui.point}
        onclick={() => select(p)}
        onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), select(p))}
      >
        <td class="where"><span class="elev">{p.elevation} m</span><span class="name">{p.name[ui.lang]}</span></td>
        <td>
          <span class="snow" class:zero={!d.snow_cm}>{num(d.snow_cm)}<small>&nbsp;cm</small></span>
          {#if rng && rng[1] - rng[0] >= 1}<span class="range">{fill(s.range_models, { lo: num(rng[0]), hi: num(rng[1]) })}</span>{/if}
        </td>
        <td class="wind">
          <WindArrow from={d.wind.from} size={14} />
          {num(d.wind.max_kmh)} <small>{d.wind.from ? d.wind.from : ''}</small>
        </td>
        <td class="temp">{num(d.temp_min_c)}…{num(d.temp_max_c)}</td>
      </tr>
    {/each}
    {#if fl && fl.lo <= (points.at(-1)?.elevation ?? -Infinity)}
      <tr class="fl" aria-hidden="true"><td colspan="4"><span>{fill(s.fl_row, { lo: num(fl.lo), hi: num(fl.hi) })}</span></td></tr>
    {/if}
  </tbody>
</table>

<style>
  table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
  caption { text-align: left; font-size: 13px; color: var(--muted); padding-bottom: 4px; }
  th { font-size: 12px; font-weight: 500; color: var(--muted); text-align: right; padding: 0 0 4px; }
  th:first-child { text-align: left; }
  tbody tr { cursor: pointer; }
  td { padding: 9px 0; border-top: 1px solid var(--line); text-align: right; vertical-align: middle; }
  td:last-child { padding-right: 8px; }
  td.where { text-align: left; padding-left: 9px; border-left: 3px solid transparent; }
  tr[aria-selected='true'] td { background: var(--tint); }
  tr[aria-selected='true'] td.where { border-left-color: var(--glacier); }
  .elev { font-weight: 700; font-size: 16px; display: block; line-height: 1.1; }
  .name { font-size: 12.5px; color: var(--muted); }
  .snow { font-size: 20px; font-weight: 750; color: var(--glacier); }
  .snow.zero { color: var(--muted); font-weight: 600; }
  .snow small { font-size: 12px; font-weight: 500; }
  .range { display: block; font-size: 11px; color: var(--muted); white-space: nowrap; }
  .wind { white-space: nowrap; font-weight: 600; }
  .wind small { color: var(--muted); font-weight: 500; }
  .temp { white-space: nowrap; }
  tr.fl td { padding: 0; border-top: 0; text-align: left; }
  tr.fl span { display: flex; align-items: center; gap: 6px; font-size: 11.5px; font-weight: 700; color: var(--glacier); }
  tr.fl span::before, tr.fl span::after { content: ''; flex: 1; border-top: 1.5px dashed var(--glacier); }
  tr.fl span::before { flex: 0 0 9px; }
</style>
