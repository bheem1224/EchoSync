<svelte:options customElement="musicbrainz-settings-card" />

<script>
  export let apiBase = '';

  import { onMount } from 'svelte';

  // ── State ─────────────────────────────────────────────────────────────────
  let loading = true;
  let saving = false;
  let saved = false;
  let error = '';

  let userToken = '';
  let tokenConfigured = false;
  let showToken = false;

  let autoContribute = false;

  // ── Lifecycle ──────────────────────────────────────────────────────────────
  onMount(async () => {
    await loadConfig();
    loading = false;
  });

  async function loadConfig() {
    try {
      const base = apiBase || '';
      const res = await fetch(`${apiBase}/config`);
      if (res.ok) {
        const data = await res.json();
        tokenConfigured = data.token_configured ?? false;
        autoContribute = data.auto_contribute ?? false;
        // Never pre-fill the token; show a placeholder if one is stored.
        if (tokenConfigured) userToken = '';
      }
    } catch (err) {
      console.error('[MusicBrainzSettingsCard] Failed to load config:', err);
    }
  }

  async function saveConfig() {
    const payload = { auto_contribute: autoContribute };

    // Only send the token if the user actually typed something
    if (userToken.trim()) {
      payload.user_token = userToken.trim();
    } else if (autoContribute && !tokenConfigured) {
      error = 'A User Token is required to enable auto-contributions.';
      return;
    }

    error = '';
    saving = true;
    saved = false;

    try {
      const base = apiBase || '';
      const res = await fetch(`${apiBase}/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        const data = await res.json();
        tokenConfigured = data.token_configured ?? tokenConfigured;
        userToken = '';
        saved = true;
        
        // Dispatch a DOM event for reactivity in the host
        dispatchEvent(new CustomEvent('musicbrainz-config-saved', {
          bubbles: true,
          composed: true,
          detail: { auto_contribute: autoContribute, token_configured: tokenConfigured }
        }));
        
        setTimeout(() => (saved = false), 3000);
      } else {
        const data = await res.json().catch(() => ({}));
        error = data.error || 'Failed to save configuration.';
      }
    } catch (err) {
      console.error('[MusicBrainzSettingsCard] Save error:', err);
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
      <circle cx="12" cy="12" r="10"/>
      <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
      <line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>
    <div>
      <h2 class="card-title">MusicBrainz Configuration</h2>
      <p class="card-subtitle">Global music encyclopedia & metadata source</p>
    </div>
    <span class="type-badge">Metadata</span>
  </div>

  {#if loading}
    <div class="loading-state">Loading configuration…</div>
  {:else}

    <!-- Info Box: Works without account -->
    <div class="info-banner">
      <p>MusicBrainz works out-of-the-box for metadata retrieval. An account is only needed for contributing data back to the community.</p>
    </div>

    <!-- User Token -->
    <div class="form-section">
      <label class="field-label" for="mb-user-token">
        User Token / API Key
        {#if tokenConfigured}
          <span class="status-tag success">● Configured</span>
        {/if}
      </label>
      <p class="helper-text">
        Obtain your personal access token from
        <a href="https://musicbrainz.org/account/applications" target="_blank" rel="noopener noreferrer" class="link">
          musicbrainz.org/account/applications
        </a>.
        Required for submitting ISRC codes and metadata corrections.
      </p>
      <div class="input-wrapper">
        <input
          id="mb-user-token"
          type={showToken ? 'text' : 'password'}
          bind:value={userToken}
          placeholder={tokenConfigured ? '••••••••  (leave blank to keep current)' : 'Enter your MusicBrainz user token'}
          class="input-field"
        />
        <button
          type="button"
          class="toggle-btn"
          on:click={() => (showToken = !showToken)}
          title={showToken ? 'Hide token' : 'Show token'}
          aria-label={showToken ? 'Hide token' : 'Show token'}
        >
          {showToken ? '🙈' : '👁️'}
        </button>
      </div>
    </div>

    <!-- Auto-Contribute Toggle -->
    <div class="toggle-card">
      <div class="toggle-header">
        <p class="toggle-label">Auto-Contribute Missing Data</p>

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
        When enabled, EchoSync will automatically submit missing acoustic fingerprints (AcoustID) and 
        ISRC data back to MusicBrainz during imports.
      </p>
      {#if autoContribute && !tokenConfigured && !userToken}
        <div class="warning-box">
          ⚠ A User Token is required to enable contributions. Please enter your token above.
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
    border-bottom: 1px solid var(--border-subtle);
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
    color: var(--text-muted);
  }

  .type-badge {
    margin-left: auto;
    font-size: 11px;
    padding: 4px 8px;
    background: rgba(16, 185, 129, 0.1);
    color: #10b981;
    border-radius: 4px;
    font-weight: 600;
    text-transform: uppercase;
  }

  .loading-state {
    padding: 20px;
    text-align: center;
    color: var(--text-muted);
  }

  .info-banner {
    margin-bottom: 24px;
    padding: 12px 16px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    font-size: 0.8125rem;
    color: var(--text-muted);
    line-height: 1.4;
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
    background: rgba(0, 0, 0, 0.2);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius, 12px);
    color: var(--text-primary);
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
    margin-top: 12px;
    padding: 8px 12px;
    background: rgba(245, 158, 11, 0.1);
    border: 1px solid rgba(245, 158, 11, 0.2);
    border-radius: 6px;
    font-size: 11px;
    color: #fbbf24;
    line-height: 1.4;
  }

  .feedback {
    margin-bottom: 16px;
    padding: 10px 14px;
    border-radius: var(--radius, 12px);
    font-size: 0.875rem;
  }

  .feedback.error {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid #ef4444;
    color: #ef4444;
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
    padding: 10px 24px;
    background: var(--color-primary, #14b8a6);
    color: var(--bg-canvas, #000000);
    font-weight: 600;
    border: none;
    border-radius: var(--radius, 12px);
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn-primary:hover:not(:disabled) {
    opacity: 0.9;
    box-shadow: 0 4px 12px rgba(20, 184, 166, 0.2);
  }

  .btn-primary:active:not(:disabled) {
    transform: scale(0.98);
  }

  .btn-primary:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .mt-2 { margin-top: 8px; }
</style>





