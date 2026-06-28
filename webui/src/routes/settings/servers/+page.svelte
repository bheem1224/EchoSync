<script>
  import { onMount } from 'svelte';
  import { plugins } from '../../../stores/plugins';
  import DynamicPluginLoader from '../../../components/DynamicPluginLoader.svelte';

  // ── State ──────────────────────────────────────────────────────────────
  let loadError = $state('');
  /** Plugin objects from the store, used to render fallback cards. */
  let serverPlugins = $state([]);

  onMount(async () => {
    try {
      await plugins.load().catch(e =>
        console.warn('[servers] Partial plugin load failure:', e)
      );

      const allProviders = Object.values($plugins?.items ?? []);
      
      serverPlugins = allProviders
        .filter(p => !p.disabled)
        .filter(p => {
          return (
            p.capabilities?.server ||
            p.service_type === 'media_server'
          );
        });
    } catch (err) {
      loadError = 'Failed to load servers. Check backend connection.';
      console.error('[servers]', err);
    }
  });

  const hasFallbackPlugins = $derived(serverPlugins.length > 0);
</script>

<svelte:head>
  <title>Servers • EchoSync</title>
</svelte:head>

<section class="page">
  <header class="page__header">
    <div class="page__eyebrow">Infrastructure</div>
    <h1>Media Servers</h1>
    <p class="subtitle">Configure your library sources and media servers</p>
  </header>

  {#if loadError}
    <div class="error-card" role="alert">
      <span class="error-card__icon">⚠</span>
      <p>{loadError}</p>
    </div>
  {:else}
    <DynamicPluginLoader category="media_server">
      <svelte:fragment slot="loading">
        <div class="services-loading">
          <div class="loading-shimmer"></div>
          <div class="loading-shimmer loading-shimmer--narrow"></div>
        </div>
      </svelte:fragment>

      <svelte:fragment slot="empty-state">
        {#if hasFallbackPlugins}
          <div class="services-grid">
            {#each serverPlugins as plugin (plugin.id)}
              <div class="plugin-card">
                <div class="plugin-card__header">
                  <span class="plugin-card__icon" aria-hidden="true">
                    {plugin.name?.includes('Plex') ? '🎬' : '📡'}
                  </span>
                  <div>
                    <div class="plugin-card__name">{plugin.name ?? plugin.id}</div>
                    <div class="plugin-card__type">{plugin.service_type ?? 'Media Server'}</div>
                  </div>
                </div>
                <p class="plugin-card__desc">
                  {plugin.description ?? 'Connect and sync your library from this server.'}
                </p>
              </div>
            {/each}
          </div>
        {:else}
          <div class="empty-state">
            <div class="empty-state__icon">📡</div>
            <p class="empty-state__title">No Media Servers Found</p>
            <p class="empty-state__body">
              Enable a media server plugin in the
              <a href="/settings/plugin-store" class="link">Plugin Store</a>.
            </p>
          </div>
        {/if}
      </svelte:fragment>
    </DynamicPluginLoader>
  {/if}
</section>

<style>
  .page {
    display: flex;
    flex-direction: column;
    gap: 24px;
    max-width: 900px;
  }

  .page__eyebrow {
    font-size: 10px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: 0.25em;
    color: var(--color-primary);
    margin-bottom: 4px;
  }

  .page__header h1 {
    margin: 0 0 6px 0;
    font-size: 28px;
    font-weight: 700;
    color: var(--text-primary, #fff);
  }

  .subtitle {
    margin: 0;
    color: var(--text-muted, rgba(255,255,255,0.45));
    font-size: 14px;
  }

  .error-card {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px 18px;
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.35);
    border-radius: 10px;
    color: #ef4444;
    font-size: 14px;
  }
  .error-card__icon { font-size: 18px; flex-shrink: 0; }

  .services-loading {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .loading-shimmer {
    height: 80px;
    border-radius: 12px;
    background: linear-gradient(
      90deg,
      rgba(255,255,255,0.04) 0%,
      rgba(255,255,255,0.08) 50%,
      rgba(255,255,255,0.04) 100%
    );
    background-size: 200% 100%;
    animation: shimmer 1.4s ease-in-out infinite;
  }
  .loading-shimmer--narrow { height: 60px; max-width: 60%; }

  @keyframes shimmer {
    0%   { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }

  .services-grid {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .plugin-card {
    padding: 20px 22px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 14px;
    transition: border-color 0.2s, background 0.2s;
  }
  .plugin-card:hover {
    background: rgba(255, 255, 255, 0.06);
    border-color: rgba(255, 255, 255, 0.14);
  }

  .plugin-card__header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 10px;
  }
  .plugin-card__icon {
    font-size: 22px;
    color: var(--color-primary);
    line-height: 1;
  }
  .plugin-card__name {
    font-size: 15px;
    font-weight: 700;
    color: var(--text-primary, #fff);
  }
  .plugin-card__type {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-muted, rgba(255,255,255,0.4));
    margin-top: 2px;
  }

  .plugin-card__desc {
    margin: 0 0 14px 0;
    font-size: 13px;
    color: var(--text-muted, rgba(255,255,255,0.5));
    line-height: 1.5;
  }
  .plugin-card__link {
    font-size: 12px;
    font-weight: 700;
    color: var(--color-primary);
    text-decoration: none;
    transition: opacity 0.15s;
  }
  .plugin-card__link:hover { opacity: 0.75; }

  .empty-state {
    padding: 52px 24px;
    text-align: center;
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.02);
    border: 1px dashed rgba(255, 255, 255, 0.08);
  }
  .empty-state__icon   { font-size: 36px; margin-bottom: 12px; opacity: 0.5; }
  .empty-state__title  { margin: 0 0 8px; font-size: 16px; font-weight: 700; color: var(--text-primary, #fff); }
  .empty-state__body   { margin: 0; font-size: 13px; color: var(--text-muted, rgba(255,255,255,0.4)); line-height: 1.6; }

  .link {
    color: var(--color-primary);
    text-decoration: none;
    font-weight: 700;
  }
  .link:hover { text-decoration: underline; }
</style>
