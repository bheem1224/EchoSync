<script>
  import { onMount } from 'svelte';
  import apiClient from '../api/client';
  import { feedback } from '../stores/feedback';
  import PathMappingEditor from '../lib/components/PathMappingEditor.svelte';

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
      await apiClient.post('/providers/navidrome/activate');
      feedback.addToast('Navidrome activated as media server', 'success');
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
      const response = await apiClient.get('/providers/navidrome/settings');
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
      feedback.addToast('Failed to load Navidrome settings', 'error');
    }
  }

  async function saveSettings() {
    if (!baseUrl.trim()) {
      feedback.addToast('Server URL is required', 'error');
      return;
    }

    if (!username.trim() || !password.trim()) {
      feedback.addToast('Username and password are required', 'error');
      return;
    }

    try {
      saving = true;
      await apiClient.post('/providers/navidrome/settings', {
        base_url: baseUrl,
        username: username,
        password: password,
        path_mappings: pathMappings
      });
      feedback.addToast('Navidrome settings saved', 'success');
      await loadSettings();
    } catch (error) {
      console.error('Failed to save Navidrome settings:', error);
      feedback.addToast('Failed to save settings', 'error');
    } finally {
      saving = false;
    }
  }

  async function testConnection() {
    try {
      testing = true;
      const response = await apiClient.post('/providers/navidrome/test-connection');
      
      if (response.data?.connected) {
        feedback.addToast(`Connected to Navidrome ${response.data.version}`, 'success');
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

<section class="navidrome-card card">
  <div class="card-header">
    <div class="header-left">
      <h2>Navidrome</h2>
      {#if isActive}
        <span class="status-badge active-server">● Active</span>
      {/if}
      {#if hasPassword}
        <span class="status-badge authenticated">✓ Authenticated</span>
      {/if}
      {#if connected}
        <span class="status-badge connected">● Connected</span>
      {:else if hasPassword}
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
            placeholder="http://192.168.1.100:4533"
            class="input"
          />
          <span class="help-text">Enter your Navidrome server URL (include port, typically :4533)</span>
        </label>

        <label>
          <span class="label-text">Username</span>
          <input
            type="text"
            bind:value={username}
            placeholder="Enter username"
            class="input"
          />
        </label>

        <label>
          <span class="label-text">Password</span>
          <div class="password-field">
            <input
              type={showPassword ? 'text' : 'password'}
              bind:value={password}
              placeholder={hasPassword ? 'Enter new password' : 'Enter password'}
              class="input"
            />
            <button 
              type="button" 
              class="password-toggle" 
              on:click={() => showPassword = !showPassword}
              title={showPassword ? 'Hide' : 'Show'}
            >
              {showPassword ? '👁️' : '👁️‍🗨️'}
            </button>
          </div>
        </label>

        <div class="border-t border-gray-700 my-4 pt-4">
            <PathMappingEditor bind:mappings={pathMappings} />
        </div>

        <div class="button-group">
          <button
            class="btn-primary"
            on:click={saveSettings}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
          
          {#if hasPassword}
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
        </div>
      </div>
    </div>
  {/if}
</section>

<style>
  .navidrome-card {
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
    background: rgba(33, 150, 243, 0.2);
    color: #2196f3;
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

  .password-field {
    position: relative;
    display: flex;
    align-items: center;
  }

  .password-field .input {
    flex: 1;
    padding-right: 45px;
  }

  .password-toggle {
    position: absolute;
    right: 8px;
    background: transparent;
    border: none;
    cursor: pointer;
    font-size: 18px;
    padding: 4px 8px;
    opacity: 0.6;
    transition: opacity 0.2s;
  }

  .password-toggle:hover {
    opacity: 1;
  }

  .button-group {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }

  .btn-primary, .btn-secondary {
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

  .btn-primary:disabled, .btn-secondary:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .loading {
    padding: 20px;
    text-align: center;
    color: var(--muted);
  }
</style>
