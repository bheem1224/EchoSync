<script>
  import { onMount } from 'svelte';
  import { providers } from '../../../stores/providers';
  import DynamicPluginLoader from '../../../components/DynamicPluginLoader.svelte';

  // ── State ──────────────────────────────────────────────────────────────
  let loadError = $state('');
  /** Provider objects from the store, used to render fallback cards for
   *  services that don't yet ship a Web Component plugin bundle. */
  let musicServiceProviders = $state([]);

  onMount(async () => {
    try {
      await providers.load().catch(e =>
        console.warn('[music-services] Partial provider load failure:', e)
      );

      const allProviders = Object.values($providers?.items ?? []);

      musicServiceProviders = allProviders
        .filter(p => !p.disabled)
        .filter(p => {
          // Keep streaming and relevant services for this page
          return (
            p.capabilities?.supports_playlists !== 'NONE' ||
            p.capabilities?.supports_sync ||
            p.service_type === 'streaming' ||
            p.service_type === 'music_service'
          );
        });
    } catch (err) {
      loadError = 'Failed to load music services. Check backend connection.';
      console.error('[music-services]', err);
    }
  });

  /** Whether there are any providers at all to show a fallback grid for */
  const hasFallbackProviders = $derived(musicServiceProviders.length > 0);
</script>

<svelte:head>
  <title>Music Services • EchoSync</title>
</svelte:head>

<section class="page">
  <header class="page__header">
    <div class="page__eyebrow">Services</div>
    <h1>Music Services</h1>
    <p class="subtitle">Configure your streaming services and music providers</p>
  </header>

  {#if loadError}
    <div class="error-card" role="alert">
      <span class="error-card__icon">⚠</span>
      <p>{loadError}</p>
    </div>
  {:else}
    <!--
      Primary: DynamicPluginLoader renders Web Components for active plugins.
      The `empty-state` slot is shown when no music_service plugins are active.
    -->
    <DynamicPluginLoader category="music_service">
      <svelte:fragment slot="loading">
        <div class="services-loading">
          <div class="loading-shimmer"></div>
          <div class="loading-shimmer loading-shimmer--narrow"></div>
        </div>
      </svelte:fragment>

      <svelte:fragment slot="empty-state">
        {#if hasFallbackProviders}
          <div class="services-grid">
            {#each musicServiceProviders as provider (provider.id)}
              <div class="provider-card">
                <div class="provider-card__header">
                  <span class="provider-card__icon" aria-hidden="true">
                    {provider.id === 'spotify' ? '♫' : provider.id === 'tidal' ? '◈' : '♪'}
                  </span>
                  <div>
                    <div class="provider-card__name">{provider.name ?? provider.id}</div>
                    <div class="provider-card__type">{provider.service_type ?? 'Music Service'}</div>
                  </div>
                </div>
                <p class="provider-card__desc">
                  {provider.description ?? 'This service is currently using the legacy view or is not yet configured.'}
                </p>
              </div>
            {/each}
          </div>
        {:else}
          <div class="empty-state">
            <div class="empty-state__icon">🎵</div>
            <p class="empty-state__title">No Music Services Active</p>
            <p class="empty-state__body">
              Enable a music service provider in the
              <a href="/settings/plugin-store" class="link">Plugin Store</a>.
            </p>
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

  .error-card { display: flex; align-items: center; gap: 12px; padding: 14px 18px; background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.35); border-radius: 10px; color: #ef4444; font-size: 14px; }

  .services-loading { display: flex; flex-direction: column; gap: 12px; }
  .loading-shimmer { height: 80px; border-radius: 12px; background: linear-gradient(90deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.04) 100%); background-size: 200% 100%; animation: shimmer 1.4s ease-in-out infinite; }
  .loading-shimmer--narrow { height: 60px; max-width: 60%; }
  @keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

  .services-grid { display: flex; flex-direction: column; gap: 12px; }
  .provider-card { padding: 20px 22px; background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.07); border-radius: 14px; }
  .provider-card__header { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
  .provider-card__icon { font-size: 22px; color: var(--color-primary); }
  .provider-card__name { font-size: 15px; font-weight: 700; color: #fff; text-transform: capitalize; }
  .provider-card__type { font-size: 11px; color: var(--text-muted, rgba(255,255,255,0.4)); text-transform: uppercase; }
  .provider-card__desc { margin: 0; font-size: 13px; color: var(--text-muted, rgba(255,255,255,0.5)); line-height: 1.5; }

  .empty-state { padding: 52px 24px; text-align: center; border-radius: 16px; background: rgba(255, 255, 255, 0.02); border: 1px dashed rgba(255, 255, 255, 0.08); }
  .empty-state__icon { font-size: 36px; margin-bottom: 12px; opacity: 0.5; }
  .empty-state__title { margin: 0 0 8px; font-size: 16px; font-weight: 700; color: #fff; }
  .empty-state__body { margin: 0; font-size: 13px; color: var(--text-muted, rgba(255,255,255,0.4)); line-height: 1.6; }

  .link { color: var(--color-primary); text-decoration: none; font-weight: 700; }
  .link:hover { text-decoration: underline; }
</style>
