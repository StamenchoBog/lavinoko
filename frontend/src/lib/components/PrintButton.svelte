<script lang="ts">
  import { printNow } from '$lib/printLoader';
  import type { PrintMode } from '$lib/printing';
  import { t } from '$lib/state.svelte';

  const s = $derived(t());
  let open = $state(false);
  let busy = $state(false);

  async function go(mode: PrintMode) {
    open = false;
    busy = true;
    await printNow(mode).catch(() => {});
    busy = false;
  }
</script>

<div class="wrap no-print">
  <button class="btn" aria-expanded={open} disabled={busy} onclick={() => (open = !open)}>
    <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 6V1.5h8V6M4 12H2.5V6.5h11V12H12M4.5 9.5h7V14.5h-7z" /></svg>
    {busy ? s.print_preparing : s.print}
  </button>
  {#if open}
    <div class="menu" role="menu">
      <button role="menuitem" onclick={() => go('sheet')}><b>{s.print_sheet}</b><small>{s.print_sheet_hint}</small></button>
      <button role="menuitem" onclick={() => go('full')}><b>{s.print_full}</b><small>{s.print_full_hint}</small></button>
    </div>
  {/if}
</div>

<style>
  .wrap { position: relative; }
  .btn { display: inline-flex; align-items: center; gap: 4px; border: 1px solid var(--line); background: #fff; border-radius: 999px; padding: 3px 10px; font-size: 13px; cursor: pointer; white-space: nowrap; }
  .btn svg { width: 14px; height: 14px; fill: none; stroke: var(--ink); stroke-width: 1.3; stroke-linejoin: round; }
  .menu { position: absolute; right: 0; top: calc(100% + 4px); z-index: 5; width: 230px; background: #fff; border-radius: 10px; box-shadow: 0 4px 16px #17283a33; padding: 4px; display: grid; }
  .menu button { border: 0; background: none; text-align: left; padding: 8px 10px; border-radius: 7px; cursor: pointer; display: grid; gap: 1px; }
  .menu button:hover { background: var(--tint); }
  .menu b { font-size: 14px; }
  .menu small { font-size: 12px; color: var(--muted); }
</style>
