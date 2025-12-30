<script>
  import { onMount } from 'svelte';
  import { providers } from '../../stores/providers';
  import { settings } from '../../stores/settings';
  import ProviderSettings from '../../components/ProviderSettings.svelte';

  let loadError = '';

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
  <title>Settings • SoulSync</title>
</svelte:head>

<section class="page">
  <header class="page__header">
    <div>
      <p class="eyebrow">Configuration</p>
      <h1>Settings</h1>
      <p class="sub">Dynamic options based on provider capabilities.</p>
    </div>
  </header>

  <div class="grid-2">
    <div class="card section-card" id="preferences">
      <div class="section-heading">
        <h2>Preferences</h2>
        <span class="chip">User defaults</span>
      </div>
      {#if loadError}
        <p class="error">{loadError}</p>
      {:else if Object.keys(userSettings).length === 0}
        <p class="muted">No settings available.</p>
      {:else}
        <div class="settings-list">
          {#each Object.entries(userSettings) as [key, value]}
            <label>
              <span>{key}</span>
              <input
                class="input"
                name={key}
                type="text"
                value={value}
                on:change={(e) => updateSetting(key, e.target.value)}
              />
            </label>
          {/each}
        </div>
      {/if}
    </div>

    <div class="card section-card" id="music-services">
      <div class="section-heading">
        <h2>Music Services</h2>
        <span class="chip">Streaming providers</span>
      </div>
      {#if streamingProviders.length === 0}
        <p class="muted">No streaming providers available.</p>
      {:else}
        <div class="provider-settings-grid">
          {#each streamingProviders as provider}
            <ProviderSettings providerId={provider.id} providerName={provider.name} />
          {/each}
        </div>
      {/if}
    </div>

    <div class="card section-card" id="servers">
      <div class="section-heading">
        <h2>Servers</h2>
        <span class="chip">Plex / Jellyfin</span>
      </div>
      {#if serverProviders.length === 0}
        <p class="muted">No servers registered.</p>
      {:else}
        <div class="provider-settings-grid">
          {#each serverProviders as provider}
            <ProviderSettings providerId={provider.id} providerName={provider.name} />
          {/each}
        </div>
      {/if}
    </div>

    <div class="card section-card" id="metadata">
      <div class="section-heading">
        <h2>Metadata</h2>
        <span class="chip">Tag sources</span>
      </div>
      {#if metadataProviders.length === 0}
        <p class="muted">No metadata providers registered.</p>
      {:else}
        <div class="provider-settings-grid">
          {#each metadataProviders as provider}
            <ProviderSettings providerId={provider.id} providerName={provider.name} />
          {/each}
        </div>
      {/if}
    </div>

    <div class="card section-card" id="search">
      <div class="section-heading">
        <h2>Search</h2>
        <span class="chip">Unified search</span>
      </div>
      {#if searchProviders.length === 0}
        <p class="muted">No search-capable providers.</p>
      {:else}
        <div class="provider-settings-grid">
          {#each searchProviders as provider}
            <ProviderSettings providerId={provider.id} providerName={provider.name} />
          {/each}
        </div>
      {/if}
    </div>

    <div class="card section-card" id="misc">
      <div class="section-heading">
        <h2>Misc</h2>
        <span class="chip">Other providers</span>
      </div>
      {#if miscProviders.length === 0}
        <p class="muted">No uncategorized providers.</p>
      {:else}
        <div class="provider-settings-grid">
          {#each miscProviders as provider}
            <ProviderSettings providerId={provider.id} providerName={provider.name} />
          {/each}
        </div>
      {/if}
    </div>

    <div class="card section-card" id="jobs">
      <div class="section-heading">
        <h2>Jobs</h2>
        <span class="chip">Scheduling</span>
      </div>
      <p class="muted">Registered jobs, next run, previous run, and run-now controls will be listed. (TODO)</p>
    </div>

    <div class="card section-card" id="system">
      <div class="section-heading">
        <h2>System</h2>
        <span class="chip">Status</span>
      </div>
      <p class="muted">CPU, memory, DB size, installed plugins/providers, logs download, recent events. (TODO)</p>
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
</style>
