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
               as attributes (e.g. { "api-base": "/api/v1/system/plugins/spotify" }).
  showEmpty  : boolean – if true and no plugins load, render the default empty slot.
               Default: true.

  Slots
  ─────
  default  – Fallback content rendered when no plugins are found (or while loading).
  loading  – Optional override for the loading state.
-->
<script>
  import apiClient from '../api/client';
  // ── Props ──────────────────────────────────────────────────────────────
  /** Category key to look up in plugin.components (e.g. "music_service") */
  export let category = '';
  /** Arbitrary key/value attributes forwarded to every rendered Web Component */
  export let passProps = {};
  /** Whether to render the default slot when no plugins are available */
  export let showEmpty = true;

  import { injectPluginBundle } from '../lib/plugin/injectPluginBundle';

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
  async function fetchPlugins(cat) {
    if (!cat) return [];

    try {
      // 1. Fetch the UI manifest from the backend
      const resp = await apiClient.get('/v1/system/ui-registry');

      if (!resp.ok) {
        if (resp.status === 404) {
          console.warn(`[DynamicPluginLoader] /api/ui/registry not found. No plugins will load for category="${cat}".`);
          return [];
        }
        throw new Error(`UI registry fetch failed: ${resp.status} ${resp.statusText}`);
      }

      const data = resp.data;
      const typeKey = cat.endsWith('s') ? cat : `${cat}s`;
      const components = Array.isArray(data?.[typeKey]) ? data[typeKey] : [];

      if (components.length === 0) {
        console.warn(`[DynamicPluginLoader] No plugins found for category="${cat}".`);
        return [];
      }

      // 3. Inject each plugin's bundle script and await registration
      const loadResults = await Promise.all(
        components.map(async (comp) => {
          const bundleUrl = comp.entry;
          const tag = comp.tag_name;
          if (!bundleUrl || !tag) return null;
          
          // Natively track paths using exactly the plugin_id
          const absoluteUrl = (bundleUrl.startsWith('http') || bundleUrl.startsWith('/'))
            ? bundleUrl
            : `/api/v1/system/plugins/${comp.plugin_id}/ui/${bundleUrl.replace(/^\//, '')}`;
            
          try {
            await injectPluginBundle(absoluteUrl, comp.version ?? null);
            
            // Defensively wait for custom element registry definition with a timeout
            await waitWithTimeout(
              customElements.whenDefined(tag),
              2000,
              `Timeout waiting for Custom Element "${tag}" registration`
            );
            
            const pluginId = String(comp.plugin_id);
            return {
              plugin: {
                id: pluginId,
                name: comp.plugin_name || pluginId
              },
              tag,
              apiBase: `/api/v1/plugins/${pluginId}`,
              failed: false,
              is_active: true
            };
          } catch (err) {
            console.error(`[DynamicPluginLoader] Error loading plugin ${comp.plugin_id} at path ${absoluteUrl}:`, err);
            const pluginId = String(comp.plugin_id);
            return {
              plugin: {
                id: pluginId,
                name: comp.plugin_name || pluginId
              },
              tag,
              apiBase: `/api/v1/plugins/${pluginId}`,
              failed: true,
              errorMsg: err?.message ?? 'Unknown loading error'
            };
          }
        })
      );

      // 4. Collect loaded plugins (including failed ones for error cards) with strict deduplication
      return loadResults
        .filter(item => item != null && item.tag)
        .filter((value, index, self) =>
          self.findIndex(item => {
            // Deduplicate by normalizing IDs and comparing tags
            const norm1 = String(item.plugin?.id || item.plugin_id);
            const norm2 = String(value.plugin?.id || value.plugin_id);
            return (norm1 === norm2 && item.tag === value.tag);
          }) === index
        );

    } catch (err) {
      console.warn('[DynamicPluginLoader] Failed to load plugin manifest:', err?.message ?? err);
      throw err;
    }
  }

  // Authoritative Async Gating via reactive promise
  $: pluginsPromise = fetchPlugins(category);

  function initCard(node, { apiBase, pluginId }) {
    // Set properties directly on the element object
    node.apiBase = apiBase;
    node.pluginId = pluginId;
    node.plugin_id = pluginId;
    
    // Set attributes as fallback
    node.setAttribute('api-base', apiBase);
    node.setAttribute('apibase', apiBase);
    node.setAttribute('plugin-id', pluginId);
    node.setAttribute('plugin_id', pluginId);
    
    return {
      update(params) {
        node.apiBase = params.apiBase;
        node.pluginId = params.pluginId;
        node.plugin_id = params.pluginId;
        
        node.setAttribute('api-base', params.apiBase);
        node.setAttribute('apibase', params.apiBase);
        node.setAttribute('plugin-id', params.pluginId);
        node.setAttribute('plugin_id', params.pluginId);
      }
    };
  }
</script>

<!-- ── Render ─────────────────────────────────────────────────────────────── -->
{#await pluginsPromise}
  <!-- Loading slot – override with <svelte:fragment slot="loading"> -->
  <slot name="loading">
    <div class="plugin-loader-spinner" aria-label="Loading plugins…">
      <span class="spinner-ring"></span>
    </div>
  </slot>

{:then resolvedPlugins}
  {#if resolvedPlugins.length > 0}
    <!-- One element per resolved Web Component -->
    <div class="plugin-loader-grid" data-category={category}>
      {#each resolvedPlugins as { tag, apiBase, plugin, failed, errorMsg } (plugin.id || `${tag}-${apiBase}`)}
        {#if failed}
          <div class="plugin-error-card">
            <h4>Failed to load {plugin.name || plugin.id}</h4>
            <p>{errorMsg}</p>
          </div>
        {:else}
          <div style="contain: content; isolation: isolate;">
            <svelte:element
              this={tag}
              use:initCard={{ apiBase, pluginId: plugin.id }}
              api-base={apiBase}
              apiBase={apiBase}
              apibase={apiBase}
              plugin-id={plugin.id}
              {...passProps}
            />
          </div>
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

{:catch error}
  <p class="plugin-loader-error" role="alert">⚠ {error.message}</p>
{/await}

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
