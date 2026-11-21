<script lang="ts">
  import { onMount } from 'svelte';
  import { fade, slide } from 'svelte/transition';
  import {
    createApiKey,
    createUser,
    deleteApiKey,
    listApiKeys,
    listExternalAccounts,
    listUsers,
    unbindExternalAccount,
    type ApiKeyRecord,
    type AuthUser,
    type ExternalAccountBinding,
  } from '../../api/client';
  import { feedback } from '../../stores/feedback';
  import LinkAccountModal from './LinkAccountModal.svelte';

  let users = $state<AuthUser[]>([]);
  let externalBindingsByUser = $state<Record<string, ExternalAccountBinding[]>>({});
  let apiKeys = $state<ApiKeyRecord[]>([]);
  let newlyCreatedRawKey = $state<string | null>(null);
  let loading = $state(true);
  let errorMsg = $state('');

  // Create User Modal state
  let showCreateUserModal = $state(false);
  let newUsername = $state('');
  let newPassword = $state('');
  let newRole = $state<'admin' | 'member'>('member');
  let showNewPassword = $state(false);
  let creatingUser = $state(false);

  // Edit / Link External Accounts Modal state
  let editingUser = $state<AuthUser | null>(null);
  let showLinkModal = $state(false);

  // API key form state
  let newApiKeyName = $state('');
  let creatingApiKey = $state(false);

  // NIST SP 800-63B-4 validation for new local user password
  const normalizedNewPw = $derived(newPassword ? newPassword.normalize('NFKC') : '');
  const newPwLen = $derived(Array.from(normalizedNewPw).length);
  const newPwValid = $derived(newPwLen >= 8 && newPwLen <= 512);
  const newPwRecommended = $derived(newPwLen >= 15);
  const newPwPassphrase = $derived(newPwLen >= 64);

  async function loadAll() {
    loading = true;
    errorMsg = '';
    try {
      const [usersData, keysData] = await Promise.all([
        listUsers().catch(() => ({ users: [], total: 0 })),
        listApiKeys().catch(() => ({ api_keys: [], total: 0 })),
      ]);

      users = usersData.users || [];
      apiKeys = keysData.api_keys || [];

      const bindingsMap: Record<string, ExternalAccountBinding[]> = {};
      await Promise.all(
        users.map(async (u) => {
          try {
            const b = await listExternalAccounts(u.id);
            bindingsMap[u.id] = b.external_accounts || [];
          } catch {
            bindingsMap[u.id] = [];
          }
        })
      );
      externalBindingsByUser = bindingsMap;
    } catch (err: any) {
      errorMsg = err?.response?.data?.detail || err?.message || 'Failed to load user management data.';
    } finally {
      loading = false;
    }
  }

  async function handleCreateUser(e: Event) {
    e.preventDefault();
    if (!newUsername.trim() || !newPwValid || creatingUser) return;

    creatingUser = true;
    errorMsg = '';
    try {
      const res = await createUser({
        username: newUsername.trim(),
        password: newPassword,
        roles: [newRole],
        auth_provider: 'local',
      });
      if (res.user) {
        feedback.addToast(`Created user "${res.user.username}" (${newRole})`, 'success');
        newUsername = '';
        newPassword = '';
        newRole = 'member';
        showCreateUserModal = false;
        await loadAll();
      }
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to create user';
      errorMsg = msg;
      feedback.addToast(msg, 'error');
    } finally {
      creatingUser = false;
    }
  }

  async function handleQuickUnbind(userId: string, b: ExternalAccountBinding) {
    try {
      const res = await unbindExternalAccount(userId, b.provider, b.external_account_id);
      externalBindingsByUser = {
        ...externalBindingsByUser,
        [userId]: res.external_accounts || [],
      };
      feedback.addToast(`Unbound ${b.provider}: ${b.display_name || b.external_account_id}`, 'success');
    } catch (err: any) {
      feedback.addToast(err?.response?.data?.detail || 'Failed to unbind account', 'error');
    }
  }

  function openManageModal(u: AuthUser) {
    editingUser = u;
    showLinkModal = true;
  }

  async function handleCreateApiKey(e: Event) {
    e.preventDefault();
    if (!newApiKeyName.trim() || creatingApiKey) return;

    creatingApiKey = true;
    newlyCreatedRawKey = null;
    try {
      const res = await createApiKey({ name: newApiKeyName.trim() });
      if (res.api_key) {
        newlyCreatedRawKey = res.api_key;
      }
      newApiKeyName = '';
      const keysData = await listApiKeys();
      apiKeys = keysData.api_keys || [];
      feedback.addToast('API key generated', 'success');
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to generate API key';
      feedback.addToast(msg, 'error');
    } finally {
      creatingApiKey = false;
    }
  }

  async function handleRevokeApiKey(keyId: string) {
    try {
      await deleteApiKey(keyId);
      apiKeys = apiKeys.filter((k) => k.id !== keyId);
      feedback.addToast('API key revoked', 'success');
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to revoke API key';
      feedback.addToast(msg, 'error');
    }
  }

  onMount(() => {
    loadAll();
  });
