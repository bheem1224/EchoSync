<svelte:options customElement="musicbrainz-dashboard-card" />
<script>
  export let apiBase = '';
  import { onMount } from 'svelte';

  // ── State ─────────────────────────────────────────────────────────────────
  let loading = true;
  let accounts = [];
  let redirectUri = '';
  let clientId = '';
  let clientSecret = '';
  let clientSecretPlaceholder = '';
  let clientIdConfigured = false;
  let clientSecretConfigured = false;
  let showSecret = false;
  let savingCreds = false;
  let redirectCollapsed = false;
  let customApiBaseUrl = 'https://musicbrainz.org/ws/2';

  // Add-account modal
  let showAddModal = false;
  let newAccountName = '';
  let savingAccount = false;

  const MAX_ACCOUNTS = 10;

  // ── Lifecycle ─────────────────────────────────────────────────────────────
  onMount(async () => {
    await loadData();
    loading = false;
  });

  async function loadData() {
    try {
      // Status (accounts + redirect URI + credential flags)
      const statusResp = await fetch(`${apiBase}/accounts`);
      const statusData = await statusResp.json();
      
      if (statusData) {
        accounts = statusData.accounts || [];
        redirectUri = statusData.redirect_uri || '';
        clientIdConfigured = statusData.client_id_configured || false;
        clientSecretConfigured = statusData.client_secret_configured || false;
        redirectCollapsed = Boolean(redirectUri);
      }

      // Load custom API Base URL
      const settingsResp = await fetch(`${apiBase}/settings`);
      const settingsData = await settingsResp.json();
      if (settingsData?.settings) {
        customApiBaseUrl = settingsData.settings.api_base_url || 'https://musicbrainz.org/ws/2';
      }

      const credsResp = await fetch(`${apiBase}/credentials`);
      const credsData = await credsResp.json();
      if (credsData?.credentials) {
        clientId = credsData.credentials.client_id || '';
        clientSecretPlaceholder = clientSecretConfigured ? '••••••••' : '';
      }
    } catch (err) {
      console.error('Failed to load MusicBrainz data:', err);
    }
  }

  // ── Credentials ───────────────────────────────────────────────────────────
  async function saveCredentials() {
    if (!clientId.trim()) {
      console.error('Client ID is required');
      return;
    }

    const creds = { client_id: clientId };
    if (clientSecret.trim()) {
      creds.client_secret = clientSecret;
    } else if (!clientSecretConfigured) {
      console.error('Client Secret is required');
      return;
    }

    try {
      savingCreds = true;
      await fetch(`${apiBase}/credentials`, {
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({ credentials: creds }) 
      });
      clientSecret = '';
      await loadData();
    } catch (err) {
      console.error('Failed to save credentials:', err);
    } finally {
      savingCreds = false;
    }
  }

  async function saveSettings() {
    try {
      await fetch(`${apiBase}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ settings: { api_base_url: customApiBaseUrl } })
      });
      console.log('MusicBrainz settings saved');
    } catch (err) {
      console.error('Failed to save settings:', err);
    }
  }

  // ── Accounts ──────────────────────────────────────────────────────────────
  function openAddModal() {
    newAccountName = '';
    showAddModal = true;
  }

  function closeAddModal() {
    showAddModal = false;
    newAccountName = '';
  }

  async function addAccount() {
    const name = newAccountName.trim();
    if (!name) return;
    
    try {
      savingAccount = true;
      await fetch(`${apiBase}/accounts`, {
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({ account_name: name }) 
      });
      closeAddModal();
      await loadData();
    } catch (err) {
      console.error('Failed to add account:', err);
    } finally {
      savingAccount = false;
    }
  }

  async function deleteAccount(accountId, displayName) {
    if (!confirm(`Delete account "${displayName}"?`)) return;
    try {
      await fetch(`${apiBase}/accounts/${accountId}`, { method: 'DELETE' });
      await loadData();
    } catch (err) {
      console.error('Failed to delete account:', err);
    }
  }

  async function toggleAccount(accountId, currentlyActive) {
    try {
      await fetch(`${apiBase}/accounts/${accountId}/activate`, {
        method: 'PUT', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({ is_active: !currentlyActive }) 
      });
      await loadData();
    } catch (err) {
      console.error('Failed to update account status:', err);
    }
  }

  async function authenticate(accountId) {
    if (!clientIdConfigured || !clientSecretConfigured) {
      alert('Save your Client ID and Secret first.');
      return;
    }
    try {
      const resp = await fetch(`${apiBase}/auth?account_id=${accountId}`);
      const data = await resp.json();
      const url = data?.auth_url;
      if (url) {
        window.open(url, '_blank', 'noopener,noreferrer');
        setTimeout(() => loadData(), 5000);
      }
    } catch (err) {
      console.error('Failed to start OAuth:', err);
    }
  }
</script>

<section class="plugin-card">
  <div class="card-header">
    <div class="header-left">
      <h2 class="card-title">MusicBrainz</h2>
      <span class="type-badge">Metadata Provider</span>
    </div>
  </div>

  {#if loading}
    <div class="loading-state">Loading...</div>
  {:else}
    <!-- Custom API Base URL -->
    <div class="settings-section">
      <h3 class="section-title">Server Configuration</h3>
      <div class="form-grid">
        <label class="form-field">
          <span class="field-label">API Base URL</span>
          <input
            type="text"
            class="input-field"
            bind:value={customApiBaseUrl}
            placeholder="https://musicbrainz.org/ws/2"
          />
          <p class="helper-text">Point this to a local MusicBrainz container for offline use.</p>
        </label>
        <button class="btn-primary" on:click={saveSettings}>
          Save Settings
        </button>
      </div>
    </div>

    <!-- Application Credentials -->
    <div class="settings-section">
      <h3 class="section-title">OAuth Credentials</h3>
      <div class="form-grid">
        <label class="form-field">
          <span class="field-label">Client ID</span>
          <input
            type="text"
            class="input-field"
            bind:value={clientId}
            placeholder="Enter Client ID"
          />
        </label>

        <label class="form-field">
          <span class="field-label">Client Secret</span>
          <div class="password-wrapper">
            <input
              type={showSecret ? 'text' : 'password'}
              class="input-field"
              bind:value={clientSecret}
              placeholder={clientSecretPlaceholder || 'Enter Client Secret'}
            />
            <button class="toggle-visibility" on:click={() => showSecret = !showSecret}>
              {showSecret ? '🙈' : '👁️'}
            </button>
          </div>
        </label>

        <button class="btn-primary" on:click={saveCredentials} disabled={savingCreds}>
          {savingCreds ? 'Saving...' : 'Save Credentials'}
        </button>
      </div>
    </div>

    <!-- Redirect URI -->
    <div class="settings-section">
      <div class="section-header">
        <h3 class="section-title">Redirect URI</h3>
        <button class="btn-ghost" on:click={() => redirectCollapsed = !redirectCollapsed}>
          {redirectCollapsed ? 'Expand' : 'Collapse'}
        </button>
      </div>
      {#if !redirectCollapsed}
        <div class="redirect-copy-group">
          <input
            type="text"
            class="input-field readonly"
            value={redirectUri}
            readonly
          />
          <button class="btn-primary" on:click={() => { navigator.clipboard.writeText(redirectUri); alert('Copied!'); }}>Copy</button>
        </div>
      {/if}
    </div>

    <!-- Accounts -->
    <div class="settings-section">
      <div class="section-header">
        <h3 class="section-title">Accounts ({accounts.length}/{MAX_ACCOUNTS})</h3>
        {#if accounts.length < MAX_ACCOUNTS}
          <button class="btn-ghost" on:click={openAddModal}>+ Add Account</button>
        {/if}
      </div>

      <div class="accounts-list">
        {#each accounts as account}
          <div class="account-item">
            <div class="account-info">
              <div class="account-name">{account.display_name || account.account_name}</div>
              <div class="account-badges">
                {#if account.is_authenticated}
                  <span class="status-badge success">✓ Authenticated</span>
                {:else}
                  <span class="status-badge warning">⚠ Not Authenticated</span>
                {/if}
                {#if account.is_active}
                  <span class="status-badge active">● Active</span>
                {/if}
              </div>
            </div>
            <div class="account-actions">
              <button class="link-btn" on:click={() => authenticate(account.id)}>
                {account.is_authenticated ? 'Reauthenticate' : 'Authenticate'}
              </button>
              <button class="btn-ghost" class:active={account.is_active} on:click={() => toggleAccount(account.id, account.is_active)}>
                {account.is_active ? 'Deactivate' : 'Activate'}
              </button>
              <button class="btn-danger" on:click={() => deleteAccount(account.id, account.display_name || account.account_name)}>✕</button>
            </div>
          </div>
        {:else}
          <div class="empty-accounts">No accounts linked.</div>
        {/each}
      </div>
    </div>
  {/if}
</section>

{#if showAddModal}
  <div class="modal-overlay" on:click={closeAddModal}>
    <div class="modal-content" on:click|stopPropagation>
      <div class="modal-header">
        <h3 class="modal-title">Add MusicBrainz Account</h3>
        <button class="close-btn" on:click={closeAddModal}>✕</button>
      </div>
      <div class="modal-body">
        <label class="form-field">
          <span class="field-label">Display Name</span>
          <input type="text" class="input-field" bind:value={newAccountName} placeholder="My Account" />
        </label>
      </div>
      <div class="modal-footer">
        <button class="btn-ghost" on:click={closeAddModal}>Cancel</button>
        <button class="btn-primary" on:click={addAccount} disabled={savingAccount}>Add</button>
      </div>
    </div>
  </div>
{/if}

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
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border-subtle, #1e293b);
  }

  .header-left { display: flex; align-items: center; gap: 12px; }
  .card-title { margin: 0; font-size: 20px; font-weight: 700; }
  
  .type-badge {
    font-size: 11px;
    padding: 4px 8px;
    background: rgba(20, 184, 166, 0.15);
    color: var(--color-primary, #14b8a6);
    border-radius: 4px;
    font-weight: 600;
    text-transform: uppercase;
  }

  .loading-state { padding: 24px; text-align: center; color: var(--text-secondary, #cbd5e1); }
  
  .settings-section { margin-bottom: 24px; }
  .section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
  .section-title { margin: 0; font-size: 16px; font-weight: 600; }

  .form-grid { display: flex; flex-direction: column; gap: 16px; }
  .form-field { display: flex; flex-direction: column; gap: 8px; }
  .field-label { font-size: 13px; font-weight: 500; color: var(--text-secondary, #cbd5e1); }

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

  .input-field.readonly { opacity: 0.6; cursor: not-allowed; }

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

  .btn-primary:hover:not(:disabled) { opacity: 0.9; }
  .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

  .btn-ghost {
    padding: 8px 16px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: var(--text-primary, #f8fafc);
    border-radius: 8px;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn-ghost:hover { background: rgba(255, 255, 255, 0.1); }
  .btn-ghost.active { border-color: var(--color-primary, #14b8a6); color: var(--color-primary, #14b8a6); }

  .btn-danger {
    background: rgba(239, 68, 68, 0.15);
    color: #ef4444;
    border: none;
    padding: 8px 12px;
    border-radius: 6px;
    cursor: pointer;
  }

  .helper-text { font-size: 11px; color: var(--text-secondary, #cbd5e1); margin-top: 4px; }

  .redirect-copy-group { display: flex; gap: 8px; align-items: stretch; }
  .redirect-copy-group .input-field { flex: 1; font-family: monospace; }

  .accounts-list { display: flex; flex-direction: column; gap: 8px; }
  .account-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 8px;
  }

  .account-info { display: flex; flex-direction: column; gap: 4px; }
  .account-name { font-weight: 600; font-size: 14px; }
  .account-badges { display: flex; gap: 8px; }

  .status-badge { font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: 700; }
  .status-badge.success { background: rgba(34, 197, 94, 0.15); color: #22c55e; }
  .status-badge.warning { background: rgba(234, 179, 8, 0.15); color: #eab308; }
  .status-badge.active { background: rgba(20, 184, 166, 0.15); color: var(--color-primary, #14b8a6); }

  .account-actions { display: flex; gap: 12px; align-items: center; }

  .link-btn {
    background: none;
    border: none;
    color: var(--color-primary, #14b8a6);
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
  }

  .link-btn:hover { text-decoration: underline; }

  .password-wrapper { position: relative; display: flex; align-items: center; width: 100%; }
  .toggle-visibility {
    position: absolute;
    right: 12px;
    background: none;
    border: none;
    cursor: pointer;
    opacity: 0.6;
    color: var(--text-primary, #f8fafc);
  }

  .modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    backdrop-filter: blur(4px);
  }

  .modal-content {
    background: #0f1216;
    border: 1px solid var(--border-subtle, #1e293b);
    border-radius: 12px;
    width: 100%;
    max-width: 440px;
    box-shadow: 0 24px 48px rgba(0,0,0,0.5);
  }

  .modal-header {
    padding: 16px 20px;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .modal-title { margin: 0; font-size: 16px; font-weight: 700; }
  .close-btn { background: none; border: none; color: var(--text-secondary, #cbd5e1); font-size: 20px; cursor: pointer; }

  .modal-body { padding: 20px; display: flex; flex-direction: column; gap: 16px; }
  .modal-footer {
    padding: 16px 20px;
    border-top: 1px solid rgba(255,255,255,0.05);
    display: flex;
    justify-content: flex-end;
    gap: 12px;
  }

  .empty-accounts {
    text-align: center;
    padding: 16px;
    color: var(--text-secondary, #cbd5e1);
    font-size: 13px;
    background: rgba(255, 255, 255, 0.02);
    border-radius: 8px;
    border: 1px dashed rgba(255, 255, 255, 0.1);
  }
</style>
