<script>
  import { onMount } from 'svelte';
  import apiClient from '../api/client';
  import { feedback } from '../stores/feedback';

  let baseUrl = '';
  let serverName = '';
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
      await apiClient.post('/plex/activate');
      feedback.addToast('Plex activated as media server', 'success');
      await loadSettings(); // Reload to get updated is_active
    } catch (error) {
      console.error('Failed to activate server:', error);
      feedback.addToast('Failed to activate server', 'error');
    } finally {
      activating = false;
    }
  }

  async function loadSettings() {
    try {
      const response = await apiClient.get('/plex/settings');
      if (response.data?.settings) {
        baseUrl = response.data.settings.base_url || '';
        serverName = response.data.settings.server_name || '';
        hasToken = response.data.settings.has_token || false;
        connected = response.data.settings.connected || false;
        isActive = response.data.settings.is_active || false;
      }
    } catch (error) {
      console.error('Failed to load Plex settings:', error);
      feedback.addToast('Failed to load Plex settings', 'error');
    }
  }

  async function saveSettings() {
    if (!baseUrl.trim()) {
      feedback.addToast('Server URL is required', 'error');
      return;
    }

    try {
      saving = true;
      await apiClient.post('/plex/settings', {
        base_url: baseUrl,
        server_name: serverName
      });
      feedback.addToast('Plex settings saved', 'success');
      await loadSettings();
    } catch (error) {
      console.error('Failed to save Plex settings:', error);
      feedback.addToast('Failed to save settings', 'error');
    } finally {
      saving = false;
    }
  }

  async function startOAuth() {
    try {
      authenticating = true;
      const response = await apiClient.post('/plex/auth/start');
      
      if (response.data?.oauth_url && response.data?.session_id) {
        oauthSession = response.data.session_id;
        
        // Open Plex OAuth page in new window
        window.open(response.data.oauth_url, 'PlexOAuth', 'width=600,height=700');
        
        // Start polling for completion
        pollInterval = setInterval(async () => {
          try {
            const pollResp = await apiClient.get(`/plex/auth/poll/${oauthSession}`);
            if (pollResp.data?.completed && pollResp.data?.token) {
              // OAuth completed - save token
              clearInterval(pollInterval);
              pollInterval = null;
              
              await apiClient.post('/plex/settings', {
                token: pollResp.data.token
              });
              
              feedback.addToast('Plex authentication successful', 'success');
              authenticating = false;
              oauthSession = null;
              await loadSettings();
            }
          } catch (pollError) {
            console.error('OAuth poll error:', pollError);
          }
        }, 2000); // Poll every 2 seconds
        
        // Stop polling after 10 minutes
        setTimeout(() => {
          if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
            authenticating = false;
            oauthSession = null;
            feedback.addToast('OAuth timeout - please try again', 'error');
          }
        }, 600000);
      }
    } catch (error) {
      console.error('Failed to start Plex OAuth:', error);
      feedback.addToast('Failed to start authentication', 'error');
      authenticating = false;
    }
  }

  async function cancelOAuth() {
    if (oauthSession && pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
      
      try {
        await apiClient.delete(`/plex/auth/cancel/${oauthSession}`);
      } catch (error) {
        console.error('Failed to cancel OAuth:', error);
      }
      
      oauthSession = null;
      authenticating = false;
      feedback.addToast('Authentication cancelled', 'info');
    }
  }

  async function testConnection() {
    try {
      testing = true;
      const response = await apiClient.post('/plex/test-connection');
      
      if (response.data?.connected) {
        feedback.addToast(`Connected to ${response.data.server_name}`, 'success');
        await loadSettings();
      }
    } catch (error) {
      console.error('Connection test failed:', error);
      const msg = error?.response?.data?.error || 'Connection failed';
      feedback.addToast(msg, 'error');
    } finally {
      testing = false;
    }
  }
</script>

