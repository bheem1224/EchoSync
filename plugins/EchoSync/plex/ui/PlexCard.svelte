<svelte:options customElement="plex-dashboard-card" />
<script>
  /**
   * @type {string} apiBase - The base URL for API calls, provided by the dashboard host.
   */
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
    // Normalize apiBase
    apiBase = apiBase.replace(/\/$/, "");
    
    await loadSettings();
    loading = false;
  });

  async function activateServer() {
    try {
      activating = true;
      const resp = await fetch(`${apiBase}/activate`, { method: 'POST' });
      if (!resp.ok) throw new Error("Activation failed");
      await loadSettings();
    } catch (error) {
      console.error('Failed to activate server:', error);
      alert("Activation failed. Check logs.");
    } finally {
      activating = false;
    }
  }

  async function loadSettings() {
    try {
      const response = await fetch(`${apiBase}/settings`);
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
      alert('Server URL is required');
      return;
    }

    try {
      saving = true;
      const resp = await fetch(`${apiBase}/settings`, { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({
          base_url: baseUrl,
          server_name: serverName,
          path_mappings: pathMappings
        }) 
      });
      if (!resp.ok) throw new Error("Save failed");
      await loadSettings();
    } catch (error) {
      console.error('Failed to save Plex settings:', error);
      alert("Failed to save settings.");
    } finally {
      saving = false;
    }
  }

  async function startOAuth() {
    try {
      authenticating = true;
      const response = await fetch(`${apiBase}/auth/start`, { method: 'POST' });
      const data = await response.json();
      
      if (data?.oauth_url && data?.session_id) {
        oauthSession = data.session_id;
        window.open(data.oauth_url, 'PlexOAuth', 'width=600,height=700,menubar=no,status=no');
        
        pollInterval = setInterval(async () => {
          try {
            const pollResp = await fetch(`${apiBase}/auth/poll/${oauthSession}`);
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
        }, 3000);
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
        await fetch(`${apiBase}/auth/cancel/${oauthSession}`, { method: 'DELETE' });
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
      const response = await fetch(`${apiBase}/test-connection`, { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({ base_url: baseUrl }) 
      });
      const data = await response.json();
      if (data?.connected) {
        alert("Connection successful!");
        await loadSettings();
      } else {
        alert("Connection failed. Check URL and ensure Plex is running.");
      }
    } catch (error) {
      console.error('Connection test failed:', error);
      alert("Test failed with error.");
    } finally {
      testing = false;
    }
  }
</script>

<section class="plugin-card">
  <div class="card-header">
    <div class="header-left">
      <h2 class="card-title">Plex Media Server</h2>
      <div class="badges">
        {#if isActive}
          <span class="status-badge active">Active</span>
        {/if}
        {#if hasToken}
          <span class="status-badge success">Authenticated</span>
        {/if}
        {#if connected}
          <span class="status-badge success">Connected</span>
        {:else if hasToken}
          <span class="status-badge warning">Disconnected</span>
        {/if}
      </div>
    </div>
    <button class="btn-ghost-small" on:click={() => collapsed = !collapsed}>
      {collapsed ? 'Expand' : 'Collapse'}
    </button>
  </div>

  {#if loading}
    <div class="loading-state">
      <div class="spinner"></div>
      <span>Linking with Plex Nexus...</span>
    </div>
  {:else if !collapsed}
    <div class="settings-section">
      <div class="form-grid">
        <div class="form-field">
          <span class="field-label">Server Access URL</span>
          <input
            type="text"
            bind:value={baseUrl}
            placeholder="http://192.168.1.100:32400"
            class="input-field"
          />
          <span class="helper-text">Typically http://[IP]:32400. Use localhost if running natively.</span>
        </div>

        <div class="form-field">
          <span class="field-label">Friendly Name</span>
          <input
            type="text"
            bind:value={serverName}
            placeholder="e.g. Home Media"
            class="input-field"
          />
        </div>

        <div class="path-mappings">
           <div class="mapping-header">
              <span class="field-label">Path Mappings</span>
           </div>
           <!-- The editor handles its own styling, but we wrap it for layout -->
           <div class="editor-wrapper">
              <echosync-path-mapping-editor 
                mappings={JSON.stringify(pathMappings)} 
                on:es-path-update={(e) => pathMappings = e.detail} 
              />
           </div>
        </div>

        <div class="actions-row">
          <button
            class="btn-primary"
            on:click={saveSettings}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Configuration'}
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

          {#if !isActive && hasToken}
            <button
              class="btn-ghost accent"
              on:click={activateServer}
              disabled={activating}
            >
              {activating ? 'Activating...' : 'Activate for Sync'}
            </button>
          {/if}

          <div class="auth-box">
            {#if authenticating}
              <button class="btn-danger-ghost" on:click={cancelOAuth}>
                Cancel Authorization
              </button>
            {:else if hasToken}
              <button class="btn-ghost" on:click={startOAuth}>Switch Account</button>
            {:else}
              <button class="btn-primary plex-btn" on:click={startOAuth}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0L9.33 6.67L2 9.33L7.33 14.67L6 22L12 18.67L18 22L16.67 14.67L22 9.33L14.67 6.67L12 0Z"/></svg>
                Sign in with Plex
              </button>
            {/if}
          </div>
        </div>
      </div>
    </div>
  {/if}
</section>

<style>
  /* SHADOW DOM STYLING */

  .plugin-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius, 12px);
    padding: 24px;
    color: var(--text-primary);
    font-family: inherit;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border-subtle);
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .card-title {
    margin: 0;
    font-size: 18px;
    font-weight: 700;
    letter-spacing: -0.01em;
  }

  .badges {
    display: flex;
    gap: 8px;
  }

  .status-badge {
    font-size: 9px;
    padding: 2px 8px;
    border-radius: 5px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .status-badge.active { 
    background: rgba(20, 184, 166, 0.1); 
    color: var(--color-primary); 
    border: 1px solid rgba(20, 184, 166, 0.2);
  }
  .status-badge.success { 
    background: rgba(16, 185, 129, 0.1); 
    color: #10b981; 
    border: 1px solid rgba(16, 185, 129, 0.2);
  }
  .status-badge.warning { 
    background: rgba(245, 158, 11, 0.1); 
    color: #f59e0b; 
    border: 1px solid rgba(245, 158, 11, 0.2);
  }

  .btn-ghost, .btn-ghost-small, .btn-danger-ghost {
    padding: 10px 18px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid var(--border-subtle);
    color: var(--text-primary);
    border-radius: 10px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn-ghost-small {
    padding: 6px 12px;
    font-size: 11px;
    border-radius: 6px;
  }

  .btn-ghost:hover, .btn-ghost-small:hover {
    background: rgba(255, 255, 255, 0.08);
    border-color: rgba(255, 255, 255, 0.2);
  }

  .btn-ghost.accent {
    color: var(--color-primary);
    border-color: rgba(20, 184, 166, 0.3);
  }

  .btn-danger-ghost {
    color: #ef4444;
    border-color: rgba(239, 68, 68, 0.2);
  }

  .btn-primary {
    padding: 10px 24px;
    background: var(--color-primary);
    color: #000;
    border: none;
    border-radius: 10px;
    font-weight: 700;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn-primary:hover:not(:disabled) {
    filter: brightness(1.1);
    transform: translateY(-1px);
  }

  .plex-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    background: #e5a00d; /* Plex Gold */
    color: #000;
  }

  .loading-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    padding: 40px;
    color: var(--text-muted);
  }

  .spinner {
    width: 28px;
    height: 28px;
    border: 3px solid rgba(255, 255, 255, 0.05);
    border-top-color: var(--color-primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin { to { transform: rotate(360deg); } }

  .settings-section {
    margin-top: 8px;
  }

  .form-grid {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .form-field {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .field-label {
    font-size: 12px;
    font-weight: 700;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .input-field {
    width: 100%;
    padding: 12px 16px;
    background: var(--bg-input, #0b0f1a);
    border: 1px solid var(--border-subtle);
    border-radius: 10px;
    color: var(--text-primary);
    font-size: 14px;
    transition: all 0.2s;
  }

  .input-field:focus {
    outline: none;
    border-color: var(--color-primary);
    box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.1);
  }

  .helper-text {
    font-size: 11px;
    color: var(--text-muted);
    font-style: italic;
  }

  .path-mappings {
    padding: 20px 0;
    border-top: 1px solid rgba(255,255,255,0.05);
  }

  .mapping-header {
    margin-bottom: 12px;
  }

  .actions-row {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    align-items: center;
    margin-top: 8px;
  }

  .auth-box {
    margin-left: auto;
  }

  @media (max-width: 600px) {
    .auth-box { margin-left: 0; width: 100%; }
    .auth-box button { width: 100%; }
  }
</style>





