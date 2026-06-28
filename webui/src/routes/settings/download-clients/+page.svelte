<script>
  import { onMount } from 'svelte';
  import { plugins } from '../../../stores/plugins';
  import DynamicPluginLoader from '../../../components/DynamicPluginLoader.svelte';

  // ── State ──────────────────────────────────────────────────────────────
  let loadError = $state('');
  let clientProviders = $state([]);

  onMount(async () => {
    try {
      await plugins.load();
      const allProviders = Object.values($plugins?.items ?? []);
      
      clientProviders = allProviders
        .filter(p => !p.disabled)
        .filter(p => {
          return (
            p.service_type === 'download_client' ||
            p.supports_downloads ||
            p.capabilities?.supports_downloads
          );
        });
    } catch (err) {
      loadError = 'Failed to load download clients.';
      console.error(err);
    }
  });

  const hasFallbackPlugins = $derived(clientProviders.length > 0);
</script>

<svelte:head>
  <title>Download Clients • EchoSync</title>
</svelte:head>

<section class="page">
  <header class="page__header">
    <div class="page__eyebrow">Acquisition</div>
    <h1>Download Clients</h1>
    <p class="subtitle">Configure download clients for obtaining music files</p>
  </header>

  {#if loadError}
    <div class="error-card" role="alert">
      <span class="error-card__icon">⚠</span>
      <p>{loadError}</p>
    </div>
  {:else}
    <DynamicPluginLoader category="download_client">
      <svelte:fragment slot="loading">
        <div class="shimmer-container">
          <div class="loading-shimmer"></div>
        </div>
      </svelte:fragment>

      <svelte:fragment slot="empty-state">
        {#if hasFallbackPlugins}
          <div class="fallback-grid">
            {#each clientProviders as plugin (plugin.id)}
              <div class="plugin-card">
                <div class="plugin-header">
                  <span class="plugin-icon">📥</span>
                  <div>
                    <div class="plugin-name">{plugin.name ?? plugin.id}</div>
                    <div class="plugin-type">Download Client</div>
                  </div>
                </div>
                <p class="plugin-desc">{plugin.description ?? 'Configure your download client settings.'}</p>
              </div>
            {/each}
          </div>
        {:else}
          <div class="empty-state">
            <p>No download clients found.</p>
          </div>
        {/if}
      </svelte:fragment>
    </DynamicPluginLoader>
  {/if}
</section>

<style>
  .page { display: flex; flex-direction: column; gap: 24px; max-width: 900px; }
  .page__eyebrow { font-size: 10px; font-weight: 900; text-transform: uppercase; letter-spacing: 0.25em; color: var(--color-primary); margin-bottom: 4px; }
  .page__header h1 { margin: 0 0 6px 0; font-size: 28px; font-weight: 700; color: #fff; }
  .subtitle { margin: 0; color: var(--text-muted, rgba(255,255,255,0.45)); font-size: 14px; }

  .error-card { display: flex; align-items: center; gap: 12px; padding: 14px 18px; background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.35); border-radius: 10px; color: #ef4444; }

  .shimmer-container { display: flex; flex-direction: column; gap: 12px; }
  .loading-shimmer { height: 120px; border-radius: 14px; background: linear-gradient(90deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.04) 100%); background-size: 200% 100%; animation: shimmer 1.4s ease-in-out infinite; }
  @keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

  .fallback-grid { display: flex; flex-direction: column; gap: 12px; }
  .plugin-card { padding: 22px; background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.07); border-radius: 14px; }
  .plugin-header { display: flex; align-items: center; gap: 14px; margin-bottom: 12px; }
  .plugin-icon { font-size: 24px; }
  .plugin-name { font-size: 16px; font-weight: 700; color: #fff; }
  .plugin-type { font-size: 11px; color: var(--text-muted, rgba(255,255,255,0.4)); text-transform: uppercase; }
  .plugin-desc { font-size: 13px; color: var(--text-muted, rgba(255,255,255,0.5)); margin: 0; }

  .empty-state { padding: 60px; text-align: center; background: rgba(255,255,255,0.02); border: 1px dashed rgba(255,255,255,0.08); border-radius: 16px; color: var(--text-muted, rgba(255,255,255,0.4)); }
</style>