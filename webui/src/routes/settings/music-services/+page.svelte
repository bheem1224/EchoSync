<script>
  import { onMount } from 'svelte';
  import { providers } from '../../../stores/providers';
  import SpotifyServiceCard from '../../../components/SpotifyServiceCard.svelte';
  import TidalServiceCard from '../../../components/TidalServiceCard.svelte';

  let loadError = '';
  let musicServiceProviders = [];

  onMount(async () => {
    try {
      await providers.load();
      // Filter providers that are music services (streaming, metadata, etc.)
      const allProviders = Object.values($providers?.items ?? []);
      musicServiceProviders = allProviders.filter(p => {
        // Include providers that support playlists, sync, search, or are streaming services
        return p.capabilities?.supports_playlists !== 'NONE' ||
               p.capabilities?.supports_sync ||
               p.capabilities?.search?.tracks ||
               p.service_type === 'streaming' ||
               p.service_type === 'metadata';
      });
    } catch (err) {
      loadError = 'Failed to load music services. Check backend connection.';
      console.error(err);
    }
  });

  $: hasSpotify = musicServiceProviders.some(p => {
    const id = (p.id || p.name || p.display_name || '').toString().toLowerCase();
    return id.includes('spotify');
  });

  $: hasTidal = musicServiceProviders.some(p => {
    const id = (p.id || p.name || p.display_name || '').toString().toLowerCase();
    return id.includes('tidal');
  });
</script>

<svelte:head>
  <title>Music Services • SoulSync</title>
</svelte:head>

<section class="page">
  <header class="page__header">
    <h1>Music Services</h1>
    <p class="subtitle">Configure your streaming services and music providers</p>
  </header>

  {#if loadError}
    <div class="error-card">
      <p>{loadError}</p>
    </div>
  {:else}
    <div class="services-container">
      <!-- Always show Spotify and Tidal cards so users can configure credentials/accounts -->
      <SpotifyServiceCard />
      <TidalServiceCard />
    </div>
  {/if}
</section>

<style>
  .page {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .page__header {
    margin-bottom: 8px;
  }

  .page__header h1 {
    margin: 0 0 8px 0;
    font-size: 28px;
    font-weight: 600;
  }

  .subtitle {
    margin: 0;
    color: var(--muted);
    font-size: 14px;
  }

  .services-container {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .service-card {
    padding: 20px;
  }

  .error-card {
    padding: 16px;
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.4);
    border-radius: 8px;
    color: #ef4444;
  }

  .empty-state {
    padding: 48px;
    text-align: center;
  }

  .muted {
    color: var(--muted);
  }

  .card {
    border-radius: 8px;
    background: var(--card-bg);
  }
</style>
