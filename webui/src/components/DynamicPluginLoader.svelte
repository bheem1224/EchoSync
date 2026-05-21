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
  function injectScript(url, version = null) {
    const separator = url.includes('?') ? '&' : '?';
    const finalUrl = version ? `${url}${separator}v=${version}` : url;

    if (_injectedUrls.has(finalUrl)) return Promise.resolve();

    // Double-check the DOM to survive HMR / multiple mounts
    // We check for the base URL to see if any version of this script is already loaded, 
    // or we can check for the exact finalUrl. 
    // For cache busting, if the version changed, we might WANT a new script tag, 
    // but browser might have already executed the old one. 
    // Usually, one script per base URL is enough per session.
    if (document.querySelector(`script[src^="${CSS.escape ? CSS.escape(url) : url}"]`)) {
      _injectedUrls.add(finalUrl);
      return Promise.resolve();
    }

    return new Promise((resolve, reject) => {
      const el = document.createElement('script');
      el.type = 'module';
      el.src = finalUrl;
      el.onload  = () => { _injectedUrls.add(finalUrl); resolve(); };
      el.onerror = () => reject(new Error(`Failed to load plugin bundle: ${url}`));
      document.head.appendChild(el);
    });
  }

  /**
   * Helper to wrap a promise with a timeout.
   */
  function waitWithTimeout(promise, ms, timeoutMsg) {
    let timeoutId;
    const timeoutPromise = new Promise((_, reject) => {
      timeoutId = setTimeout(() => reject(new Error(timeoutMsg)), ms);
    });
    return Promise.race([promise, timeoutPromise]).finally(() => {
      clearTimeout(timeoutId);
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

      // 3. Inject each plugin's bundle script and await registration
      const loadResults = await Promise.all(
        matching.map(async (plugin) => {
          const componentInfo = plugin.components[category];
          const bundleUrl = componentInfo?.bundle_url;
          const tag = componentInfo?.element_tag;
          if (!bundleUrl || !tag) return null;
          
          const absoluteUrl = (bundleUrl.startsWith('http') || bundleUrl.startsWith('/'))
            ? bundleUrl
            : `/api/system/plugins/${plugin.id}/ui/${bundleUrl.replace(/^\//, '')}`;
            
          try {
            await injectScript(absoluteUrl, plugin.version);
            
            // Defensively wait for custom element registry definition with a timeout
            await waitWithTimeout(
              customElements.whenDefined(tag),
              2000,
              `Timeout waiting for Custom Element "${tag}" registration`
            );
            
            return {
              plugin,
              tag,
              apiBase: plugin.api_base ?? `/api/plugins/${plugin.id}`,
              failed: false
            };
          } catch (err) {
            console.error(`[DynamicPluginLoader] Error loading plugin ${plugin.id}:`, err);
            return {
              plugin,
              tag,
              apiBase: plugin.api_base ?? `/api/plugins/${plugin.id}`,
              failed: true,
              errorMsg: err?.message ?? 'Unknown loading error'
            };
          }
        })
      );

      // 4. Collect loaded plugins (including failed ones for error cards) with strict deduplication
      resolvedPlugins = loadResults
        .filter(item => item != null && item.tag)
        .filter((value, index, self) =>
          self.findIndex(item => {
            // Deduplicate by normalizing IDs (strip core./plugin. prefixes) and comparing tags
            const norm1 = item.plugin.id.replace('core.', '').replace('plugin.', '');
            const norm2 = value.plugin.id.replace('core.', '').replace('plugin.', '');
            return (norm1 === norm2 && item.tag === value.tag);
          }) === index
        );

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
    {#each resolvedPlugins as { tag, apiBase, plugin, failed, errorMsg } (plugin.id || `${tag}-${apiBase}`)}
      {#if failed}
        <div class="plugin-error-card">
          <h4>Failed to load {plugin.name || plugin.id}</h4>
          <p>{errorMsg}</p>
        </div>
      {:else}
        <svelte:element
          this={tag}
          api-base={apiBase}
          plugin-id={plugin.id}
          {...passProps}
        />
      {/if}
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

  /* ── Failed Plugin Card ─────────────────────────────────────────── */
  .plugin-error-card {
    padding: 16px;
    border-radius: 12px;
    background: rgba(239, 68, 68, 0.05);
    border: 1px solid rgba(239, 68, 68, 0.2);
    color: #f87171;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .plugin-error-card h4 {
    margin: 0;
    font-size: 14px;
    font-weight: 600;
    color: #fca5a5;
  }

  .plugin-error-card p {
    margin: 0;
    font-size: 12px;
    color: rgba(255, 255, 255, 0.6);
  }
</style>
