<script lang="ts">
  import { printNow } from '#lib/printLoader.ts';
  import { t } from '#lib/state.svelte.ts';

  const s = $derived(t());
  let busy = $state(false);

  async function go() {
    busy = true;
    await printNow().catch(() => {});
    busy = false;
  }
</script>

<div class="wrap no-print">
  <button class="btn" disabled={busy} onclick={go}>
    <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 6V1.5h8V6M4 12H2.5V6.5h11V12H12M4.5 9.5h7V14.5h-7z" /></svg>
    {busy ? s.print_preparing : s.print}
  </button>
</div>

<style>
  .wrap { position: relative; }
  .btn { display: inline-flex; align-items: center; gap: 4px; border: 1px solid var(--line); background: #fff; border-radius: 999px; padding: 3px 10px; font-size: var(--fs-s); cursor: pointer; white-space: nowrap; }
  .btn svg { width: 14px; height: 14px; fill: none; stroke: var(--ink); stroke-width: 1.3; stroke-linejoin: round; }
</style>
