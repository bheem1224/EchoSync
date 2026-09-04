<svelte:options customElement="slskd-dashboard-card" />

<script>
  export let apiBase = "";
  import { onMount } from "svelte";

  let slskdUrl = "";
  let apiKey = "";
  let serverName = "";
  let connected = false;
  let loading = true;
  let saving = false;
  let testing = false;
  let collapsed = false;
  let showApiKey = false;
  let hasApiKeyInDb = false;
  let dbApiKeyRevealed = false;
  let isActive = false;

  let webhookEndpoint = null;
  let webhookLoading = false;
  let webhookTesting = false;
  let webhookTestResult = null;
  let copiedYaml = false;
  let copiedUrl = false;

  onMount(async () => {
    await loadSettings();
    await checkActiveStatus();
    await loadWebhookInfo();
    loading = false;
  });

  async function loadWebhookInfo() {
    try {
      webhookLoading = true;
      const resp = await fetch(`${apiBase}/webhooks/info`);
      const data = await resp.json();
      if (data && data.endpoint) {
        webhookEndpoint = data.endpoint;
      }
    } catch (err) {
      console.error("Failed to load webhook info:", err);
    } finally {
      webhookLoading = false;
    }
  }

  async function testWebhookPing() {
    try {
      webhookTesting = true;
      webhookTestResult = null;
      const resp = await fetch(`${apiBase}/webhooks/test`, { method: "POST" });
      const data = await resp.json();
      if (resp.ok && data.success) {
        webhookTestResult = {
          success: true,
          message:
            "Ping successful! Webhook gateway received and dispatched event.",
        };
      } else {
        webhookTestResult = {
          success: false,
          message: data.detail || "Ping failed.",
        };
      }
    } catch (err) {
      webhookTestResult = {
        success: false,
        message: `Ping failed: ${err.message}`,
      };
    } finally {
      webhookTesting = false;
    }
  }

  async function checkActiveStatus() {
    try {
      const response = await fetch(`${apiBase}/download-clients/active`);
      const data = await response.json();
      isActive = data.active_client === "slskd";
    } catch (error) {
      console.error("Failed to check active status:", error);
    }
  }

  async function activateClient() {
    try {
      await fetch(`${apiBase}/download-clients/activate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client: "slskd" }),
      });
      isActive = true;
    } catch (error) {
      console.error("Failed to activate client:", error);
    }
  }

  async function loadSettings() {
    try {
      const response = await fetch(`${apiBase}/settings`);
      const data = await response.json();
      if (data) {
        slskdUrl = data.slskd_url || "";
        serverName = data.server_name || "";
        apiKey = data.api_key || "";
        hasApiKeyInDb = data.has_api_key || false;
        connected = data.configured || false;
      }
    } catch (error) {
      console.error("Failed to load slskd settings:", error);
    }
  }

  async function saveSettings() {
    if (!slskdUrl.trim()) {
      console.error("Server URL is required");
      return;
    }

    try {
      saving = true;
      const payload = {
        slskd_url: slskdUrl,
        server_name: serverName,
      };

      if (apiKey && apiKey !== "****") {
        payload.api_key = apiKey;
      }

      await fetch(`${apiBase}/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      await loadSettings();
    } catch (error) {
      console.error("Failed to save slskd settings:", error);
    } finally {
      saving = false;
    }
  }

  async function testConnection() {
    if (!slskdUrl.trim()) return;

    try {
      testing = true;
      const response = await fetch(`${apiBase}/connection/test`, {
        method: "POST",
      });
      const data = await response.json();

      if (data?.success) {
        connected = true;
        await loadSettings();
      } else {
        connected = false;
      }
    } catch (error) {
      console.error("Failed to test slskd connection:", error);
      connected = false;
    } finally {
      testing = false;
    }
  }

  async function toggleApiKeyVisibility() {
    const willShow = !showApiKey;
    showApiKey = willShow;

    if (willShow && hasApiKeyInDb && apiKey === "****" && !dbApiKeyRevealed) {
      try {
        const resp = await fetch(`${apiBase}/settings/key`);
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
      apiKey = "****";
      dbApiKeyRevealed = false;
    }
  }

  function copyToClipboard(text, type) {
    if (!navigator?.clipboard) return;
    navigator.clipboard.writeText(text).then(() => {
      if (type === "yaml") {
        copiedYaml = true;
        setTimeout(() => (copiedYaml = false), 2000);
      } else {
        copiedUrl = true;
        setTimeout(() => (copiedUrl = false), 2000);
      }
    });
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
        <button class="btn-ghost small" on:click={activateClient}
          >Activate</button
        >
      {/if}
      <button class="btn-ghost" on:click={() => (collapsed = !collapsed)}>
        {collapsed ? "Expand" : "Collapse"}
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
          <span class="helper-text"
            >Enter your slskd server address (include port, default :5030)</span
          >
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
              type={showApiKey ? "text" : "password"}
              bind:value={apiKey}
              placeholder="Enter API key"
              class="input-field"
            />
            <button
              type="button"
              class="toggle-visibility"
              on:click={toggleApiKeyVisibility}
            >
              {showApiKey ? "🙈" : "👁️"}
            </button>
          </div>
          <span class="helper-text"
            >API key from slskd settings (Options → Security → API Keys)</span
          >
        </label>

        <div class="actions-row">
          <button class="btn-primary" on:click={saveSettings} disabled={saving}>
            {saving ? "Saving..." : "Save Settings"}
          </button>

          {#if slskdUrl && (hasApiKeyInDb || apiKey)}
            <button
              class="btn-ghost"
              on:click={testConnection}
              disabled={testing}
            >
              {testing ? "Testing..." : "Test Connection"}
            </button>
          {/if}
        </div>
      </div>
    </div>

    <!-- Webhook & Automation Section -->
    <div class="settings-section webhook-section">
      <h3 class="section-title">Webhooks & Automation</h3>
      <p class="section-description">
        Configure slskd to immediately notify EchoSync upon download completion
        or failure. This enables real-time tag verification, automatic library
        admission, and immediate daemon transfer eviction.
      </p>

      {#if webhookEndpoint}
        <div class="webhook-details">
          <label class="form-field">
            <span class="field-label">Webhook Callback URL</span>
            <div class="copy-input-wrapper">
              <input
                type="text"
                readonly
                value={`${webhookEndpoint.url}${webhookEndpoint.secret ? "?secret=" + webhookEndpoint.secret : ""}`}
                class="input-field readonly"
              />
              <button
                type="button"
                class="btn-copy"
                on:click={() =>
                  copyToClipboard(
                    `${webhookEndpoint.url}${webhookEndpoint.secret ? "?secret=" + webhookEndpoint.secret : ""}`,
                    "url",
                  )}
              >
                {copiedUrl ? "Copied!" : "Copy"}
              </button>
            </div>
            <span class="helper-text"
              >Add this URL to your slskd configuration to enable real-time
              ingestion.</span
            >
          </label>

          <div class="yaml-block">
            <div class="yaml-header">
              <span>slskd.yml Integration Config</span>
              <button
                type="button"
                class="btn-ghost small"
                on:click={() =>
                  copyToClipboard(webhookEndpoint.yaml_template, "yaml")}
              >
                {copiedYaml ? "Copied!" : "Copy YAML"}
              </button>
            </div>
            <pre class="code-block"><code>{webhookEndpoint.yaml_template}</code
              ></pre>
          </div>

          <div class="actions-row">
            <button
              class="btn-ghost"
              on:click={testWebhookPing}
              disabled={webhookTesting}
            >
              {webhookTesting ? "Pinging Webhook..." : "Test Webhook Ingress"}
            </button>
            <button
              class="btn-ghost"
              on:click={loadWebhookInfo}
              disabled={webhookLoading}
            >
              Refresh Details
            </button>
          </div>

          {#if webhookTestResult}
            <div
              class="test-result-banner {webhookTestResult.success
                ? 'success'
                : 'error'}"
            >
              {webhookTestResult.message}
            </div>
          {/if}
        </div>
      {:else}
        <div class="loading-state">Loading webhook configuration...</div>
      {/if}
    </div>
  {/if}
</section>

<style>
  .plugin-card {
    background: var(--bg-surface, #0f172a);
    backdrop-filter: blur(12px);
    border: 1px solid var(--border-subtle, #1e293b);
    border-radius: var(--radius, 12px);
    padding: 24px;
    margin-bottom: 24px;
    color: var(--text-primary, #f8fafc);
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border-subtle, #1e293b);
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
    background: rgba(20, 184, 166, 0.15);
    color: var(--color-primary, #14b8a6);
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

  .status-badge.success {
    background: rgba(16, 185, 129, 0.15);
    color: #10b981;
  }
  .status-badge.warning {
    background: rgba(234, 179, 8, 0.15);
    color: #eab308;
  }
  .status-badge.active {
    background: rgba(20, 184, 166, 0.15);
    color: var(--color-primary, #14b8a6);
  }

  .header-right {
    display: flex;
    gap: 8px;
  }

  .btn-ghost {
    padding: 8px 16px;
    background: var(--bg-surface-elevated, #1e293b);
    border: 1px solid var(--border-subtle, #334155);
    color: var(--text-primary, #f8fafc);
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
    color: var(--bg-canvas, #000000);
    border: none;
  }

  .btn-ghost:hover {
    background: var(--bg-surface-elevated);
    filter: brightness(1.2);
  }

  .btn-primary {
    padding: 10px 20px;
    background: var(--color-primary, #14b8a6);
    color: var(--bg-canvas, #000000);
    border: none;
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn-primary:hover {
    opacity: 0.9;
  }

  .loading-state {
    padding: 24px;
    text-align: center;
    color: var(--text-secondary, #94a3b8);
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
    color: var(--text-secondary, #94a3b8);
  }

  .input-field {
    width: 100%;
    padding: 10px 14px;
    background: var(--bg-surface-elevated, #1e293b);
    border: 1px solid var(--border-subtle, #334155);
    border-radius: 8px;
    color: var(--text-primary, #f8fafc);
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
    color: var(--text-primary, #f8fafc);
  }

  .helper-text {
    font-size: 11px;
    color: var(--text-secondary, #94a3b8);
  }

  .actions-row {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    margin-top: 8px;
  }

  .webhook-section {
    border-top: 1px solid var(--border-subtle, #1e293b);
    padding-top: 20px;
    margin-top: 24px;
  }

  .section-description {
    font-size: 13px;
    color: var(--text-secondary, #94a3b8);
    margin: -8px 0 16px 0;
    line-height: 1.4;
  }

  .copy-input-wrapper {
    display: flex;
    gap: 8px;
  }

  .input-field.readonly {
    background: rgba(15, 23, 42, 0.6);
    color: var(--color-primary, #14b8a6);
    font-family: monospace;
    font-size: 12px;
  }

  .btn-copy {
    padding: 0 16px;
    background: var(--bg-surface-elevated, #1e293b);
    border: 1px solid var(--border-subtle, #334155);
    color: var(--text-primary, #f8fafc);
    border-radius: 8px;
    font-size: 12px;
    cursor: pointer;
    font-weight: 600;
    transition: all 0.2s;
    white-space: nowrap;
  }

  .btn-copy:hover {
    background: var(--color-primary, #14b8a6);
    color: #000;
  }

  .yaml-block {
    margin-top: 12px;
    background: #090d16;
    border: 1px solid var(--border-subtle, #1e293b);
    border-radius: 8px;
    overflow: hidden;
  }

  .yaml-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    background: rgba(30, 41, 59, 0.4);
    border-bottom: 1px solid var(--border-subtle, #1e293b);
    font-size: 12px;
    font-weight: 600;
    color: var(--text-secondary, #94a3b8);
  }

  .code-block {
    margin: 0;
    padding: 12px;
    font-family: "JetBrains Mono", "Fira Code", monospace;
    font-size: 12px;
    color: #38bdf8;
    overflow-x: auto;
    white-space: pre;
    line-height: 1.4;
  }

  .test-result-banner {
    margin-top: 12px;
    padding: 10px 14px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 500;
  }

  .test-result-banner.success {
    background: rgba(16, 185, 129, 0.15);
    color: #10b981;
    border: 1px solid rgba(16, 185, 129, 0.3);
  }

  .test-result-banner.error {
    background: rgba(239, 68, 68, 0.15);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.3);
  }
</style>
