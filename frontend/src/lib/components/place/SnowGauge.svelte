<script lang="ts">
  // New snow over the past 3 days plus the next 3 at a point, against the SLF leaflet's critical
  // amounts (10–20 cm unfavourable snowpack, 20–30 mixed, 30–50 favourable).
  import { num } from '#lib/format.ts';
  import { fill } from '#lib/i18n.ts';
  import { t } from '#lib/state.svelte.ts';
  import type { WeatherPoint } from '#lib/types.ts';

  let { point }: { point: WeatherPoint } = $props();
  const s = $derived(t());
  const snow3 = $derived(point.past72.snow_cm + point.next72.snow_cm);
  const SCALE = 60;
  const pct = (cm: number) => Math.min(100, (cm / SCALE) * 100);
</script>

<div class="gauge" aria-label={fill(s.snow3_aria, { cm: num(snow3) })}>
  <div class="glabel"><span>{s.snow3_title}</span><b>{num(snow3)} cm</b></div>
  <div class="bar">
    <span class="zone z1" style="left: {pct(10)}%; width: {pct(20) - pct(10)}%"></span>
    <span class="zone z2" style="left: {pct(20)}%; width: {pct(30) - pct(20)}%"></span>
    <span class="zone z3" style="left: {pct(30)}%; width: {pct(50) - pct(30)}%"></span>
    <span class="fill" style="width: {pct(snow3)}%"></span>
  </div>
  <div class="ticks">{#each [0, 10, 20, 30, 50] as v (v)}<span style="left: {pct(v)}%">{v}</span>{/each}</div>
  <p class="small">{s.snow3_note}</p>
</div>

<style>
  .gauge { padding: 4px 0 0; }
  .glabel { display: flex; justify-content: space-between; margin-bottom: 4px; }
  .glabel b { color: var(--glacier); }
  .bar { position: relative; height: 10px; border-radius: 5px; background: #e8edf2; overflow: hidden; }
  .zone { position: absolute; top: 0; bottom: 0; }
  .z1 { background: #f6e3a8; } .z2 { background: #f2c27a; } .z3 { background: #ea9a7a; }
  .fill { position: absolute; left: 0; top: 3px; bottom: 3px; background: var(--glacier); border-radius: 3px; }
  .ticks { position: relative; height: 16px; font-size: var(--fs-xs); color: var(--muted); }
  .ticks span { position: absolute; transform: translateX(-50%); }
  .ticks span:first-child { transform: none; }
</style>
