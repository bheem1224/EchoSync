<script>
  import { onMount } from 'svelte';
  import { providers } from '../../../stores/providers';
  import { settings } from '../../../stores/settings';
  import { settingsPanel } from '../../../stores/settingsPanel';
  import QualityProfiles from '../../../components/QualityProfiles.svelte';
  import StorageSettings from '../../../components/StorageSettings.svelte';
  import LibraryImportSettings from '../../../components/LibraryImportSettings.svelte';
  import { preferences, sidebarPrefs, LOCKED_ROUTES } from '../../../stores/preferences';
  import { pluginViews } from '../../../stores/pluginViews';

  let loadError = $state('');
  let storageRef = $state();
  let libImportRef = $state();
  
  // logLevel is managed via $derived or $effect in Svelte 5 to sync with store
  let logLevel = $state('INFO');

  // Sync logLevel with userSettings whenever it changes
  $effect(() => {
    const level = $settings?.data?.log_level;
    if (level) {
      logLevel = level;
    }
  });

  import { feedback } from '../../../stores/feedback';

  async function saveAll() {
    try {
      feedback.setLoading(true);
      // if storage component exposes save, call it
      if (storageRef && typeof storageRef.save === 'function') {
        await storageRef.save();
      }
      // if library import component exposes save, call it
      if (libImportRef && typeof libImportRef.save === 'function') {
        await libImportRef.save();
      }
      // persist quality profiles as part of Save All
      try {
        await preferences.saveProfiles($preferences?.profiles || []);
        feedback.addToast('Preferences saved', 'success');
      } catch (e) {
        console.error('Failed to save preferences during Save All', e);
        feedback.addToast('Failed saving preferences', 'error');
      }
      // Note: log_level is saved immediately on dropdown change via updateSetting().
      // Sending the full $settings.data blob here would hit the backend allowlist → 400.
      feedback.addToast('Settings saved', 'success');
    } catch (e) {
      console.error('Failed to save all settings', e);
      feedback.addToast('Failed to save settings', 'error');
    } finally {
      feedback.setLoading(false);
    }
  }

  onMount(async () => {
    try {
      await Promise.all([providers.load(), settings.load()]);
    } catch (err) {
      loadError = 'Failed to load settings. Check backend /api/settings.';
      console.error(err);
    }
  });

  const providerList = $derived(Object.values($providers?.items ?? []));
  const userSettings = $derived($settings?.data ?? {});
  const devMode = $derived(userSettings?.dev_mode === true);
  const safeMode = $derived(userSettings?.safe_mode === true);
  
  const streamingProviders = $derived(providerList.filter((p) => (p.capabilities?.supports_playlists ?? 'NONE') !== 'NONE' || p.capabilities?.supports_sync));
  const serverProviders = $derived(providerList.filter((p) => p.capabilities?.server));
  const metadataProviders = $derived(providerList.filter((p) => p.capabilities?.metadata));
  const searchProviders = $derived(providerList.filter((p) => p.capabilities?.search?.tracks));
  const miscProviders = $derived(providerList.filter((p) => !streamingProviders.includes(p) && !serverProviders.includes(p) && !metadataProviders.includes(p) && !searchProviders.includes(p)));

  function updateSetting(key, value) {
    settings.save({ [key]: value });
  }
</script>

<svelte:head>
  <title>Settings • Echosync</title>
</svelte:head>

