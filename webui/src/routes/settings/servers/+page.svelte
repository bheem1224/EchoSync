<script>
  import { onMount } from 'svelte';
  import { providers } from '../../../stores/providers';
  import PlexServiceCard from '../../../components/PlexServiceCard.svelte';
  import NavidromeServiceCard from '../../../components/NavidromeServiceCard.svelte';
  import JellyfinServiceCard from '../../../components/JellyfinServiceCard.svelte';

  let enabledServers = [];

  onMount(async () => {
    await providers.load().catch(() => {});
    const all = Object.values($providers.items || {});
    enabledServers = all.filter(p => !p.disabled && ['plex','navidrome','jellyfin'].includes((p.id||p.name||'').toLowerCase()));
  });
</script>

<svelte:head>
  <title>Servers • Echosync</title>
</svelte:head>

<section class="page">
  <header class="page__header">
    <h1>Servers</h1>
    <p class="subtitle">Configure your media servers</p>
  </header>

  <div class="servers-container">
    {#if enabledServers.some(p => p.id.toLowerCase() === 'plex')}
      <PlexServiceCard />
    {/if}
    {#if enabledServers.some(p => p.id.toLowerCase() === 'navidrome')}
      <NavidromeServiceCard />
    {/if}
    {#if enabledServers.some(p => p.id.toLowerCase() === 'jellyfin')}
      <JellyfinServiceCard />
    {/if}
    {#if enabledServers.length === 0}
      <div class="empty-state">
        <p>No media servers are enabled. Enable one in the provider list first.</p>
      </div>
    {/if}
  </div>
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

  .servers-container {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .muted {
    color: var(--muted);
  }
</style>
