<svelte:options customElement={{
  tag: 'spotify-dashboard-card',
  shadow: 'none'
}} />
<script>
  export let apiBase = '';
  import { onMount } from 'svelte';

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
      const response = await fetch(`${apiBase}/settings`);
      const data = await response.json();
      if (data?.settings) {
        clientId = data.settings.client_id || '';
        clientSecret = data.settings.client_secret || '';
        redirectUri = data.settings.redirect_uri || '';
      }
    } catch (error) {
      console.error('Failed to load Spotify settings:', error);
    }
  }

  async function saveGlobalSettings() {
    if (!clientId || !clientSecret) {
      console.error('Client ID and Secret are required');
      return;
    }

    try {
      savingGlobal = true;
      await fetch(`${apiBase}/settings`, { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({
          client_id: clientId,
          client_secret: clientSecret,
          redirect_uri: redirectUri
        }) 
      });
      console.log('Spotify credentials saved');
    } catch (error) {
      console.error('Failed to save Spotify settings:', error);
      throw error;
    } finally {
      savingGlobal = false;
    }
  }

  async function loadAccounts() {
    try {
      const response = await fetch(`${apiBase}/accounts/spotify`);
      const data = await response.json();
      accounts = data?.accounts || [];
    } catch (error) {
      console.error('Failed to load Spotify accounts:', error);
      accounts = [];
    }
  }

  async function addAccount() {
    if (!newAccountName.trim()) {
      console.error('Account name is required');
      return;
    }

    if (accounts.length >= MAX_ACCOUNTS) {
      console.error(`Maximum ${MAX_ACCOUNTS} accounts allowed`);
      return;
    }

    try {
      await fetch(`${apiBase}/accounts/spotify`, { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({
          account_name: newAccountName,
          display_name: newAccountName
        }) 
      });
      console.log('Account added');
      newAccountName = '';
      showAddAccount = false;
      await loadAccounts();
    } catch (error) {
      console.error('Failed to add account:', error);
    }
  }

  async function toggleAccount(accountId, currentlyActive) {
    try {
      await fetch(`${apiBase}/accounts/spotify/${accountId}/activate`, { 
        method: 'PUT', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({
          is_active: !currentlyActive
        }) 
      });
      console.log(currentlyActive ? 'Account deactivated' : 'Account activated');
      await loadAccounts();
    } catch (error) {
      console.error('Failed to toggle account:', error);
    }
  }

  async function deleteAccount(accountId, accountName) {
    if (!confirm(`Delete account "${accountName}"?`)) return;

    try {
      await fetch(`${apiBase}/accounts/spotify/${accountId}`, { method: 'DELETE' });
      console.log('Account deleted');
      await loadAccounts();
    } catch (error) {
      console.error('Failed to delete account:', error);
    }
  }

  async function authenticate(accountId) {
    if (!clientId || !clientSecret) {
      console.error('Please save Spotify Client ID and Client Secret before authenticating an account');
      return;
    }

    try {
        await saveGlobalSettings();
    } catch (e) {
        return;
    }

    try {
      const resp = await fetch(`${apiBase}/auth?account_id=${accountId}`);
      const data = await resp.json();
      const url = data?.auth_url;
      if (url) {
        window.location.href = url;
      } else {
        console.error('Failed to get Spotify auth URL');
      }
    } catch (err) {
      console.error('Failed to start OAuth:', err);
    }
  }
</script>

