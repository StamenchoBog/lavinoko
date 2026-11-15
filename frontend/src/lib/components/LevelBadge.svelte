<script lang="ts">
  // Weather alert level: always symbol + word, never colour alone.
  import { t } from '$lib/state.svelte';
  import type { Level } from '$lib/types';

  let { level, compact = false }: { level: Level; compact?: boolean } = $props();
  const s = $derived(t());
</script>

{#if level !== 'none'}
  <span class="badge {level}" class:compact title={level === 'serious' ? s.level_serious : s.level_attention}>
    <svg viewBox="0 0 16 16" aria-hidden="true">
      {#if level === 'serious'}
        <path d="M8 1.5 15 14H1z" fill="currentColor" /><path d="M8 6v4M8 11.6v.4" stroke="#fff" stroke-width="1.8" stroke-linecap="round" />
      {:else}
        <circle cx="8" cy="8" r="6.5" fill="currentColor" /><path d="M8 4.6v4M8 10.9v.4" stroke="#fff" stroke-width="1.8" stroke-linecap="round" />
      {/if}
    </svg>
    {#if !compact}<span>{level === 'serious' ? s.level_serious : s.level_attention}</span>{/if}
  </span>
{/if}

<style>
  .badge { display: inline-flex; align-items: center; gap: 4px; font-size: 12px; font-weight: 700; white-space: nowrap; }
  .badge svg { width: 15px; height: 15px; flex: none; }
  .attention { color: var(--attention-ink); }
  .attention svg { color: var(--signal); }
  .serious { color: var(--serious); }
</style>