<section class="page">
  {#if devMode}
    <div class="dev-mode-banner" role="alert">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
        <line x1="12" y1="9" x2="12" y2="13"/>
        <line x1="12" y1="17" x2="12.01" y2="17"/>
      </svg>
      <span><strong>DEV MODE</strong> — Debug logging active · ISRC matching disabled</span>
    </div>
  {/if}

  {#if safeMode}
    <div class="safe-mode-banner" role="alert">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
      </svg>
      <span><strong>SAFE MODE</strong> — Plugin loading is disabled · Previous crash or unclean shutdown detected</span>
    </div>
  {/if}

  <header class="page__header">
    <div>
      <h1 class="prefs-title">{({ preferences: 'Preferences' }[$settingsPanel?.active] ?? ($settingsPanel?.active?.replace(/-/g, ' ') || 'Settings'))}</h1>
    </div>
    <div class="header-actions">
      <button class="btn-primary save-all active:scale-95 transition-all duration-200" on:click={saveAll} title="Save All">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:8px">
          <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
          <polyline points="17 21 17 13 7 13 7 21"></polyline>
          <polyline points="7 3 7 8 15 8"></polyline>
        </svg>
        Save All
      </button>
    </div>
  </header>

  <div class="grid-2">
    <div class="section-card" id="preferences">
      {#if loadError}
        <p class="error">{loadError}</p>
      {:else}
        <div class="settings-list">
          <QualityProfiles />

          <section class="appearance card">
            <div class="section-heading">
              <h2>Appearance</h2>
            </div>
            <div class="appearance-content">
              <label>
                <span class="label-text">Theme</span>
                <select class="theme-select">
                  <option value="dark" selected>Dark</option>
                </select>
              </label>
            </div>
          </section>

          <!-- Logging preferences -->
          <section class="logging card">
            <div class="section-heading">
              <h2>Logging</h2>
            </div>
            <div class="logging-content">
              <label>
                <span class="label-text">Console level</span>
                <select class="log-select" bind:value={logLevel} on:change={() => updateSetting('log_level', logLevel)}>
                  <option value="INFO">Normal</option>
                  <option value="DEBUG">Debug</option>
                  <option value="NOTSET">Verbose</option>
                </select>
              </label>
            </div>
          </section>
        </div>
      {/if}
    </div>

    <div class="section-card" id="storage">
      {#if loadError}
        <p class="error">{loadError}</p>
      {:else}
        <div class="settings-list">
          <StorageSettings bind:this={storageRef} />
          <LibraryImportSettings bind:this={libImportRef} />
        </div>
      {/if}
    </div>
  </div>
</section>

<!-- ── Sidebar Customization ────────────────────────────────────── -->
<section class="sidebar-custom card" id="sidebar-customization">
  <div class="section-heading">
    <div class="section-heading__icon" aria-hidden="true">☰</div>
    <div>
      <h2>Sidebar Customization</h2>
      <p class="section-heading__sub">Control which items appear in the main navigation. Changes apply immediately.</p>
    </div>
  </div>

  <!-- ── Default routes visibility ───────────────────────── -->
  <div class="sc-block">
    <div class="sc-block__title">Default Routes</div>
    <div class="sc-rows">
      {#each [
        { label: 'Dashboard', href: '/dashboard', icon: '🏠' },
        { label: 'Sync',      href: '/sync',      icon: '🔄' },
        { label: 'Search',    href: '/search',    icon: '🔍' },
        { label: 'Discover',  href: '/discover',  icon: '✨' },
        { label: 'Library',   href: '/library',   icon: '🎵' },
      ] as route}
        {@const isLocked  = LOCKED_ROUTES.has(route.href)}
        {@const isHidden  = ($sidebarPrefs?.hiddenRoutes ?? []).includes(route.href)}
        <div class="sc-row" class:sc-row--locked={isLocked}>
          <span class="sc-row__icon" aria-hidden="true">{route.icon}</span>
          <span class="sc-row__label">{route.label}</span>
          <span class="sc-row__href">{route.href}</span>

          {#if isLocked}
            <span class="sc-locked-badge" title="This route is permanently locked and cannot be hidden">
              🔒 Locked
            </span>
          {:else}
            <button
              id="sidebar-toggle-{route.href.replace('/', '')}"
              class="sc-toggle"
              class:sc-toggle--hidden={isHidden}
              on:click={() => sidebarPrefs.toggleHidden(route.href)}
              aria-pressed={isHidden}
              title={isHidden ? 'Show in sidebar' : 'Hide from sidebar'}
            >
              <span class="sc-toggle__track">
                <span class="sc-toggle__thumb"></span>
              </span>
              <span class="sc-toggle__label">{isHidden ? 'Hidden' : 'Visible'}</span>
            </button>
          {/if}
        </div>
      {/each}
    </div>
  </div>

  <!-- ── Plugin views pinning ──────────────────────────── -->
  <div class="sc-block">
    <div class="sc-block__title">Plugin Views
      <span class="sc-block__count">{$pluginViews.length} available</span>
    </div>

    {#if $pluginViews.length === 0}
      <div class="sc-empty">
        <p>No plugin views are registered yet.</p>
        <p class="sc-empty__hint">Install a plugin with a custom view from the
          <a href="/settings/plugin-store" class="sc-link">Plugin Store</a>.
        </p>
      </div>
    {:else}
      <div class="sc-rows">
        {#each $pluginViews as view (view.id)}
          {@const pinnedViews = $sidebarPrefs?.pinnedViews ?? []}
          {@const isPinned    = pinnedViews.includes(view.id)}
          {@const pinIdx      = pinnedViews.indexOf(view.id)}
          <div class="sc-row" class:sc-row--pinned={isPinned}>
            <span class="sc-row__icon" aria-hidden="true">{view.icon}</span>
            <div class="sc-row__info">
              <span class="sc-row__label">{view.title}</span>
              <span class="sc-row__sub">{view.pluginId} · {view.href}</span>
            </div>

            <div class="sc-pin-controls">
              {#if isPinned}
                <button
                  class="sc-order-btn"
                  disabled={pinIdx === 0}
                  on:click={() => sidebarPrefs.reorderPinned(view.id, 'up')}
                  title="Move up"
                  aria-label="Move {view.title} up in sidebar"
                >↑</button>
                <button
                  class="sc-order-btn"
                  disabled={pinIdx === pinnedViews.length - 1}
                  on:click={() => sidebarPrefs.reorderPinned(view.id, 'down')}
                  title="Move down"
                  aria-label="Move {view.title} down in sidebar"
                >↓</button>
              {/if}

              <button
                id="pin-view-{view.id}"
                class="sc-pin-btn"
                class:sc-pin-btn--active={isPinned}
                on:click={() => sidebarPrefs.togglePinned(view.id)}
                title={isPinned ? 'Unpin from sidebar' : 'Pin to sidebar'}
              >
                {#if isPinned}
                  <span class="sc-pin-btn__icon">📌</span> Pinned
                {:else}
                  <span class="sc-pin-btn__icon">📍</span> Pin
                {/if}
              </button>
            </div>
          </div>
        {/each}
      </div>

      <!-- Pinned order preview -->
      {#if ($sidebarPrefs?.pinnedViews ?? []).length > 0}
        <div class="sc-order-preview">
          <span class="sc-order-preview__label">Sidebar order:</span>
          {#each ($sidebarPrefs?.pinnedViews ?? []) as id, i}
            {@const v = $pluginViews.find(pv => pv.id === id)}
            {#if v}
              <span class="sc-order-preview__chip">{i + 1}. {v.icon} {v.title}</span>
            {/if}
          {/each}
        </div>
      {/if}
    {/if}
  </div>
</section>

<style>
  .page {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .section-card {
    padding: 16px;
  }

  .header-actions { display:flex; align-items:center }

  .settings-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .grid-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    align-items: start;
  }

  @media (max-width: 900px) {
    .grid-2 { grid-template-columns: 1fr; }
  }

  .error {
    color: #f87171;
    background: rgba(248, 113, 113, 0.1);
    border: 1px solid rgba(248, 113, 113, 0.4);
    padding: 10px 12px;
    border-radius: 8px;
  }

  .appearance { padding: 12px; margin-top: 0; } /* Reset margin top as gap handles it */
  .appearance .section-heading { margin-bottom: 12px; }
  .appearance .section-heading h2 { margin: 0; font-size: 16px; font-weight: 600; }
  .appearance-content { display: flex; flex-direction: column; gap: 12px; }
  .appearance-content label { display: flex; flex-direction: column; gap: 6px; }
  .appearance-content .label-text { font-size: 14px; color: var(--text); }
  .appearance-content .theme-select {
    padding: 8px 12px;
    border-radius: 6px;
    background: var(--card-bg);
    border: 1px solid var(--border-color, rgba(255,255,255,0.1));
    color: var(--text);
    font-size: 14px;
  }
  /* Logging card styles mirror appearance for consistency */
  .logging { padding: 12px; margin-top: 0; }
  .logging .section-heading { margin-bottom: 12px; }
  .logging .section-heading h2 { margin: 0; font-size: 16px; font-weight: 600; }
  .logging-content { display: flex; flex-direction: column; gap: 12px; }
  .logging-content label { display: flex; flex-direction: column; gap: 6px; }
  .logging-content .label-text { font-size: 14px; color: var(--text); }
  .logging-content .log-select {
    padding: 8px 12px;
    border-radius: 6px;
    background: var(--card-bg);
    border: 1px solid var(--border-color, rgba(255,255,255,0.1));
    color: var(--text);
    font-size: 14px;
  }

  .dev-mode-banner {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 16px;
    border-radius: 8px;
    background: rgba(239, 68, 68, 0.15);
    border: 1px solid rgba(239, 68, 68, 0.5);
    color: #fca5a5;
    font-size: 13px;
  }
  .dev-mode-banner strong { color: #f87171; }

  .safe-mode-banner {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 16px;
    border-radius: 8px;
    background: rgba(251, 146, 60, 0.15);
    border: 1px solid rgba(251, 146, 60, 0.5);
    color: #fed7aa;
    font-size: 13px;
    margin-top: 8px;
  }
  .safe-mode-banner strong { color: #fb923c; }

  /* ── Sidebar Customization card ──────────────────────────────────── */
  .sidebar-custom {
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .section-heading {
    display: flex;
    align-items: flex-start;
    gap: 14px;
  }
  .section-heading__icon {
    font-size: 22px;
    line-height: 1;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    padding: 8px 10px;
    flex-shrink: 0;
    color: rgba(255,255,255,0.6);
  }
  .section-heading h2 { margin: 0 0 4px; font-size: 17px; font-weight: 700; }
  .section-heading__sub { margin: 0; font-size: 13px; color: var(--muted, rgba(255,255,255,0.4)); line-height: 1.5; }

  /* ── Sub-blocks ───────────────────────────────────────────────────── */
  .sc-block { display: flex; flex-direction: column; gap: 10px; }
  .sc-block__title {
    font-size: 10px; font-weight: 900; letter-spacing: 0.2em;
    text-transform: uppercase; color: rgba(255,255,255,0.35);
    display: flex; align-items: center; gap: 8px;
  }
  .sc-block__count {
    font-size: 10px; font-weight: 600;
    color: var(--color-primary, #1db954);
    background: rgba(29, 185, 84, 0.1);
    border: 1px solid rgba(29, 185, 84, 0.2);
    border-radius: 20px; padding: 1px 8px;
    text-transform: none; letter-spacing: 0;
  }

  /* ── Row ──────────────────────────────────────────────────────────── */
  .sc-rows { display: flex; flex-direction: column; gap: 6px; }
  .sc-row {
    display: flex; align-items: center; gap: 10px;
    padding: 10px 14px;
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 10px;
    transition: background 0.15s, border-color 0.15s;
  }
  .sc-row:hover              { background: rgba(255,255,255,0.04); }
  .sc-row--locked            { opacity: 0.65; cursor: not-allowed; }
  .sc-row--pinned            { border-color: rgba(29, 185, 84, 0.25); background: rgba(29, 185, 84, 0.04); }

  .sc-row__icon  { font-size: 18px; flex-shrink: 0; width: 24px; text-align: center; }
  .sc-row__label { font-size: 14px; font-weight: 600; color: #fff; flex: 1; }
  .sc-row__href  { font-size: 11px; color: rgba(255,255,255,0.3); font-family: monospace; }
  .sc-row__info  { flex: 1; display: flex; flex-direction: column; gap: 2px; }
  .sc-row__sub   { font-size: 11px; color: rgba(255,255,255,0.3); font-family: monospace; }

  /* ── Lock badge ───────────────────────────────────────────────────── */
  .sc-locked-badge {
    font-size: 11px; font-weight: 700;
    color: rgba(255,255,255,0.3);
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 6px; padding: 3px 10px;
    white-space: nowrap; flex-shrink: 0;
  }

  /* ── Toggle switch ────────────────────────────────────────────────── */
  .sc-toggle {
    display: flex; align-items: center; gap: 8px;
    background: none; border: none; cursor: pointer;
    padding: 0; color: rgba(255,255,255,0.5);
    font-size: 12px; font-weight: 600;
    flex-shrink: 0;
  }
  .sc-toggle__track {
    width: 38px; height: 20px; border-radius: 10px;
    background: rgba(255,255,255,0.1);
    border: 1px solid rgba(255,255,255,0.12);
    position: relative; transition: background 0.25s, border-color 0.25s;
    flex-shrink: 0;
  }
  .sc-toggle__thumb {
    position: absolute; top: 2px; left: 2px;
    width: 14px; height: 14px; border-radius: 50%;
    background: rgba(255,255,255,0.4);
    transition: transform 0.25s, background 0.25s;
  }
  /* Visible = "on" → green track, thumb right */
  .sc-toggle:not(.sc-toggle--hidden) .sc-toggle__track {
    background: rgba(29, 185, 84, 0.35);
    border-color: rgba(29, 185, 84, 0.5);
  }
  .sc-toggle:not(.sc-toggle--hidden) .sc-toggle__thumb {
    background: var(--color-primary, #1db954);
    transform: translateX(18px);
  }
  .sc-toggle:not(.sc-toggle--hidden) { color: var(--color-primary, #1db954); }
  .sc-toggle__label { min-width: 44px; }

  /* ── Pin controls ─────────────────────────────────────────────────── */
  .sc-pin-controls { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }

  .sc-order-btn {
    width: 28px; height: 28px; border-radius: 7px;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.08);
    color: rgba(255,255,255,0.5); font-size: 13px;
    cursor: pointer; display: flex; align-items: center; justify-content: center;
    transition: background 0.15s, color 0.15s;
  }
  .sc-order-btn:hover:not(:disabled) { background: rgba(255,255,255,0.12); color: #fff; }
  .sc-order-btn:disabled { opacity: 0.25; cursor: not-allowed; }

  .sc-pin-btn {
    display: flex; align-items: center; gap: 5px;
    padding: 5px 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1);
    background: rgba(255,255,255,0.04);
    color: rgba(255,255,255,0.55); font-size: 12px; font-weight: 700;
    cursor: pointer; transition: all 0.18s; white-space: nowrap;
  }
  .sc-pin-btn:hover { background: rgba(255,255,255,0.09); color: #fff; border-color: rgba(255,255,255,0.18); }
  .sc-pin-btn--active {
    background: rgba(29, 185, 84, 0.12);
    border-color: rgba(29, 185, 84, 0.4);
    color: var(--color-primary, #1db954);
  }
  .sc-pin-btn--active:hover { background: rgba(29, 185, 84, 0.2); }
  .sc-pin-btn__icon { font-size: 13px; }

  /* ── Order preview strip ──────────────────────────────────────────── */
  .sc-order-preview {
    display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
    padding: 10px 14px;
    background: rgba(29, 185, 84, 0.05);
    border: 1px solid rgba(29, 185, 84, 0.15);
    border-radius: 10px;
    margin-top: 4px;
  }
  .sc-order-preview__label {
    font-size: 10px; font-weight: 900; text-transform: uppercase;
    letter-spacing: 0.12em; color: rgba(255,255,255,0.35);
  }
  .sc-order-preview__chip {
    font-size: 12px; font-weight: 600;
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 20px; padding: 2px 10px;
    color: rgba(255,255,255,0.65);
  }

  /* ── Empty state ──────────────────────────────────────────────────── */
  .sc-empty {
    padding: 28px 20px; text-align: center;
    border-radius: 10px; background: rgba(255,255,255,0.02);
    border: 1px dashed rgba(255,255,255,0.07);
    font-size: 13px; color: rgba(255,255,255,0.4);
  }
  .sc-empty p { margin: 0 0 6px; }
  .sc-empty__hint { font-size: 12px; }
  .sc-link { color: var(--color-primary, #1db954); text-decoration: none; font-weight: 700; }
  .sc-link:hover { text-decoration: underline; }
</style>

