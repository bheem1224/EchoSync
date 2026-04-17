<script>
  import { onMount } from 'svelte';
  import { providers } from '../../stores/providers';
  import { settings } from '../../stores/settings';
  import { settingsPanel } from '../../stores/settingsPanel';
  import QualityProfiles from '../../components/QualityProfiles.svelte';
  import StorageSettings from '../../components/StorageSettings.svelte';
  import { preferences } from '../../stores/preferences';

  let loadError = '';
  let storageRef;

  import { feedback } from '../../stores/feedback';

  async function saveAll() {
    try {
      feedback.setLoading(true);
      // if storage component exposes save, call it
      if (storageRef && typeof storageRef.save === 'function') {
        await storageRef.save();
      }
      // persist quality profiles as part of Save All
      try {
        await preferences.saveProfiles($preferences?.profiles || []);
        feedback.addToast('Preferences saved', 'success');
      } catch (e) {
        console.error('Failed to save preferences during Save All', e);
        feedback.addToast('Failed saving preferences', 'error');
      }
      // persist full settings state to backend
      await settings.save($settings?.data || {});
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
  <header class="page__header">
    <div>
      <h1 class="prefs-title">{({ preferences: 'Preferences' }[$settingsPanel?.active] ?? ($settingsPanel?.active?.replace(/-/g, ' ') || 'Settings'))}</h1>
    </div>
    <div class="header-actions">
      <button class="btn-primary save-all" on:click={saveAll} title="Save All">
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
        </div>
      {/if}
    </div>

    <div class="section-card" id="storage">
      {#if loadError}
        <p class="error">{loadError}</p>
      {:else}
        <StorageSettings bind:this={storageRef} />
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

  .eyebrow {
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 12px;
    color: var(--muted);
    margin: 0 0 4px;
  }

  .sub {
    margin: 6px 0 0;
    color: var(--muted);
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

  label {
    display: flex;
    flex-direction: column;
    gap: 6px;
    color: var(--text);
  }

  .provider-settings-grid {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .error {
    color: #f87171;
    background: rgba(248, 113, 113, 0.1);
    border: 1px solid rgba(248, 113, 113, 0.4);
    padding: 10px 12px;
    border-radius: 8px;
  }

  .appearance { padding: 12px; margin-top: 12px; }
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
</style>
