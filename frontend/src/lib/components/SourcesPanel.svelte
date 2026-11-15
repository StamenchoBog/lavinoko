<script lang="ts">
  import { data, t, ui } from '$lib/state.svelte';

  const s = $derived(t());
</script>

<details class="sources">
  <summary>{s.sources_title}</summary>
  <ul>
    {#each data.sources as src (src.id)}
      <li>
        <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- external site -->
        <a href={src.url} target="_blank" rel="noopener">{src.name}</a>
        <span class="small">{src.used_for[ui.lang]}</span>
        <span class="credit">{src.credit}</span>
        <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- external site -->
        <span class="small"><a href={src.terms_url} target="_blank" rel="noopener">{src.licence}</a></span>
      </li>
    {/each}
  </ul>
  <p class="small">{s.disclaimer}</p>
</details>

<style>
  ul { list-style: none; padding: 0; margin: 0 0 8px; }
  li { display: grid; gap: 1px; padding: 6px 0; border-top: 1px dotted var(--line); font-size: 13px; }
  li:first-child { border-top: 0; }
  a { color: var(--glacier); font-weight: 600; }
  .small a { font-weight: 400; }
  .credit { font-size: 12px; }
  /* Touch screens (gloves): the source's name link is a 48 px target. */
  @media (pointer: coarse) {
    li > a { display: flex; align-items: center; min-height: 48px; }
  }
</style>