</script>

<section class="space-y-6">
  <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
    <div>
      <span class="text-xs font-bold uppercase tracking-wider" style="color: var(--color-primary);">
        Identity &amp; Access Control
      </span>
      <h2 class="text-xl font-bold mt-0.5" style="color: var(--text-primary);">
        Users &amp; External Accounts
      </h2>
      <p class="text-xs mt-1" style="color: var(--text-muted);">
        Manage EchoSync users, RBAC roles, and bound external accounts (Spotify, Tidal, ListenBrainz, Plex, Jellyfin, Navidrome).
      </p>
    </div>

    <div class="flex items-center gap-2.5 self-start sm:self-auto">
      <button
        type="button"
        onclick={loadAll}
        class="px-3.5 py-2 rounded-xl text-xs font-semibold border transition-all active:scale-95"
        style="background-color: var(--bg-surface-elevated); border-color: var(--border-subtle); color: var(--text-primary);"
      >
        {loading ? 'Refreshing…' : '↻ Refresh'}
      </button>
      <button
        type="button"
        onclick={() => (showCreateUserModal = true)}
        class="px-4 py-2 rounded-xl text-xs font-bold transition-all active:scale-95"
        style="background-color: var(--color-primary); color: #020617;"
      >
        + Create User
      </button>
    </div>
  </div>

  {#if errorMsg}
    <div
      class="p-3.5 rounded-xl text-xs font-medium border"
      style="background: rgba(239, 68, 68, 0.12); border-color: rgba(239, 68, 68, 0.4); color: #fca5a5;"
      role="alert"
    >
      {errorMsg}
    </div>
  {/if}

  <!-- Registered Users Full-Width Directory -->
  <div
    class="rounded-2xl border overflow-hidden"
    style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
  >
    <div class="px-5 py-4 border-b flex items-center justify-between" style="border-color: var(--border-subtle);">
      <h3 class="text-sm font-bold" style="color: var(--text-primary);">
        Registered Users ({users.length})
      </h3>
    </div>

    {#if loading && users.length === 0}
      <div class="p-8 text-center text-xs" style="color: var(--text-muted);">
        Loading users and external account bindings…
      </div>
    {:else if users.length === 0}
      <div class="p-8 text-center text-xs" style="color: var(--text-muted);">
        No users registered yet.
      </div>
    {:else}
      <div class="divide-y" style="border-color: var(--border-subtle);">
        {#each users as user (user.id)}
          {@const bindings = externalBindingsByUser[user.id] || []}
          {@const isAdmin = (user.roles || []).includes('admin')}
          <div class="p-4 sm:px-5 flex flex-col lg:flex-row lg:items-center justify-between gap-4" transition:fade={{ duration: 150 }}>
            <div class="space-y-1.5 min-w-0 flex-1">
              <div class="flex items-center gap-2.5 flex-wrap">
                <span class="font-bold text-sm" style="color: var(--text-primary);">
                  {user.username}
                </span>
                <span
                  class="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider"
                  style={isAdmin
                    ? 'background: rgba(20, 184, 166, 0.16); color: var(--color-primary); border: 1px solid rgba(20, 184, 166, 0.35);'
                    : 'background: rgba(148, 163, 184, 0.12); color: var(--text-secondary); border: 1px solid var(--border-subtle);'}
                >
                  {isAdmin ? 'ADMIN' : 'MEMBER'}
                </span>
                <span
                  class="px-2 py-0.5 rounded text-[10px] font-mono uppercase"
                  style="background-color: var(--bg-surface-elevated); color: var(--text-muted);"
                >
                  {(user.auth_provider || 'local').toUpperCase()}
                </span>
              </div>

              <!-- Unified Bound External Accounts Pills -->
              <div class="flex flex-wrap items-center gap-1.5 pt-0.5">
                <span class="text-[11px]" style="color: var(--text-muted);">External Accounts:</span>
                {#if bindings.length === 0}
                  <span class="text-[11px] italic" style="color: var(--text-muted);">None bound</span>
                {:else}
                  {#each bindings as b (`${b.provider}:${b.external_account_id}`)}
                    <span
                      class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border"
                      style="background-color: var(--bg-surface-elevated); border-color: rgba(20, 184, 166, 0.3); color: var(--text-primary);"
                      transition:slide={{ duration: 150 }}
                    >
                      <span class="text-[10px] font-bold uppercase" style="color: var(--color-primary);">
                        {b.provider}:
                      </span>
                      <span>{b.display_name || b.external_account_id}</span>
                      <button
                        type="button"
                        onclick={() => handleQuickUnbind(user.id, b)}
                        class="ml-0.5 hover:opacity-100 opacity-60 text-xs"
                        style="color: var(--color-danger, #f87171);"
                        title="Unbind external account"
                        aria-label="Unbind external account"
                      >
                        ✕
                      </button>
                    </span>
                  {/each}
                {/if}
              </div>
            </div>

            <div class="flex items-center gap-2 shrink-0">
              <button
                type="button"
                onclick={() => openManageModal(user)}
                class="px-3.5 py-2 rounded-xl text-xs font-semibold border transition-all hover:border-teal-400 active:scale-95"
                style="background-color: var(--bg-surface-elevated); border-color: var(--border-subtle); color: var(--text-primary);"
              >
                Manage Accounts / Edit
              </button>
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </div>

  <!-- Personal / Automation API Keys Section -->
  <div
    class="rounded-2xl border p-5 space-y-4"
    style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
  >
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-3">
      <div>
        <h3 class="text-sm font-bold" style="color: var(--text-primary);">
          API Keys ({apiKeys.length})
        </h3>
        <p class="text-xs mt-0.5" style="color: var(--text-muted);">
          Issue scoped bearer / <code>X-API-Key</code> tokens for headless integrations and scripts.
        </p>
      </div>

      <form onsubmit={handleCreateApiKey} class="flex items-center gap-2 w-full md:w-auto md:min-w-[380px]">
        <input
          type="text"
          bind:value={newApiKeyName}
          placeholder="Key label (e.g. CLI Automation)"
          class="input-field text-xs py-2 min-w-[240px] flex-1"
        />
        <button
          type="submit"
          disabled={!newApiKeyName.trim() || creatingApiKey}
          class="px-3.5 py-2 rounded-xl text-xs font-bold whitespace-nowrap transition-all active:scale-95 disabled:opacity-40 shrink-0"
          style="background-color: var(--color-primary); color: #020617;"
        >
          {creatingApiKey ? 'Generating…' : '+ New API Key'}
        </button>
      </form>
    </div>

    {#if newlyCreatedRawKey}
      <div
        class="p-3.5 rounded-xl border space-y-1.5"
        style="background: rgba(20, 184, 166, 0.12); border-color: rgba(20, 184, 166, 0.4);"
      >
        <div class="text-xs font-bold" style="color: var(--color-primary);">
          Copy your new API key now — it will not be shown again:
        </div>
        <div class="font-mono text-xs break-all p-2 rounded-lg" style="background-color: var(--bg-input); color: var(--text-primary);">
          {newlyCreatedRawKey}
        </div>
      </div>
    {/if}

    {#if apiKeys.length > 0}
      <div class="divide-y" style="border-color: var(--border-subtle);">
        {#each apiKeys as key (key.id)}
          <div class="py-2.5 flex items-center justify-between gap-3 text-xs">
            <div class="flex items-center gap-3">
              <span class="font-semibold" style="color: var(--text-primary);">{key.name}</span>
              <span class="font-mono px-2 py-0.5 rounded" style="background-color: var(--bg-surface-elevated); color: var(--text-muted);">
                {key.key_prefix}…
              </span>
            </div>
            <button
              type="button"
              onclick={() => handleRevokeApiKey(key.id)}
              class="px-2.5 py-1 rounded-lg text-xs font-semibold border transition-colors"
              style="border-color: rgba(239, 68, 68, 0.35); color: #fca5a5;"
            >
              Revoke
            </button>
          </div>
        {/each}
      </div>
    {/if}
  </div>
</section>

<!-- Create User Pop-Up Modal -->
{#if showCreateUserModal}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div
    class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm"
    onclick={(e) => { if (e.target === e.currentTarget) showCreateUserModal = false; }}
    transition:fade={{ duration: 150 }}
    role="dialog"
    aria-modal="true"
  >
    <div
      class="w-full max-w-md rounded-2xl border shadow-2xl overflow-hidden"
      style="background-color: var(--bg-surface, #0f172a); border-color: var(--border-subtle);"
    >
      <div class="px-6 py-4 border-b flex items-center justify-between" style="border-color: var(--border-subtle);">
        <div>
          <span class="text-[10px] font-bold uppercase tracking-widest" style="color: var(--color-primary);">
            New Account
          </span>
          <h3 class="text-base font-bold mt-0.5" style="color: var(--text-primary);">
            Create Local User
          </h3>
        </div>
        <button
          type="button"
          onclick={() => (showCreateUserModal = false)}
          class="w-8 h-8 rounded-lg flex items-center justify-center border hover:bg-white/10"
          style="border-color: var(--border-subtle); color: var(--text-muted);"
          aria-label="Close modal"
        >
          ✕
        </button>
      </div>

      <form onsubmit={handleCreateUser} class="p-6 space-y-4">
        <p class="text-xs" style="color: var(--text-muted);">
          NIST SP 800-63B-4 policy: 8+ chars minimum, 15+ recommended, 64+ passphrases with spaces/Unicode supported.
        </p>

        <div>
          <label for="new-user-username" class="block text-xs font-semibold mb-1" style="color: var(--text-secondary);">
            Username
          </label>
          <input
            id="new-user-username"
            type="text"
            bind:value={newUsername}
            required
            placeholder="e.g. alice"
            class="input-field w-full"
          />
        </div>

        <div>
          <span class="block text-xs font-semibold mb-1" style="color: var(--text-secondary);">
            Role
          </span>
          <div class="grid grid-cols-2 gap-1.5 p-1 rounded-xl border" style="background-color: var(--bg-input); border-color: var(--border-subtle);" role="group" aria-label="Role">
            {#each ['member', 'admin'] as r}
              <button
                type="button"
                onclick={() => (newRole = r as 'admin' | 'member')}
                class="py-1.5 px-2 rounded-lg text-xs font-bold capitalize transition-all"
                style={newRole === r
                  ? 'background-color: var(--color-primary); color: #020617;'
                  : 'color: var(--text-muted);'}
              >
                {r}
              </button>
            {/each}
          </div>
        </div>

        <div>
          <div class="flex items-center justify-between mb-1">
            <label for="new-user-password" class="block text-xs font-semibold" style="color: var(--text-secondary);">
              Password / Passphrase
            </label>
            <span class="text-[11px] font-mono" style="color: {newPwLen === 0 ? 'var(--text-muted)' : !newPwValid ? '#fca5a5' : newPwRecommended ? 'var(--color-primary)' : '#fde047'};">
              {newPwLen} chars {newPwPassphrase ? '• 64+ Passphrase' : newPwRecommended ? '• 15+ Recommended' : newPwValid ? '• Min 8 met' : ''}
            </span>
          </div>
          <div class="password-wrapper flex items-center gap-2">
            <input
              id="new-user-password"
              type={showNewPassword ? 'text' : 'password'}
              bind:value={newPassword}
              required
              minlength="8"
              maxlength="512"
              placeholder="Minimum 8 chars (15+ passphrase recommended)"
              class="input-field w-full"
            />
            <button
              type="button"
              class="px-2.5 py-2 rounded-lg text-xs font-semibold border shrink-0"
              style="border-color: var(--border-subtle); color: var(--text-secondary);"
              onclick={() => (showNewPassword = !showNewPassword)}
            >
              {showNewPassword ? 'Hide' : 'Show'}
            </button>
          </div>
        </div>

        <div class="flex items-center justify-end gap-2 pt-2">
          <button
            type="button"
            onclick={() => (showCreateUserModal = false)}
            class="px-4 py-2 rounded-xl text-xs font-semibold border"
            style="border-color: var(--border-subtle); color: var(--text-secondary);"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!newUsername.trim() || !newPwValid || creatingUser}
            class="px-4 py-2 rounded-xl text-xs font-bold transition-all active:scale-95 disabled:opacity-40"
            style="background-color: var(--color-primary); color: #020617;"
          >
            {creatingUser ? 'Creating…' : 'Create User'}
          </button>
        </div>
      </form>
    </div>
  </div>
{/if}

<LinkAccountModal
  isOpen={showLinkModal}
  user={editingUser}
  allUsers={users}
  onClose={() => {
    showLinkModal = false;
    editingUser = null;
  }}
  onUpdated={loadAll}
/>
