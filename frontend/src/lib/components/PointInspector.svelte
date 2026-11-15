<script lang="ts">
  // Card for a tapped point: coordinates to read out to 112, terrain at the spot, live weather window.
  import { num } from '#lib/format.ts';
  import { fill } from '#lib/i18n.ts';
  import { compassOf, terrainAt, toDms, weatherAt, type HourRow, type Terrain } from '#lib/inspect.ts';
  import { data, t, ui } from '#lib/state.svelte.ts';

  const s = $derived(t());
  const pt = $derived(ui.inspect);
  let terrain: Terrain | null = $state(null);
  let hours: HourRow[] = $state([]);
  let failed = $state(false);
  let copied = $state(false);

  $effect(() => {
    const p = pt;
    terrain = null;
    hours = [];
    failed = false;
    copied = false;
    if (!p) return;
    terrainAt(p.lat, p.lon)
      .then(async (tr) => {
        if (p !== ui.inspect) return;
        terrain = tr;
        const w = await weatherAt(p.lat, p.lon, tr.elevation);
        if (p === ui.inspect) hours = w;
      })
      .catch(() => (failed = true));
  });

  const nearest = $derived.by(() => {
    if (!pt) return null;
    let best: { name: string; km: number } | null = null;
    for (const pl of data.weather?.places ?? []) {
      const km = Math.hypot((pl.center[0] - pt.lon) * 111 * Math.cos((pt.lat * Math.PI) / 180), (pl.center[1] - pt.lat) * 111);
      if (!best || km < best.km) best = { name: pl.name[ui.lang], km };
    }
    return best;
  });
  const steep = $derived(((terrain as Terrain | null)?.slope ?? 0) >= 30);
  const rows = $derived(hours.filter((_, i) => i % 3 === 0));
  const coordText = $derived(pt ? `${pt.lat.toFixed(5)}, ${pt.lon.toFixed(5)}` : '');

  async function copy() {
    try {
      await navigator.clipboard.writeText(`${coordText} (${toDms(pt!.lat, 'N', 'S')} ${toDms(pt!.lon, 'E', 'W')})`);
      copied = true;
    } catch {
      /* clipboard not available */
    }
  }
</script>

{#if pt}
  <section class="card" aria-label={s.inspect_title}>
    <header>
      <b>{s.inspect_title}</b>
      <button class="x" onclick={() => (ui.inspect = null)} aria-label={s.close}>×</button>
    </header>

    <p class="coord">{coordText}</p>
    <p class="dms">{toDms(pt.lat, 'N', 'S')} · {toDms(pt.lon, 'E', 'W')}</p>
    <button class="copy" onclick={copy}>{copied ? s.copied : s.copy_coords}</button>

    {#if terrain}
      <div class="terrain">
        <span><small>{s.elevation}</small><b>{terrain.elevation} m</b></span>
        <span class:steep><small>{s.slope}</small><b>{num(terrain.slope)}°</b></span>
        <span><small>{s.aspect}</small><b>{terrain.aspect ?? '–'}</b></span>
      </div>
      {#if steep}<p class="warn">{s.inspect_steep}</p>{/if}
    {:else if failed}
      <p class="small">{s.inspect_offline}</p>
    {:else}
      <p class="small">…</p>
    {/if}
    {#if nearest}<p class="small">{fill(s.inspect_nearest, { name: nearest.name, km: nearest.km.toFixed(1) })}</p>{/if}

    {#if rows.length}
      <h3>{s.inspect_window}</h3>
      <table>
        <thead><tr><th></th><th>{s.col_wind}</th><th>{s.gusts}</th><th>{s.cloud}</th><th>{s.visibility}</th><th>{s.precip}</th></tr></thead>
        <tbody>
          {#each rows as r (r.time)}
            <tr>
              <td>{r.time}</td>
              <td>{num(r.wind)} {compassOf(r.dir)}</td>
              <td>{num(r.gust)}</td>
              <td>{num(r.cloud)}%</td>
              <td class:low={(r.visibility ?? 99999) < 1000}>{r.visibility === null ? '–' : r.visibility >= 10000 ? '>10 km' : `${num(r.visibility / 1000, 1)} km`}</td>
              <td>{r.snow ? `${num(r.snow, 1)} cm` : r.precip ? `${num(r.precip, 1)} mm` : '–'}</td>
            </tr>
          {/each}
        </tbody>
      </table>
      <p class="small">{s.inspect_note}</p>
    {/if}
  </section>
{/if}

<style>
  .card {
    position: absolute; z-index: 3; right: 64px; top: 12px; width: 320px; max-height: calc(100% - 24px); overflow: auto;
    background: var(--snow); border-radius: 12px; box-shadow: 0 2px 10px #17283a33; padding: 12px 14px; font-size: var(--fs-s);
  }
  header { display: flex; justify-content: space-between; align-items: center; }
  .x { border: 0; background: none; font-size: var(--fs-xl); line-height: 1; cursor: pointer; padding: 0 4px; color: var(--muted); }
  .coord { font: 700 var(--fs-l)/1.2 system-ui, sans-serif; margin: 6px 0 0; font-variant-numeric: tabular-nums; }
  .dms { margin: 1px 0 6px; color: var(--muted); font-size: var(--fs-xs); }
  .copy { border: 1px solid var(--line); background: #fff; border-radius: 999px; padding: 4px 12px; font-size: var(--fs-xs); cursor: pointer; }
  .terrain { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin: 10px 0 4px; }
  .terrain span { display: grid; background: #fff; border: 1px solid var(--line); border-radius: 8px; padding: 5px 8px; }
  .terrain small { font-size: var(--fs-xs); color: var(--muted); }
  .terrain b { font-size: var(--fs-m); }
  .terrain .steep { border-color: var(--serious); }
  .warn { margin: 4px 0; padding: 5px 8px; border-radius: 7px; background: var(--serious-bg); color: var(--serious); font-weight: 600; font-size: var(--fs-xs); }
  h3 { font-size: var(--fs-s); margin: 10px 0 4px; }
  table { width: 100%; border-collapse: collapse; font-size: var(--fs-xs); font-variant-numeric: tabular-nums; }
  th { font-weight: 400; color: var(--muted); font-size: var(--fs-xs); text-align: right; padding: 0 3px 3px; }
  td { text-align: right; padding: 3px; border-top: 1px solid var(--line); white-space: nowrap; }
  th:first-child, td:first-child { text-align: left; }
  td.low { color: var(--serious); font-weight: 700; }
  /* Touch screens (gloves): at least 48 px targets. */
  @media (pointer: coarse) {
    .x { min-width: 48px; min-height: 48px; margin: -8px -8px -8px 0; }
    .copy { min-height: 48px; padding: 4px 16px; font-size: var(--fs-s); }
  }
  @media (max-width: 560px) {
    .card { left: 0; right: 0; bottom: 0; top: auto; width: auto; max-height: 55%; border-radius: 14px 14px 0 0; }
  }
  @media print { .card { display: none; } }
</style>
