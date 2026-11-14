<script lang="ts">
  // "Situation": the weather concerns of a place, expressed as the avalanche problem they typically
  // create (after SLF "Caution Avalanches!", 2026): what, how long it lasts, where, what to look for.
  // Weather-based only: not a danger rating, and old weak layers can't be judged from weather.
  import { byHeight, num } from '$lib/format';
  import { fill } from '$lib/i18n';
  import { currentPlace, t } from '$lib/state.svelte';
  import type { Compass, Flag } from '$lib/types';
  import AspectRose from '../AspectRose.svelte';
  import LevelBadge from '../LevelBadge.svelte';
  import { flagText } from '$lib/flags';

  type Problem = 'new_snow' | 'wind_slab' | 'wet_snow';
  const PROBLEM: Record<string, Problem> = {
    heavy_snow_coming: 'new_snow', recent_heavy_snow: 'new_snow',
    wind_drifting: 'wind_slab', strong_wind: 'wind_slab',
    rain_on_snow: 'wet_snow', warming_after_snow: 'wet_snow'
  };
  const ORDER: Compass[] = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];

  const s = $derived(t());
  const place = $derived(currentPlace());
  const pts = $derived(place ? byHeight(place.points) : []);
  const top = $derived(pts[0]);

  // One card per problem: its most severe flag, the flags behind it, and the lowest elevation affected.
  const problems = $derived.by(() => {
    const m = new Map<Problem, { flag: Flag; codes: Set<string>; flags: Flag[]; from_m: number }>();
    for (const p of pts)
      for (const f of p.flags) {
        const k = PROBLEM[f.code];
        if (!k) continue;
        const cur = m.get(k);
        if (!cur) m.set(k, { flag: f, codes: new Set([f.code]), flags: [f], from_m: p.elevation });
        else {
          if (!cur.codes.has(f.code)) cur.flags.push(f);
          cur.codes.add(f.code);
          cur.from_m = Math.min(cur.from_m, p.elevation);
          if (f.level === 'serious' && cur.flag.level !== 'serious') cur.flag = f;
        }
      }
    const rank = (x: { flag: Flag }) => (x.flag.level === 'serious' ? 1 : 0);
    return [...m.entries()].map(([k, v]) => ({ key: k, ...v })).sort((a, b) => rank(b) - rank(a));
  });

  const lee = (f: Flag): Compass[] => {
    const i = ORDER.indexOf(f.loads as Compass);
    return i < 0 ? [] : [ORDER[(i + 7) % 8], ORDER[i], ORDER[(i + 1) % 8]];
  };

  // New snow over the past 3 days plus the next 3, against the leaflet's critical amounts.
  const snow3 = $derived(top ? top.past72.snow_cm + top.next72.snow_cm : 0);
  const SCALE = 60;
  const pct = (cm: number) => Math.min(100, (cm / SCALE) * 100);
</script>

