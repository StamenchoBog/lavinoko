<script lang="ts">
  import { onMount } from 'svelte';
  import { fill } from '$lib/i18n';
  import { ROLES, store, type Report, type Role } from '$lib/reports';
  import { currentPlace, t, ui } from '$lib/state.svelte';
  import ReportForm from './ReportForm.svelte';

  const s = $derived(t());
  const place = $derived(currentPlace());

  let role: Role = $state('guide');
  let organisation = $state('');
  let notice = $state('');

  export async function refresh() {
    ui.reports = await store.list();
    ui.observer = await store.observer();
  }
  onMount(refresh);

  const shown = $derived.by(() => {
    if (!place) return ui.reports;
    const [lon, lat] = place.center;
    return ui.reports.filter((r) => {
      const dx = (r.lon - lon) * 111 * Math.cos((lat * Math.PI) / 180);
      return r.place_id === place.id || Math.hypot(dx, (r.lat - lat) * 111) < 10;
    });
  });

  function ago(iso: string): string {
    const min = Math.max(0, Math.round((Date.now() - Date.parse(iso)) / 60000));
    if (min < 60) return fill(s.ago_min, { n: min });
    if (min < 48 * 60) return fill(s.ago_hour, { n: Math.round(min / 60) });
    return fill(s.ago_day, { n: Math.round(min / 1440) });
  }
  const placeName = (r: Report) => ui.weather?.places.find((p) => p.id === r.place_id)?.name[ui.lang] ?? '';

  async function signIn() {
    await store.signIn({ role, organisation: organisation.trim() || null });
    await refresh();
  }
  async function signOut() {
    await store.signOut();
    ui.reportForm = false;
    await refresh();
  }
  async function done(saved: boolean) {
    ui.reportForm = false;
    ui.draftPoint = null;
    notice = saved ? s.form_sent : '';
    await refresh();
  }
  async function remove(id: string) {
    await store.remove(id);
    await refresh();
  }
</script>

{#if store.mode === 'local'}<p class="local">{s.reports_local}</p>{/if}

{#if ui.reportForm}
  <ReportForm onDone={done} />
{:else}
  {#if ui.observer}
    <div class="me">
      <button class="primary" onclick={() => ((ui.reportForm = true), (notice = ''))}>{s.report_new}</button>
      <span class="small">{fill(s.signed_in_as, { role: s.roles[ui.observer.role] })} · <button class="link" onclick={signOut}>{s.sign_out}</button></span>
    </div>
  {/if}
  {#if notice}<p class="notice" role="status">{notice}</p>{/if}

  <h2>{place ? s.reports_near : s.reports_all}</h2>
  {#each shown as r (r.id)}
    <article>
      <header>
        <span class="kinds">{r.kinds.map((k) => s.kinds[k]).join(', ')}{r.avalanche_size ? ` (${fill(s.size_n, { n: r.avalanche_size })})` : ''}{r.new_snow_cm !== null ? ` ${r.new_snow_cm} cm` : ''}</span>
        <time datetime={r.observed_at}>{ago(r.observed_at)}</time>
      </header>
      <p class="meta">
        {[placeName(r), r.elevation_m !== null ? `${r.elevation_m} m` : '', r.aspect ? r.aspect : '']
          .filter(Boolean).join(', ')}
        <span>— {s.roles[r.display_role]}{r.organisation ? `, ${r.organisation}` : ''}</span>
      </p>
      {#if r.note}<p class="note">{r.note}</p>{/if}
      {#if r.photo}<img src={r.photo} alt="" loading="lazy" />{/if}
      {#if store.mode === 'local' && ui.observer}<button class="link" onclick={() => remove(r.id)}>{s.report_delete}</button>{/if}
    </article>
  {:else}
    <p class="small">{s.reports_empty}</p>
  {/each}

  {#if !ui.observer}
    <details class="signin">
      <summary>{s.signin_title}</summary>
      <p class="small">{s.signin_text}</p>
      <label>{s.signin_role}
        <select bind:value={role}>{#each ROLES as r (r)}<option value={r}>{s.roles[r]}</option>{/each}</select>
      </label>
      <label>{s.signin_org}<input bind:value={organisation} maxlength="80" /></label>
      <button class="primary" onclick={signIn}>{s.signin_go}</button>
    </details>
  {/if}
{/if}

<style>
  .local { font-size: 12.5px; background: #eef1f4; border-radius: 8px; padding: 7px 10px; margin: 0 0 10px; color: var(--muted); }
  .me { display: flex; flex-wrap: wrap; gap: 8px 12px; align-items: center; margin-bottom: 10px; }
  h2 { font-size: 13px; font-weight: 650; color: var(--muted); margin: 10px 0 2px; }
  article { border-top: 1px solid var(--line); padding: 9px 0; }
  header { display: flex; justify-content: space-between; gap: 8px; align-items: baseline; }
  .kinds { font-weight: 700; font-size: 14.5px; }
  time { font-size: 12.5px; color: var(--muted); white-space: nowrap; }
  .meta { margin: 2px 0 0; font-size: 13px; color: var(--muted); }
  .note { margin: 6px 0 0; font-size: 14px; white-space: pre-line; }
  img { display: block; max-width: 100%; border-radius: 8px; margin-top: 8px; }
  .notice { background: var(--tint); border-radius: 8px; padding: 7px 10px; font-size: 13.5px; margin: 0 0 8px; }
  .primary { border: 0; background: var(--glacier); color: #fff; border-radius: 8px; padding: 9px 14px; font-weight: 700; cursor: pointer; }
  .link { border: 0; background: none; padding: 0; color: var(--glacier); cursor: pointer; font-size: 13px; text-decoration: underline; }
  .signin label { display: grid; gap: 4px; font-size: 13px; font-weight: 650; margin-bottom: 8px; }
  .signin select, .signin input { font: inherit; font-weight: 400; border: 1px solid var(--line); border-radius: 8px; padding: 7px 9px; background: #fff; }
</style>
