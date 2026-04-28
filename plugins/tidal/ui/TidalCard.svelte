<svelte:options customElement={{
  tag: 'tidal-dashboard-card',
  shadow: 'none'
}} />
<script>
  export let apiBase = '';
  import { onMount } from 'svelte';

  let accounts = [];
  let redirectUri = '';
  let redirectCollapsed = false;
  let loading = true;
  let savingRedirectUri = false;
  let showAddAccount = false;

  // Modal state for adding/editing account
  let showCredentialsModal = false;
  let modalMode = 'add'; // 'add' or 'edit'
  let modalAccount = {
    id: null,
    account_name: '',
    client_id: '',
    client_secret: ''
  };
  let secretChanged = false; // Track if user modified the secret field
  let showSecret = false; // Toggle password visibility

  const MAX_ACCOUNTS = 25;

  onMount(async () => {
    await loadAccounts();
    // Collapse redirect URI when already configured
    redirectCollapsed = Boolean(redirectUri);
    loading = false;
  });

  async function loadAccounts() {
    try {
      const response = await fetch(`${apiBase}/accounts/tidal`);
      const data = await response.json();
      if (data) {
        accounts = data.accounts || [];
        redirectUri = data.redirect_uri || '';
        redirectCollapsed = Boolean(redirectUri);
      }
    } catch (error) {
      console.error('Failed to load Tidal accounts:', error);
    }
  }

  async function saveRedirectUri() {
    if (!redirectUri.trim()) {
      console.error('Redirect URI is required');
      return;
    }

    try {
      savingRedirectUri = true;
      await fetch(`${apiBase}/accounts/tidal/redirect-uri`, { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({
          redirect_uri: redirectUri
        }) 
      });
      console.log('Redirect URI saved');
    } catch (error) {
      console.error('Failed to save redirect URI:', error);
    } finally {
      savingRedirectUri = false;
    }
  }

  function openAddModal() {
    modalMode = 'add';
    modalAccount = {
      id: null,
      account_name: '',
      client_id: '',
      client_secret: ''
    };
    secretChanged = true;
    showSecret = false;
    showCredentialsModal = true;
  }

  async function openEditModal(account) {
    modalMode = 'edit';
    try {
      const response = await fetch(`${apiBase}/accounts/tidal/${account.id}`);
      const data = await response.json();
      if (data?.account) {
        modalAccount = {
          id: data.account.id,
          account_name: data.account.account_name,
          client_id: data.account.client_id || '',
          client_secret: data.account.client_secret || ''
        };
        secretChanged = false;
        showSecret = false;
        showCredentialsModal = true;
      }
    } catch (error) {
      console.error('Failed to load account credentials:', error);
    }
  }

  function closeModal() {
    showCredentialsModal = false;
    secretChanged = false;
    showSecret = false;
    modalAccount = {
      id: null,
      account_name: '',
      client_id: '',
      client_secret: ''
    };
  }

  async function saveAccount() {
    if (!modalAccount.account_name.trim() || !modalAccount.client_id.trim()) {
      console.error('Account name and Client ID are required');
      return;
    }

    if (!modalAccount.client_secret.trim()) {
      console.error('Client Secret is required');
      return;
    }

    try {
      const accountData = {
        account_name: modalAccount.account_name,
        client_id: modalAccount.client_id,
        client_secret: modalAccount.client_secret
      };
      
      if (modalMode === 'add') {
        await fetch(`${apiBase}/accounts/tidal`, { 
          method: 'POST', 
          headers: { 'Content-Type': 'application/json' }, 
          body: JSON.stringify(accountData) 
        });
      } else {
        await fetch(`${apiBase}/accounts/tidal/${modalAccount.id}`, { 
          method: 'PUT', 
          headers: { 'Content-Type': 'application/json' }, 
          body: JSON.stringify(accountData) 
        });
      }
      closeModal();
      await loadAccounts();
    } catch (error) {
      console.error('Failed to save account:', error);
    }
  }

  async function toggleAccount(accountId, currentlyActive) {
    try {
      await fetch(`${apiBase}/accounts/tidal/${accountId}/activate`, { 
        method: 'PUT', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({
          is_active: !currentlyActive
        }) 
      });
      await loadAccounts();
    } catch (error) {
      console.error('Failed to toggle account:', error);
    }
  }

  async function deleteAccount(accountId, accountName) {
    if (!confirm(`Delete account "${accountName}"?`)) return;

    try {
      await fetch(`${apiBase}/accounts/tidal/${accountId}`, { method: 'DELETE' });
      await loadAccounts();
    } catch (error) {
      console.error('Failed to delete account:', error);
    }
  }

  async function authenticate(accountId) {
    try {
      const resp = await fetch(`${apiBase}/tidal/auth?account_id=${accountId}`);
      const data = await resp.json();
      const url = data?.auth_url;
      if (url) {
        window.location.href = url;
      } else {
        console.error('Failed to get Tidal auth URL');
      }
    } catch (err) {
      console.error('Failed to start OAuth:', err);
    }
  }
