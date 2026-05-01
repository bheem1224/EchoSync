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
      await loadSettings();
    } catch (error) {
      console.error('Failed to activate server:', error);
    } finally {
      activating = false;
    }
  }

  async function loadSettings() {
    try {
      const response = await fetch(`${apiBase}/plex/settings`);
      const data = await response.json();
      if (data?.settings) {
        baseUrl = data.settings.base_url || '';
        serverName = data.settings.server_name || '';
        pathMappings = data.settings.path_mappings || [];
        hasToken = data.settings.has_token || false;
        connected = data.settings.connected || false;
        isActive = data.settings.is_active || false;
      }
    } catch (error) {
      console.error('Failed to load Plex settings:', error);
    }
  }

  async function saveSettings() {
    if (!baseUrl.trim()) {
      console.error('Server URL is required');
      return;
    }

    try {
      saving = true;
      await fetch(`${apiBase}/plex/settings`, { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({
          base_url: baseUrl,
          server_name: serverName,
          path_mappings: pathMappings
        }) 
      });
      await loadSettings();
    } catch (error) {
      console.error('Failed to save Plex settings:', error);
    } finally {
      saving = false;
    }
  }

  async function startOAuth() {
    try {
      authenticating = true;
      const response = await fetch(`${apiBase}/plex/auth/start`, { method: 'POST' });
      const data = await response.json();
      
      if (data?.oauth_url && data?.session_id) {
        oauthSession = data.session_id;
        window.open(data.oauth_url, 'PlexOAuth', 'width=600,height=700');
        
        pollInterval = setInterval(async () => {
          try {
            const pollResp = await fetch(`${apiBase}/plex/auth/poll/${oauthSession}`);
            const pollData = await pollResp.json();
            if (pollData?.completed) {
              clearInterval(pollInterval);
              pollInterval = null;
              authenticating = false;
              oauthSession = null;
              await loadSettings();
            }
          } catch (pollError) {
            console.error('OAuth poll error:', pollError);
            if (pollError.status === 404) {
              clearInterval(pollInterval);
              pollInterval = null;
              authenticating = false;
              oauthSession = null;
            }
          }
        }, 2000);
      }
    } catch (error) {
      console.error('Failed to start Plex OAuth:', error);
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
    }
  }

  async function testConnection() {
    try {
      testing = true;
      const response = await fetch(`${apiBase}/plex/test-connection`, { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({ base_url: baseUrl }) 
      });
      const data = await response.json();
      if (data?.connected) {
        await loadSettings();
      }
    } catch (error) {
      console.error('Connection test failed:', error);
    } finally {
      testing = false;
    }
  }
</script>

<section class="plugin-card">
  <div class="card-header">
    <div class="header-left">
      <h2 class="card-title">Plex</h2>
      <div class="badges">
        {#if isActive}
          <span class="status-badge active">● Active</span>
        {/if}
        {#if hasToken}
          <span class="status-badge success">✓ Authenticated</span>
        {/if}
        {#if connected}
          <span class="status-badge success">● Connected</span>
        {:else if hasToken}
          <span class="status-badge warning">⚠ Disconnected</span>
        {/if}
      </div>
    </div>
    <button class="btn-ghost" on:click={() => collapsed = !collapsed}>
      {collapsed ? 'Expand' : 'Collapse'}
    </button>
  </div>

  {#if loading}
    <div class="loading-state">Loading...</div>
  {:else if !collapsed}
    <div class="settings-section">
      <h3 class="section-title">Server Configuration</h3>
      
      <div class="form-grid">
        <label class="form-field">
          <span class="field-label">Server URL</span>
          <input
            type="text"
            bind:value={baseUrl}
            placeholder="http://192.168.1.100:32400"
            class="input-field"
          />
          <span class="helper-text">Enter your Plex server IP address or URL (include port, typically :32400)</span>
        </label>

        <label class="form-field">
          <span class="field-label">Server Name (Optional)</span>
          <input
            type="text"
            bind:value={serverName}
            placeholder="My Plex Server"
            class="input-field"
          />
        </label>

        <div class="path-mappings">
          <echosync-path-mapping-editor mappings={JSON.stringify(pathMappings)} on:es-path-update={(e) => pathMappings = e.detail} />
        </div>

        <div class="actions-row">
          <button
            class="btn-primary"
            on:click={saveSettings}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
          
          {#if hasToken}
            <button
              class="btn-ghost"
              on:click={testConnection}
              disabled={testing || !baseUrl.trim()}
            >
              {testing ? 'Testing...' : 'Test Connection'}
            </button>
          {/if}

          {#if !isActive}
            <button
              class="btn-ghost"
              on:click={activateServer}
              disabled={activating}
            >
              {activating ? 'Activating...' : 'Activate Server'}
            </button>
          {/if}

          {#if authenticating}
            <button class="btn-ghost" on:click={cancelOAuth} disabled>
              Waiting for authorization...
            </button>
          {:else if hasToken}
            <button class="btn-primary" on:click={startOAuth}>Reauthenticate</button>
          {:else}
            <button class="btn-primary" on:click={startOAuth}>
              Login with Plex
            </button>
          {/if}
        </div>
      </div>
    </div>
  {/if}
</section>

<style>
  .plugin-card {
    background: var(--glass, rgba(20, 24, 31, 0.7));
    backdrop-filter: blur(12px);
    border: 1px solid var(--glass-border, rgba(255,255,255,0.08));
    border-radius: var(--radius, 12px);
    padding: 24px;
    margin-bottom: 24px;
    color: var(--text-main, #fff);
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border-subtle, rgba(255,255,255,0.08));
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .card-title {
    margin: 0;
    font-size: 20px;
    font-weight: 700;
  }

  .badges {
    display: flex;
    gap: 8px;
  }

  .status-badge {
    font-size: 10px;
    padding: 2px 8px;
    border-radius: 4px;
    font-weight: 700;
  }

  .status-badge.active { background: rgba(59, 130, 246, 0.15); color: #3b82f6; }
  .status-badge.success { background: rgba(34, 197, 94, 0.15); color: #22c55e; }
  .status-badge.warning { background: rgba(234, 179, 8, 0.15); color: #eab308; }

  .btn-ghost {
    padding: 8px 16px;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    color: var(--text-main, #fff);
    border-radius: 8px;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn-ghost:hover {
    background: rgba(255,255,255,0.1);
  }

  .btn-primary {
    padding: 10px 20px;
    background: var(--color-primary, #14b8a6);
    color: #000;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .loading-state {
    padding: 24px;
    text-align: center;
    color: var(--text-muted, #64748b);
  }

  .settings-section {
    margin-top: 16px;
  }

  .section-title {
    margin: 0 0 16px 0;
    font-size: 16px;
    font-weight: 600;
  }

  .form-grid {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .form-field {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .field-label {
    font-size: 13px;
    color: var(--text-muted, #64748b);
  }

  .input-field {
    width: 100%;
    padding: 10px 14px;
    background: var(--bg-input, #08080a);
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.08));
    border-radius: 8px;
    color: var(--text-main, #fff);
    font-size: 14px;
    transition: all 0.2s;
  }

  .input-field:focus {
    outline: none;
    border-color: var(--color-primary, #14b8a6);
    box-shadow: 0 0 0 2px rgba(20, 184, 166, 0.1);
  }

  .helper-text {
    font-size: 11px;
    color: var(--text-muted, #64748b);
  }

  .path-mappings {
    padding: 16px 0;
    border-top: 1px solid rgba(255,255,255,0.05);
  }

  .actions-row {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    margin-top: 8px;
  }
</style>
