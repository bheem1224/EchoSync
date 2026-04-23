<svelte:options customElement={{
  tag: 'musicbrainz-dashboard-card',
  shadow: 'none'
}} />
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
      const statusResp = await fetch(`${apiBase}/musicbrainz/accounts`);
      if (statusResp.data) {
        accounts = statusResp.data.accounts || [];
        redirectUri = statusResp.data.redirect_uri || '';
        clientIdConfigured = statusResp.data.client_id_configured || false;
        clientSecretConfigured = statusResp.data.client_secret_configured || false;
        redirectCollapsed = Boolean(redirectUri);
      }

      // Load existing credentials for display
      const credsResp = await fetch(`${apiBase}/providers/musicbrainz/credentials`);
      if (credsResp.data?.credentials) {
        clientId = credsResp.data.credentials.client_id || '';
        // Never pre-fill the secret; show a placeholder if one is stored
        clientSecretPlaceholder = clientSecretConfigured ? '••••••••' : '';
      }
    } catch (err) {
      console.error('Failed to load MusicBrainz data:', err);
      console.error('Failed to load MusicBrainz settings');
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
      await fetch(`${apiBase}/providers/musicbrainz/credentials`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ credentials: creds }) });
      console.log('MusicBrainz credentials saved');
      clientSecret = '';
      await loadData();
    } catch (err) {
      console.error('Failed to save credentials');
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
      console.error('Account name is required');
      return;
    }
    try {
      savingAccount = true;
      await fetch(`${apiBase}/musicbrainz/accounts`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ account_name: name }) });
      console.log('Account added');
      closeAddModal();
      await loadData();
    } catch (err) {
      console.error('Failed to add account');
      console.error(err);
    } finally {
      savingAccount = false;
    }
  }

  async function deleteAccount(accountId, displayName) {
    if (!confirm(`Delete account "${displayName}"? This will also remove its stored tokens.`)) return;
    try {
      await fetch(`${apiBase}/musicbrainz/accounts/${accountId}`, { method: 'DELETE' });
      console.log('Account deleted');
      await loadData();
    } catch (err) {
      console.error('Failed to delete account');
    }
  }

  async function toggleAccount(accountId, currentlyActive) {
    try {
      await fetch(`${apiBase}/musicbrainz/accounts/${accountId}/activate`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
        is_active: !currentlyActive,
      }) });
      console.log(currentlyActive ? 'Account deactivated' : 'Account activated');
      await loadData();
    } catch (err) {
      console.error('Failed to update account status');
    }
  }

  async function authenticate(accountId) {
    if (!clientIdConfigured || !clientSecretConfigured) {
      console.log(
        'Save your MusicBrainz Client ID and Client Secret before authenticating.',
        'error'
      );
      return;
    }
    try {
      const resp = await fetch(`${apiBase}/musicbrainz/auth`, {
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
        console.error('Failed to get MusicBrainz auth URL');
      }
    } catch (err) {
      const msg = err?.response?.data?.error || 'Failed to start OAuth';
      console.error(msg);
    }
  }
</script>

<section class="p-6 bg-surface backdrop-blur-md border border-glass-border rounded-global mb-4">
  <div class="flex justify-between items-center mb-5 pb-3 border-b border-glass-border">
    <div class="flex items-center gap-3">
      <h2 class="m-0 text-xl font-semibold">MusicBrainz</h2>
      <span class="text-[12px] px-2 py-1 rounded-[4px] bg-[#ba6415]/20 text-[#ba6415]">Metadata</span>
    </div>
  </div>

  {#if loading}
    <div class="p-5 text-center text-secondary">Loading...</div>
  {:else}

    <!-- Application Credentials -->
    <div class="mb-6">
      <h3 class="m-0 mb-4 text-base font-semibold">Application Credentials</h3>
      <p class="text-xs text-secondary mt-1">
        Register an application at
        <a href="https://musicbrainz.org/account/applications" target="_blank" rel="noopener noreferrer">
          musicbrainz.org/account/applications
        </a>
        to obtain a Client ID and Secret. These are required for OAuth logins and ISRC submissions.
      </p>

      <div class="flex flex-col gap-3">
        <div class="flex flex-col gap-1">
          <label class="text-[13px] font-medium text-primary" for="mb-client-id">Client ID</label>
          <input
            id="mb-client-id"
            type="text"
            class="px-3 py-2 bg-background border border-border rounded-global text-sm text-primary w-full box-border focus:outline-none focus:border-accent"
            bind:value={clientId}
            placeholder="Enter your MusicBrainz Client ID"
          />
        </div>

        <div class="flex flex-col gap-1">
          <label class="text-[13px] font-medium text-primary" for="mb-client-secret">Client Secret</label>
          <div class="relative flex items-center">
            <input
              id="mb-client-secret"
              type={showSecret ? 'text' : 'password'}
              class="px-3 py-2 bg-background border border-border rounded-global text-sm text-primary w-full box-border focus:outline-none focus:border-accent"
              bind:value={clientSecret}
              placeholder={clientSecretConfigured ? '••••••••  (leave blank to keep current)' : 'Enter your MusicBrainz Client Secret'}
            />
            <button
              type="button"
              class="absolute right-2 bg-transparent border-none cursor-pointer text-lg p-1 opacity-60 hover:opacity-100 transition-opacity"
              on:click={() => (showSecret = !showSecret)}
              title={showSecret ? 'Hide' : 'Show'}
            >
              {showSecret ? '👁️' : '👁️‍🗨️'}
            </button>
          </div>
        </div>

        <button class="px-4 py-2 bg-accent text-black font-medium rounded-global transition-colors hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed" on:click={saveCredentials} disabled={savingCreds}>
          {savingCreds ? 'Saving…' : 'Save Credentials'}
        </button>
      </div>
    </div>

    <!-- Redirect URI (auto-generated, read-only) -->
    <div class="mb-6">
      <div class="mb-3">
        <h3 class="m-0 mb-4 text-base font-semibold">OAuth Redirect URI (Auto-generated)</h3>
        <button class="px-4 py-2 bg-white/10 text-primary border border-white/20 rounded-global transition-colors hover:bg-white/15 disabled:opacity-50 disabled:cursor-not-allowed" on:click={() => (redirectCollapsed = !redirectCollapsed)}>
          {redirectCollapsed ? 'Expand' : 'Collapse'}
        </button>
      </div>
      {#if !redirectCollapsed}
        <input
          type="text"
          class="px-3 py-2 bg-background/50 border border-border rounded-global text-sm text-primary w-full box-border opacity-70 cursor-not-allowed select-all"
          value={redirectUri}
          readonly
          disabled
        />
        <p class="text-xs text-secondary mt-1" style="margin-top:6px;">
          Add this URI as a callback URL in your MusicBrainz application settings.
        </p>
      {/if}
    </div>

    <!-- Accounts -->
    <div class="mb-6">
      <div class="mb-3">
        <h3 class="m-0 mb-4 text-base font-semibold">Accounts ({accounts.length}/{MAX_ACCOUNTS})</h3>
        <p class="text-xs text-secondary mt-1">
          Each account represents a MusicBrainz user that will authenticate via OAuth.
          Authenticated accounts can contribute ISRCs and metadata to MusicBrainz.
        </p>
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
              </div>
            </div>
            <div class="flex gap-2 items-center flex-wrap">
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
              <button
                class="px-4 py-2 bg-red-500/20 text-red-500 border-none rounded-global transition-colors hover:bg-red-500/30"
                on:click={() => deleteAccount(account.id, account.display_name || account.account_name)}
              >
                ✕
              </button>
            </div>
          </div>
        {:else}
          <div class="p-4 text-center text-secondary text-sm">
            No accounts added yet. Click "Add Account" to get started.
          </div>
        {/each}
      </div>
    </div>

  {/if}
</section>

<!-- Add Account Modal -->
{#if showAddModal}
  <div class="fixed inset-0 bg-black/60 flex items-center justify-center z-[1000]" on:click={closeAddModal}>
    <div class="bg-[#1e1e2e] rounded-[10px] p-0 min-w-[420px] max-w-[90vw] border border-white/15" on:click|stopPropagation>
      <div class="flex justify-between items-center px-5 py-4 border-b border-white/10">
        <h3 class="m-0 mb-4 text-base font-semibold">Add MusicBrainz Account</h3>
        <button class="bg-transparent border-none text-[18px] cursor-pointer text-secondary p-0 leading-none" on:click={closeAddModal}>✕</button>
      </div>
      <div class="p-5 flex flex-col gap-[14px]">
        <label class="flex flex-col gap-[6px]">
          <span class="text-[13px] font-medium text-primary">Display Name</span>
          <input
            type="text"
            bind:value={newAccountName}
            placeholder="e.g. My MusicBrainz Username"
            class="px-3 py-2 bg-background border border-border rounded-global text-sm text-primary w-full box-border focus:outline-none focus:border-accent"
          />
        </label>
        <p class="text-[12px] text-secondary m-0">
          Give this slot a friendly name. After adding, click "Authenticate" to link it
          to a real MusicBrainz account via OAuth.
        </p>
      </div>
      <div class="flex justify-end gap-[10px] px-5 py-4 border-t border-white/10">
        <button class="px-4 py-2 bg-white/10 text-primary border border-white/20 rounded-global transition-colors hover:bg-white/15 disabled:opacity-50 disabled:cursor-not-allowed" on:click={closeAddModal}>Cancel</button>
        <button class="px-4 py-2 bg-accent text-black font-medium rounded-global transition-colors hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed" on:click={addAccount} disabled={savingAccount}>
          {savingAccount ? 'Adding…' : 'Add Account'}
        </button>
      </div>
    </div>
  </div>
{/if}


