<script lang="ts">
  // Which slope aspects are affected, as an eight-sector compass (as in Alpine bulletins),
  // always with the elevation written next to it.
  import type { Compass } from '$lib/types';

  let { aspects, label }: { aspects: Compass[]; label: string } = $props();
  const ORDER: Compass[] = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];

  // Sector i spans (i*45 - 22.5) .. (i*45 + 22.5) degrees, clockwise from north.
  function sector(i: number): string {
    const r = 26, c = 30;
    const a0 = ((i * 45 - 22.5 - 90) * Math.PI) / 180;
    const a1 = ((i * 45 + 22.5 - 90) * Math.PI) / 180;
    return `M${c},${c} L${c + r * Math.cos(a0)},${c + r * Math.sin(a0)} A${r},${r} 0 0 1 ${c + r * Math.cos(a1)},${c + r * Math.sin(a1)} Z`;
  }
</script>

<figure>
  <svg viewBox="0 0 60 60" width="60" height="60" role="img" aria-label={`${aspects.join(', ')}. ${label}`}>
    {#each ORDER as a, i (a)}
      <path d={sector(i)} class:on={aspects.includes(a)} />
    {/each}
    <text x="30" y="7.5" text-anchor="middle">N</text>
  </svg>
  <figcaption>
    <b>{aspects.join(', ')}</b>
    <span>{label}</span>
  </figcaption>
</figure>

<style>
  figure { display: flex; align-items: center; gap: 10px; margin: 0; }
  svg { flex: none; }
  path { fill: #fff; stroke: #9aa6b2; stroke-width: 1; }
  path.on { fill: var(--ink); }
  text { font-size: 7px; font-weight: 700; fill: var(--ink); paint-order: stroke; stroke: #fff; stroke-width: 2px; }
  figcaption { display: grid; font-size: 13px; line-height: 1.3; }
  figcaption b { font-size: 14px; }
  figcaption span { color: var(--muted); }
</style>