</script>

<section class="plugin-card">
  <div class="card-header">
    <div class="header-left">
      <h2 class="card-title">Tidal</h2>
      <span class="type-badge">Streaming Service</span>
    </div>
  </div>

  {#if loading}
    <div class="loading-state">Loading...</div>
  {:else}
    <!-- Global Redirect URI -->
    <div class="settings-section">
      <div class="section-header">
        <h3 class="section-title">Global Redirect URI (Immutable)</h3>
        <button class="btn-ghost" on:click={() => redirectCollapsed = !redirectCollapsed}>
          {redirectCollapsed ? 'Expand' : 'Collapse'}
        </button>
      </div>
      {#if !redirectCollapsed}
        <div class="form-grid">
          <input
            type="text"
            bind:value={redirectUri}
            class="input-field readonly"
            readonly
            disabled
          />
          <p class="helper-text">This auto-generated URI must be registered in your Tidal Developer Applications.</p>
        </div>
      {/if}
    </div>

    <!-- Accounts -->
    <div class="settings-section">
      <div class="section-header">
        <h3 class="section-title">Accounts ({accounts.length}/{MAX_ACCOUNTS})</h3>
        {#if accounts.length < MAX_ACCOUNTS}
          <button class="btn-ghost" on:click={openAddModal}>
            + Add Account
          </button>
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
              <button class="link-btn" on:click={() => openEditModal(account)}>⚙️ Edit</button>
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
          <div class="empty-accounts">No accounts added yet. Click "Add Account" to get started.</div>
        {/each}
      </div>
    </div>
  {/if}
</section>

<!-- Credentials Modal -->
{#if showCredentialsModal}
  <div class="modal-overlay" on:click={closeModal}>
    <div class="modal-content" on:click|stopPropagation>
      <div class="modal-header">
        <h3 class="modal-title">{modalMode === 'add' ? 'Add Tidal Account' : 'Edit Tidal Account'}</h3>
        <button class="close-btn" on:click={closeModal}>✕</button>
      </div>
      <div class="modal-body">
        <label class="form-field">
          <span class="field-label">Account Name</span>
          <input
            type="text"
            bind:value={modalAccount.account_name}
            placeholder="My Tidal Account"
            class="input-field"
          />
        </label>
        <label class="form-field">
          <span class="field-label">Client ID</span>
          <input
            type="text"
            bind:value={modalAccount.client_id}
            placeholder="Enter Tidal Client ID"
            class="input-field"
          />
        </label>
        <label class="form-field">
          <span class="field-label">Client Secret</span>
          <div class="password-wrapper">
            <input
              type={showSecret ? 'text' : 'password'}
              bind:value={modalAccount.client_secret}
              on:input={() => secretChanged = true}
              placeholder="Enter Tidal Client Secret"
              class="input-field"
            />
            <button 
              type="button" 
              class="toggle-visibility"
              on:click={() => showSecret = !showSecret}
            >
              {showSecret ? '🙈' : '👁️'}
            </button>
          </div>
        </label>
      </div>
      <div class="modal-footer">
        <button class="btn-ghost" on:click={closeModal}>Cancel</button>
        <button class="btn-primary" on:click={saveAccount}>
          {modalMode === 'add' ? 'Add Account' : 'Save Changes'}
        </button>
      </div>
    </div>
  </div>
{/if}

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
    gap: 12px;
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

  .helper-text {
    font-size: 11px;
    color: var(--text-muted, #64748b);
    margin-top: 4px;
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

  .btn-danger {
    background: rgba(239, 68, 68, 0.15);
    color: #ef4444;
    border: none;
    padding: 8px 12px;
    border-radius: 6px;
    cursor: pointer;
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
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.08));
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
  .close-btn { background: none; border: none; color: var(--text-muted, #64748b); font-size: 20px; cursor: pointer; }

  .modal-body {
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .modal-footer {
    padding: 16px 20px;
    border-top: 1px solid rgba(255,255,255,0.05);
    display: flex;
    justify-content: flex-end;
    gap: 12px;
  }

  .form-field {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .field-label { font-size: 13px; color: var(--text-muted, #64748b); }

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
