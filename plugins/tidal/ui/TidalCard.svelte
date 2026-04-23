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
      if (response.data) {
        accounts = response.data.accounts || [];
        redirectUri = response.data.redirect_uri || '';
        redirectCollapsed = Boolean(redirectUri);
      }
    } catch (error) {
      console.error('Failed to load Tidal accounts:', error);
      console.error('Failed to load Tidal accounts');
    }
  }

  async function saveRedirectUri() {
    if (!redirectUri.trim()) {
      console.error('Redirect URI is required');
      return;
    }

    try {
      savingRedirectUri = true;
      await fetch(`${apiBase}/accounts/tidal/redirect-uri`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
        redirect_uri: redirectUri
      }) });
      console.log('Redirect URI saved');
    } catch (error) {
      console.error('Failed to save redirect URI:', error);
      console.error('Failed to save redirect URI');
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
      const response = await fetch(`${apiBase}/accounts/tidal/${account.id}`);
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
      console.error('Failed to load account');
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

    if (modalMode === 'add' && accounts.length >= MAX_ACCOUNTS) {
      console.error(`Maximum ${MAX_ACCOUNTS} accounts allowed`);
      return;
    }

    try {
      const accountData = {
        account_name: modalAccount.account_name,
        client_id: modalAccount.client_id,
        client_secret: modalAccount.client_secret
      };
      
      if (modalMode === 'add') {
        await fetch(`${apiBase}/accounts/tidal`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(accountData) });
        console.log('Account added');
      } else {
        await fetch(`${apiBase}/accounts/tidal/${modalAccount.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(accountData) });
        console.log('Account updated');
      }
      closeModal();
      await loadAccounts();
    } catch (error) {
      console.error('Failed to save account:', error);
      console.error('Failed to save account');
    }
  }

  async function toggleAccount(accountId, currentlyActive) {
    try {
      await fetch(`${apiBase}/accounts/tidal/${accountId}/activate`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
        is_active: !currentlyActive
      }) });
      console.log(currentlyActive ? 'Account deactivated' : 'Account activated');
      await loadAccounts();
    } catch (error) {
      console.error('Failed to toggle account:', error);
      console.error('Failed to update account');
    }
  }

  async function deleteAccount(accountId, accountName) {
    if (!confirm(`Delete account "${accountName}"? This will also delete its credentials.`)) return;

    try {
      await fetch(`${apiBase}/accounts/tidal/${accountId}`, { method: 'DELETE' });
      console.log('Account deleted');
      await loadAccounts();
    } catch (error) {
      console.error('Failed to delete account:', error);
      console.error('Failed to delete account');
    }
  }

  async function authenticate(accountId) {
    try {
      const resp = await fetch(`${apiBase}/tidal/auth?account_id=${accountId}`);
      const url = resp.data?.auth_url;
      if (url) {
        window.location.href = url;
      } else {
        console.error('Failed to get Tidal auth URL');
      }
    } catch (err) {
      console.error('Failed to start OAuth:', err);
      const msg = err?.response?.data?.error || 'Failed to start OAuth';
      console.error(msg);
    }
  }
</script>

<section class="p-6 bg-surface backdrop-blur-md border border-glass-border rounded-global mb-4">
  <div class="flex justify-between items-center mb-5 pb-3 border-b border-glass-border">
    <div class="flex items-center gap-3">
      <h2 class="m-0 text-xl font-semibold">Tidal</h2>
      <span class="text-[12px] px-2 py-1 rounded-[4px] bg-[#ba6415]/20 text-[#ba6415]">Streaming Service</span>
    </div>
  </div>

  {#if loading}
    <div class="p-5 text-center text-secondary">Loading...</div>
  {:else}
    <!-- Global Redirect URI -->
    <div class="mb-6">
      <div class="mb-3">
        <h3 class="m-0 mb-4 text-base font-semibold">Global Redirect URI (Auto-generated & Immutable)</h3>
        <button class="px-4 py-2 bg-white/10 text-primary border border-white/20 rounded-global transition-colors hover:bg-white/15 disabled:opacity-50 disabled:cursor-not-allowed" on:click={() => redirectCollapsed = !redirectCollapsed}>
          {redirectCollapsed ? 'Expand' : 'Collapse'}
        </button>
      </div>
      {#if !redirectCollapsed}
        <div class="redirect-uri-group">
          <input
            type="text"
            bind:value={redirectUri}
            placeholder="Loading dynamic redirect URI..."
            class="px-3 py-2 bg-background/50 border border-border rounded-global text-sm text-primary w-full box-border opacity-70 cursor-not-allowed select-all"
            readonly={true}
            disabled={true}
          />
        </div>
        <p class="text-xs text-secondary mt-1" style="margin-top: 8px;">This auto-generated URI must be registered in all of your Tidal Developer Applications.</p>
      {/if}
    </div>

    <!-- Accounts -->
    <div class="mb-6">
      <div class="mb-3">
        <h3 class="m-0 mb-4 text-base font-semibold">Accounts ({accounts.length}/{MAX_ACCOUNTS})</h3>
        <p class="text-xs text-secondary mt-1">Tidal requires per-account Client ID and Secret.</p>
        {#if accounts.length < MAX_ACCOUNTS}
          <button class="px-4 py-2 bg-white/10 text-primary border border-white/20 rounded-global transition-colors hover:bg-white/15 disabled:opacity-50 disabled:cursor-not-allowed" on:click={openAddModal}>
            + Add Account
          </button>
        {/if}
      </div>

      <div class="flex flex-col gap-2">
        {#each accounts as account}
          <div class="flex justify-between items-center p-3 bg-white/5 border border-white/10 rounded-global">
            <div class="flex flex-col gap-1">
              <div class="font-medium text-[14px]">{account.display_name || account.account_name}</div>
              <div class="flex gap-[6px] flex-wrap">
                {#if account.is_authenticated}
                  <span class="text-[12px] px-2 py-1 rounded-[4px] bg-[#00e676]/20 text-[#00e676]">✓ Authenticated</span>
                {:else}
                  <span class="text-[12px] px-2 py-1 rounded-[4px] bg-yellow-500/20 text-yellow-500">⚠ Not Authenticated</span>
                {/if}
                {#if account.is_active}
                  <span class="text-[12px] px-2 py-1 rounded-[4px] bg-[#ba6415]/20 text-[#ba6415]">● Active</span>
                {/if}
                {#if account.client_secret_configured}
                  <span class="status-badge configured">🔒 Configured</span>
                {/if}
              </div>
            </div>
            <div class="flex gap-2 items-center flex-wrap">
              <button class="bg-transparent text-[#ba6415] px-2 py-1 hover:underline" on:click={() => openEditModal(account)} title="Edit credentials">
                ⚙️ Edit
              </button>
              <button class="bg-transparent text-[#ba6415] px-2 py-1 hover:underline" on:click={() => authenticate(account.id)}>
                {account.is_authenticated ? 'Reauthenticate' : 'Authenticate'}
              </button>
              <button 
                class="px-4 py-2 bg-white/10 text-primary border-none rounded-global transition-colors hover:bg-white/15"
                class:active={account.is_active}
                on:click={() => toggleAccount(account.id, account.is_active)}
                title={account.is_active ? 'Deactivate' : 'Activate'}
              >
                {account.is_active ? 'Deactivate' : 'Activate'}
              </button>
              <button class="px-4 py-2 bg-red-500/20 text-red-500 border-none rounded-global transition-colors hover:bg-red-500/30" on:click={() => deleteAccount(account.id, account.display_name || account.account_name)}>
                ✕
              </button>
            </div>
          </div>
        {:else}
          <div class="p-4 text-center text-secondary text-sm">No accounts added yet. Click "Add Account" to get started.</div>
        {/each}
      </div>
    </div>
  {/if}
</section>

<!-- Credentials Modal -->
{#if showCredentialsModal}
  <div class="fixed inset-0 bg-black/60 flex items-center justify-center z-[1000]" on:click={closeModal}>
    <div class="bg-[#1e1e2e] rounded-[10px] p-0 min-w-[420px] max-w-[90vw] border border-white/15" on:click|stopPropagation>
      <div class="flex justify-between items-center px-5 py-4 border-b border-white/10">
        <h3 class="m-0 mb-4 text-base font-semibold">{modalMode === 'add' ? 'Add Tidal Account' : 'Edit Tidal Account'}</h3>
        <button class="bg-transparent border-none text-[18px] cursor-pointer text-secondary p-0 leading-none" on:click={closeModal}>✕</button>
      </div>
      <div class="p-5 flex flex-col gap-[14px]">
        <label class="flex flex-col gap-[6px]">
          <span class="text-[13px] font-medium text-primary">Account Name</span>
          <input
            type="text"
            bind:value={modalAccount.account_name}
            placeholder="My Tidal Account"
            class="px-3 py-2 bg-background border border-border rounded-global text-sm text-primary w-full box-border focus:outline-none focus:border-accent"
          />
        </label>
        <label class="flex flex-col gap-[6px]">
          <span class="text-[13px] font-medium text-primary">Client ID</span>
          <input
            type="text"
            bind:value={modalAccount.client_id}
            placeholder="Enter Tidal Client ID"
            class="px-3 py-2 bg-background border border-border rounded-global text-sm text-primary w-full box-border focus:outline-none focus:border-accent"
          />
        </label>
        <label class="flex flex-col gap-[6px]">
          <span class="text-[13px] font-medium text-primary">Client Secret</span>
          <div class="relative flex items-center">
            <input
              type={showSecret ? 'text' : 'password'}
              bind:value={modalAccount.client_secret}
              on:input={() => secretChanged = true}
              placeholder="Enter Tidal Client Secret"
              class="px-3 py-2 bg-background border border-border rounded-global text-sm text-primary w-full box-border focus:outline-none focus:border-accent"
            />
            <button 
              type="button" 
              class="absolute right-2 bg-transparent border-none cursor-pointer text-lg p-1 opacity-60 hover:opacity-100 transition-opacity"
              on:click={() => showSecret = !showSecret}
              title={showSecret ? 'Hide' : 'Show'}
            >
              {showSecret ? '👁️' : '👁️‍🗨️'}
            </button>
          </div>
        </label>
        <p class="text-[12px] text-secondary m-0">Each Tidal account requires its own Client ID and Client Secret from the Tidal Developer Portal.</p>
      </div>
      <div class="flex justify-end gap-[10px] px-5 py-4 border-t border-white/10">
        <button class="px-4 py-2 bg-white/10 text-primary border border-white/20 rounded-global transition-colors hover:bg-white/15 disabled:opacity-50 disabled:cursor-not-allowed" on:click={closeModal}>Cancel</button>
        <button class="px-4 py-2 bg-accent text-black font-medium rounded-global transition-colors hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed" on:click={saveAccount}>
          {modalMode === 'add' ? 'Add Account' : 'Save Changes'}
        </button>
      </div>
    </div>
  </div>
{/if}


