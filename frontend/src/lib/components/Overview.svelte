<script lang="ts">
  import WindArrow from './WindArrow.svelte';
  import { num, snowFree, STRONG_WIND_KMH } from '#lib/format.ts';
  import { fill } from '#lib/i18n.ts';
  import { data, selectPlace, t, ui } from '#lib/state.svelte.ts';
  import type { Place } from '#lib/types.ts';
  import LevelBadge from './LevelBadge.svelte';

  const s = $derived(t());
  const groups = $derived.by(() => {
    const places = data.weather?.places ?? [];
    // Most severe first, then pilot, then most new snow, then alphabetical.
    const rank = { serious: 2, attention: 1, none: 0 };
    const order = (a: Place, b: Place) =>
      rank[b.level] - rank[a.level] ||
      Number(b.pilot) - Number(a.pilot) ||
      b.headline.snow_next72_cm - a.headline.snow_next72_cm ||
      a.name[ui.lang].localeCompare(b.name[ui.lang], ui.lang);
    const followed = places.filter((p) => ui.followed.includes(p.id)).sort(order);
    return [
      ...(followed.length ? [{ title: s.followed_title, places: followed }] : []),
      { title: s.group_resort, places: places.filter((p) => p.kind === 'resort' && !ui.followed.includes(p.id)).sort(order) },
      { title: s.group_touring, places: places.filter((p) => p.kind === 'touring' && !ui.followed.includes(p.id)).sort(order) }
    ];
  });
  // Places whose level went up since this browser last saw the overview.
  const SEEN = 'lavinoko.seenLevels';
  const RANK = { none: 0, attention: 1, serious: 2 } as const;
  let rose = $state(new Set<string>());
  $effect(() => {
    const places = data.weather?.places;
    if (!places) return;
    let seen: Record<string, keyof typeof RANK> = {};
    try { seen = JSON.parse(localStorage.getItem(SEEN) ?? '{}'); } catch { /* first visit */ }
    rose = new Set(places.filter((p) => { const before = seen[p.id]; return before !== undefined && RANK[p.level] > RANK[before]; }).map((p) => p.id));
    try { localStorage.setItem(SEEN, JSON.stringify(Object.fromEntries(places.map((p) => [p.id, p.level])))); } catch { /* private mode */ }
  });

  const noSnow = $derived((data.weather?.places ?? []).every((p) => p.points.every(snowFree)));
  const counts = $derived({
    serious: (data.weather?.places ?? []).filter((p) => p.level === 'serious').length,
    attention: (data.weather?.places ?? []).filter((p) => p.level === 'attention').length
  });
</script>

{#if counts.serious}
  <p class="banner serious"><LevelBadge level="serious" compact /> {counts.serious === 1 ? s.banner_serious_one : fill(s.banner_serious, { n: counts.serious })}</p>
{:else if counts.attention}
  <p class="banner attention"><LevelBadge level="attention" compact /> {counts.attention === 1 ? s.banner_attention_one : fill(s.banner_attention, { n: counts.attention })}</p>
{:else}
  <p class="banner calm">{noSnow ? s.banner_snowfree : s.banner_none}</p>
{/if}
<p class="small note">{s.overview_note}</p>
<div class="cols-head" aria-hidden="true"><span></span><span>{s.ov_col_snow}</span><span>{s.ov_col_wind}</span><span></span></div>

{#each groups as g (g.title)}
  <h2>{g.title}</h2>
  <ul>
    {#each g.places as p (p.id)}
      {@const h = p.headline}
      <li>
        <button
          onclick={() => selectPlace(p.id)}
          onpointerenter={() => (ui.hoverPlace = p.id)}
          onpointerleave={() => (ui.hoverPlace = null)}
          onfocus={() => (ui.hoverPlace = p.id)}
          onblur={() => (ui.hoverPlace = null)}
        >
          <span class="where">
            <b>{p.name[ui.lang]}</b>{#if p.pilot}<em>{s.pilot}</em>{/if}{#if rose.has(p.id)}<em class="new">{s.new_badge}</em>{/if}
            <small>{#if p.range[ui.lang] !== p.name[ui.lang]}{p.range[ui.lang]}, {/if}{h.elevation} m</small>
          </span>
          <span class="snow" class:zero={!h.snow_next72_cm}>{num(h.snow_next72_cm)}<small>&nbsp;cm</small></span>
          <span class="wind" class:strong={(h.wind_next72.max_kmh ?? 0) >= STRONG_WIND_KMH}>
            <WindArrow from={h.wind_next72.from} size={12} />{num(h.wind_next72.max_kmh)}
          </span>
          <span class="lvl"><LevelBadge level={p.level} compact /></span>
        </button>
      </li>
    {/each}
  </ul>
{/each}

<style>
  .note { margin: 0 0 4px; }
  h2 { font-size: var(--fs-s); font-weight: 600; color: var(--muted); margin: 14px 0 2px; }
  ul { list-style: none; margin: 0; padding: 0; }
  button {
    width: 100%; display: grid; grid-template-columns: 1fr 64px 72px 16px; align-items: center; gap: 8px;
    border: 0; border-top: 1px solid var(--line); background: none; padding: 8px 2px; text-align: left; cursor: pointer;
    font-variant-numeric: tabular-nums;
  }
  button:hover { background: var(--tint); }
  .where b { font-weight: 600; }
  .where em { font-style: normal; font-size: var(--fs-xs); font-weight: 700; color: var(--glacier); border: 1px solid var(--glacier); border-radius: 4px; padding: 0 4px; margin-left: 6px; vertical-align: 1px; }
  .where em.new { color: var(--serious); border-color: var(--serious); }
  .where small { display: block; font-size: var(--fs-xs); color: var(--muted); }
  .snow { font-size: var(--fs-l); font-weight: 700; color: var(--glacier); text-align: right; }
  .snow.zero { color: var(--muted); font-weight: 600; }
  .snow small { font-size: var(--fs-xs); font-weight: 400; }
  .wind { font-size: var(--fs-s); font-weight: 400; color: var(--muted); text-align: right; white-space: nowrap; }
  .wind.strong { font-weight: 700; color: var(--ink); }
  .cols-head { display: grid; grid-template-columns: 1fr 64px 72px 16px; gap: 8px; padding: 6px 2px 0; font-size: var(--fs-xs); color: var(--muted); text-align: right; line-height: 1.2; }
  .lvl { display: flex; justify-content: center; }
  .banner { display: flex; gap: 8px; align-items: center; margin: 0 0 8px; padding: 8px 10px; border-radius: 8px; font-size: var(--fs-s); font-weight: 600; }
  .banner.serious { background: var(--serious-bg); color: var(--serious); }
  .banner.attention { background: var(--signal-bg); color: var(--attention-ink); }
  .banner.calm { background: var(--tint); color: var(--ink); font-weight: 400; }
</style>
