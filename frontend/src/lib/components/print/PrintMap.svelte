<script lang="ts">
  import type { MapPicture } from '$lib/mapHandle';
  import { t, ui } from '$lib/state.svelte';

  let { pic, labels }: { pic: MapPicture | null; labels: string[] } = $props();
  const s = $derived(t());

  // The overlay uses the picture's own pixel space, so grid and points line up exactly.
  const W = $derived(pic?.width ?? 1600);
  const H = $derived(pic?.height ?? 724);
  const FONT = 21; // ≈ 7 pt on the 190 mm wide frame

  const decimals = $derived(pic ? (pic.step < 0.01 ? 3 : pic.step < 0.1 ? 2 : 1) : 2);

  // Two-segment scale bar of a round length, about a fifth of the width.
  const scale = $derived.by(() => {
    if (!pic) return null;
    const target = pic.widthMeters * 0.2;
    const nice = [100, 200, 250, 500, 1000, 2000, 2500, 5000, 10000, 20000];
    const m = nice.reduce((a, b) => (Math.abs(b - target) < Math.abs(a - target) ? b : a));
    return { px: (m / pic.widthMeters) * W, label: m >= 1000 ? `${m / 1000} km` : `${m} m` };
  });
</script>

<figure>
  <div class="frame">
    {#if pic}
      <img src={pic.url} alt="" />
      <svg viewBox="0 0 {W} {H}" preserveAspectRatio="none" aria-hidden="true">
        {#each pic.lons as g (g.value)}
          <line x1={g.at * W} x2={g.at * W} y1="0" y2={H} class="grid" />
          <text x={g.at * W + 5} y={H - 8} class="glabel">{g.value.toFixed(decimals)}°</text>
        {/each}
        {#each pic.lats as g (g.value)}
          <line y1={g.at * H} y2={g.at * H} x1="0" x2={W} class="grid" />
          <text x="8" y={g.at * H - 6} class="glabel">{g.value.toFixed(decimals)}°</text>
        {/each}

        {#each pic.points as p, i (i)}
          {#if p}
            <circle cx={p.x * W} cy={p.y * H} r="17" class="pt" />
            <text x={p.x * W} y={p.y * H + 7} class="ptn" text-anchor="middle">{i + 1}</text>
            <text x={p.x * W + 24} y={p.y * H + 7} class="ptl">{labels[i]}</text>
          {/if}
        {/each}

        {#if scale}
          <g transform="translate(24 {H - 58})">
            <rect x="-10" y="-30" width={scale.px + 110} height="52" rx="6" class="box" />
            <rect x="0" y="0" width={scale.px / 2} height="9" class="sb-dark" />
            <rect x={scale.px / 2} y="0" width={scale.px / 2} height="9" class="sb-light" />
            <text x="0" y="-9" class="sbt">0</text>
            <text x={scale.px} y="-9" class="sbt" text-anchor="middle">{scale.label}</text>
          </g>
        {/if}

        <g transform="translate({W - 52} 26)">
          <rect x="-26" y="-14" width="52" height="74" rx="6" class="box" />
          <path d="M0 0 L13 34 L0 26 L-13 34 Z" class="north" />
          <text x="0" y="54" text-anchor="middle" class="sbt">N</text>
        </g>
      </svg>
    {:else}
      <p class="missing">{s.map_missing}</p>
    {/if}
  </div>
  <figcaption>
    <span class="lg"><b>{s.map_legend}</b>
      {#each ui.meta?.slope_legend ?? [] as c (c.label)}
        <span><i style="background: rgba({c.rgba.slice(0, 3).join(',')}, {Math.min(1, c.rgba[3] / 200)})"></i>{c.label}</span>
      {/each}
    </span>
    <span class="muted">{s.map_grid}</span>
  </figcaption>
</figure>

<style>
  figure { margin: 0; }
  .frame { position: relative; width: 190mm; height: 86mm; border: 0.3mm solid #17283a; overflow: hidden; background: #f3f5f7; }
  img, svg { position: absolute; inset: 0; width: 100%; height: 100%; }
  img { object-fit: fill; }
  .grid { stroke: #17283a; stroke-opacity: 0.35; stroke-width: 1.2; }
  .glabel { font: 600 19px system-ui, sans-serif; fill: #17283a; paint-order: stroke; stroke: #fff; stroke-width: 5px; }
  .pt { fill: #17283a; stroke: #fff; stroke-width: 4; }
  .ptn { font: 800 21px system-ui, sans-serif; fill: #fff; }
  .ptl { font: 700 21px system-ui, sans-serif; fill: #17283a; paint-order: stroke; stroke: #fff; stroke-width: 6px; }
  .box { fill: #fff; fill-opacity: 0.9; }
  .sb-dark { fill: #17283a; }
  .sb-light { fill: #fff; stroke: #17283a; stroke-width: 2; }
  .sbt { font: 700 20px system-ui, sans-serif; fill: #17283a; }
  .north { fill: #17283a; }
  .missing { position: absolute; inset: 0; display: grid; place-items: center; margin: 0; padding: 10mm; text-align: center; font-size: 9pt; color: #5e6b78; }
  figcaption { display: flex; justify-content: space-between; gap: 4mm; font-size: 7pt; margin-top: 1.2mm; }
  .lg { display: flex; flex-wrap: wrap; gap: 0 3mm; align-items: center; }
  .lg span { white-space: nowrap; }
  .lg i { display: inline-block; width: 2.6mm; height: 2.6mm; margin-right: 0.8mm; vertical-align: -0.4mm; border: 0.15mm solid #0003; }
  .muted { color: #5e6b78; }
</style>
