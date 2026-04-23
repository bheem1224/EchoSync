<script>
  import { onMount } from 'svelte';
  import { providers } from '../../../stores/providers';
  import { settings } from '../../../stores/settings';
  import { settingsPanel } from '../../../stores/settingsPanel';
  import QualityProfiles from '../../../components/QualityProfiles.svelte';
  import StorageSettings from '../../../components/StorageSettings.svelte';
  import LibraryImportSettings from '../../../components/LibraryImportSettings.svelte';
  import { preferences } from '../../../stores/preferences';

  let loadError = '';
  let storageRef;
  let libImportRef;
  // console log level for dropdown (INFO/DEBUG/NOTSET)
  let logLevel = 'INFO';

  // when settings are loaded or change, update our local logLevel
  $: if (userSettings && userSettings.log_level) {
    logLevel = userSettings.log_level;
  }

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

  $: providerList = Object.values($providers?.items ?? []);
  $: userSettings = $settings?.data ?? {};
  $: devMode = userSettings?.dev_mode === true;
  $: safeMode = userSettings?.safe_mode === true;
  $: streamingProviders = providerList.filter((p) => (p.capabilities?.supports_playlists ?? 'NONE') !== 'NONE' || p.capabilities?.supports_sync);
  $: serverProviders = providerList.filter((p) => p.capabilities?.server);
  $: metadataProviders = providerList.filter((p) => p.capabilities?.metadata);
  $: searchProviders = providerList.filter((p) => p.capabilities?.search?.tracks);
  $: miscProviders = providerList.filter((p) => !streamingProviders.includes(p) && !serverProviders.includes(p) && !metadataProviders.includes(p) && !searchProviders.includes(p));

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
</style>
