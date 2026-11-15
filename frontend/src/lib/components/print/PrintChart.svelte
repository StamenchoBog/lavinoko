<script lang="ts">
  // Hour-by-hour forecast for paper: last 24 h + next 72 h, stacked panels on one time axis,
  // one scale per panel. Units are millimetres (viewBox), so it prints at a fixed, crisp size.
  import { t } from '$lib/state.svelte';
  import type { HourlyPoint } from '$lib/types';

  let { h }: { h: HourlyPoint } = $props();
  const s = $derived(t());

  const W = 190, L = 11, R = 2, plotW = W - L - R;
  const start = $derived(Math.max(0, h.now_index - 24));
  const end = $derived(Math.min(h.time.length, h.now_index + 72));
  const n = $derived(end - start);
  const sl = <T,>(a: T[]) => a.slice(start, end);
  const x = (i: number) => L + (n > 1 ? (i / (n - 1)) * plotW : 0);
  const now = $derived(h.now_index - start);

  const sums = (vals: (number | null)[]) => {
    const out: { i: number; v: number }[] = [];
    for (let i = 0; i < vals.length; i += 3) out.push({ i, v: vals.slice(i, i + 3).reduce((a: number, b) => a + (b ?? 0), 0) });
    return out;
  };
  const snow = $derived(sums(sl(h.snow_cm)));
  const rain = $derived(sums(sl(h.rain_mm)));
  const temp = $derived(sl(h.temp_c));
  const wind = $derived(sl(h.wind_kmh));
  const dir = $derived(sl(h.wind_dir));
  const hasRain = $derived(rain.some((r) => r.v > 0.05));

  const snowMax = $derived(Math.max(5, ...snow.map((d) => Math.ceil(d.v))));
  const rainMax = $derived(Math.max(2, ...rain.map((d) => Math.ceil(d.v))));
  const temps = $derived(temp.filter((v): v is number => v !== null));
  const tMin = $derived(Math.min(-2, Math.floor(Math.min(...temps))));
  const tMax = $derived(Math.max(2, Math.ceil(Math.max(...temps))));
  const wMax = $derived(Math.max(30, Math.ceil(Math.max(...wind.filter((v): v is number => v !== null)) / 10) * 10));

  // Panel geometry (mm).
  const T = 3.6; // title band
  const panels = $derived.by(() => {
    let y = 0;
    const p = (hgt: number) => ({ top: (y += T), h: hgt, end: (y += hgt + 2.2) });
    return { snow: p(15), rain: hasRain ? p(9) : null, temp: p(22), wind: p(15) };
  });
  const height = $derived(panels.wind.end + 6);
  const bw = $derived(Math.max(0.4, (plotW / n) * 3 - 0.35));

  function line(vals: (number | null)[], top: number, hgt: number, lo: number, hi: number) {
    let d = '';
    vals.forEach((v, i) => {
      if (v === null) return;
      d += `${d ? 'L' : 'M'}${x(i).toFixed(2)},${(top + hgt - ((v - lo) / (hi - lo)) * hgt).toFixed(2)}`;
    });
    return d;
  }
  const days = $derived(
    sl(h.time)
      .map((tm, i) => ({ tm, i }))
      .filter((d) => d.tm.endsWith('T00:00'))
  );
  const label = (iso: string) => {
    const d = new Date(iso.slice(0, 10) + 'T00:00:00Z');
    return `${s.weekdays[d.getUTCDay()]} ${d.getUTCDate()}.${d.getUTCMonth() + 1}.`;
  };
  const zeroY = $derived(panels.temp.top + panels.temp.h - ((0 - tMin) / (tMax - tMin)) * panels.temp.h);
</script>

