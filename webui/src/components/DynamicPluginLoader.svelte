<!--
  DynamicPluginLoader.svelte
  ──────────────────────────────────────────────────────────────────────────
  Accepts a `category` prop and:
    1. Fetches active plugins for that category from GET /api/system/plugins/ui-manifest.
    2. Injects <script type="module"> tags into <head> for each plugin bundle (once only).
    3. Renders the declared Web Component tags via <svelte:element>.

  Props
  ─────
  category   : string  – e.g. "music_service" | "media_server" | "metadata"
               Matched against plugin.components[category] from the ui-manifest.
  passProps  : object  – optional key/value pairs forwarded to every Web Component
               as attributes (e.g. { "api-base": "/api/plugins/spotify" }).
  showEmpty  : boolean – if true and no plugins load, render the default empty slot.
               Default: true.

  Slots
  ─────
  default  – Fallback content rendered when no plugins are found (or while loading).
  loading  – Optional override for the loading state.
-->
<script>
  import { onMount } from 'svelte';

  // ── Props ──────────────────────────────────────────────────────────────
  /** Category key to look up in plugin.components (e.g. "music_service") */
  export let category = '';
  /** Arbitrary key/value attributes forwarded to every rendered Web Component */
  export let passProps = {};
  /** Whether to render the default slot when no plugins are available */
  export let showEmpty = true;

  // ── State ──────────────────────────────────────────────────────────────
  /** Plugins resolved for this category */
  let resolvedPlugins = [];
  let loading = true;
  let error = null;

  // Keep track of <script> tags we've already injected so we never double-inject.
  const _injectedUrls = new Set();

  // ── Plugin script injection ────────────────────────────────────────────
  /**
   * Injects a <script type="module" src="…"> tag into document.head if it
   * hasn't been injected in this session yet.  Returns a Promise that
   * resolves once the script has loaded (or immediately if already present).
   */
  function injectScript(url) {
    if (_injectedUrls.has(url)) return Promise.resolve();

    // Double-check the DOM to survive HMR / multiple mounts
    if (document.querySelector(`script[src="${CSS.escape ? CSS.escape(url) : url}"]`)) {
      _injectedUrls.add(url);
      return Promise.resolve();
    }

    return new Promise((resolve, reject) => {
      const el = document.createElement('script');
      el.type = 'module';
      el.src = url;
      el.onload  = () => { _injectedUrls.add(url); resolve(); };
      el.onerror = () => reject(new Error(`Failed to load plugin bundle: ${url}`));
      document.head.appendChild(el);
    });
  }

  // ── Data fetching ──────────────────────────────────────────────────────
  onMount(async () => {
    if (!category) {
      loading = false;
      return;
    }

    try {
      // 1. Fetch the UI manifest from the backend
      const resp = await fetch('/api/system/plugins/ui-manifest', {
        credentials: 'include',
      });

      if (!resp.ok) {
        if (resp.status === 404) {
          console.warn(`[DynamicPluginLoader] /api/system/plugins/ui-manifest not found. No plugins will load for category="${category}".`);
          loading = false;
          return;
        }
        throw new Error(`UI manifest fetch failed: ${resp.status} ${resp.statusText}`);
      }

      const data = await resp.json();
      const allPlugins = data?.plugins ?? [];

      // 2. Filter to plugins that declare a component for the requested category
      const matching = allPlugins.filter(
        p => p?.components?.[category]
      );

      if (matching.length === 0) {
        console.warn(`[DynamicPluginLoader] No plugins found for category="${category}".`);
        loading = false;
        return;
      }

      // 3. Inject each plugin's bundle script and wait for all to settle
      const loadResults = await Promise.allSettled(
        matching.map(plugin => {
          const bundleUrl = plugin.components[category]?.bundle_url;
          if (!bundleUrl) return Promise.resolve(null);
          // Build absolute URL: the backend serves bundles at /api/system/plugins/<id>/ui/<file>
          const absoluteUrl = (bundleUrl.startsWith('http') || bundleUrl.startsWith('/'))
            ? bundleUrl
            : `/api/system/plugins/${plugin.id}/ui/${bundleUrl.replace(/^\//, '')}`;
          return injectScript(absoluteUrl).then(() => ({
            plugin,
            tag: plugin.components[category]?.element_tag,
            apiBase: plugin.api_base ?? `/api/plugins/${plugin.id}`,
          }));
        })
      );

      // 4. Collect successfully loaded plugins
      resolvedPlugins = loadResults
        .filter(r => r.status === 'fulfilled' && r.value != null && r.value.tag)
        .map(r => r.value)
        .filter((value, index, self) =>
          self.findIndex(item => item.plugin.id === value.plugin.id && item.tag === value.tag) === index
        );

      // Log any failures but don't crash the page
      loadResults
        .filter(r => r.status === 'rejected')
        .forEach(r => console.warn('[DynamicPluginLoader] Plugin bundle failed to load:', r.reason));

    } catch (err) {
      console.warn('[DynamicPluginLoader] Failed to load plugin manifest:', err?.message ?? err);
      error = err?.message ?? 'Plugin loader failed';
    } finally {
      loading = false;
    }
  });
</script>

<!-- ── Render ─────────────────────────────────────────────────────────────── -->
{#if loading}
  <!-- Loading slot – override with <svelte:fragment slot="loading"> -->
  <slot name="loading">
    <div class="plugin-loader-spinner" aria-label="Loading plugins…">
      <span class="spinner-ring"></span>
    </div>
  </slot>

{:else if resolvedPlugins.length > 0}
  <!-- One element per resolved Web Component -->
  <div class="plugin-loader-grid" data-category={category}>
    {#each resolvedPlugins as { tag, apiBase, plugin } (plugin.id || `${tag}-${apiBase}`)}
      <svelte:element
        this={tag}
        api-base={apiBase}
        plugin-id={plugin.id}
        {...passProps}
      />
    {/each}
  </div>

{:else if showEmpty}
  <!-- Fallback slot when no plugins loaded -->
  <slot>
    <!-- Default empty state – pages can override this slot -->
    <div class="plugin-loader-empty">
      <slot name="empty-state">
        <p class="plugin-loader-empty__msg">
          No <strong>{category.replace(/_/g, ' ')}</strong> plugins are currently active.
        </p>
      </slot>
    </div>
  </slot>
{/if}

{#if error}
  <p class="plugin-loader-error" role="alert">⚠ {error}</p>
{/if}

<style>
  .plugin-loader-grid {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  /* ── Spinner ──────────────────────────────────────────────────────── */
  .plugin-loader-spinner {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 32px 0;
  }

  .spinner-ring {
    display: inline-block;
    width: 28px;
    height: 28px;
    border: 3px solid rgba(255, 255, 255, 0.08);
    border-top-color: var(--color-primary, #1db954);
    border-radius: 50%;
    animation: spin 0.75s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  /* ── Empty state ──────────────────────────────────────────────────── */
  .plugin-loader-empty {
    padding: 40px 24px;
    text-align: center;
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px dashed rgba(255, 255, 255, 0.08);
  }

  .plugin-loader-empty__msg {
    margin: 0;
    color: var(--text-muted, rgba(255,255,255,0.4));
    font-size: 14px;
    line-height: 1.5;
  }

  /* ── Error banner ────────────────────────────────────────────────── */
  .plugin-loader-error {
    margin: 8px 0 0;
    padding: 10px 14px;
    border-radius: 8px;
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.3);
    color: #ef4444;
    font-size: 13px;
  }
</style>
