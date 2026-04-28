<svelte:options customElement={{
  tag: 'jellyfin-dashboard-card',
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
      await fetch(`${apiBase}/jellyfin/activate`, { method: 'POST' });
      await loadSettings();
    } catch (error) {
      console.error('Failed to activate server:', error);
    } finally {
      activating = false;
    }
  }

  async function loadSettings() {
    try {
      const response = await fetch(`${apiBase}/jellyfin/settings`);
      const data = await response.json();
      if (data?.settings) {
        baseUrl = data.settings.base_url || '';
        username = data.settings.username || '';
        pathMappings = data.settings.path_mappings || [];
        hasPassword = data.settings.has_password || false;
        connected = data.settings.connected || false;
        isActive = data.settings.is_active || false;
        password = ''; 
      }
    } catch (error) {
      console.error('Failed to load Jellyfin settings:', error);
    }
  }

  async function saveSettings() {
    if (!baseUrl.trim()) {
      console.error('Server URL is required');
      return;
    }

    if (!username.trim() || (!hasPassword && !password.trim())) {
      console.error('Username and password are required');
      return;
    }

    try {
      saving = true;
      await fetch(`${apiBase}/jellyfin/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          base_url: baseUrl,
          username: username,
          password: password,
          path_mappings: pathMappings
        })
      });
      await loadSettings();
    } catch (error) {
      console.error('Failed to save Jellyfin settings:', error);
    } finally {
      saving = false;
    }
  }

  async function testConnection() {
    try {
      testing = true;
      const response = await fetch(`${apiBase}/jellyfin/test-connection`, { method: 'POST' });
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
      <h2 class="card-title">Jellyfin</h2>
      <div class="badges">
        {#if isActive}
          <span class="status-badge active">● Active</span>
        {/if}
        {#if hasPassword}
          <span class="status-badge success">✓ Authenticated</span>
        {/if}
        {#if connected}
          <span class="status-badge success">● Connected</span>
        {:else if hasPassword}
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
            placeholder="http://192.168.1.100:8096"
            class="input-field"
          />
          <span class="helper-text">Enter your Jellyfin server URL (include port, typically :8096)</span>
        </label>

        <label class="form-field">
          <span class="field-label">Username</span>
          <input
            type="text"
            bind:value={username}
            placeholder="Enter username"
            class="input-field"
          />
        </label>

        <label class="form-field">
          <span class="field-label">Password</span>
          <div class="password-wrapper">
            <input
              type={showPassword ? 'text' : 'password'}
              bind:value={password}
              placeholder={hasPassword ? '••••••••' : 'Enter password'}
              class="input-field"
            />
            <button
              type="button"
              class="toggle-visibility"
              on:click={() => showPassword = !showPassword}
            >
              {showPassword ? '🙈' : '👁️'}
            </button>
          </div>
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

          {#if hasPassword}
            <button
              class="btn-ghost"
              on:click={testConnection}
              disabled={testing}
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

  .password-wrapper {
    position: relative;
    display: flex;
    align-items: center;
  }

  .toggle-visibility {
    position: absolute;
    right: 12px;
    background: none;
    border: none;
    cursor: pointer;
    opacity: 0.6;
    color: #fff;
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
