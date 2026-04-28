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
      const data = await response.json();
      isActive = data.active_client === 'slskd';
    } catch (error) {
      console.error('Failed to check active status:', error);
    }
  }

  async function activateClient() {
    try {
      await fetch(`${apiBase}/providers/download-clients/activate`, { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({ client: 'slskd' }) 
      });
      isActive = true;
    } catch (error) {
      console.error('Failed to activate client:', error);
    }
  }

  async function loadSettings() {
    try {
      const response = await fetch(`${apiBase}/providers/soulseek/settings`);
      const data = await response.json();
      if (data) {
        slskdUrl = data.slskd_url || '';
        serverName = data.server_name || '';
        apiKey = data.api_key || '';
        hasApiKeyInDb = data.has_api_key || false;
        connected = data.configured || false;
      }
    } catch (error) {
      console.error('Failed to load slskd settings:', error);
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
      
      if (apiKey && apiKey !== '****') {
        payload.api_key = apiKey;
      }
      
      await fetch(`${apiBase}/providers/soulseek/settings`, { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify(payload) 
      });
      await loadSettings();
    } catch (error) {
      console.error('Failed to save slskd settings:', error);
    } finally {
      saving = false;
    }
  }

  async function testConnection() {
    if (!slskdUrl.trim()) return;

    try {
      testing = true;
      const response = await fetch(`${apiBase}/providers/soulseek/connection/test`, { method: 'POST' });
      const data = await response.json();
      
      if (data?.success) {
        connected = true;
        await loadSettings();
      } else {
        connected = false;
      }
    } catch (error) {
      console.error('Failed to test slskd connection:', error);
      connected = false;
    } finally {
      testing = false;
    }
  }

  async function toggleApiKeyVisibility() {
    const willShow = !showApiKey;
    showApiKey = willShow;

    if (willShow && hasApiKeyInDb && apiKey === '****' && !dbApiKeyRevealed) {
      try {
        const resp = await fetch(`${apiBase}/providers/soulseek/settings/key`);
        const data = await resp.json();
        if (data && data.api_key) {
          apiKey = data.api_key;
          dbApiKeyRevealed = true;
        } else {
          showApiKey = false;
        }
      } catch (err) {
        showApiKey = false;
      }
    }

    if (!willShow && dbApiKeyRevealed) {
      apiKey = '****';
      dbApiKeyRevealed = false;
    }
  }
</script>

<section class="plugin-card">
  <div class="card-header">
    <div class="header-left">
      <h2 class="card-title">Slskd</h2>
      <div class="badges">
        <span class="type-badge">Download Client</span>
        {#if connected}
          <span class="status-badge success">● Connected</span>
        {:else if slskdUrl}
          <span class="status-badge warning">⚠ Disconnected</span>
        {/if}
        {#if isActive}
          <span class="status-badge active">● Active</span>
        {/if}
      </div>
    </div>
    <div class="header-right">
      {#if !isActive && connected}
        <button class="btn-ghost small" on:click={activateClient}>Activate</button>
      {/if}
      <button class="btn-ghost" on:click={() => collapsed = !collapsed}>
        {collapsed ? 'Expand' : 'Collapse'}
      </button>
    </div>
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
            bind:value={slskdUrl}
            placeholder="http://192.168.1.100:5030"
            class="input-field"
          />
          <span class="helper-text">Enter your slskd server address (include port, default :5030)</span>
        </label>

        <label class="form-field">
          <span class="field-label">Server Name (Optional)</span>
          <input
            type="text"
            bind:value={serverName}
            placeholder="My slskd Server"
            class="input-field"
          />
        </label>

        <label class="form-field">
          <span class="field-label">API Key</span>
          <div class="password-wrapper">
            <input
              type={showApiKey ? 'text' : 'password'}
              bind:value={apiKey}
              placeholder="Enter API key"
              class="input-field"
            />
            <button 
              type="button" 
              class="toggle-visibility"
              on:click={toggleApiKeyVisibility}
            >
              {showApiKey ? '🙈' : '👁️'}
            </button>
          </div>
          <span class="helper-text">API key from slskd settings (Options → Security → API Keys)</span>
        </label>

        <div class="actions-row">
          <button
            class="btn-primary"
            on:click={saveSettings}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
          
          {#if slskdUrl && (hasApiKeyInDb || apiKey)}
            <button
              class="btn-ghost"
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

  .type-badge {
    font-size: 10px;
    padding: 2px 8px;
    background: rgba(186, 100, 21, 0.15);
    color: #ba6415;
    border-radius: 4px;
    font-weight: 700;
    text-transform: uppercase;
  }

  .status-badge {
    font-size: 10px;
    padding: 2px 8px;
    border-radius: 4px;
    font-weight: 700;
  }

  .status-badge.success { background: rgba(34, 197, 94, 0.15); color: #22c55e; }
  .status-badge.warning { background: rgba(234, 179, 8, 0.15); color: #eab308; }
  .status-badge.active { background: rgba(20, 184, 166, 0.15); color: var(--color-primary, #14b8a6); }

  .header-right {
    display: flex;
    gap: 8px;
  }

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

  .btn-ghost.small {
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 700;
    background: var(--color-primary, #14b8a6);
    color: #000;
    border: none;
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

  .actions-row {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    margin-top: 8px;
  }
</style>
