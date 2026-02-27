<script>
  import { onMount } from 'svelte';
  import apiClient from '../api/client';
  import { feedback } from '../stores/feedback';

  let clientId = '';
  let clientSecret = '';
  let redirectUri = '';
  let accounts = [];
  let showAddAccount = false;
  let newAccountName = '';
  let loading = true;
  let savingGlobal = false;
  let credsCollapsed = false;

  const MAX_ACCOUNTS = 25;

  onMount(async () => {
    await loadGlobalSettings();
    await loadAccounts();

    // Auto-populate redirect URI if empty
    if (!redirectUri && typeof window !== 'undefined') {
      redirectUri = `${window.location.protocol}//${window.location.host}/api/spotify/callback`;
    }

    // Collapse credentials by default when all globals are present and at least one account is authenticated
    credsCollapsed = Boolean(clientId && clientSecret && redirectUri && accounts.some(a => a.is_authenticated));
    loading = false;
  });

  async function loadGlobalSettings() {
    try {
      const response = await apiClient.get('/providers/spotify/settings');
      if (response.data?.settings) {
        clientId = response.data.settings.client_id || '';
        clientSecret = response.data.settings.client_secret || '';
        redirectUri = response.data.settings.redirect_uri || '';
      }
    } catch (error) {
      console.error('Failed to load Spotify settings:', error);
    }
  }

  async function saveGlobalSettings() {
    if (!clientId || !clientSecret) {
      feedback.addToast('Client ID and Secret are required', 'error');
      return;
    }

    try {
      savingGlobal = true;
      await apiClient.post('/providers/spotify/settings', {
        client_id: clientId,
        client_secret: clientSecret,
        redirect_uri: redirectUri
      });
      feedback.addToast('Spotify credentials saved', 'success');
    } catch (error) {
      console.error('Failed to save Spotify settings:', error);
      feedback.addToast('Failed to save credentials', 'error');
    } finally {
      savingGlobal = false;
    }
  }

  async function loadAccounts() {
    try {
      const response = await apiClient.get('/accounts/spotify');
      accounts = response.data?.accounts || [];
    } catch (error) {
      console.error('Failed to load Spotify accounts:', error);
      accounts = [];
    }
  }

  async function addAccount() {
    if (!newAccountName.trim()) {
      feedback.addToast('Account name is required', 'error');
      return;
    }

    if (accounts.length >= MAX_ACCOUNTS) {
      feedback.addToast(`Maximum ${MAX_ACCOUNTS} accounts allowed`, 'error');
      return;
    }

    try {
      await apiClient.post('/accounts/spotify', {
        account_name: newAccountName,
        display_name: newAccountName
      });
      feedback.addToast('Account added', 'success');
      newAccountName = '';
      showAddAccount = false;
      await loadAccounts();
    } catch (error) {
      console.error('Failed to add account:', error);
      feedback.addToast('Failed to add account', 'error');
    }
  }

  async function toggleAccount(accountId, currentlyActive) {
    try {
      await apiClient.put(`/accounts/spotify/${accountId}/activate`, {
        is_active: !currentlyActive
      });
      feedback.addToast(currentlyActive ? 'Account deactivated' : 'Account activated', 'success');
      await loadAccounts();
    } catch (error) {
      console.error('Failed to toggle account:', error);
      feedback.addToast('Failed to update account', 'error');
    }
  }

  async function deleteAccount(accountId, accountName) {
    if (!confirm(`Delete account "${accountName}"?`)) return;

    try {
      await apiClient.delete(`/accounts/spotify/${accountId}`);
      feedback.addToast('Account deleted', 'success');
      await loadAccounts();
    } catch (error) {
      console.error('Failed to delete account:', error);
      feedback.addToast('Failed to delete account', 'error');
    }
  }

  async function authenticate(accountId) {
    // Ensure global credentials are saved before starting OAuth
    if (!clientId || !clientSecret) {
      feedback.addToast('Please save Spotify Client ID and Client Secret before authenticating an account', 'error');
      return;
    }

    try {
      // Request auth URL for this account and redirect the browser
      const resp = await apiClient.get('/spotify/auth', { params: { account_id: accountId } });
      const url = resp.data?.auth_url;
      if (url) {
        window.location.href = url;
      } else {
        feedback.addToast('Failed to get Spotify auth URL', 'error');
      }
    } catch (err) {
      console.error('Failed to start OAuth:', err);
      // Surface backend error message if available
      const msg = err?.response?.data?.error || 'Failed to start OAuth';
      feedback.addToast(msg, 'error');
    }
  }
</script>

