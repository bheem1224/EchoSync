<script>
  import { onMount } from 'svelte';
  import apiClient from '../api/client';
  import { feedback } from '../stores/feedback';

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
      const response = await apiClient.get('/accounts/tidal');
      if (response.data) {
        accounts = response.data.accounts || [];
        redirectUri = response.data.redirect_uri || '';
        redirectCollapsed = Boolean(redirectUri);
      }
    } catch (error) {
      console.error('Failed to load Tidal accounts:', error);
      feedback.addToast('Failed to load Tidal accounts', 'error');
    }
  }

  async function saveRedirectUri() {
    if (!redirectUri.trim()) {
      feedback.addToast('Redirect URI is required', 'error');
      return;
    }

    try {
      savingRedirectUri = true;
      await apiClient.post('/accounts/tidal/redirect-uri', {
        redirect_uri: redirectUri
      });
      feedback.addToast('Redirect URI saved', 'success');
    } catch (error) {
      console.error('Failed to save redirect URI:', error);
      feedback.addToast('Failed to save redirect URI', 'error');
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
    secretChanged = true; // New accounts always need secret
    showSecret = false;
    showCredentialsModal = true;
  }

  async function openEditModal(account) {
    modalMode = 'edit';
    try {
      // Fetch account with credentials
      const response = await apiClient.get(`/accounts/tidal/${account.id}`);
      if (response.data?.account) {
        modalAccount = {
          id: response.data.account.id,
          account_name: response.data.account.account_name,
          client_id: response.data.account.client_id || '',
          client_secret: response.data.account.client_secret || '' // Load actual value
        };
        secretChanged = false; // Only send if user types something
        showSecret = false; // Start hidden
        showCredentialsModal = true;
      }
    } catch (error) {
      console.error('Failed to load account credentials:', error);
      feedback.addToast('Failed to load account', 'error');
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
      feedback.addToast('Account name and Client ID are required', 'error');
      return;
    }

    if (!modalAccount.client_secret.trim()) {
      feedback.addToast('Client Secret is required', 'error');
      return;
    }

    if (modalMode === 'add' && accounts.length >= MAX_ACCOUNTS) {
      feedback.addToast(`Maximum ${MAX_ACCOUNTS} accounts allowed`, 'error');
      return;
    }

    try {
      const accountData = {
        account_name: modalAccount.account_name,
        client_id: modalAccount.client_id,
        client_secret: modalAccount.client_secret
      };
      
      if (modalMode === 'add') {
        await apiClient.post('/accounts/tidal', accountData);
        feedback.addToast('Account added', 'success');
      } else {
        await apiClient.put(`/accounts/tidal/${modalAccount.id}`, accountData);
        feedback.addToast('Account updated', 'success');
      }
      closeModal();
      await loadAccounts();
    } catch (error) {
      console.error('Failed to save account:', error);
      feedback.addToast('Failed to save account', 'error');
    }
  }

  async function toggleAccount(accountId, currentlyActive) {
    try {
      await apiClient.put(`/accounts/tidal/${accountId}/activate`, {
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
    if (!confirm(`Delete account "${accountName}"? This will also delete its credentials.`)) return;

    try {
      await apiClient.delete(`/accounts/tidal/${accountId}`);
      feedback.addToast('Account deleted', 'success');
      await loadAccounts();
    } catch (error) {
      console.error('Failed to delete account:', error);
      feedback.addToast('Failed to delete account', 'error');
    }
  }

  async function authenticate(accountId) {
    try {
      const resp = await apiClient.get('/tidal/auth', { params: { account_id: accountId } });
      const url = resp.data?.auth_url;
      if (url) {
        window.location.href = url;
      } else {
        feedback.addToast('Failed to get Tidal auth URL', 'error');
      }
    } catch (err) {
      console.error('Failed to start OAuth:', err);
      const msg = err?.response?.data?.error || 'Failed to start OAuth';
      feedback.addToast(msg, 'error');
    }
  }
</script>

<section class="tidal-card card">
  <div class="card-header">
    <div class="header-left">
      <h2>Tidal</h2>
      <span class="provider-badge">Streaming Service</span>
    </div>
  </div>

  {#if loading}
    <div class="loading">Loading...</div>
  {:else}
    <!-- Global Redirect URI -->
    <div class="section">
      <div class="section-header">
        <h3>Global Redirect URI</h3>
        <button class="btn-secondary" on:click={() => redirectCollapsed = !redirectCollapsed}>
          {redirectCollapsed ? 'Expand' : 'Collapse'}
        </button>
      </div>
      {#if !redirectCollapsed}
        <div class="redirect-uri-group">
          <input
            type="text"
            bind:value={redirectUri}
            placeholder="http://127.0.0.1:8000/api/tidal/callback"
            class="input"
          />
          <button 
            class="btn-primary" 
            on:click={saveRedirectUri}
            disabled={savingRedirectUri}
          >
            {savingRedirectUri ? 'Saving...' : 'Save'}
          </button>
        </div>
      {/if}
    </div>

    <!-- Accounts -->
    <div class="section">
      <div class="section-header">
        <h3>Accounts ({accounts.length}/{MAX_ACCOUNTS})</h3>
        <p class="help-text">Tidal requires per-account Client ID and Secret.</p>
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
                {#if account.client_secret_configured}
                  <span class="status-badge configured">🔒 Configured</span>
                {/if}
              </div>
            </div>
            <div class="account-actions">
              <button class="btn-link" on:click={() => openEditModal(account)} title="Edit credentials">
                ⚙️ Edit
              </button>
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
          <div class="empty-state">No accounts added yet. Click "Add Account" to get started.</div>
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
        <h3>{modalMode === 'add' ? 'Add Tidal Account' : 'Edit Tidal Account'}</h3>
        <button class="modal-close" on:click={closeModal}>✕</button>
      </div>
      <div class="modal-body">
        <label>
          <span class="label-text">Account Name</span>
          <input
            type="text"
            bind:value={modalAccount.account_name}
            placeholder="My Tidal Account"
            class="input"
          />
        </label>
        <label>
          <span class="label-text">Client ID</span>
          <input
            type="text"
            bind:value={modalAccount.client_id}
            placeholder="Enter Tidal Client ID"
            class="input"
          />
        </label>
        <label>
          <span class="label-text">Client Secret</span>
          <div class="password-field">
            <input
              type={showSecret ? 'text' : 'password'}
              bind:value={modalAccount.client_secret}
              on:input={() => secretChanged = true}
              placeholder="Enter Tidal Client Secret"
              class="input"
            />
            <button 
              type="button" 
              class="password-toggle" 
              on:click={() => showSecret = !showSecret}
              title={showSecret ? 'Hide' : 'Show'}
            >
              {showSecret ? '👁️' : '👁️‍🗨️'}
            </button>
          </div>
        </label>
        <p class="modal-help">Each Tidal account requires its own Client ID and Client Secret from the Tidal Developer Portal.</p>
      </div>
      <div class="modal-footer">
        <button class="btn-secondary" on:click={closeModal}>Cancel</button>
        <button class="btn-primary" on:click={saveAccount}>
          {modalMode === 'add' ? 'Add Account' : 'Save Changes'}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .tidal-card {
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
    background: rgba(0, 180, 255, 0.2);
    color: #00b4ff;
  }

  .section {
    margin-bottom: 24px;
  }

  .section h3 {
    margin: 0 0 8px 0;
    font-size: 16px;
    font-weight: 600;
  }

  .help-text {
    font-size: 13px;
    color: var(--muted);
    margin: 0 0 12px 0;
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

  .redirect-uri-group {
    display: flex;
    gap: 8px;
  }

  .redirect-uri-group .input {
    flex: 1;
  }

  .input {
    padding: 8px 12px;
    border-radius: 6px;
    background: var(--input-bg, rgba(255,255,255,0.05));
    border: 1px solid var(--border-color, rgba(255,255,255,0.1));
    color: var(--text);
    font-size: 14px;
    width: 100%;
  }

  .input:focus {
    outline: none;
    border-color: #00b4ff;
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
    background: #00b4ff;
    color: white;
  }

  .btn-primary:hover:not(:disabled) {
    background: #0099dd;
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
    color: #00b4ff;
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
    background: rgba(0, 180, 255, 0.2);
    color: #00b4ff;
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

  .status-badge.configured {
    background: rgba(168, 85, 247, 0.2);
    color: #a855f7;
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

  /* Modal Styles */
  .modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .modal-content {
    background: var(--card-bg, #1e1e1e);
    border-radius: 8px;
    width: 90%;
    max-width: 500px;
    max-height: 90vh;
    overflow-y: auto;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.5);
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px;
    border-bottom: 1px solid var(--border-color, rgba(255,255,255,0.1));
  }

  .modal-header h3 {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
  }

  .modal-close {
    background: transparent;
    border: none;
    color: var(--text);
    font-size: 20px;
    cursor: pointer;
    padding: 4px 8px;
  }

  .modal-close:hover {
    color: #ef4444;
  }

  .modal-body {
    padding: 20px;
  }

  .modal-body label {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-bottom: 16px;
  }

  .label-text {
    font-size: 14px;
    color: var(--text);
    font-weight: 500;
  }

  .modal-help {
    font-size: 13px;
    color: var(--muted);
    margin-top: 8px;
  }

  .password-field {
    position: relative;
    display: flex;
    align-items: center;
  }

  .password-field .input {
    flex: 1;
    padding-right: 40px;
  }

  .password-toggle {
    position: absolute;
    right: 8px;
    background: transparent;
    border: none;
    color: var(--text);
    cursor: pointer;
    font-size: 18px;
    padding: 4px 8px;
    opacity: 0.6;
    transition: opacity 0.2s;
  }

  .password-toggle:hover {
    opacity: 1;
  }

  .modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    padding: 16px 20px;
    border-top: 1px solid var(--border-color, rgba(255,255,255,0.1));
  }
</style>
