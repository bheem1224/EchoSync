<svelte:options customElement={{
  tag: 'plex-dashboard-card',
  shadow: 'none'
}} />
<script>
  export let apiBase = '';
  import { onMount } from 'svelte';


  let baseUrl = '';
  let serverName = '';
  let pathMappings = [];
  let hasToken = false;
  let connected = false;
  let loading = true;
  let saving = false;
  let testing = false;
  let authenticating = false;
  let oauthSession = null;
  let pollInterval = null;
  let collapsed = false;
  let isActive = false;
  let activating = false;

  onMount(async () => {
    await loadSettings();
    loading = false;
  });

  async function activateServer() {
    try {
      activating = true;
      await fetch(`${apiBase}/plex/activate`, { method: 'POST' });
      console.log('Plex activated as media server');
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
      const response = await fetch(`${apiBase}/plex/settings`);
      if (response.data?.settings) {
        baseUrl = response.data.settings.base_url || '';
        serverName = response.data.settings.server_name || '';
        pathMappings = response.data.settings.path_mappings || [];
        hasToken = response.data.settings.has_token || false;
        connected = response.data.settings.connected || false;
        isActive = response.data.settings.is_active || false;
      }
    } catch (error) {
      console.error('Failed to load Plex settings:', error);
      console.error('Failed to load Plex settings');
    }
  }

  async function saveSettings() {
    if (!baseUrl.trim()) {
      console.error('Server URL is required');
      return;
    }

    try {
      saving = true;
      await fetch(`${apiBase}/plex/settings`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
        base_url: baseUrl,
        server_name: serverName,
        path_mappings: pathMappings
      }) });
      console.log('Plex settings saved');
      await loadSettings();
    } catch (error) {
      console.error('Failed to save Plex settings:', error);
      console.error('Failed to save settings');
    } finally {
      saving = false;
    }
  }

  async function startOAuth() {
    try {
      authenticating = true;
      const response = await fetch(`${apiBase}/plex/auth/start`, { method: 'POST' });
      
      if (response.data?.oauth_url && response.data?.session_id) {
        oauthSession = response.data.session_id;
        
        // Open Plex OAuth page in new window
        window.open(response.data.oauth_url, 'PlexOAuth', 'width=600,height=700');
        
        // Start polling for completion
        pollInterval = setInterval(async () => {
          try {
            const pollResp = await fetch(`${apiBase}/plex/auth/poll/${oauthSession}`);
            if (pollResp.data?.completed) {
              // OAuth completed (backend already saved token to account_tokens)
              clearInterval(pollInterval);
              pollInterval = null;
              
              console.log('Plex authentication successful');
              authenticating = false;
              oauthSession = null;

              // Remove old localStorage stale PIN (if it was used by a previous version)
              localStorage.removeItem('plex_oauth_session');

              await loadSettings();
            }
          } catch (pollError) {
            console.error('OAuth poll error:', pollError);
            // If the session is missing or server restarted (404 Not Found), stop zombie polling
            if (pollError.response && pollError.response.status === 404) {
              clearInterval(pollInterval);
              pollInterval = null;
              authenticating = false;
              oauthSession = null;
              localStorage.removeItem('plex_oauth_session');
              console.error('Authentication session expired or server restarted');
            }
          }
        }, 2000); // Poll every 2 seconds
        
        // Stop polling after 10 minutes
        setTimeout(() => {
          if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
            authenticating = false;
            oauthSession = null;
            console.error('OAuth timeout - please try again');
          }
        }, 600000);
      }
    } catch (error) {
      console.error('Failed to start Plex OAuth:', error);
      console.error('Failed to start authentication');
      authenticating = false;
    }
  }

  async function cancelOAuth() {
    if (oauthSession && pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
      
      try {
        await fetch(`${apiBase}/plex/auth/cancel/${oauthSession}`, { method: 'DELETE' });
      } catch (error) {
        console.error('Failed to cancel OAuth:', error);
      }
      
      oauthSession = null;
      authenticating = false;
      console.log('Authentication cancelled');
    }
  }

  async function testConnection() {
    try {
      testing = true;
      const response = await fetch(`${apiBase}/plex/test-connection`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
        base_url: baseUrl
      }) });
      
      if (response.data?.connected) {
        console.log(`Connected to ${response.data.server_name}`);
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
      <h2 class="m-0 text-xl font-semibold">Plex</h2>
      {#if isActive}
        <span class="text-[12px] px-2 py-1 rounded-[4px] bg-[#3b82f6]/20 text-[#3b82f6] font-semibold">● Active</span>
      {/if}
      {#if hasToken}
        <span class="text-[12px] px-2 py-1 rounded-[4px] bg-[#00e676]/20 text-[#00e676]">✓ Authenticated</span>
      {/if}
      {#if connected}
        <span class="text-[12px] px-2 py-1 rounded-[4px] bg-[#00e676]/20 text-[#00e676]">● Connected</span>
      {:else if hasToken}
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
            placeholder="http://192.168.1.100:32400"
            class="px-3 py-2 bg-background border border-border rounded-global text-sm text-primary w-full box-border focus:outline-none focus:border-accent"
          />
          <span class="text-xs text-secondary mt-1">Enter your Plex server IP address or URL (include port, typically :32400)</span>
        </label>

        <label class="flex flex-col gap-[6px]">
          <span class="text-[13px] font-medium text-primary">Server Name (Optional)</span>
          <input
            type="text"
            bind:value={serverName}
            placeholder="My Plex Server"
            class="px-3 py-2 bg-background border border-border rounded-global text-sm text-primary w-full box-border focus:outline-none focus:border-accent"
          />
          <span class="text-xs text-secondary mt-1">Preferred server if you have multiple</span>
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
          
          {#if hasToken}
            <button
              class="px-4 py-2 bg-white/10 text-primary border border-white/20 rounded-global transition-colors hover:bg-white/15 disabled:opacity-50 disabled:cursor-not-allowed"
              on:click={testConnection}
              disabled={testing || !baseUrl.trim()}
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

          {#if authenticating}
            <button class="px-4 py-2 bg-white/10 text-primary border border-white/20 rounded-global transition-colors hover:bg-white/15 disabled:opacity-50 disabled:cursor-not-allowed" on:click={cancelOAuth} disabled>
              Waiting for authorization...
            </button>
          {:else if hasToken}
            <button class="px-4 py-2 bg-accent text-black font-medium rounded-global transition-colors hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed" on:click={startOAuth}>Reauthenticate</button>
          {:else}
            <button class="px-4 py-2 bg-accent text-black font-medium rounded-global transition-colors hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed" on:click={startOAuth}>
              Login with Plex
            </button>
          {/if}
        </div>
      </div>
    </div>
  {/if}
</section>