<section class="plex-card card">
  <div class="card-header">
    <div class="header-left">
      <h2>Plex</h2>
      {#if isActive}
        <span class="status-badge active-server">● Active</span>
      {/if}
      {#if hasToken}
        <span class="status-badge authenticated">✓ Authenticated</span>
      {/if}
      {#if connected}
        <span class="status-badge connected">● Connected</span>
      {:else if hasToken}
        <span class="status-badge disconnected">⚠ Disconnected</span>
      {/if}
    </div>
    <button class="btn-secondary" on:click={() => collapsed = !collapsed}>
      {collapsed ? 'Expand' : 'Collapse'}
    </button>
  </div>

  {#if loading}
    <div class="loading">Loading...</div>
  {:else if !collapsed}
    <div class="section">
      <h3>Server Configuration</h3>
      
      <div class="form-group">
        <label>
          <span class="label-text">Server URL</span>
          <input
            type="text"
            bind:value={baseUrl}
            placeholder="http://192.168.1.100:32400"
            class="input"
          />
          <span class="help-text">Enter your Plex server IP address or URL (include port, typically :32400)</span>
        </label>

        <label>
          <span class="label-text">Server Name (Optional)</span>
          <input
            type="text"
            bind:value={serverName}
            placeholder="My Plex Server"
            class="input"
          />
          <span class="help-text">Preferred server if you have multiple</span>
        </label>

        <div class="button-group">
          <button
            class="btn-primary"
            on:click={saveSettings}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
          
          {#if hasToken}
            <button
              class="btn-secondary"
              on:click={testConnection}
              disabled={testing}
            >
              {testing ? 'Testing...' : 'Test Connection'}
            </button>
          {/if}

          {#if !isActive}
            <button
              class="btn-secondary"
              on:click={activateServer}
              disabled={activating}
            >
              {activating ? 'Activating...' : 'Activate Server'}
            </button>
          {/if}

          {#if authenticating}
            <button class="btn-secondary" on:click={cancelOAuth} disabled>
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
  .plex-card {
    padding: 20px;
    margin-bottom: 16px;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border-color, rgba(255,255,255,0.1));
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .card-header h2 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
  }

  .provider-badge {
    font-size: 12px;
    padding: 4px 8px;
    border-radius: 4px;
    background: rgba(229, 160, 13, 0.2);
    color: #e5a00d;
  }

  .status-badge {
    font-size: 12px;
    padding: 4px 8px;
    border-radius: 4px;
  }

  .status-badge.connected {
    background: rgba(0, 230, 118, 0.2);
    color: #00e676;
  }

  .status-badge.disconnected {
    background: rgba(255, 152, 0, 0.2);
    color: #ff9800;
  }

  .status-badge.authenticated {
    background: rgba(0, 230, 118, 0.2);
    color: #00e676;
  }

  .status-badge.active-server {
    background: rgba(59, 130, 246, 0.2);
    color: #3b82f6;
    font-weight: 600;
  }

  .section {
    margin-bottom: 24px;
  }

  .section h3 {
    margin: 0 0 16px 0;
    font-size: 16px;
    font-weight: 600;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  label {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .label-text {
    font-size: 13px;
    font-weight: 500;
    color: var(--text-primary);
  }

  .help-text {
    font-size: 12px;
    color: var(--muted);
  }

  .input {
    padding: 10px 12px;
    border-radius: 6px;
    border: 1px solid var(--border-color, rgba(255,255,255,0.1));
    background: var(--input-bg, rgba(0,0,0,0.2));
    color: var(--text-primary);
    font-size: 14px;
  }

  .input:focus {
    outline: none;
    border-color: var(--primary, #00e676);
  }

  .button-group {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }

  .btn-primary, .btn-secondary, .btn-link {
    padding: 10px 20px;
    border-radius: 6px;
    border: none;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn-primary {
    background: var(--primary, #00e676);
    color: #000;
  }

  .btn-primary:hover:not(:disabled) {
    background: var(--primary-hover, #00d368);
  }

  .btn-secondary {
    background: transparent;
    color: var(--text-primary);
    border: 1px solid var(--border-color, rgba(255,255,255,0.2));
  }

  .btn-secondary:hover:not(:disabled) {
    background: rgba(255,255,255,0.05);
  }

  .btn-link {
    background: transparent;
    color: var(--primary, #00e676);
    padding: 8px 12px;
  }

  .btn-link:hover:not(:disabled) {
    text-decoration: underline;
  }

  .btn-primary:disabled, .btn-secondary:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .auth-status {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
  }

  .auth-status p {
    margin: 0;
  }

  .loading {
    padding: 20px;
    text-align: center;
    color: var(--muted);
  }

  .spinner {
    width: 20px;
    height: 20px;
    border: 2px solid rgba(255,255,255,0.1);
    border-top-color: var(--primary, #00e676);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }
</style>
