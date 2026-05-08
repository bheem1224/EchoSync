<svelte:options customElement="acoustid-settings-card" />

<script>
  export let apiBase = '';

  import { onMount } from 'svelte';

  // ── State ─────────────────────────────────────────────────────────────────
  let loading = true;
  let saving = false;
  let saved = false;
  let error = '';

  let apiKey = '';
  let keyConfigured = false;
  let showKey = false;

  let autoContribute = false;

  // ── Lifecycle ──────────────────────────────────────────────────────────────
  onMount(async () => {
    await loadConfig();
    loading = false;
  });

  async function loadConfig() {
    try {
      const base = apiBase || '';
      const res = await fetch(`${base}/api/plugins/acoustid/config`);
      if (res.ok) {
        const data = await res.json();
        keyConfigured = data.api_key_configured ?? false;
        autoContribute = data.auto_contribute ?? false;
        // Never pre-fill the key; show a placeholder if one is stored.
        if (keyConfigured) apiKey = '';
      }
    } catch (err) {
      console.error('[AcoustIDSettingsCard] Failed to load config:', err);
    }
  }

  async function saveConfig() {
    const payload = { auto_contribute: autoContribute };

    // Only send the key if the user actually typed something
    if (apiKey.trim()) {
      payload.api_key = apiKey.trim();
    } else if (!keyConfigured) {
      error = 'An API Key is required for fingerprinting.';
      return;
    }

    error = '';
    saving = true;
    saved = false;

    try {
      const base = apiBase || '';
      const res = await fetch(`${base}/api/plugins/acoustid/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        const data = await res.json();
        keyConfigured = data.api_key_configured ?? keyConfigured;
        apiKey = '';
        saved = true;
        // Dispatch a DOM event
        dispatchEvent(new CustomEvent('acoustid-config-saved', {
          bubbles: true,
          composed: true,
          detail: { api_key_configured: keyConfigured, auto_contribute: autoContribute }
        }));
        setTimeout(() => (saved = false), 3000);
      } else {
        const data = await res.json().catch(() => ({}));
        error = data.error || 'Failed to save configuration.';
      }
    } catch (err) {
      console.error('[AcoustIDSettingsCard] Save error:', err);
      error = 'Network error while saving. Please try again.';
    } finally {
      saving = false;
    }
  }
</script>

<section class="plugin-card">

  <!-- Header -->
  <div class="card-header">
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="accent-icon">
      <path d="M2 12c.6.5 1.2 1 2.5 1s2.5-1 3.5-2c1-1 2.2-2 3.5-2s2.5 1 3.5 2c1 1 2.2 2 3.5 2s1.9-.5 2.5-1"/>
      <path d="M2 18c.6.5 1.2 1 2.5 1s2.5-1 3.5-2c1-1 2.2-2 3.5-2s2.5 1 3.5 2c1 1 2.2 2 3.5 2s1.9-.5 2.5-1"/>
      <path d="M2 6c.6.5 1.2 1 2.5 1s2.5-1 3.5-2c1-1 2.2-2 3.5-2s2.5 1 3.5 2c1 1 2.2 2 3.5 2s1.9-.5 2.5-1"/>
    </svg>
    <div>
      <h2 class="card-title">AcoustID Configuration</h2>
      <p class="card-subtitle">Audio fingerprinting service</p>
    </div>
    <span class="type-badge">Fingerprinting</span>
  </div>

  {#if loading}
    <div class="loading-state">Loading configuration…</div>
  {:else}

    <!-- API Key -->
    <div class="form-section">
      <label class="field-label" for="acoustid-api-key">
        AcoustID API Key
        {#if keyConfigured}
          <span class="status-tag success">● Configured</span>
        {/if}
      </label>
      <p class="helper-text">
        Get your free API key from
        <a href="https://acoustid.org/new-application" target="_blank" rel="noopener noreferrer" class="link">
          acoustid.org/new-application
        </a>.
        Required to identify songs by their audio signature.
      </p>
      <div class="input-wrapper">
        <input
          id="acoustid-api-key"
          type={showKey ? 'text' : 'password'}
          bind:value={apiKey}
          placeholder={keyConfigured ? '••••••••  (leave blank to keep current)' : 'Enter your AcoustID API key'}
          class="input-field"
        />
        <button
          type="button"
          class="toggle-btn"
          on:click={() => (showKey = !showKey)}
          title={showKey ? 'Hide key' : 'Show key'}
          aria-label={showKey ? 'Hide key' : 'Show key'}
        >
          {showKey ? '🙈' : '👁️'}
        </button>
      </div>
    </div>

    <!-- Auto-Contribute Toggle -->
    <div class="toggle-card">
      <div class="toggle-header">
        <p class="toggle-label">Auto-Contribute Fingerprints</p>

        <!-- Toggle Switch -->
        <button
          type="button"
          role="switch"
          aria-checked={autoContribute}
          class="switch {autoContribute ? 'active' : ''}"
          on:click={() => (autoContribute = !autoContribute)}
          aria-label="Toggle auto-contribute"
        >
          <span class="switch-thumb"></span>
        </button>
      </div>
      <p class="helper-text mt-2">
        When enabled, EchoSync will automatically submit acoustic fingerprints of your music to the 
        AcoustID database to help identify tracks for other community members.
      </p>
      {#if autoContribute}
        <div class="warning-box">
          ⚠ Submissions are anonymous but require a valid API key. Fingerprints are generated locally and uploaded during background library enrichment.
        </div>
      {/if}
    </div>

    <!-- Error / Success feedback -->
    {#if error}
      <div class="feedback error">
        ⚠ {error}
      </div>
    {/if}
    {#if saved}
      <div class="feedback success">
        ✓ Configuration saved successfully.
      </div>
    {/if}

    <!-- Save Button -->
    <div class="actions">
      <button
        class="btn-primary"
        on:click={saveConfig}
        disabled={saving}
      >
        {saving ? 'Saving…' : 'Save Settings'}
      </button>
    </div>

  {/if}
</section>

<style>
  .plugin-card {
    background: var(--bg-surface);
    backdrop-filter: blur(12px);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius, 12px);
    padding: 24px;
    margin-bottom: 16px;
    color: var(--text-primary);
  }

  .card-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 20px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border-subtle, #1e293b);
  }

  .accent-icon {
    color: var(--color-primary);
  }

  .card-title {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 600;
    line-height: 1.2;
  }

  .card-subtitle {
    margin: 4px 0 0;
    font-size: 0.75rem;
    color: var(--text-secondary, #94a3b8);
  }

  .type-badge {
    margin-left: auto;
    font-size: 11px;
    padding: 4px 8px;
    background: rgba(99, 102, 241, 0.15);
    color: var(--color-primary);
    border-radius: 4px;
    font-weight: 600;
  }

  .loading-state {
    padding: 20px;
    text-align: center;
    color: var(--text-secondary, #94a3b8);
  }

  .form-section {
    margin-bottom: 24px;
  }

  .field-label {
    display: block;
    font-size: 0.875rem;
    font-weight: 500;
    margin-bottom: 4px;
  }

  .status-tag.success {
    margin-left: 8px;
    font-size: 11px;
    padding: 2px 6px;
    background: rgba(16, 185, 129, 0.15);
    color: #10b981;
    border-radius: 4px;
  }

  .helper-text {
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-bottom: 8px;
    line-height: 1.5;
  }

  .link {
    color: var(--color-primary);
    text-decoration: none;
  }

  .link:hover {
    text-decoration: underline;
  }

  .input-wrapper {
    position: relative;
    display: flex;
    align-items: center;
  }

  .input-field {
    width: 100%;
    padding: 10px 14px;
    padding-right: 40px;
    background: var(--bg-surface-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius, 12px);
    color: var(--text-primary, #f8fafc);
    font-size: 0.875rem;
    transition: border-color 0.2s;
  }

  .input-field:focus {
    outline: none;
    border-color: var(--color-primary);
  }

  .toggle-btn {
    position: absolute;
    right: 12px;
    background: transparent;
    border: none;
    cursor: pointer;
    font-size: 1.1rem;
    opacity: 0.6;
    transition: opacity 0.2s;
  }

  .toggle-btn:hover {
    opacity: 1;
  }

  .toggle-card {
    margin-bottom: 24px;
    padding: 16px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius, 12px);
  }

  .toggle-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .toggle-label {
    margin: 0;
    font-size: 0.875rem;
    font-weight: 600;
  }

  .switch {
    position: relative;
    width: 44px;
    height: 24px;
    background: rgba(255, 255, 255, 0.2);
    border-radius: 999px;
    border: none;
    cursor: pointer;
    transition: background 0.2s;
  }

  .switch.active {
    background: var(--color-primary, #14b8a6);
  }

  .switch-thumb {
    position: absolute;
    top: 2px;
    left: 2px;
    width: 20px;
    height: 20px;
    background: white;
    border-radius: 50%;
    transition: transform 0.2s;
  }

  .switch.active .switch-thumb {
    transform: translateX(20px);
  }

  .warning-box {
    margin-top: 8px;
    padding: 6px 12px;
    background: rgba(245, 158, 11, 0.1);
    border: 1px solid rgba(245, 158, 11, 0.2);
    border-radius: 4px;
    font-size: 11px;
    color: var(--color-primary, #14b8a6);
  }

  .feedback {
    margin-bottom: 16px;
    padding: 8px 12px;
    border-radius: var(--radius, 12px);
    font-size: 0.875rem;
  }

  .feedback.error {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid var(--color-danger);
    color: var(--color-danger);
  }

  .feedback.success {
    background: rgba(16, 185, 129, 0.1);
    border: 1px solid #10b981;
    color: #10b981;
  }

  .actions {
    display: flex;
    justify-content: flex-end;
  }

  .btn-primary {
    padding: 10px 20px;
    background: var(--color-primary, #14b8a6);
    color: var(--bg-canvas, #000000);
    font-weight: 500;
    border: none;
    border-radius: var(--radius, 12px);
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn-primary:hover:not(:disabled) {
    opacity: 0.9;
  }

  .btn-primary:active:not(:disabled) {
    transform: scale(0.98);
  }

  .btn-primary:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
</style>




