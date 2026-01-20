<script>
  import { onMount } from 'svelte';
  import apiClient from '../api/client';
  import { feedback } from '../stores/feedback';

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
      const response = await apiClient.get('/providers/download-clients/active');
      isActive = response.data.active_client === 'slskd';
    } catch (error) {
      console.error('Failed to check active status:', error);
    }
  }

  async function activateClient() {
    try {
      await apiClient.post('/providers/download-clients/activate', { client: 'slskd' });
      isActive = true;
      feedback.addToast('Slskd activated as download client', 'success');
    } catch (error) {
      console.error('Failed to activate client:', error);
      feedback.addToast('Failed to activate client', 'error');
    }
  }

  async function loadSettings() {
    try {
      const response = await apiClient.get('/providers/soulseek/settings');
      if (response.data) {
        slskdUrl = response.data.slskd_url || '';
        serverName = response.data.server_name || '';
        apiKey = response.data.api_key || '';
        hasApiKeyInDb = response.data.has_api_key || false;
        connected = response.data.configured || false;
      }
    } catch (error) {
      console.error('Failed to load slskd settings:', error);
      feedback.addToast('Failed to load slskd settings', 'error');
    }
  }

  async function saveSettings() {
    if (!slskdUrl.trim()) {
      feedback.addToast('Server URL is required', 'error');
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
      
      await apiClient.post('/providers/soulseek/settings', payload);
      feedback.addToast('slskd settings saved', 'success');
      await loadSettings();
    } catch (error) {
      console.error('Failed to save slskd settings:', error);
      feedback.addToast('Failed to save settings', 'error');
    } finally {
      saving = false;
    }
  }

  async function testConnection() {
    if (!slskdUrl.trim()) {
      feedback.addToast('Server URL is required', 'error');
      return;
    }

    if (!hasApiKeyInDb && !apiKey.trim()) {
      feedback.addToast('API Key is required', 'error');
      return;
    }

    try {
      testing = true;
      const response = await apiClient.post('/providers/soulseek/connection/test');
      
      if (response.data?.success) {
        feedback.addToast('slskd connection successful!', 'success');
        connected = true;
      } else {
        feedback.addToast(response.data?.error || 'Connection failed', 'error');
        connected = false;
      }
    } catch (error) {
      console.error('Failed to test slskd connection:', error);
      feedback.addToast('Connection test failed', 'error');
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
        const resp = await apiClient.get('/providers/soulseek/settings/key');
        if (resp.data && resp.data.api_key) {
          apiKey = resp.data.api_key;
          dbApiKeyRevealed = true;
        } else {
          feedback.addToast('Failed to reveal API key', 'error');
          // revert UI
          showApiKey = false;
        }
      } catch (err) {
        console.error('Failed to fetch API key:', err);
        feedback.addToast('Unable to reveal API key', 'error');
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

<section class="slskd-card card">
  <div class="card-header">
    <div class="header-left">
      <h2>slskd</h2>
      <span class="provider-badge">Download Client</span>
      {#if connected}
        <span class="status-badge connected">● Connected</span>
      {:else if slskdUrl}
        <span class="status-badge disconnected">⚠ Disconnected</span>
      {/if}
      {#if isActive}
        <span class="status-badge active-client">● Active</span>
      {/if}
    </div>
    <div class="header-right">
      {#if !isActive && connected}
        <button class="btn-sm btn-secondary" on:click={activateClient}>Activate</button>
      {/if}
      <button class="btn-link" on:click={() => collapsed = !collapsed}>
        {collapsed ? 'Expand' : 'Collapse'}
      </button>
    </div>
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
            bind:value={slskdUrl}
            placeholder="http://192.168.1.100:5030"
            class="input"
          />
          <span class="help-text">Enter your slskd server address (include port, default :5030)</span>
        </label>

        <label>
          <span class="label-text">Server Name (Optional)</span>
          <input
            type="text"
            bind:value={serverName}
            placeholder="My slskd Server"
            class="input"
          />
          <span class="help-text">Friendly name for this server</span>
        </label>

        <label>
          <span class="label-text">API Key</span>
          <div class="input-with-toggle">
            <input
              type={showApiKey ? 'text' : 'password'}
              bind:value={apiKey}
              placeholder="Enter API key"
              class="input"
            />
            <button 
              type="button" 
              class="toggle-btn"
              on:click={toggleApiKeyVisibility}
              title={showApiKey ? 'Hide' : 'Show'}
            >
              {showApiKey ? '👁️' : '👁️‍🗨️'}
            </button>
          </div>
          <span class="help-text">API key from slskd settings (Options → Security → API Keys)</span>
        </label>

        <div class="button-group">
          <button
            class="btn-primary"
            on:click={saveSettings}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
          
          {#if slskdUrl && (hasApiKeyInDb || apiKey)}
            <button
              class="btn-secondary"
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

<style>
  .slskd-card {
    background: var(--bg-card, #14181f);
    border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 20px;
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

  .header-right {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .card-header h2 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
    color: var(--text-main, #ffffff);
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
    background: rgba(255, 82, 82, 0.2);
    color: #ff5252;
  }

  .status-badge.active-client {
    background: rgba(0, 230, 118, 0.2);
    color: #00e676;
    border: 1px solid rgba(0, 230, 118, 0.3);
  }

  .loading {
    padding: 20px;
    text-align: center;
    color: var(--text-muted, #8b9bb4);
  }

  .section {
    margin-bottom: 24px;
  }

  .section h3 {
    font-size: 16px;
    font-weight: 600;
    margin: 0 0 16px 0;
    color: var(--text-main, #ffffff);
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
    font-size: 14px;
    font-weight: 500;
    color: var(--text-primary, #ffffff);
  }

  .help-text {
    font-size: 12px;
    color: var(--text-muted, #8b9bb4);
  }

  .input {
    padding: 10px 12px;
    border-radius: 6px;
    border: 1px solid var(--border-color, rgba(255,255,255,0.1));
    background: var(--bg-input, #0a0c10);
    color: var(--text-primary, #ffffff);
    font-size: 14px;
  }

  .input:focus {
    outline: none;
    border-color: var(--color-primary, #00fa9a);
  }

  .input-with-toggle {
    position: relative;
    display: flex;
    align-items: center;
  }

  .input-with-toggle input {
    flex: 1;
    padding-right: 40px;
  }

  .toggle-btn {
    position: absolute;
    right: 8px;
    background: transparent;
    border: none;
    cursor: pointer;
    font-size: 18px;
    padding: 4px 8px;
    color: var(--text-muted, #8b9bb4);
    transition: color 0.2s;
  }

  .toggle-btn:hover {
    color: var(--text-primary, #ffffff);
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
    background: var(--color-primary, #00fa9a);
    color: #000;
  }

  .btn-primary:hover:not(:disabled) {
    background: var(--color-primary-hover, #00e08a);
  }

  .btn-primary:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn-secondary {
    background: rgba(255, 255, 255, 0.1);
    color: var(--text-primary, #ffffff);
    border: 1px solid rgba(255, 255, 255, 0.2);
  }

  .btn-secondary:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.15);
  }

  .btn-secondary:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn-link {
    background: transparent;
    color: var(--color-primary, #00fa9a);
    padding: 6px 12px;
  }

  .btn-link:hover {
    text-decoration: underline;
  }
</style>
