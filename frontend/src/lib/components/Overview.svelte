<script lang="ts">
  import { COMPASS_DEG, num } from '$lib/format';
  import { fill } from '$lib/i18n';
  import { selectPlace, t, toggleFollow, ui } from '$lib/state.svelte';
  import type { Place } from '$lib/types';
  import LevelBadge from './LevelBadge.svelte';

  const s = $derived(t());
  const groups = $derived.by(() => {
    const places = ui.weather?.places ?? [];
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
    const places = ui.weather?.places;
    if (!places) return;
    let seen: Record<string, keyof typeof RANK> = {};
    try { seen = JSON.parse(localStorage.getItem(SEEN) ?? '{}'); } catch { /* first visit */ }
    rose = new Set(places.filter((p) => seen[p.id] && RANK[p.level] > RANK[seen[p.id]]).map((p) => p.id));
    try { localStorage.setItem(SEEN, JSON.stringify(Object.fromEntries(places.map((p) => [p.id, p.level])))); } catch { /* private mode */ }
  });

  const counts = $derived({
    serious: (ui.weather?.places ?? []).filter((p) => p.level === 'serious').length,
    attention: (ui.weather?.places ?? []).filter((p) => p.level === 'attention').length
  });
</script>

{#if counts.serious}
  <p class="banner serious"><LevelBadge level="serious" compact /> {counts.serious === 1 ? s.banner_serious_one : fill(s.banner_serious, { n: counts.serious })}</p>
{:else if counts.attention}
  <p class="banner attention"><LevelBadge level="attention" compact /> {counts.attention === 1 ? s.banner_attention_one : fill(s.banner_attention, { n: counts.attention })}</p>
{:else}
  <p class="banner calm">{s.banner_none}</p>
{/if}
<p class="small note">{s.overview_note}</p>

{#each groups as g (g.title)}
  <h2>{g.title}</h2>
  <ul>
    {#each g.places as p (p.id)}
      {@const h = p.headline}
      <li>
        <button onclick={() => selectPlace(p.id)}>
          <span class="where">
            <b>{p.name[ui.lang]}</b>{#if p.pilot}<em>{s.pilot}</em>{/if}{#if rose.has(p.id)}<em class="new">{s.new_badge}</em>{/if}
            <small>{p.range[ui.lang]}, {h.elevation} m</small>
          </span>
          <span class="snow" class:zero={!h.snow_next72_cm}>{num(h.snow_next72_cm)}<small>&nbsp;cm</small></span>
          <span class="wind">
            {#if h.wind_next72.from}
              <svg viewBox="0 0 16 16" aria-hidden="true" style="transform: rotate({COMPASS_DEG[h.wind_next72.from] + 180}deg)">
                <path d="M8 1 13 9H9.5v6h-3V9H3z" fill="currentColor" />
              </svg>
            {/if}{num(h.wind_next72.max_kmh)}
          </span>
          <span class="lvl"><LevelBadge level={p.level} compact /></span>
        </button>
      </li>
    {/each}
  </ul>
{/each}

<style>
  .note { margin: 0 0 4px; }
  h2 { font-size: 13px; font-weight: 650; color: var(--muted); margin: 14px 0 2px; }
  ul { list-style: none; margin: 0; padding: 0; }
  button {
    width: 100%; display: grid; grid-template-columns: 1fr auto 62px 16px; align-items: center; gap: 8px;
    border: 0; border-top: 1px solid var(--line); background: none; padding: 8px 2px; text-align: left; cursor: pointer;
    font-variant-numeric: tabular-nums;
  }
  button:hover { background: var(--tint); }
  .where b { font-weight: 650; }
  .where em { font-style: normal; font-size: 11px; font-weight: 700; color: var(--glacier); border: 1px solid var(--glacier); border-radius: 4px; padding: 0 4px; margin-left: 6px; vertical-align: 1px; }
  .where em.new { color: var(--serious); border-color: var(--serious); }
  .where small { display: block; font-size: 12px; color: var(--muted); }
  .snow { font-size: 17px; font-weight: 750; color: var(--glacier); text-align: right; }
  .snow.zero { color: var(--muted); font-weight: 600; }
  .snow small { font-size: 11px; font-weight: 500; }
  .wind { font-size: 13px; font-weight: 600; text-align: right; white-space: nowrap; }
  .wind svg { width: 12px; height: 12px; vertical-align: -1px; margin-right: 3px; }
  .lvl { display: flex; justify-content: center; }
  .banner { display: flex; gap: 8px; align-items: center; margin: 0 0 8px; padding: 8px 10px; border-radius: 8px; font-size: 14px; font-weight: 600; }
  .banner.serious { background: var(--serious-bg); color: var(--serious); }
  .banner.attention { background: var(--signal-bg); color: #7a5200; }
  .banner.calm { background: var(--tint); color: var(--ink); font-weight: 500; }
</style>
