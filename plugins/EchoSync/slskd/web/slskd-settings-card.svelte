<svelte:options customElement="slskd-settings-card" />

<script>
  export let apiBase = "";
  import { onMount } from "svelte";

  let webhookEndpoint = null;
  let webhookLoading = false;
  let webhookTesting = false;
  let webhookTestResult = null;
  let copiedYaml = false;
  let copiedUrl = false;

  onMount(async () => {
    await loadWebhookInfo();
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

<div class="settings-card">
  <h3 class="section-title">Slskd Webhook Automation</h3>
  <p class="section-description">
    Configure slskd to immediately notify EchoSync upon download completion or
    failure. This enables real-time tag verification, automatic library
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

<style>
  .settings-card {
    background: var(--bg-surface, #0f172a);
    backdrop-filter: blur(12px);
    border: 1px solid var(--border-subtle, #1e293b);
    border-radius: var(--radius, 12px);
    padding: 24px;
    color: var(--text-primary, #f8fafc);
  }

  .section-title {
    margin: 0 0 8px 0;
    font-size: 16px;
    font-weight: 600;
  }

  .section-description {
    font-size: 13px;
    color: var(--text-secondary, #94a3b8);
    margin: 0 0 16px 0;
    line-height: 1.4;
  }

  .form-field {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-bottom: 16px;
  }

  .field-label {
    font-size: 13px;
    color: var(--text-secondary, #94a3b8);
  }

  .copy-input-wrapper {
    display: flex;
    gap: 8px;
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

  .helper-text {
    font-size: 11px;
    color: var(--text-secondary, #94a3b8);
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
    filter: brightness(1.2);
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

  .actions-row {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    margin-top: 16px;
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

  .loading-state {
    padding: 24px;
    text-align: center;
    color: var(--text-secondary, #94a3b8);
  }
</style>