<section class="plugin-card">
  <div class="card-header">
    <div class="header-left">
      <h2 class="card-title">Spotify</h2>
      <span class="type-badge">Streaming Service</span>
    </div>
  </div>

  {#if loading}
    <div class="loading-state">Loading...</div>
  {:else}
    <!-- Global Credentials -->
    <div class="settings-section">
      <div class="section-header">
        <h3 class="section-title">Global Credentials</h3>
        <button class="btn-ghost" on:click={() => credsCollapsed = !credsCollapsed}>
          {credsCollapsed ? 'Expand' : 'Collapse'}
        </button>
      </div>

      {#if !credsCollapsed}
        <div class="form-grid">
          <label class="form-field">
            <span class="field-label">Client ID</span>
            <input 
              type="text" 
              bind:value={clientId} 
              placeholder="Enter Spotify Client ID"
              class="input-field"
            />
          </label>
          <label class="form-field">
            <span class="field-label">Client Secret</span>
            <input 
              type="password" 
              bind:value={clientSecret} 
              placeholder="Enter Spotify Client Secret"
              class="input-field"
            />
          </label>
          <label class="form-field">
            <span class="field-label">Redirect URI (Immutable)</span>
            <input
              type="text"
              bind:value={redirectUri}
              class="input-field readonly"
              readonly
              disabled
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
    <div class="settings-section">
      <div class="section-header">
        <h3 class="section-title">Accounts ({accounts.length}/{MAX_ACCOUNTS})</h3>
        {#if accounts.length < MAX_ACCOUNTS}
          <button class="btn-ghost" on:click={() => showAddAccount = !showAddAccount}>
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
            class="input-field"
            on:keydown={(e) => e.key === 'Enter' && addAccount()}
          />
          <div class="form-actions">
            <button class="btn-primary" on:click={addAccount}>Add</button>
            <button class="btn-ghost" on:click={() => showAddAccount = false}>Cancel</button>
          </div>
        </div>
      {/if}

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
              <button 
                class="btn-ghost"
                class:active={account.is_active}
                on:click={() => toggleAccount(account.id, account.is_active)}
              >
                {account.is_active ? 'Deactivate' : 'Activate'}
              </button>
              <button class="btn-danger" on:click={() => deleteAccount(account.id, account.display_name || account.account_name)}>
                ✕
              </button>
            </div>
          </div>
        {:else}
          <div class="empty-accounts">No accounts added yet</div>
        {/each}
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
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border-subtle, rgba(255,255,255,0.08));
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .card-title {
    margin: 0;
    font-size: 20px;
    font-weight: 700;
  }

  .type-badge {
    font-size: 11px;
    padding: 4px 8px;
    background: rgba(20, 184, 166, 0.15);
    color: var(--color-primary, #14b8a6);
    border-radius: 4px;
    font-weight: 600;
    text-transform: uppercase;
  }

  .loading-state {
    padding: 24px;
    text-align: center;
    color: var(--text-muted, #64748b);
  }

  .settings-section {
    margin-bottom: 24px;
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
  }

  .section-title {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    color: var(--text-main, #fff);
  }

  .form-grid {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .form-field {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .field-label {
    font-size: 13px;
    font-weight: 500;
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

  .input-field.readonly {
    opacity: 0.6;
    cursor: not-allowed;
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

  .btn-primary:hover {
    opacity: 0.9;
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

  .btn-ghost:hover {
    background: rgba(255,255,255,0.1);
  }

  .add-account-form {
    background: rgba(255,255,255,0.03);
    padding: 16px;
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-bottom: 16px;
  }

  .form-actions {
    display: flex;
    gap: 8px;
  }

  .accounts-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .account-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 8px;
  }

  .account-info {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .account-name {
    font-weight: 600;
    font-size: 14px;
  }

  .account-badges {
    display: flex;
    gap: 8px;
  }

  .status-badge {
    font-size: 10px;
    padding: 2px 6px;
    border-radius: 4px;
    font-weight: 700;
  }

  .status-badge.success { background: rgba(34, 197, 94, 0.15); color: #22c55e; }
  .status-badge.warning { background: rgba(234, 179, 8, 0.15); color: #eab308; }
  .status-badge.active { background: rgba(20, 184, 166, 0.15); color: var(--color-primary, #14b8a6); }

  .account-actions {
    display: flex;
    gap: 12px;
    align-items: center;
  }

  .link-btn {
    background: none;
    border: none;
    color: var(--color-primary, #14b8a6);
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
  }

  .link-btn:hover {
    text-decoration: underline;
  }

  .btn-danger {
    background: rgba(239, 68, 68, 0.15);
    color: #ef4444;
    border: none;
    padding: 8px 12px;
    border-radius: 6px;
    cursor: pointer;
  }

  .empty-accounts {
    text-align: center;
    padding: 16px;
    color: var(--text-muted, #64748b);
    font-size: 13px;
    background: rgba(255,255,255,0.02);
    border-radius: 8px;
    border: 1px dashed rgba(255,255,255,0.1);
  }
</style>
