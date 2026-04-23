<svelte:options customElement={{
  tag: 'navidrome-dashboard-card',
  shadow: 'none'
}} />
<script>
  export let apiBase = '';
  import { onMount } from 'svelte';


  let baseUrl = '';
  let username = '';
  let password = '';
  let pathMappings = [];
  let hasPassword = false;
  let connected = false;
  let loading = true;
  let saving = false;
  let testing = false;
  let collapsed = false;
  let showPassword = false;
  let isActive = false;
  let activating = false;

  onMount(async () => {
    await loadSettings();
    loading = false;
  });

  async function activateServer() {
    try {
      activating = true;
      await fetch(`${apiBase}/navidrome/activate`, { method: 'POST' });
      console.log('Navidrome activated as media server');
      await loadSettings(); // Reload to get updated is_active
    } catch (error) {
      console.error('Failed to activate server:', error);
      console.error('Failed to activate server');
    } finally {
      activating = false;
    }
  }

  async function loadSettings() {
    try {
      const response = await fetch(`${apiBase}/navidrome/settings`);
      if (response.data?.settings) {
        baseUrl = response.data.settings.base_url || '';
        username = response.data.settings.username || '';
        pathMappings = response.data.settings.path_mappings || [];
        hasPassword = response.data.settings.has_password || false;
        connected = response.data.settings.connected || false;
        isActive = response.data.settings.is_active || false;
        password = ''; // Don't load actual password for security
      }
    } catch (error) {
      console.error('Failed to load Navidrome settings:', error);
      console.error('Failed to load Navidrome settings');
    }
  }

  async function saveSettings() {
    if (!baseUrl.trim()) {
      console.error('Server URL is required');
      return;
    }

    if (!username.trim() || !password.trim()) {
      console.error('Username and password are required');
      return;
    }

    try {
      saving = true;
      await fetch(`${apiBase}/navidrome/settings`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
        base_url: baseUrl,
        username: username,
        password: password,
        path_mappings: pathMappings
      }) });
      console.log('Navidrome settings saved');
      await loadSettings();
    } catch (error) {
      console.error('Failed to save Navidrome settings:', error);
      console.error('Failed to save settings');
    } finally {
      saving = false;
    }
  }

  async function testConnection() {
    try {
      testing = true;
      const response = await fetch(`${apiBase}/navidrome/test-connection`, { method: 'POST' });
      
      if (response.data?.connected) {
        console.log(`Connected to Navidrome ${response.data.version}`);
        await loadSettings();
      }
    } catch (error) {
      console.error('Connection test failed:', error);
      const msg = error?.response?.data?.error || 'Connection failed';
      console.error(msg);
    } finally {
      testing = false;
    }
  }
</script>

<section class="p-6 bg-surface backdrop-blur-md border border-glass-border rounded-global mb-4">
  <div class="flex justify-between items-center mb-5 pb-3 border-b border-glass-border">
    <div class="flex items-center gap-3">
      <h2 class="m-0 text-xl font-semibold">Navidrome</h2>
      {#if isActive}
        <span class="text-[12px] px-2 py-1 rounded-[4px] bg-[#3b82f6]/20 text-[#3b82f6] font-semibold">● Active</span>
      {/if}
      {#if hasPassword}
        <span class="text-[12px] px-2 py-1 rounded-[4px] bg-[#00e676]/20 text-[#00e676]">✓ Authenticated</span>
      {/if}
      {#if connected}
        <span class="text-[12px] px-2 py-1 rounded-[4px] bg-[#00e676]/20 text-[#00e676]">● Connected</span>
      {:else if hasPassword}
        <span class="text-[12px] px-2 py-1 rounded-[4px] bg-[#ff9800]/20 text-[#ff9800]">⚠ Disconnected</span>
      {/if}
    </div>
    <button class="px-4 py-2 bg-white/10 text-primary border border-white/20 rounded-global transition-colors hover:bg-white/15 disabled:opacity-50 disabled:cursor-not-allowed" on:click={() => collapsed = !collapsed}>
      {collapsed ? 'Expand' : 'Collapse'}
    </button>
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
            bind:value={baseUrl}
            placeholder="http://192.168.1.100:4533"
            class="px-3 py-2 bg-background border border-border rounded-global text-sm text-primary w-full box-border focus:outline-none focus:border-accent"
          />
          <span class="text-xs text-secondary mt-1">Enter your Navidrome server URL (include port, typically :4533)</span>
        </label>

        <label class="flex flex-col gap-[6px]">
          <span class="text-[13px] font-medium text-primary">Username</span>
          <input
            type="text"
            bind:value={username}
            placeholder="Enter username"
            class="px-3 py-2 bg-background border border-border rounded-global text-sm text-primary w-full box-border focus:outline-none focus:border-accent"
          />
        </label>

        <label class="flex flex-col gap-[6px]">
          <span class="text-[13px] font-medium text-primary">Password</span>
          <div class="relative flex items-center">
            <input
              type={showPassword ? 'text' : 'password'}
              bind:value={password}
              placeholder={hasPassword ? 'Enter new password' : 'Enter password'}
              class="px-3 py-2 bg-background border border-border rounded-global text-sm text-primary w-full box-border focus:outline-none focus:border-accent"
            />
            <button 
              type="button" 
              class="absolute right-2 bg-transparent border-none cursor-pointer text-lg p-1 opacity-60 hover:opacity-100 transition-opacity"
              on:click={() => showPassword = !showPassword}
              title={showPassword ? 'Hide' : 'Show'}
            >
              {showPassword ? '👁️' : '👁️‍🗨️'}
            </button>
          </div>
        </label>

        <div class="border-t border-gray-700 my-4 pt-4">
            <echosync-path-mapping-editor mappings={JSON.stringify(pathMappings)} on:es-path-update={(e) => pathMappings = e.detail} />
        </div>

        <div class="flex gap-3 flex-wrap">
          <button
            class="px-4 py-2 bg-accent text-black font-medium rounded-global transition-colors hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
            on:click={saveSettings}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
          
          {#if hasPassword}
            <button
              class="px-4 py-2 bg-white/10 text-primary border border-white/20 rounded-global transition-colors hover:bg-white/15 disabled:opacity-50 disabled:cursor-not-allowed"
              on:click={testConnection}
              disabled={testing}
            >
              {testing ? 'Testing...' : 'Test Connection'}
            </button>
          {/if}

          {#if !isActive}
            <button
              class="px-4 py-2 bg-white/10 text-primary border border-white/20 rounded-global transition-colors hover:bg-white/15 disabled:opacity-50 disabled:cursor-not-allowed"
              on:click={activateServer}
              disabled={activating}
            >
              {activating ? 'Activating...' : 'Activate Server'}
            </button>
          {/if}
        </div>
      </div>
    </div>
  {/if}
</section>


