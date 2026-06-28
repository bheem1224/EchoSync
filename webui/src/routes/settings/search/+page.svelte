<script>
  import { onMount } from 'svelte';
  import { settings } from '../../../stores/settings';
  import { plugins } from '../../../stores/plugins';
  import { feedback } from '../../../stores/feedback';

  let searchPluginsList = [];
  let enabledPlugins = [];
  let loading = true;

  onMount(async () => {
    loading = true;
    try {
      await Promise.all([settings.load(), plugins.load()]);
      
      // Filter to only plugins that have search capabilities
      searchPluginsList = Object.values($plugins.items || {}).filter(p => p.capabilities?.search?.tracks);
      
      // Load enabled state from settings (if undefined, default to all enabled)
      const savedPlugins = $settings.data?.search_plugins;
      if (savedPlugins !== undefined && Array.isArray(savedPlugins)) {
        enabledPlugins = [...savedPlugins];
      } else {
        enabledPlugins = searchPluginsList.map(p => p.name);
      }
    } catch (err) {
      feedback.addToast('Failed to load search settings', 'error');
    } finally {
      loading = false;
    }
  });

  async function saveSettings() {
    try {
      feedback.setLoading(true);
      await settings.save({ search_plugins: enabledPlugins });
      feedback.addToast('Search settings saved successfully', 'success');
    } catch (e) {
      feedback.addToast('Failed to save settings', 'error');
    } finally {
      feedback.setLoading(false);
    }
  }

  function togglePlugin(pluginName) {
    if (enabledPlugins.includes(pluginName)) {
      enabledPlugins = enabledPlugins.filter(p => p !== pluginName);
    } else {
      enabledPlugins = [...enabledPlugins, pluginName];
    }
    saveSettings();
  }
</script>

<svelte:head>
  <title>Search Settings • EchoSync</title>
</svelte:head>

<section class="page flex flex-col gap-6 w-full">
  <header class="page__header">
    <div>
      <h1 class="prefs-title">Search Engine</h1>
      <p class="sub">Manage your federated discovery and search capabilities.</p>
    </div>
  </header>

  {#if loading}
    <div class="flex justify-center py-12">
      <div class="w-8 h-8 border-4 border-white/10 border-t-accent rounded-full animate-spin"></div>
    </div>
  {:else}
    <div class="bg-surface border border-glass-border rounded-global p-6 shadow-xl backdrop-blur-md">
      <div class="mb-6">
        <h2 class="text-lg font-semibold text-white">Federated Search Plugins</h2>
        <p class="text-sm text-slate-400 mt-1">
          Select which plugins should participate in the global Discovery Search (triggered via the <code>?</code> prefix). 
          Disabling slow plugins can drastically improve your search latency.
        </p>
      </div>

      <div class="flex flex-col gap-3">
        {#each searchPluginsList as plugin}
          <div class="flex items-center justify-between p-4 bg-black/20 border border-white/5 rounded-lg hover:bg-white/5 transition-colors">
            <div class="flex flex-col justify-center">
              <span class="font-medium text-white text-base">{plugin.manifest?.name || plugin.name.replace(/^EchoSync\./i, '').replace(/^\w/, c => c.toUpperCase())}</span>
            </div>
            
            <label class="relative inline-flex items-center cursor-pointer">
              <input 
                type="checkbox" 
                class="sr-only peer" 
                checked={enabledPlugins.includes(plugin.name)}
                on:change={() => togglePlugin(plugin.name)}
              >
              <div class="w-11 h-6 bg-black/40 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-slate-300 after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[var(--accent)] peer-checked:after:bg-white border border-glass-border"></div>
            </label>
          </div>
        {/each}

        {#if searchPluginsList.length === 0}
          <div class="p-6 text-center text-muted text-sm border border-dashed border-white/10 rounded-lg">
            No search-capable plugins found. Install plugins from the Plugin Store to expand your search.
          </div>
        {/if}
      </div>
    </div>
  {/if}
</section>

<style>
  .prefs-title {
    font-size: 24px;
    font-weight: 700;
    margin: 0;
    color: var(--text);
  }
  .sub {
    margin: 6px 0 0;
    color: var(--muted);
  }
</style>
