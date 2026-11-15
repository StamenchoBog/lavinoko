<script lang="ts">
  // Hour-by-hour forecast for one point: stacked panels on one shared time axis
  // (new snow, rain, temperature, ridge wind). One scale per panel, never two in one.
  import { loadData } from '#lib/data.ts';
  import { currentHourIndex, dayLabel, num } from '#lib/format.ts';
  import { fill } from '#lib/i18n.ts';
  import { t } from '#lib/state.svelte.ts';
  import type { HourlyPoint } from '#lib/types.ts';

  let { placeId, pointId }: { placeId: string; pointId: string } = $props();

  // eslint-disable-next-line svelte/prefer-svelte-reactivity -- a plain cache, nothing renders from it
  const cache = new Map<string, Promise<HourlyPoint[]>>();
  function load(id: string) {
    if (!cache.has(id)) {
      cache.set(
        id,
        loadData('hourly', `hourly/${id}.json`).then((d) => {
          if (!d) cache.delete(id); // try again next time
          return d?.points ?? [];
        })
      );
    }
    return cache.get(id)!;
  }

  let points: HourlyPoint[] = $state([]);
  $effect(() => {
    const id = placeId;
    load(id).then((p) => { if (id === placeId) points = p; }).catch(() => (points = []));
  });

  const s = $derived(t());
  const h = $derived(points.find((p) => p.id === pointId));

  // The "now" line follows the clock: the file's now_index is the hour the forecast was issued.
  let clock = $state(Date.now());
  $effect(() => {
    const id = setInterval(() => (clock = Date.now()), 60e3);
    return () => clearInterval(id);
  });
  const nowI = $derived(h ? currentHourIndex(h.time, new Date(clock), h.now_index) : 0);

  let width = $state(320);
  const L = 30, R = 8;
  const plotW = $derived(Math.max(100, width - L - R));
  const n = $derived(h?.time.length ?? 0);
  const x = (i: number) => L + (n > 1 ? (i / (n - 1)) * plotW : 0);

  // Precipitation in 3-hour sums, so bars stay readable.
  const STEP = 3;
  function sums(vals: (number | null)[]) {
    const out: { i: number; v: number }[] = [];
    for (let i = 0; i < vals.length; i += STEP) {
      let v = 0;
      for (let k = i; k < Math.min(i + STEP, vals.length); k++) v += vals[k] ?? 0;
      out.push({ i, v: Math.round(v * 10) / 10 });
    }
    return out;
  }
  const snow = $derived(h ? sums(h.snow_cm) : []);
  const rain = $derived(h ? sums(h.rain_mm) : []);
  const hasRain = $derived(rain.some((r) => r.v > 0));

  const TITLE = 16, GAP = 14;
  const H_SNOW = 56, H_RAIN = 34, H_TEMP = 64, H_WIND = 46;
  const layout = $derived.by(() => {
    let y = 0;
    const panel = (hgt: number) => { const top = y + TITLE; y = top + hgt + GAP; return { top, h: hgt }; };
    const snowP = panel(H_SNOW);
    const rainP = hasRain ? panel(H_RAIN) : null;
    const tempP = panel(H_TEMP);
    const windP = panel(H_WIND);
    return { snowP, rainP, tempP, windP, height: y + 6 };
  });

  const snowMax = $derived(Math.max(5, ...snow.map((d) => d.v)));
  const rainMax = $derived(Math.max(2, ...rain.map((d) => d.v)));
  const temps = $derived((h?.temp_c ?? []).filter((v): v is number => v !== null));
  const tMin = $derived(Math.min(-2, Math.floor(Math.min(...temps, 0))));
  const tMax = $derived(Math.max(2, Math.ceil(Math.max(...temps, 0))));
  const zeroY = $derived(layout.tempP.top + layout.tempP.h - ((0 - tMin) / (tMax - tMin)) * layout.tempP.h);
  const winds = $derived((h?.wind_kmh ?? []).filter((v): v is number => v !== null));
  const wMax = $derived(Math.max(30, Math.ceil(Math.max(...winds, 0) / 10) * 10));

  function linePath(vals: (number | null)[], top: number, hgt: number, lo: number, hi: number) {
    let d = '';
    vals.forEach((v, i) => {
      if (v === null) return;
      const y = top + hgt - ((v - lo) / (hi - lo)) * hgt;
      d += `${d ? 'L' : 'M'}${x(i).toFixed(1)},${y.toFixed(1)}`;
    });
    return d;
  }
  const barW = $derived(Math.max(1.5, (plotW / Math.max(1, n - 1)) * STEP - 2));
  const midnights = $derived(h ? h.time.map((tm, i) => ({ tm, i })).filter((d) => d.tm.endsWith('T00:00')) : []);

  let hover: number | null = $state(null);
  function onMove(e: PointerEvent) {
    const r = (e.currentTarget as SVGElement).getBoundingClientRect();
    const i = Math.round(((e.clientX - r.left - L) / plotW) * (n - 1));
    hover = i >= 0 && i < n ? i : null;
  }
  const COMPASS = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'] as const;
  const dirLabel = (deg: number | null) => (deg === null ? '' : COMPASS[Math.round(deg / 45) % 8]);
  const readout = $derived.by(() => {
    if (!h || hover === null) return null;
    const i = hover, tm = h.time[i];
    if (tm === undefined) return null;
    const s3 = snow.find((d) => i >= d.i && i < d.i + STEP);
    const r3 = rain.find((d) => i >= d.i && i < d.i + STEP);
    return {
      left: Math.min(Math.max(x(i) - 70, 0), width - 140),
      when: `${dayLabel(tm.slice(0, 10), s.weekdays)} ${tm.slice(11, 16)}`,
      snow: s3?.v ?? 0, rain: r3?.v ?? 0,
      temp: h.temp_c[i], wind: h.wind_kmh[i], dir: dirLabel(h.wind_dir[i] ?? null)
    };
  });
