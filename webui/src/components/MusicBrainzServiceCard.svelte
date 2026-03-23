<script>
  import { onMount } from 'svelte';
  import apiClient from '../api/client';
  import { feedback } from '../stores/feedback';

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
      const statusResp = await apiClient.get('/musicbrainz/accounts');
      if (statusResp.data) {
        accounts = statusResp.data.accounts || [];
        redirectUri = statusResp.data.redirect_uri || '';
        clientIdConfigured = statusResp.data.client_id_configured || false;
        clientSecretConfigured = statusResp.data.client_secret_configured || false;
        redirectCollapsed = Boolean(redirectUri);
      }

      // Load existing credentials for display
      const credsResp = await apiClient.get('/providers/musicbrainz/credentials');
      if (credsResp.data?.credentials) {
        clientId = credsResp.data.credentials.client_id || '';
        // Never pre-fill the secret; show a placeholder if one is stored
        clientSecretPlaceholder = clientSecretConfigured ? '••••••••' : '';
      }
    } catch (err) {
      console.error('Failed to load MusicBrainz data:', err);
      feedback.addToast('Failed to load MusicBrainz settings', 'error');
    }
  }

  // ── Credentials ───────────────────────────────────────────────────────────
  async function saveCredentials() {
    if (!clientId.trim()) {
      feedback.addToast('Client ID is required', 'error');
      return;
    }

    const creds = { client_id: clientId };
    if (clientSecret.trim()) {
      creds.client_secret = clientSecret;
    } else if (!clientSecretConfigured) {
      feedback.addToast('Client Secret is required', 'error');
      return;
    }

    try {
      savingCreds = true;
      await apiClient.post('/providers/musicbrainz/credentials', { credentials: creds });
      feedback.addToast('MusicBrainz credentials saved', 'success');
      clientSecret = '';
      await loadData();
    } catch (err) {
      feedback.addToast('Failed to save credentials', 'error');
      console.error(err);
    } finally {
      savingCreds = false;
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
    if (!name) {
      feedback.addToast('Account name is required', 'error');
      return;
    }
    try {
      savingAccount = true;
      await apiClient.post('/musicbrainz/accounts', { account_name: name });
      feedback.addToast('Account added', 'success');
      closeAddModal();
      await loadData();
    } catch (err) {
      feedback.addToast('Failed to add account', 'error');
      console.error(err);
    } finally {
      savingAccount = false;
    }
  }

  async function deleteAccount(accountId, displayName) {
    if (!confirm(`Delete account "${displayName}"? This will also remove its stored tokens.`)) return;
    try {
      await apiClient.delete(`/musicbrainz/accounts/${accountId}`);
      feedback.addToast('Account deleted', 'success');
      await loadData();
    } catch (err) {
      feedback.addToast('Failed to delete account', 'error');
    }
  }

  async function toggleAccount(accountId, currentlyActive) {
    try {
      await apiClient.put(`/musicbrainz/accounts/${accountId}/activate`, {
        is_active: !currentlyActive,
      });
      feedback.addToast(currentlyActive ? 'Account deactivated' : 'Account activated', 'success');
      await loadData();
    } catch (err) {
      feedback.addToast('Failed to update account status', 'error');
    }
  }

  async function authenticate(accountId) {
    if (!clientIdConfigured || !clientSecretConfigured) {
      feedback.addToast(
        'Save your MusicBrainz Client ID and Client Secret before authenticating.',
        'error'
      );
      return;
    }
    try {
      const resp = await apiClient.get('/musicbrainz/auth', {
        params: { account_id: accountId },
      });
      const url = resp.data?.auth_url;
      if (url) {
        window.open(url, '_blank', 'noopener,noreferrer');
        // Poll for auth completion after a delay
        setTimeout(async () => {
          await loadData();
        }, 5000);
      } else {
        feedback.addToast('Failed to get MusicBrainz auth URL', 'error');
      }
    } catch (err) {
      const msg = err?.response?.data?.error || 'Failed to start OAuth';
      feedback.addToast(msg, 'error');
    }
  }
</script>

<section class="mb-card card">
  <div class="card-header">
    <div class="header-left">
      <h2>MusicBrainz</h2>
      <span class="provider-badge">Metadata</span>
    </div>
  </div>

  {#if loading}
    <div class="loading">Loading...</div>
  {:else}

    <!-- Application Credentials -->
    <div class="section">
      <h3>Application Credentials</h3>
      <p class="help-text">
        Register an application at
        <a href="https://musicbrainz.org/account/applications" target="_blank" rel="noopener noreferrer">
          musicbrainz.org/account/applications
        </a>
        to obtain a Client ID and Secret. These are required for OAuth logins and ISRC submissions.
      </p>

      <div class="creds-form">
        <div class="form-row">
          <label class="form-label" for="mb-client-id">Client ID</label>
          <input
            id="mb-client-id"
            type="text"
            class="input"
            bind:value={clientId}
            placeholder="Enter your MusicBrainz Client ID"
          />
        </div>

        <div class="form-row">
          <label class="form-label" for="mb-client-secret">Client Secret</label>
          <div class="password-field">
            <input
              id="mb-client-secret"
              type={showSecret ? 'text' : 'password'}
              class="input"
              bind:value={clientSecret}
              placeholder={clientSecretConfigured ? '••••••••  (leave blank to keep current)' : 'Enter your MusicBrainz Client Secret'}
            />
            <button
              type="button"
              class="password-toggle"
              on:click={() => (showSecret = !showSecret)}
              title={showSecret ? 'Hide' : 'Show'}
            >
              {showSecret ? '👁️' : '👁️‍🗨️'}
            </button>
          </div>
        </div>

        <button class="btn-primary" on:click={saveCredentials} disabled={savingCreds}>
          {savingCreds ? 'Saving…' : 'Save Credentials'}
        </button>
      </div>
    </div>

    <!-- Redirect URI (auto-generated, read-only) -->
    <div class="section">
      <div class="section-header">
        <h3>OAuth Redirect URI (Auto-generated)</h3>
        <button class="btn-secondary" on:click={() => (redirectCollapsed = !redirectCollapsed)}>
          {redirectCollapsed ? 'Expand' : 'Collapse'}
        </button>
      </div>
      {#if !redirectCollapsed}
        <input
          type="text"
          class="input readonly-input"
          value={redirectUri}
          readonly
          disabled
        />
        <p class="help-text" style="margin-top:6px;">
          Add this URI as a callback URL in your MusicBrainz application settings.
        </p>
      {/if}
    </div>

    <!-- Accounts -->
    <div class="section">
      <div class="section-header">
        <h3>Accounts ({accounts.length}/{MAX_ACCOUNTS})</h3>
        <p class="help-text">
          Each account represents a MusicBrainz user that will authenticate via OAuth.
          Authenticated accounts can contribute ISRCs and metadata to MusicBrainz.
        </p>
        {#if accounts.length < MAX_ACCOUNTS}
          <button class="btn-secondary" on:click={openAddModal}>
            + Add Account
          </button>
        {/if}
      </div>

      <div class="accounts-list">
        {#each accounts as account}
          <div class="account-row">
            <div class="account-info">
              <div class="account-name">{account.display_name || account.account_name}</div>
              <div class="account-status">
                {#if account.is_authenticated}
                  <span class="status-badge authenticated">✓ Authenticated</span>
                {:else}
                  <span class="status-badge unauthenticated">⚠ Not Authenticated</span>
                {/if}
                {#if account.is_active}
                  <span class="status-badge active">● Active</span>
                {/if}
              </div>
            </div>
            <div class="account-actions">
              <button class="btn-link" on:click={() => authenticate(account.id)}>
                {account.is_authenticated ? 'Reauthenticate' : 'Authenticate'}
              </button>
              <button
                class="btn-toggle"
                class:active={account.is_active}
                on:click={() => toggleAccount(account.id, account.is_active)}
                title={account.is_active ? 'Deactivate' : 'Activate'}
              >
                {account.is_active ? 'Deactivate' : 'Activate'}
              </button>
              <button
                class="btn-delete"
                on:click={() => deleteAccount(account.id, account.display_name || account.account_name)}
              >
                ✕
              </button>
            </div>
          </div>
        {:else}
          <div class="empty-state">
            No accounts added yet. Click "Add Account" to get started.
          </div>
        {/each}
      </div>
    </div>

  {/if}
</section>

<!-- Add Account Modal -->
{#if showAddModal}
  <div class="modal-overlay" on:click={closeAddModal}>
    <div class="modal-content" on:click|stopPropagation>
      <div class="modal-header">
        <h3>Add MusicBrainz Account</h3>
        <button class="modal-close" on:click={closeAddModal}>✕</button>
      </div>
      <div class="modal-body">
        <label>
          <span class="label-text">Display Name</span>
          <input
            type="text"
            bind:value={newAccountName}
            placeholder="e.g. My MusicBrainz Username"
            class="input"
          />
        </label>
        <p class="modal-help">
          Give this slot a friendly name. After adding, click "Authenticate" to link it
          to a real MusicBrainz account via OAuth.
        </p>
      </div>
      <div class="modal-footer">
        <button class="btn-secondary" on:click={closeAddModal}>Cancel</button>
        <button class="btn-primary" on:click={addAccount} disabled={savingAccount}>
          {savingAccount ? 'Adding…' : 'Add Account'}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .mb-card {
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
    background: rgba(186, 100, 21, 0.2);
    color: #ba6415;
  }

  .section {
    margin-bottom: 24px;
  }

  .section h3 {
    margin: 0 0 8px 0;
    font-size: 16px;
    font-weight: 600;
  }

  .section-header {
    margin-bottom: 12px;
  }

  .section-header h3 {
    margin-bottom: 4px;
  }

  .section-header button {
    margin-top: 8px;
  }

  .help-text {
    font-size: 13px;
    color: var(--muted);
    margin: 0 0 12px 0;
  }

  .help-text a {
    color: #ba6415;
    text-decoration: underline;
  }

  .creds-form {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .form-row {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .form-label {
    font-size: 13px;
    font-weight: 500;
    color: var(--text);
  }

  .password-field {
    display: flex;
    gap: 6px;
  }

  .password-field .input {
    flex: 1;
  }

  .password-toggle {
    background: rgba(255,255,255,0.08);
    border: 1px solid var(--border-color, rgba(255,255,255,0.1));
    border-radius: 6px;
    padding: 0 10px;
    cursor: pointer;
    font-size: 16px;
    color: var(--text);
  }

  .input {
    padding: 8px 12px;
    border-radius: 6px;
    background: var(--input-bg, rgba(255,255,255,0.05));
    border: 1px solid var(--border-color, rgba(255,255,255,0.1));
    color: var(--text);
    font-size: 14px;
    width: 100%;
    box-sizing: border-box;
  }

  .input:focus {
    outline: none;
    border-color: #ba6415;
  }

  .readonly-input {
    opacity: 0.7;
    cursor: not-allowed;
    background: rgba(0,0,0,0.2);
    user-select: all;
  }

  .btn-primary,
  .btn-secondary,
  .btn-link,
  .btn-toggle,
  .btn-delete {
    padding: 8px 16px;
    border-radius: 6px;
    border: none;
    cursor: pointer;
    font-size: 14px;
    transition: all 0.2s;
  }

  .btn-primary {
    background: #ba6415;
    color: white;
  }

  .btn-primary:hover:not(:disabled) {
    background: #9d5412;
  }

  .btn-primary:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn-secondary {
    background: rgba(255,255,255,0.1);
    color: var(--text);
  }

  .btn-secondary:hover {
    background: rgba(255,255,255,0.15);
  }

  .btn-link {
    background: transparent;
    color: #ba6415;
    padding: 4px 8px;
  }

  .btn-link:hover {
    text-decoration: underline;
  }

  .btn-toggle {
    background: rgba(255,255,255,0.1);
    color: var(--text);
  }

  .btn-toggle.active {
    background: rgba(186,100,21,0.2);
    color: #ba6415;
  }

  .btn-toggle:hover {
    background: rgba(255,255,255,0.15);
  }

  .btn-delete {
    background: rgba(239,68,68,0.2);
    color: #ef4444;
  }

  .btn-delete:hover {
    background: rgba(239,68,68,0.3);
  }

  .accounts-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .account-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px;
    background: var(--input-bg, rgba(255,255,255,0.03));
    border: 1px solid var(--border-color, rgba(255,255,255,0.08));
    border-radius: 8px;
  }

  .account-info {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .account-name {
    font-weight: 500;
    font-size: 14px;
  }

  .account-status {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }

  .account-actions {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
  }

  .status-badge {
    font-size: 11px;
    padding: 2px 6px;
    border-radius: 4px;
  }

  .status-badge.authenticated {
    background: rgba(34,197,94,0.2);
    color: #22c55e;
  }

  .status-badge.unauthenticated {
    background: rgba(234,179,8,0.2);
    color: #eab308;
  }

  .status-badge.active {
    background: rgba(186,100,21,0.2);
    color: #ba6415;
  }

  .empty-state {
    padding: 16px;
    text-align: center;
    color: var(--muted);
    font-size: 14px;
  }

  .loading {
    padding: 24px;
    text-align: center;
    color: var(--muted);
  }

  /* Modal */
  .modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.6);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .modal-content {
    background: var(--bg-elevated, #1e1e2e);
    border-radius: 10px;
    padding: 0;
    min-width: 420px;
    max-width: 90vw;
    border: 1px solid var(--border-color, rgba(255,255,255,0.15));
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    border-bottom: 1px solid var(--border-color, rgba(255,255,255,0.1));
  }

  .modal-header h3 {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
  }

  .modal-close {
    background: transparent;
    border: none;
    font-size: 18px;
    cursor: pointer;
    color: var(--muted);
    padding: 0;
    line-height: 1;
  }

  .modal-body {
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .label-text {
    display: block;
    font-size: 13px;
    font-weight: 500;
    margin-bottom: 4px;
    color: var(--text);
  }

  .modal-help {
    font-size: 12px;
    color: var(--muted);
    margin: 0;
  }

  .modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    padding: 16px 20px;
    border-top: 1px solid var(--border-color, rgba(255,255,255,0.1));
  }
</style>
