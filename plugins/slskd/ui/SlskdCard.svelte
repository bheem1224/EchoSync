<svelte:options customElement={{
  tag: 'slskd-dashboard-card',
  shadow: 'none'
}} />
<script>
  export let apiBase = '';
  import { onMount } from 'svelte';

  let slskdUrl = '';
  let apiKey = '';
  let serverName = '';
  let connected = false;
  let loading = true;
  let saving = false;
  let testing = false;
  let collapsed = false;
  let showApiKey = false;
  let hasApiKeyInDb = false;
  let dbApiKeyRevealed = false;
  let isActive = false;

  onMount(async () => {
    await loadSettings();
    await checkActiveStatus();
    loading = false;
  });

  async function checkActiveStatus() {
    try {
      const response = await fetch(`${apiBase}/providers/download-clients/active`);
      isActive = response.data.active_client === 'slskd';
    } catch (error) {
      console.error('Failed to check active status:', error);
    }
  }

  async function activateClient() {
    try {
      await fetch(`${apiBase}/providers/download-clients/activate`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ client: 'slskd' }) });
      isActive = true;
      console.log('Slskd activated as download client');
    } catch (error) {
      console.error('Failed to activate client:', error);
      console.error('Failed to activate client');
    }
  }

  async function loadSettings() {
    try {
      const response = await fetch(`${apiBase}/providers/soulseek/settings`);
      if (response.data) {
        slskdUrl = response.data.slskd_url || '';
        serverName = response.data.server_name || '';
        apiKey = response.data.api_key || '';
        hasApiKeyInDb = response.data.has_api_key || false;
        connected = response.data.configured || false;
      }
    } catch (error) {
      console.error('Failed to load slskd settings:', error);
      console.error('Failed to load slskd settings');
    }
  }

  async function saveSettings() {
    if (!slskdUrl.trim()) {
      console.error('Server URL is required');
      return;
    }

    try {
      saving = true;
      const payload = {
        slskd_url: slskdUrl,
        server_name: serverName
      };
      
      // Only include API key if it's not the masked placeholder
      if (apiKey && apiKey !== '****') {
        payload.api_key = apiKey;
      }
      
      await fetch(`${apiBase}/providers/soulseek/settings`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      console.log('slskd settings saved');
      await loadSettings();
    } catch (error) {
      console.error('Failed to save slskd settings:', error);
      console.error('Failed to save settings');
    } finally {
      saving = false;
    }
  }

  async function testConnection() {
    if (!slskdUrl.trim()) {
      console.error('Server URL is required');
      return;
    }

    if (!hasApiKeyInDb && !apiKey.trim()) {
      console.error('API Key is required');
      return;
    }

    try {
      testing = true;
      const response = await fetch(`${apiBase}/providers/soulseek/connection/test`, { method: 'POST' });
      
      if (response.data?.success) {
        console.log('slskd connection successful!');
        connected = true;
      } else {
        console.error(response.data?.error || 'Connection failed');
        connected = false;
      }
    } catch (error) {
      console.error('Failed to test slskd connection:', error);
      console.error('Connection test failed');
      connected = false;
    } finally {
      testing = false;
    }
  }

  async function toggleApiKeyVisibility() {
    // Toggle UI state
    const willShow = !showApiKey;
    showApiKey = willShow;

    // If revealing and the key is stored (masked), fetch the real key
    if (willShow && hasApiKeyInDb && apiKey === '****' && !dbApiKeyRevealed) {
      try {
        const resp = await fetch(`${apiBase}/providers/soulseek/settings/key`);
        if (resp.data && resp.data.api_key) {
          apiKey = resp.data.api_key;
          dbApiKeyRevealed = true;
        } else {
          console.error('Failed to reveal API key');
          // revert UI
          showApiKey = false;
        }
      } catch (err) {
        console.error('Failed to fetch API key:', err);
        console.error('Unable to reveal API key');
        showApiKey = false;
      }
    }

    // If hiding and key was revealed from DB, re-mask it
    if (!willShow && dbApiKeyRevealed) {
      apiKey = '****';
      dbApiKeyRevealed = false;
    }
  }
</script>

<section class="p-6 bg-surface backdrop-blur-md border border-glass-border rounded-global mb-4">
  <div class="flex justify-between items-center mb-5 pb-3 border-b border-glass-border">
    <div class="flex items-center gap-3">
      <h2 class="m-0 text-xl font-semibold">slskd</h2>
      <span class="text-[12px] px-2 py-1 rounded-[4px] bg-[#ba6415]/20 text-[#ba6415]">Download Client</span>
      {#if connected}
        <span class="text-[12px] px-2 py-1 rounded-[4px] bg-[#00e676]/20 text-[#00e676]">● Connected</span>
      {:else if slskdUrl}
        <span class="text-[12px] px-2 py-1 rounded-[4px] bg-[#ff9800]/20 text-[#ff9800]">⚠ Disconnected</span>
      {/if}
      {#if isActive}
        <span class="status-badge active-client">● Active</span>
      {/if}
    </div>
    <div class="header-right">
      {#if !isActive && connected}
        <button class="btn-sm btn-secondary active:scale-95 transition-all duration-200" on:click={activateClient}>Activate</button>
      {/if}
      <button class="bg-transparent text-[#ba6415] px-2 py-1 hover:underline active:scale-95 transition-all duration-200" on:click={() => collapsed = !collapsed}>
        {collapsed ? 'Expand' : 'Collapse'}
      </button>
    </div>
  </div>

  {#if loading}
    <div class="p-5 text-center text-secondary">Loading...</div>
  {:else if !collapsed}
    <div class="mb-6">
      <h3 class="m-0 mb-4 text-base font-semibold">Server Configuration</h3>
      
      <div class="flex flex-col gap-4">
        <label class="flex flex-col gap-[6px]">
          <span class="text-[13px] font-medium text-primary">Server URL</span>
          <input
            type="text"
            bind:value={slskdUrl}
            placeholder="http://192.168.1.100:5030"
            class="px-3 py-2 bg-background border border-border rounded-global text-sm text-primary w-full box-border focus:outline-none focus:border-accent"
          />
          <span class="text-xs text-secondary mt-1">Enter your slskd server address (include port, default :5030)</span>
        </label>

        <label class="flex flex-col gap-[6px]">
          <span class="text-[13px] font-medium text-primary">Server Name (Optional)</span>
          <input
            type="text"
            bind:value={serverName}
            placeholder="My slskd Server"
            class="px-3 py-2 bg-background border border-border rounded-global text-sm text-primary w-full box-border focus:outline-none focus:border-accent"
          />
          <span class="text-xs text-secondary mt-1">Friendly name for this server</span>
        </label>

        <label class="flex flex-col gap-[6px]">
          <span class="text-[13px] font-medium text-primary">API Key</span>
          <div class="input-with-toggle">
            <input
              type={showApiKey ? 'text' : 'password'}
              bind:value={apiKey}
              placeholder="Enter API key"
              class="px-3 py-2 bg-background border border-border rounded-global text-sm text-primary w-full box-border focus:outline-none focus:border-accent"
            />
            <button 
              type="button" 
              class="toggle-btn active:scale-95 transition-all duration-200"
              on:click={toggleApiKeyVisibility}
              title={showApiKey ? 'Hide' : 'Show'}
            >
              {showApiKey ? '👁️' : '👁️‍🗨️'}
            </button>
          </div>
          <span class="text-xs text-secondary mt-1">API key from slskd settings (Options → Security → API Keys)</span>
        </label>

        <div class="flex gap-3 flex-wrap">
          <button
            class="px-4 py-2 bg-accent text-black font-medium rounded-global transition-colors hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95"
            on:click={saveSettings}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
          
          {#if slskdUrl && (hasApiKeyInDb || apiKey)}
            <button
              class="px-4 py-2 bg-white/10 text-primary border border-white/20 rounded-global transition-colors hover:bg-white/15 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95"
              on:click={testConnection}
              disabled={testing}
            >
              {testing ? 'Testing...' : 'Test Connection'}
            </button>
          {/if}
        </div>
      </div>
    </div>
  {/if}
</section>