</script>

<div class="wrap" bind:clientWidth={width}>
  {#if h}
    {@const { snowP, rainP, tempP, windP, height } = layout}
    <svg {width} {height} viewBox="0 0 {width} {height}" role="img" aria-label={`${fill(s.chart_title, { elev: h.elevation })}. ${s.chart_summary}`}
      onpointermove={onMove} onpointerleave={() => (hover = null)} onpointerdown={onMove}>
      <rect x={L} y={0} width={x(nowI) - L} height={height - 6} class="past" />
      {#each midnights as m (m.i)}
        <line x1={x(m.i)} x2={x(m.i)} y1={snowP.top} y2={windP.top + windP.h} class="day" />
        {#if m.i + 12 < n}
          <text x={x(m.i + 12)} y={height - 8} class="tick" text-anchor="middle">{s.weekdays[new Date(m.tm.slice(0, 10) + 'T00:00:00Z').getUTCDay()]}</text>
        {/if}
      {/each}

      <text x={0} y={snowP.top - 5} class="label">{s.chart_snow}</text>
      <text x={L - 4} y={snowP.top + 8} class="axis" text-anchor="end">{num(snowMax)}</text>
      <line x1={L} x2={L + plotW} y1={snowP.top + snowP.h} y2={snowP.top + snowP.h} class="base" />
      {#each snow as d (d.i)}
        {#if d.v > 0}
          {@const bh = Math.max(2, (d.v / snowMax) * snowP.h)}
          <rect x={x(d.i)} y={snowP.top + snowP.h - bh} width={barW} height={bh} rx="2" class="snow" />
        {/if}
      {/each}

      {#if rainP}
        <text x={0} y={rainP.top - 5} class="label">{s.chart_rain}</text>
        <text x={L - 4} y={rainP.top + 8} class="axis" text-anchor="end">{num(rainMax)}</text>
        <line x1={L} x2={L + plotW} y1={rainP.top + rainP.h} y2={rainP.top + rainP.h} class="base" />
        {#each rain as d (d.i)}
          {#if d.v > 0}
            {@const bh = Math.max(2, (d.v / rainMax) * rainP.h)}
            <rect x={x(d.i)} y={rainP.top + rainP.h - bh} width={barW} height={bh} rx="2" class="rain" />
          {/if}
        {/each}
      {/if}

      <text x={0} y={tempP.top - 5} class="label">{s.chart_temp}</text>
      {#if zeroY - tempP.top > 14}<text x={L - 4} y={tempP.top + 8} class="axis" text-anchor="end">{tMax}</text>{/if}
      {#if tempP.top + tempP.h - zeroY > 11}<text x={L - 4} y={tempP.top + tempP.h} class="axis" text-anchor="end">{tMin}</text>{/if}
      <line x1={L} x2={L + plotW} y1={zeroY} y2={zeroY} class="zero" />
      <text x={L - 4} y={zeroY + 3} class="axis" text-anchor="end">0</text>
      <path d={linePath(h.temp_c, tempP.top, tempP.h, tMin, tMax)} class="temp" />

      <text x={0} y={windP.top - 5} class="label">{s.chart_wind}</text>
      <text x={L - 4} y={windP.top + 8} class="axis" text-anchor="end">{wMax}</text>
      <line x1={L} x2={L + plotW} y1={windP.top + windP.h} y2={windP.top + windP.h} class="base" />
      <path d={linePath(h.wind_kmh, windP.top, windP.h, 0, wMax)} class="wind" />

      <line x1={x(nowI)} x2={x(nowI)} y1={snowP.top - 2} y2={windP.top + windP.h} class="now" />
      <text x={x(nowI) + 3} y={snowP.top + 8} class="nowlabel">{s.chart_now}</text>

      {#if hover !== null}
        <line x1={x(hover)} x2={x(hover)} y1={snowP.top} y2={windP.top + windP.h} class="cross" />
        {#if h.temp_c[hover] !== null}
          <circle cx={x(hover)} cy={tempP.top + tempP.h - (((h.temp_c[hover] ?? 0) - tMin) / (tMax - tMin)) * tempP.h} r="4" class="dot" />
        {/if}
        {#if h.wind_kmh[hover] !== null}
          <circle cx={x(hover)} cy={windP.top + windP.h - ((h.wind_kmh[hover] ?? 0) / wMax) * windP.h} r="4" class="dot" />
        {/if}
      {/if}
      <rect x={L} y={0} width={plotW} height={height} fill="transparent" />
    </svg>
    {#if readout}
      <div class="tip" style="left: {readout.left}px">
        <b>{readout.when}</b>
        <span><i class="sw snow"></i>{num(readout.snow, 1)} cm</span>
        {#if hasRain}<span><i class="sw rain"></i>{num(readout.rain, 1)} mm</span>{/if}
        <span>{num(readout.temp, 1)} °C</span>
        <span>{num(readout.wind)} km/h {readout.dir}</span>
      </div>
    {:else}
      <p class="hint">{s.chart_hint}</p>
    {/if}
  {/if}
</div>

<style>
  .wrap { position: relative; margin: 4px 0 2px; touch-action: pan-y; }
  svg { display: block; overflow: visible; font-variant-numeric: tabular-nums; }
  .past { fill: #eef1f4; }
  .day { stroke: var(--line); stroke-width: 1; }
  .tick, .axis { font-size: 10.5px; fill: var(--muted); }
  .label { font-size: 12px; fill: var(--ink); font-weight: 600; }
  .base { stroke: #b9c3cd; stroke-width: 1; }
  .zero { stroke: var(--glacier); stroke-width: 1; stroke-dasharray: 3 3; }
  .snow { fill: var(--glacier); }
  .rain { fill: var(--rain); }
  .temp, .wind { fill: none; stroke: var(--ink); stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }
  .now { stroke: var(--ink); stroke-width: 1; stroke-dasharray: 2 2; }
  .nowlabel { font-size: 10.5px; fill: var(--ink); font-weight: 700; }
  .cross { stroke: var(--ink); stroke-width: 1; opacity: 0.5; }
  .dot { fill: var(--ink); stroke: var(--snow); stroke-width: 2; }
  .tip {
    position: absolute; top: 0; width: 140px; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px #17283a33;
    padding: 6px 9px; font-size: var(--fs-xs); display: grid; gap: 1px; pointer-events: none; font-variant-numeric: tabular-nums;
  }
  .sw { display: inline-block; width: 9px; height: 9px; border-radius: 2px; margin-right: 5px; }
  .sw.snow { background: var(--glacier); }
  .sw.rain { background: var(--rain); }
  .hint { font-size: 12px; color: var(--muted); margin: 2px 0 0; }
</style>