{#snippet icon(key: string)}
  {#if key === 'new_snow'}
    <svg viewBox="0 0 24 24"><path d="M12 2v20M3.3 7l17.4 10M20.7 7 3.3 17M9 4l3 3 3-3M9 20l3-3 3 3" /></svg>
  {:else if key === 'wind_slab'}
    <svg viewBox="0 0 24 24"><path d="M3 8h11a3 3 0 1 0-3-3M3 12h16a3 3 0 1 1-3 3M3 16h8" /></svg>
  {:else if key === 'wet_snow'}
    <svg viewBox="0 0 24 24"><path d="M12 3s6 7 6 11a6 6 0 0 1-12 0c0-4 6-11 6-11z" /></svg>
  {:else}
    <svg viewBox="0 0 24 24"><path d="m5 12 4 4 10-10" /></svg>
  {/if}
{/snippet}

{#if place && top}
  <section aria-labelledby="sit-h">
    <h2 id="sit-h">{s.sit_title}</h2>

    {#each problems as p, i (p.key)}
      <details class="card {p.flag.level}" open={i === 0}>
        <summary>
          <span class="icon" aria-hidden="true">{@render icon(p.key)}</span>
          <span class="head">
            <span class="title"><b>{s.prob[p.key].name}</b><LevelBadge level={p.flag.level} compact /></span>
            <span class="meta">{s.prob[p.key].lasts}{#if p.flag.agree} · {fill(s.agree, { n: p.flag.agree, m: p.flag.models })}{/if}</span>
            {#if i > 0}<span class="fact">{flagText(p.flag, s)}</span>{/if}
          </span>
        </summary>
        {#if p.key === 'wind_slab' && p.flag.loads}
          <AspectRose aspects={lee(p.flag)} label={fill(s.above_m, { m: p.from_m })} />
        {:else}
          <p class="where"><b>{s.sit_where}:</b> {fill(s.above_m, { m: p.from_m })}. {s.prob[p.key].where}</p>
        {/if}
        <ul class="facts">{#each p.flags as f (f.code + (f.period ?? ''))}<li>{flagText(f, s)}</li>{/each}</ul>
        <p class="why">{s.prob[p.key].why}</p>
        <p class="look"><b>{s.sit_look}:</b> {s.prob[p.key].look}</p>
      </details>
    {:else}
      <article class="card calm">
        <div class="summary-row">
          <span class="icon" aria-hidden="true">{@render icon('favourable')}</span>
          <span class="head"><span class="title"><b>{s.prob.favourable.name}</b></span></span>
        </div>
        <p class="why">{s.prob.favourable.why}</p>
      </article>
    {/each}

    <div class="gauge" aria-label={fill(s.snow3_aria, { cm: num(snow3) })}>
      <div class="glabel"><b>{s.snow3_title}</b><span>{num(snow3)} cm</span></div>
      <div class="bar">
        <span class="zone z1" style="left: {pct(10)}%; width: {pct(20) - pct(10)}%"></span>
        <span class="zone z2" style="left: {pct(20)}%; width: {pct(30) - pct(20)}%"></span>
        <span class="zone z3" style="left: {pct(30)}%; width: {pct(50) - pct(30)}%"></span>
        <span class="fill" style="width: {pct(snow3)}%"></span>
      </div>
      <div class="ticks">{#each [0, 10, 20, 30, 50] as v (v)}<span style="left: {pct(v)}%">{v}</span>{/each}</div>
      <p class="small">{s.snow3_note}</p>
    </div>

    <p class="overnight"><b>{s.overnight}:</b> {fill(s.overnight_line, {
      snow: num(top.past12.snow_cm), wind: num(top.past12.wind.max_kmh), from: top.past12.wind.from ?? '', temp: num(top.past12.temp_min_c)
    })} <span>({top.elevation} m)</span></p>
  </section>
{/if}

<style>
  section { display: grid; gap: 8px; }
  h2 { font-size: 15px; margin: 0; }
  .card { border-radius: 10px; padding: 10px 12px; display: grid; gap: 6px; border: 1px solid var(--line); background: #fff; }
  details.card { border-top: 1px solid var(--line); }
  details.card[open] { gap: 8px; }
  .card.attention { background: var(--signal-bg); border-color: #f0d38a; }
  .card.serious { background: var(--serious-bg); border-color: #f0b8b2; }
  .card.calm { background: var(--tint); border-color: #cfe0f1; }
  summary, .summary-row { display: flex; gap: 10px; align-items: flex-start; list-style: none; cursor: pointer; padding: 0; font-weight: 400; }
  .summary-row { cursor: default; }
  summary::after { display: none; }
  details:not([open]) summary { opacity: 0.95; }
  .icon { flex: none; width: 34px; height: 34px; border-radius: 8px; background: #fff; display: grid; place-items: center; box-shadow: 0 0 0 1px #17283a1a; }
  .icon :global(svg) { width: 20px; height: 20px; fill: none; stroke: var(--ink); stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
  .facts { margin: 0; padding-left: 18px; font-size: 13.5px; font-weight: 600; }
  .head { display: grid; gap: 1px; min-width: 0; }
  .title { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; font-size: 15.5px; line-height: 1.25; }
  .meta { font-size: 12px; color: var(--muted); }
  .fact { font-size: 13px; font-weight: 600; margin-top: 2px; }
  .where, .why, .look { margin: 0; font-size: 13.5px; }
  .look { color: var(--ink); }
  .gauge { padding: 4px 2px 0; }
  .glabel { display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 4px; }
  .glabel span { font-weight: 800; color: var(--glacier); }
  .bar { position: relative; height: 10px; border-radius: 5px; background: #e8edf2; overflow: hidden; }
  .zone { position: absolute; top: 0; bottom: 0; }
  .z1 { background: #f6e3a8; } .z2 { background: #f2c27a; } .z3 { background: #ea9a7a; }
  .fill { position: absolute; left: 0; top: 3px; bottom: 3px; background: var(--glacier); border-radius: 3px; }
  .ticks { position: relative; height: 14px; font-size: 10.5px; color: var(--muted); }
  .ticks span { position: absolute; transform: translateX(-50%); }
  .ticks span:first-child { transform: none; }
  .overnight { margin: 0; font-size: 13px; padding-top: 8px; border-top: 1px solid var(--line); }
  .overnight span { color: var(--muted); }
</style>
