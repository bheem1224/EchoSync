<svelte:options customElement="jellyfin-dashboard-card" />

<script>
  export let apiBase = "";
  import { onMount } from "svelte";

  let baseUrl = "";
  let username = "";
  let password = "";
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
      await fetch(`${apiBase}/activate`, { method: "POST" });
      await loadSettings();
    } catch (error) {
      console.error("Failed to activate server:", error);
    } finally {
      activating = false;
    }
  }

  async function loadSettings() {
    try {
      const response = await fetch(`${apiBase}/settings`);
      const data = await response.json();
      if (data?.settings) {
        baseUrl = data.settings.base_url || "";
        username = data.settings.username || "";
        hasPassword = data.settings.has_password || false;
        connected = data.settings.connected || false;
        isActive = data.settings.is_active || false;
        password = "";
      }
    } catch (error) {
      console.error("Failed to load Jellyfin settings:", error);
    }
  }

  async function saveSettings() {
    if (!baseUrl.trim()) {
      console.error("Server URL is required");
      return;
    }

    if (!username.trim() || (!hasPassword && !password.trim())) {
      console.error("Username and password are required");
      return;
    }

    try {
      saving = true;
      await fetch(`${apiBase}/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          base_url: baseUrl,
          username: username,
          password: password,
        }),
      });
      await loadSettings();
    } catch (error) {
      console.error("Failed to save Jellyfin settings:", error);
    } finally {
      saving = false;
    }
  }

  async function testConnection() {
    try {
      testing = true;
      const response = await fetch(`${apiBase}/test-connection`, {
        method: "POST",
      });
      const data = await response.json();
      if (data?.connected) {
        await loadSettings();
      }
    } catch (error) {
      console.error("Connection test failed:", error);
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
    <button class="btn-ghost" on:click={() => (collapsed = !collapsed)}>
      {collapsed ? "Expand" : "Collapse"}
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
          <span class="helper-text"
            >Enter your Jellyfin server URL (include port, typically :8096)</span
          >
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
              type={showPassword ? "text" : "password"}
              bind:value={password}
              placeholder={hasPassword ? "••••••••" : "Enter password"}
              class="input-field"
            />
            <button
              type="button"
              class="toggle-visibility"
              on:click={() => (showPassword = !showPassword)}
            >
              {showPassword ? "🙈" : "👁️"}
            </button>
          </div>
        </label>

        <div class="actions-row">
          <button class="btn-primary" on:click={saveSettings} disabled={saving}>
            {saving ? "Saving..." : "Save Settings"}
          </button>

          {#if hasPassword}
            <button
              class="btn-ghost"
              on:click={testConnection}
              disabled={testing}
            >
              {testing ? "Testing..." : "Test Connection"}
            </button>
          {/if}

          {#if !isActive}
            <button
              class="btn-ghost"
              on:click={activateServer}
              disabled={activating}
            >
              {activating ? "Activating..." : "Activate Server"}
            </button>
          {/if}
        </div>
      </div>
    </div>
  {/if}
</section>

<style>
  .plugin-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius, 16px);
    padding: 28px;
    color: var(--text-primary);
    font-family: "Inter", sans-serif;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.2);
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 28px;
    padding-bottom: 20px;
    border-bottom: 1px solid var(--border-subtle);
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .card-title {
    margin: 0;
    font-size: 22px;
    font-weight: 800;
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, #fff 0%, #a5b4fc 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  .badges {
    display: flex;
    gap: 8px;
  }

  .status-badge {
    font-size: 10px;
    padding: 3px 10px;
    border-radius: 6px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.03em;
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

  .btn-ghost {
    padding: 10px 18px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--border-subtle);
    color: var(--text-primary);
    border-radius: 10px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .btn-ghost:hover {
    background: rgba(255, 255, 255, 0.1);
    border-color: rgba(255, 255, 255, 0.2);
    transform: translateY(-1px);
  }

  .btn-primary {
    padding: 12px 28px;
    background: var(--color-primary);
    color: #000;
    border: none;
    border-radius: 12px;
    font-weight: 700;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 4px 12px rgba(20, 184, 166, 0.2);
  }

  .btn-primary:hover:not(:disabled) {
    filter: brightness(1.1);
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(20, 184, 166, 0.3);
  }

  .btn-primary:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .loading-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 20px;
    padding: 60px;
    color: var(--text-muted);
  }

  .settings-section {
    margin-top: 24px;
  }

  .section-title {
    margin: 0 0 20px 0;
    font-size: 14px;
    font-weight: 700;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .form-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 20px;
  }

  @media (min-width: 640px) {
    .form-grid {
      grid-template-columns: 1fr 1fr;
    }
  }

  .form-field {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .field-label {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-secondary);
    opacity: 0.8;
  }

  .input-field {
    width: 100%;
    padding: 14px 18px;
    background: var(--bg-input, #0f172a);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    color: var(--text-primary);
    font-size: 14px;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  }

  .input-field:focus {
    outline: none;
    border-color: var(--color-primary);
    box-shadow: 0 0 0 4px rgba(20, 184, 166, 0.15);
    background: rgba(255, 255, 255, 0.03);
  }

  .password-wrapper {
    position: relative;
    display: flex;
    align-items: center;
  }

  .toggle-visibility {
    position: absolute;
    right: 14px;
    background: none;
    border: none;
    cursor: pointer;
    opacity: 0.6;
    color: var(--text-primary);
    font-size: 18px;
    padding: 0;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .toggle-visibility:hover {
    opacity: 1;
  }

  .helper-text {
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 6px;
    font-style: italic;
  }

  .actions-row {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    margin-top: 12px;
  }
</style>