<section class="spotify-card card">
  <div class="card-header">
    <div class="header-left">
      <h2>Spotify</h2>
      <span class="provider-badge">Streaming Service</span>
    </div>
  </div>

  {#if loading}
    <div class="loading">Loading...</div>
  {:else}
    <!-- Global Credentials (collapsible) -->
    <div class="section">
      <div class="section-header">
        <h3>Global Credentials</h3>
        <button class="btn-secondary" on:click={() => credsCollapsed = !credsCollapsed}>
          {credsCollapsed ? 'Expand' : 'Collapse'}
        </button>
      </div>

      {#if !credsCollapsed}
        <div class="form-group">
          <label>
            <span class="label-text">Client ID</span>
            <input 
              type="text" 
              bind:value={clientId} 
              placeholder="Enter Spotify Client ID"
              class="input"
            />
          </label>
          <label>
            <span class="label-text">Client Secret</span>
            <input 
              type="password" 
              bind:value={clientSecret} 
              placeholder="Enter Spotify Client Secret"
              class="input"
            />
          </label>
          <label>
            <span class="label-text">Redirect URI</span>
            <input
              type="text"
              bind:value={redirectUri}
              placeholder="http://127.0.0.1:8008/api/spotify/callback"
              class="input"
            />
          </label>
          <button 
            class="btn-primary" 
            on:click={saveGlobalSettings}
            disabled={savingGlobal}
          >
            {savingGlobal ? 'Saving...' : 'Save Credentials'}
          </button>
        </div>
      {/if}
    </div>

    <!-- Accounts -->
    <div class="section">
      <div class="section-header">
        <h3>Accounts ({accounts.length}/{MAX_ACCOUNTS})</h3>
        {#if accounts.length < MAX_ACCOUNTS}
          <button class="btn-secondary" on:click={() => showAddAccount = !showAddAccount}>
            + Add Account
          </button>
        {/if}
      </div>

      {#if showAddAccount}
        <div class="add-account-form">
          <input 
            type="text" 
            bind:value={newAccountName} 
            placeholder="Account name" 
            class="input"
            on:keydown={(e) => e.key === 'Enter' && addAccount()}
          />
          <button class="btn-primary" on:click={addAccount}>Add</button>
          <button class="btn-secondary" on:click={() => showAddAccount = false}>Cancel</button>
        </div>
      {/if}

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
              <button class="btn-delete" on:click={() => deleteAccount(account.id, account.display_name || account.account_name)}>
                ✕
              </button>
            </div>
          </div>
        {:else}
          <div class="empty-state">No accounts added yet</div>
        {/each}
      </div>
    </div>
  {/if}
</section>

<style>
  .spotify-card {
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
    background: rgba(29, 185, 84, 0.2);
    color: #1db954;
  }

  .section {
    margin-bottom: 24px;
  }

  .section h3 {
    margin: 0 0 12px 0;
    font-size: 16px;
    font-weight: 600;
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  label {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .label-text {
    font-size: 14px;
    color: var(--text);
  }

  .input {
    padding: 8px 12px;
    border-radius: 6px;
    background: var(--input-bg, rgba(255,255,255,0.05));
    border: 1px solid var(--border-color, rgba(255,255,255,0.1));
    color: var(--text);
    font-size: 14px;
  }

  .input:focus {
    outline: none;
    border-color: #1db954;
  }

  .btn-primary, .btn-secondary, .btn-link, .btn-toggle, .btn-delete {
    padding: 8px 16px;
    border-radius: 6px;
    border: none;
    cursor: pointer;
    font-size: 14px;
    transition: all 0.2s;
  }

  .btn-primary {
    background: #1db954;
    color: white;
  }

  .btn-primary:hover:not(:disabled) {
    background: #1ed760;
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
    color: #1db954;
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
    background: rgba(29, 185, 84, 0.2);
    color: #1db954;
  }

  .btn-toggle:hover {
    background: rgba(255,255,255,0.15);
  }

  .btn-delete {
    background: rgba(239, 68, 68, 0.2);
    color: #ef4444;
    padding: 6px 10px;
  }

  .btn-delete:hover {
    background: rgba(239, 68, 68, 0.3);
  }

  .add-account-form {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
    padding: 12px;
    background: rgba(255,255,255,0.05);
    border-radius: 6px;
  }

  .add-account-form .input {
    flex: 1;
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
    background: rgba(255,255,255,0.05);
    border-radius: 6px;
    border: 1px solid var(--border-color, rgba(255,255,255,0.1));
  }

  .account-info {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .account-name {
    font-weight: 500;
    font-size: 14px;
  }

  .account-status {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  .status-badge {
    font-size: 12px;
    padding: 2px 8px;
    border-radius: 4px;
  }

  .status-badge.authenticated {
    background: rgba(34, 197, 94, 0.2);
    color: #22c55e;
  }

  .status-badge.unauthenticated {
    background: rgba(251, 191, 36, 0.2);
    color: #fbbf24;
  }

  .status-badge.active {
    background: rgba(59, 130, 246, 0.2);
    color: #3b82f6;
  }

  .account-actions {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .empty-state {
    padding: 24px;
    text-align: center;
    color: var(--muted);
  }

  .loading {
    padding: 24px;
    text-align: center;
    color: var(--muted);
  }
  .collapsed-summary {
    padding: 12px;
    background: rgba(255,255,255,0.03);
    border-radius: 6px;
    color: var(--muted);
    font-size: 14px;
  }
</style>