<svg viewBox="0 0 {W} {height}" style="width: {W}mm; height: {height}mm" role="img" aria-label={s.doc_forecast}>
  <rect x={L} y="0" width={x(now) - L} height={panels.wind.end} class="past" />
  {#each days as d (d.i)}
    <line x1={x(d.i)} x2={x(d.i)} y1={panels.snow.top} y2={panels.wind.top + panels.wind.h} class="day" />
    {#if d.i + 12 < n}<text x={x(d.i + 12)} y={height - 1.2} class="tick" text-anchor="middle">{label(d.tm)}</text>{/if}
  {/each}

  <text x="0" y={panels.snow.top - 1} class="title">{s.chart_snow}</text>
  <text x={L - 1} y={panels.snow.top + 2.4} class="axis" text-anchor="end">{snowMax}</text>
  <line x1={L} x2={W - R} y1={panels.snow.top + panels.snow.h} y2={panels.snow.top + panels.snow.h} class="base" />
  {#each snow as d (d.i)}
    {#if d.v > 0.05}
      {@const bh = Math.max(0.5, (d.v / snowMax) * panels.snow.h)}
      <rect x={x(d.i)} y={panels.snow.top + panels.snow.h - bh} width={bw} height={bh} class="snow" />
    {/if}
  {/each}

  {#if panels.rain}
    <text x="0" y={panels.rain.top - 1} class="title">{s.chart_rain}</text>
    <text x={L - 1} y={panels.rain.top + 2.4} class="axis" text-anchor="end">{rainMax}</text>
    <line x1={L} x2={W - R} y1={panels.rain.top + panels.rain.h} y2={panels.rain.top + panels.rain.h} class="base" />
    {#each rain as d (d.i)}
      {#if d.v > 0.05}
        {@const bh = Math.max(0.5, (d.v / rainMax) * panels.rain.h)}
        <rect x={x(d.i)} y={panels.rain.top + panels.rain.h - bh} width={bw} height={bh} class="rain" />
      {/if}
    {/each}
  {/if}

  <text x="0" y={panels.temp.top - 1} class="title">{s.chart_temp}</text>
  <text x={L - 1} y={panels.temp.top + 2.4} class="axis" text-anchor="end">{tMax}</text>
  <text x={L - 1} y={panels.temp.top + panels.temp.h} class="axis" text-anchor="end">{tMin}</text>
  <line x1={L} x2={W - R} y1={zeroY} y2={zeroY} class="zero" />
  {#if zeroY - panels.temp.top > 4 && panels.temp.top + panels.temp.h - zeroY > 4}
    <text x={L - 1} y={zeroY + 1} class="axis" text-anchor="end">0</text>
  {/if}
  <path d={line(temp, panels.temp.top, panels.temp.h, tMin, tMax)} class="ln" />

  <text x="0" y={panels.wind.top - 1} class="title">{s.chart_wind}</text>
  <text x={L - 1} y={panels.wind.top + 2.4} class="axis" text-anchor="end">{wMax}</text>
  <line x1={L} x2={W - R} y1={panels.wind.top + panels.wind.h} y2={panels.wind.top + panels.wind.h} class="base" />
  <path d={line(wind, panels.wind.top, panels.wind.h, 0, wMax)} class="ln" />
  {#each dir as d, i (i)}
    {#if d !== null && i % 6 === 3}
      <path d="M0 -1.4 L0.9 0.9 L0 0.4 L-0.9 0.9 Z" class="arrow"
        transform="translate({x(i)} {panels.wind.top + 1.4}) rotate({(d + 180) % 360})" />
    {/if}
  {/each}

  <line x1={x(now)} x2={x(now)} y1={panels.snow.top - 0.6} y2={panels.wind.top + panels.wind.h} class="now" />
  <text x={x(now) + 0.8} y={panels.snow.top + 2.4} class="nowt">{s.chart_now}</text>
</svg>

<style>
  svg { display: block; overflow: visible; font-family: system-ui, sans-serif; font-variant-numeric: tabular-nums; }
  .past { fill: #eef1f4; }
  .day { stroke: #c9d1da; stroke-width: 0.2; }
  .tick, .axis { font-size: 2.4px; fill: #5e6b78; }
  .title { font-size: 2.7px; font-weight: 700; fill: #17283a; }
  .base { stroke: #9aa6b2; stroke-width: 0.2; }
  .zero { stroke: #2468a8; stroke-width: 0.25; stroke-dasharray: 0.8 0.8; }
  .snow { fill: #2468a8; }
  .rain { fill: #1f9e89; }
  .ln { fill: none; stroke: #17283a; stroke-width: 0.45; stroke-linejoin: round; stroke-linecap: round; }
  .arrow { fill: #17283a; }
  .now { stroke: #17283a; stroke-width: 0.25; stroke-dasharray: 0.6 0.6; }
  .nowt { font-size: 2.4px; font-weight: 700; fill: #17283a; }
</style>
