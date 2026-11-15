<script lang="ts">
  // "Weather to watch": the weather concerns of a place, grouped by the avalanche problem they typically
  // create (after SLF "Caution Avalanches!", 2026): what, how long it lasts, where, what to look for.
  // Cards are named after the weather, never the avalanche problem, and nothing here may read as
  // "safe": this is not a danger rating, and old weak layers can't be judged from weather.
  import { byHeight, snowFree } from '#lib/format.ts';
  import { fill, type Problem } from '#lib/i18n.ts';
  import { currentPlace, t } from '#lib/state.svelte.ts';
  import type { Compass, Flag, FlagCode } from '#lib/types.ts';
  import AspectRose from '../AspectRose.svelte';
  import LevelBadge from '../LevelBadge.svelte';
  import { flagKey, flagText } from '#lib/flags.ts';

  const PROBLEM: Record<FlagCode, Problem> = {
    heavy_snow_coming: 'new_snow', recent_heavy_snow: 'new_snow',
    wind_drifting: 'wind_slab', strong_wind: 'wind_slab',
    rain_on_snow: 'wet_snow', warming_after_snow: 'wet_snow'
  };
  const ORDER: Compass[] = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];

  const s = $derived(t());
  const place = $derived(currentPlace());
  const pts = $derived(place ? byHeight(place.points) : []);
  const top = $derived(pts[0]);
  const calm = $derived(pts.length && pts.every(snowFree) ? 'snowfree' : 'favourable');

  // One card per problem: its most severe flag, the flags behind it, and the lowest elevation affected.
  const problems = $derived.by(() => {
    // eslint-disable-next-line svelte/prefer-svelte-reactivity -- built and read inside this $derived, never kept
    const m = new Map<Problem, { flag: Flag; codes: Set<string>; flags: Flag[]; from_m: number }>();
    for (const p of pts)
      for (const f of p.flags) {
        const k = PROBLEM[f.code];
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
    return [...m.entries()].map(([k, v]) => ({ key: k, ...v, loads: loads(v.flag) })).sort((a, b) => rank(b) - rank(a));
  });

  /** The loaded slopes of a drifting-snow flag (other flags carry no aspect). */
  const loads = (f: Flag): Compass | null => (f.code === 'wind_drifting' ? f.loads : null);
  const lee = (c: Compass): Compass[] => {
    const i = ORDER.indexOf(c);
    return [ORDER[(i + 7) % 8]!, c, ORDER[(i + 1) % 8]!];
  };

</script>

{#snippet icon(key: string)}
  {#if key === 'new_snow'}
    <svg viewBox="0 0 24 24"><path d="M12 2v20M3.3 7l17.4 10M20.7 7 3.3 17M9 4l3 3 3-3M9 20l3-3 3 3" /></svg>
  {:else if key === 'wind_slab'}
    <svg viewBox="0 0 24 24"><path d="M3 8h11a3 3 0 1 0-3-3M3 12h16a3 3 0 1 1-3 3M3 16h8" /></svg>
  {:else if key === 'wet_snow'}
    <svg viewBox="0 0 24 24"><path d="M12 3s6 7 6 11a6 6 0 0 1-12 0c0-4 6-11 6-11z" /></svg>
  {:else}
    <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" /><path d="M12 11v6M12 7.5v.5" /></svg>
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
        {#if p.key === 'wind_slab' && p.loads}
          <AspectRose aspects={lee(p.loads)} label={fill(s.above_m, { m: p.from_m })} />
        {:else}
          <p class="where"><b>{s.sit_where}:</b> {fill(s.above_m, { m: p.from_m })}. {s.prob[p.key].where}</p>
        {/if}
        <ul class="facts">{#each p.flags as f (flagKey(f))}<li>{flagText(f, s)}</li>{/each}</ul>
        <p class="why">{s.prob[p.key].why}</p>
        <p class="look"><b>{s.sit_look}:</b> {s.prob[p.key].look}</p>
      </details>
    {:else}
      <article class="card calm">
        <div class="summary-row">
          <span class="icon" aria-hidden="true">{@render icon('favourable')}</span>
          <span class="head">
            <span class="title"><b>{s.prob[calm].name}</b></span>
            <span class="meta">{s.prob[calm].short}</span>
          </span>
        </div>
        <details class="more">
          <summary>{s.why_label}</summary>
          <p class="why">{s.prob[calm].why}</p>
        </details>
      </article>
    {/each}

  </section>
{/if}

<style>
  section { display: grid; gap: 8px; }
  h2 { font-size: var(--fs-m); margin: 0; }
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
  .facts { margin: 0; padding-left: 18px; font-size: var(--fs-s); font-weight: 600; }
  .head { display: grid; gap: 1px; min-width: 0; }
  .title { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; font-size: var(--fs-m); line-height: 1.25; }
  .meta { font-size: var(--fs-xs); color: var(--muted); }
  .fact { font-size: var(--fs-s); font-weight: 600; margin-top: 2px; }
  .where, .why, .look { margin: 0; font-size: var(--fs-s); }
  .look { color: var(--ink); }
  .more { border-top: 0; margin: 0; }
  .more summary { font-size: var(--fs-s); font-weight: 400; color: var(--glacier); cursor: pointer; padding: 4px 0 0; }
  .more summary::after { content: none; }
  .more .why { margin-top: 4px; }
</style>
