<script lang="ts">
  // Arrow pointing where the wind blows to; a light circle when the wind has no steady direction,
  // so numbers always line up.
  import { COMPASS_DEG } from '#lib/format.ts';
  import type { Compass } from '#lib/types.ts';

  let { from, size = 13 }: { from: Compass | null | undefined; size?: number } = $props();
</script>

<svg viewBox="0 0 16 16" width={size} height={size} aria-hidden="true"
  style={from ? `transform: rotate(${COMPASS_DEG[from] + 180}deg)` : ''}>
  {#if from}<path d="M8 1 13 9H9.5v6h-3V9H3z" fill="currentColor" />{:else}<circle cx="8" cy="8" r="3" fill="none" stroke="currentColor" stroke-width="1.6" opacity="0.5" />{/if}
</svg>

<style>
  svg { display: inline-block; vertical-align: -2px; margin-right: 3px; flex: none; }
</style>
