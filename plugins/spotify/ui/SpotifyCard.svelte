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
      const response = await fetch(`${apiBase}/providers/spotify/settings`);
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
      console.error('Client ID and Secret are required');
      return;
    }

    try {
      savingGlobal = true;
      await fetch(`${apiBase}/providers/spotify/settings`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
        client_id: clientId,
        client_secret: clientSecret,
        redirect_uri: redirectUri
      }) });
      console.log('Spotify credentials saved');
    } catch (error) {
      console.error('Failed to save Spotify settings:', error);
      console.error('Failed to save credentials');
      throw error; // Re-throw to allow caller to handle failure
    } finally {
      savingGlobal = false;
    }
  }

  async function loadAccounts() {
    try {
      const response = await fetch(`${apiBase}/accounts/spotify`);
      accounts = response.data?.accounts || [];
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
      await fetch(`${apiBase}/accounts/spotify`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
        account_name: newAccountName,
        display_name: newAccountName
      }) });
      console.log('Account added');
      newAccountName = '';
      showAddAccount = false;
      await loadAccounts();
    } catch (error) {
      console.error('Failed to add account:', error);
      console.error('Failed to add account');
    }
  }

  async function toggleAccount(accountId, currentlyActive) {
    try {
      await fetch(`${apiBase}/accounts/spotify/${accountId}/activate`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
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
    if (!confirm(`Delete account "${accountName}"?`)) return;

    try {
      await fetch(`${apiBase}/accounts/spotify/${accountId}`, { method: 'DELETE' });
      console.log('Account deleted');
      await loadAccounts();
    } catch (error) {
      console.error('Failed to delete account:', error);
      console.error('Failed to delete account');
    }
  }

  async function authenticate(accountId) {
    // Ensure global credentials are saved before starting OAuth
    if (!clientId || !clientSecret) {
      console.error('Please save Spotify Client ID and Client Secret before authenticating an account');
      return;
    }

    // Force save settings first to ensure backend has the latest Redirect URI
    // This fixes the issue where auto-populated URI isn't seen by backend until manual save
    try {
        await saveGlobalSettings();
    } catch (e) {
        // saveGlobalSettings already shows toast, just abort
        return;
    }

    try {
      // Request auth URL for this account and redirect the browser
      const resp = await fetch(`${apiBase}/spotify/auth`, { params: { account_id: accountId } });
      const url = resp.data?.auth_url;
      if (url) {
        window.location.href = url;
      } else {
        console.error('Failed to get Spotify auth URL');
      }
    } catch (err) {
      console.error('Failed to start OAuth:', err);
      // Surface backend error message if available
      const msg = err?.response?.data?.error || 'Failed to start OAuth';
      console.error(msg);
    }
  }
</script>

<section class="p-6 bg-surface backdrop-blur-md border border-glass-border rounded-global mb-4">
  <div class="flex justify-between items-center mb-5 pb-3 border-b border-glass-border">
    <div class="flex items-center gap-3">
      <h2 class="m-0 text-xl font-semibold">Spotify</h2>
      <span class="text-[12px] px-2 py-1 rounded-[4px] bg-[#ba6415]/20 text-[#ba6415]">Streaming Service</span>
    </div>
  </div>

  {#if loading}
    <div class="p-5 text-center text-secondary">Loading...</div>
  {:else}
    <!-- Global Credentials (collapsible) -->
    <div class="mb-6">
      <div class="mb-3">
        <h3 class="m-0 mb-4 text-base font-semibold">Global Credentials</h3>
        <button class="px-4 py-2 bg-white/10 text-primary border border-white/20 rounded-global transition-colors hover:bg-white/15 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95" on:click={() => credsCollapsed = !credsCollapsed}>
          {credsCollapsed ? 'Expand' : 'Collapse'}
        </button>
      </div>

      {#if !credsCollapsed}
        <div class="flex flex-col gap-4">
          <label class="flex flex-col gap-[6px]">
            <span class="text-[13px] font-medium text-primary">Client ID</span>
            <input 
              type="text" 
              bind:value={clientId} 
              placeholder="Enter Spotify Client ID"
              class="px-3 py-2 bg-background border border-border rounded-global text-sm text-primary w-full box-border focus:outline-none focus:border-accent"
            />
          </label>
          <label class="flex flex-col gap-[6px]">
            <span class="text-[13px] font-medium text-primary">Client Secret</span>
            <input 
              type="password" 
              bind:value={clientSecret} 
              placeholder="Enter Spotify Client Secret"
              class="px-3 py-2 bg-background border border-border rounded-global text-sm text-primary w-full box-border focus:outline-none focus:border-accent"
            />
          </label>
          <label class="flex flex-col gap-[6px]">
            <span class="text-[13px] font-medium text-primary">Redirect URI (Auto-generated & Immutable)</span>
            <input
              type="text"
              bind:value={redirectUri}
              placeholder="Loading dynamic redirect URI..."
              class="px-3 py-2 bg-background/50 border border-border rounded-global text-sm text-primary w-full box-border opacity-70 cursor-not-allowed select-all"
              readonly={true}
              disabled={true}
            />
          </label>
          <button 
            class="px-4 py-2 bg-accent text-black font-medium rounded-global transition-colors hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95"
            on:click={saveGlobalSettings}
            disabled={savingGlobal}
          >
            {savingGlobal ? 'Saving...' : 'Save Credentials'}
          </button>
        </div>
      {/if}
    </div>

    <!-- Accounts -->
    <div class="mb-6">
      <div class="mb-3">
        <h3 class="m-0 mb-4 text-base font-semibold">Accounts ({accounts.length}/{MAX_ACCOUNTS})</h3>
        {#if accounts.length < MAX_ACCOUNTS}
          <button class="px-4 py-2 bg-white/10 text-primary border border-white/20 rounded-global transition-colors hover:bg-white/15 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95" on:click={() => showAddAccount = !showAddAccount}>
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
            class="px-3 py-2 bg-background border border-border rounded-global text-sm text-primary w-full box-border focus:outline-none focus:border-accent"
            on:keydown={(e) => e.key === 'Enter' && addAccount()}
          />
          <button class="px-4 py-2 bg-accent text-black font-medium rounded-global transition-colors hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95" on:click={addAccount}>Add</button>
          <button class="px-4 py-2 bg-white/10 text-primary border border-white/20 rounded-global transition-colors hover:bg-white/15 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95" on:click={() => showAddAccount = false}>Cancel</button>
        </div>
      {/if}

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
              </div>
            </div>
            <div class="flex gap-2 items-center flex-wrap">
                <button class="bg-transparent text-[#ba6415] px-2 py-1 hover:underline active:scale-95 transition-all duration-200" on:click={() => authenticate(account.id)}>
                  {account.is_authenticated ? 'Reauthenticate' : 'Authenticate'}
                </button>
              <button 
                class="px-4 py-2 bg-white/10 text-primary border-none rounded-global transition-colors hover:bg-white/15 active:scale-95"
                class:active={account.is_active}
                on:click={() => toggleAccount(account.id, account.is_active)}
                title={account.is_active ? 'Deactivate' : 'Activate'}
              >
                {account.is_active ? 'Deactivate' : 'Activate'}
              </button>
              <button class="px-4 py-2 bg-red-500/20 text-red-500 border-none rounded-global transition-colors hover:bg-red-500/30 active:scale-95" on:click={() => deleteAccount(account.id, account.display_name || account.account_name)}>
                ✕
              </button>
            </div>
          </div>
        {:else}
          <div class="p-4 text-center text-secondary text-sm">No accounts added yet</div>
        {/each}
      </div>
    </div>
  {/if}
</section>


