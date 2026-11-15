<script lang="ts">
  import { fill } from '#lib/i18n.ts';
  import { data, t, ui } from '#lib/state.svelte.ts';

  const s = $derived(t());
  const m = $derived(data.meta);
  // AutoATES v3.0 palette (as in backend/ates/export_maps.py).
  const ATES = [['simple', '144,239,152'], ['challenging', '0,173,255'], ['complex', '241,83,147'], ['extreme', '180,0,255']] as const;
</script>

{#if m}
  <div class="seg" role="group">
    <button aria-pressed={ui.layer === 'slope'} onclick={() => (ui.layer = 'slope')}>{s.slope}</button>
    <button aria-pressed={ui.layer === 'aspect'} onclick={() => (ui.layer = 'aspect')}>{s.aspect}</button>
    {#if ui.draftAtes}<button aria-pressed={ui.layer === 'ates'} onclick={() => (ui.layer = 'ates')}>{s.ates}</button>{/if}
  </div>

  {#if ui.layer === 'ates'}
    <p class="draft">{s.ates_note}</p>
    <div class="ates" role="list">
      {#each ATES as [key, rgb] (key)}
        <span role="listitem"><i style="background: rgb({rgb})"></i>{s.ates_classes[key]}</span>
      {/each}
    </div>
  {:else if ui.layer === 'slope'}
    <!-- Labels sit under the colours, in ink: no text colour reaches 7:1 on the red and purple bands. -->
    <div class="scale" role="list">
      {#each m.slope_legend as c (c.label)}
        <span role="listitem"><i style="background: rgb({c.rgba.slice(0, 3).join(',')})"></i>{c.label}</span>
      {/each}
    </div>
    <p class="hint">{s.slope_hint}</p>
  {:else}
    <div class="compass" role="list">
      {#each m.aspect_legend as c (c.label)}
        <span role="listitem"><i style="background: rgb({c.rgb.join(',')})"></i>{c.label}</span>
      {/each}
    </div>
    <p class="hint">{s.aspect_hint}</p>
  {/if}

  <label class="toggle"><input type="checkbox" bind:checked={ui.relief} /> {s.relief}</label>
  <label class="toggle"><input type="checkbox" bind:checked={ui.contours} /> {s.contours}</label>

  <details>
    <summary>{s.area_title}</summary>
    <div class="kv"><span>{s.elevation}</span><b>{m.stats.elevation_min_m}–{m.stats.elevation_max_m} m</b></div>
    <p class="small">{fill(s.terrain_about, { res: m.resolution_m })}</p>
    <p class="small">{m.source}</p>
  </details>
{/if}

<style>
  .seg { display: inline-flex; background: #e8edf2; border-radius: 8px; padding: 3px; margin-bottom: 10px; }
  .seg button { border: 0; background: none; padding: 5px 12px; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 600; color: var(--muted); }
  .seg button[aria-pressed='true'] { background: #fff; color: var(--ink); box-shadow: 0 1px 2px #17283a26; }
  .scale { display: flex; font-size: 12px; font-weight: 650; color: var(--ink); }
  .scale span { flex: 1; display: grid; gap: 4px; text-align: center; }
  .scale i { height: 14px; }
  .scale span:first-child i { border-radius: 6px 0 0 6px; }
  .scale span:last-child i { border-radius: 0 6px 6px 0; }
  .compass { display: grid; grid-template-columns: repeat(8, 1fr); gap: 3px; font-size: 12px; font-weight: 650; color: var(--ink); }
  .compass span { display: grid; gap: 4px; text-align: center; }
  .compass i { height: 14px; border-radius: 4px; }
  .draft { margin: 0 0 10px; padding: 8px 10px; border-radius: 8px; background: var(--serious-bg); color: var(--serious); font-size: 13px; font-weight: 600; }
  .ates { display: grid; gap: 6px; font-size: 13px; font-weight: 600; margin-bottom: 10px; }
  .ates span { display: flex; align-items: center; gap: 8px; }
  .ates i { width: 22px; height: 14px; border-radius: 3px; box-shadow: 0 0 0 1px #17283a33; }
  .hint { font-size: 13px; color: var(--muted); margin: 8px 0 10px; }
  .toggle { display: flex; align-items: center; gap: 8px; font-size: 14px; padding: 6px 0 10px; cursor: pointer; }
  .kv { display: flex; justify-content: space-between; font-size: 14px; padding: 4px 0; }
  /* Touch screens (gloves): at least 48 px targets. */
  @media (pointer: coarse) {
    .seg button { min-height: 48px; }
    .toggle { min-height: 48px; padding: 0; }
    .toggle input { width: 22px; height: 22px; }
  }
</style>
