<script lang="ts">
  import { onMount } from 'svelte';
  import { fade, slide } from 'svelte/transition';
  import apiClient, {
    listUsers,
    createUser,
    listRoles,
    assignUserRoles,
    listManagedAccounts,
    assignManagedAccount,
    removeManagedAccount,
    listApiKeys,
    createApiKey,
    deleteApiKey,
    type AuthUser,
    type ManagedAccountBinding,
    type ApiKeyRecord,
  } from '../../api/client';
  import { plugins } from '../../stores/plugins';
  import { feedback } from '../../stores/feedback';

  let users = $state<AuthUser[]>([]);
  let availableRoles = $state<string[]>(['admin', 'member']);
  let managedBindingsByUser = $state<Record<string, ManagedAccountBinding[]>>({});
  let apiKeys = $state<ApiKeyRecord[]>([]);
  let newlyCreatedRawKey = $state<string | null>(null);
  let loading = $state(true);
  let errorMsg = $state('');

  // Create user form state
  let newUsername = $state('');
  let newPassword = $state('');
  let newRole = $state<'admin' | 'member'>('member');
  let showNewPassword = $state(false);
  let creatingUser = $state(false);

  // Managed account assignment state
  let selectedUserForBinding = $state<string>('');
  let selectedServerPluginId = $state<number>(3021005569); // deterministic CRC32 default (EchoSync.plex)
  let managedAccountInput = $state('');
  let discoverableManagedAccounts = $state<Array<{ id: string; name: string; server_plugin_id?: number }>>([]);
  let assigningBinding = $state(false);

  // API key form state
  let newApiKeyName = $state('');
  let creatingApiKey = $state(false);

  // NIST SP 800-63B-4 validation for new local user password
  const normalizedNewPw = $derived(newPassword ? newPassword.normalize('NFKC') : '');
  const newPwLen = $derived(Array.from(normalizedNewPw).length);
  const newPwValid = $derived(newPwLen >= 8 && newPwLen <= 512);
  const newPwRecommended = $derived(newPwLen >= 15);
  const newPwPassphrase = $derived(newPwLen >= 64);

  const serverPluginOptions = $derived.by(() => {
    const items = Object.values(($plugins as any)?.items ?? {}) as any[];
    const servers = items.filter(
      (p) => p && (p.capabilities?.server || p.service_type === 'media_server' || p.category === 'media_server')
    );
    if (servers.length > 0) {
      return servers.map((p) => ({
        plugin_id: Number(p.plugin_id) || 3021005569,
        name: p.display_name || p.name || String(p.id),
      }));
    }
    return [
      { plugin_id: 3021005569, name: 'Plex Media Server' },
      { plugin_id: 2305548545, name: 'Jellyfin' },
      { plugin_id: 4010168341, name: 'Navidrome' },
    ];
  });

  function getServerLabel(pluginId: number): string {
    const match = serverPluginOptions.find((s) => Number(s.plugin_id) === Number(pluginId));
    if (match) return match.name;
    const known: Record<number, string> = {
      3021005569: 'Plex',
      2305548545: 'Jellyfin',
      4010168341: 'Navidrome',
    };
    return known[Number(pluginId)] || `Plugin #${pluginId}`;
  }

  async function loadAll() {
    loading = true;
    errorMsg = '';
    try {
      const [usersData, rolesData, keysData] = await Promise.all([
        listUsers().catch(() => ({ users: [], total: 0 })),
        listRoles().catch(() => ({ roles: [{ name: 'admin' }, { name: 'member' }], total: 2 })),
        listApiKeys().catch(() => ({ api_keys: [], total: 0 })),
      ]);

      users = usersData.users || [];
      if (rolesData.roles && rolesData.roles.length > 0) {
        availableRoles = rolesData.roles.map((r) => r.name);
      }
      apiKeys = keysData.api_keys || [];

      if (!selectedUserForBinding && users.length > 0) {
        selectedUserForBinding = users[0].id;
      }

      // Load managed account bindings for each user
      const bindingsMap: Record<string, ManagedAccountBinding[]> = {};
      await Promise.all(
        users.map(async (u) => {
          try {
            const b = await listManagedAccounts(u.id);
            bindingsMap[u.id] = b.managed_accounts || [];
          } catch {
            bindingsMap[u.id] = [];
          }
        })
      );
      managedBindingsByUser = bindingsMap;

      // Also attempt to discover media server accounts if available
      try {
        const acctRes = await apiClient.get('/system/accounts');
        if (Array.isArray(acctRes.data?.media_users)) {
          discoverableManagedAccounts = acctRes.data.media_users.map((mu: any) => ({
            id: String(mu.id || mu.user_id || mu.name),
            name: String(mu.name || mu.display_name || mu.username || mu.id),
          }));
        }
      } catch {
        // Optional discovery endpoint
      }
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

  async function handleToggleUserRole(user: AuthUser, targetRole: 'admin' | 'member') {
    try {
      const res = await assignUserRoles(user.id, [targetRole]);
      if (res.user) {
        users = users.map((u) => (u.id === user.id ? res.user : u));
        feedback.addToast(`Updated role for ${user.username} to ${targetRole}`, 'success');
      }
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to update role';
      feedback.addToast(msg, 'error');
    }
  }

  async function handleAssignManagedAccount(e: Event) {
    e.preventDefault();
    if (!selectedUserForBinding || !managedAccountInput.trim() || assigningBinding) return;

    assigningBinding = true;
    try {
      const res = await assignManagedAccount(
        selectedUserForBinding,
        Number(selectedServerPluginId),
        managedAccountInput.trim()
      );
      managedBindingsByUser = {
        ...managedBindingsByUser,
        [selectedUserForBinding]: res.managed_accounts || [],
      };
      managedAccountInput = '';
      feedback.addToast('Managed server account bound to user', 'success');
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to bind managed account';
      feedback.addToast(msg, 'error');
    } finally {
      assigningBinding = false;
    }
  }

  async function handleRemoveManagedAccount(userId: string, binding: ManagedAccountBinding) {
    try {
      await removeManagedAccount(userId, binding.server_plugin_id, binding.managed_account_id);
      const current = managedBindingsByUser[userId] || [];
      managedBindingsByUser = {
        ...managedBindingsByUser,
        [userId]: current.filter(
          (b) =>
            !(
              Number(b.server_plugin_id) === Number(binding.server_plugin_id) &&
              b.managed_account_id === binding.managed_account_id
            )
        ),
      };
      feedback.addToast('Removed managed account binding', 'success');
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to remove binding';
      feedback.addToast(msg, 'error');
    }
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
    plugins.load().catch(() => {});
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
        Users, Roles &amp; Media Server Managed Accounts
      </h2>
      <p class="text-xs mt-1" style="color: var(--text-muted);">
        Manage local accounts, assign RBAC roles (<code>admin</code> / <code>member</code>), and bind users to managed media server accounts.
      </p>
    </div>

    <button
      type="button"
      onclick={loadAll}
      class="px-3.5 py-2 rounded-xl text-xs font-semibold border transition-all active:scale-95 self-start"
      style="background-color: var(--bg-surface-elevated); border-color: var(--border-subtle); color: var(--text-primary);"
    >
      {loading ? 'Refreshing…' : '↻ Refresh'}
    </button>
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

  <div class="grid grid-cols-1 xl:grid-cols-2 gap-6">
    <!-- Left Card: Create Local User -->
    <div
      class="rounded-2xl border p-5 space-y-4"
      style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
    >
      <div>
        <h3 class="text-sm font-bold" style="color: var(--text-primary);">
          Create Local User
        </h3>
        <p class="text-xs mt-0.5" style="color: var(--text-muted);">
          NIST SP 800-63B-4 policy: 8+ chars minimum, 15+ recommended, 64+ passphrases with spaces/Unicode supported.
        </p>
      </div>

      <form onsubmit={handleCreateUser} class="space-y-3.5">
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div class="sm:col-span-2">
            <label for="new-user-username" class="block text-xs font-semibold mb-1" style="color: var(--text-secondary);">
              Username
            </label>
            <input
              id="new-user-username"
              type="text"
              bind:value={newUsername}
              required
              placeholder="e.g. alice"
              class="input-field"
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
          <div class="password-wrapper">
            <input
              id="new-user-password"
              type={showNewPassword ? 'text' : 'password'}
              bind:value={newPassword}
              required
              minlength="8"
              maxlength="512"
              placeholder="Minimum 8 chars (15+ passphrase recommended)"
              class="input-field pr-16"
            />
            <button
              type="button"
              class="toggle-visibility text-xs font-semibold"
              onclick={() => (showNewPassword = !showNewPassword)}
            >
              {showNewPassword ? 'Hide' : 'Show'}
            </button>
          </div>
        </div>

        <button
          type="submit"
          disabled={!newUsername.trim() || !newPwValid || creatingUser}
          class="px-4 py-2.5 rounded-xl text-xs font-bold transition-all active:scale-95 disabled:opacity-40"
          style="background-color: var(--color-primary); color: #020617;"
        >
          {creatingUser ? 'Creating User…' : '+ Create User Account'}
        </button>
      </form>
    </div>

    <!-- Right Card: Bind User to Media Server Managed Account -->
    <div
      class="rounded-2xl border p-5 space-y-4"
      style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
    >
      <div>
        <h3 class="text-sm font-bold" style="color: var(--text-primary);">
          Bind Media Server Managed Account
        </h3>
        <p class="text-xs mt-0.5" style="color: var(--text-muted);">
          Associate an EchoSync user with a managed user/profile on your media server (Plex, Jellyfin, Navidrome).
        </p>
      </div>

      <form onsubmit={handleAssignManagedAccount} class="space-y-3.5">
        <div>
          <span class="block text-xs font-semibold mb-1.5" style="color: var(--text-secondary);">
            1. Select EchoSync User
          </span>
          <div class="flex flex-wrap gap-1.5" role="group" aria-label="Select EchoSync User">
            {#each users as u (u.id)}
              <button
                type="button"
                onclick={() => (selectedUserForBinding = u.id)}
                class="px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all"
                style={selectedUserForBinding === u.id
                  ? 'background: rgba(20, 184, 166, 0.16); border-color: var(--color-primary); color: var(--color-primary);'
                  : 'background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-secondary);'}
              >
                {u.username}
              </button>
            {/each}
            {#if users.length === 0}
              <span class="text-xs italic" style="color: var(--text-muted);">No users found</span>
            {/if}
          </div>
        </div>

        <div>
          <span class="block text-xs font-semibold mb-1.5" style="color: var(--text-secondary);">
            2. Media Server Provider
          </span>
          <div class="flex flex-wrap gap-1.5" role="group" aria-label="Media Server Provider">
            {#each serverPluginOptions as srv (srv.plugin_id)}
              <button
                type="button"
                onclick={() => (selectedServerPluginId = srv.plugin_id)}
                class="px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all"
                style={Number(selectedServerPluginId) === Number(srv.plugin_id)
                  ? 'background: rgba(20, 184, 166, 0.16); border-color: var(--color-primary); color: var(--color-primary);'
                  : 'background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-secondary);'}
              >
                {srv.name}
              </button>
            {/each}
          </div>
        </div>

        <div>
          <label for="managed-account-id-input" class="block text-xs font-semibold mb-1" style="color: var(--text-secondary);">
            3. Managed Server Account ID / Username
          </label>
          <input
            id="managed-account-id-input"
            type="text"
            bind:value={managedAccountInput}
            required
            placeholder="e.g. plex-managed-user-id or username"
            class="input-field"
          />
          {#if discoverableManagedAccounts.length > 0}
            <div class="flex flex-wrap items-center gap-1.5 mt-2">
              <span class="text-[11px]" style="color: var(--text-muted);">Discovered:</span>
              {#each discoverableManagedAccounts as da (da.id)}
                <button
                  type="button"
                  onclick={() => (managedAccountInput = da.id)}
                  class="px-2 py-0.5 rounded text-[11px] font-medium border transition-colors"
                  style="background-color: var(--bg-surface-elevated); border-color: var(--border-subtle); color: var(--text-secondary);"
                >
                  {da.name} ({da.id})
                </button>
              {/each}
            </div>
          {/if}
        </div>

        <button
          type="submit"
          disabled={!selectedUserForBinding || !managedAccountInput.trim() || assigningBinding}
          class="px-4 py-2.5 rounded-xl text-xs font-bold transition-all active:scale-95 disabled:opacity-40"
          style="background-color: var(--color-primary); color: #020617;"
        >
          {assigningBinding ? 'Binding Account…' : '🔗 Bind Managed Account'}
        </button>
      </form>
    </div>
  </div>

  <!-- Users Directory & Managed Account Bindings Table -->
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
        Loading users and managed account assignments…
      </div>
    {:else if users.length === 0}
      <div class="p-8 text-center text-xs" style="color: var(--text-muted);">
        No users registered yet.
      </div>
    {:else}
      <div class="divide-y" style="border-color: var(--border-subtle);">
        {#each users as user (user.id)}
          {@const bindings = managedBindingsByUser[user.id] || []}
          {@const isAdmin = (user.roles || []).includes('admin')}
          <div class="p-4 sm:px-5 flex flex-col lg:flex-row lg:items-center justify-between gap-4" transition:fade={{ duration: 150 }}>
            <div class="space-y-1">
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
                  {isAdmin ? 'Admin' : 'Member'}
                </span>
                <span
                  class="px-2 py-0.5 rounded text-[10px] font-mono uppercase"
                  style="background-color: var(--bg-surface-elevated); color: var(--text-muted);"
                >
                  {user.auth_provider || 'local'}
                </span>
              </div>

              <!-- Managed Accounts Pills -->
              <div class="flex flex-wrap items-center gap-1.5 pt-1">
                <span class="text-[11px]" style="color: var(--text-muted);">Managed Accounts:</span>
                {#if bindings.length === 0}
                  <span class="text-[11px] italic" style="color: var(--text-muted);">None bound</span>
                {:else}
                  {#each bindings as b (`${b.server_plugin_id}:${b.managed_account_id}`)}
                    <span
                      class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border"
                      style="background-color: var(--bg-surface-elevated); border-color: rgba(20, 184, 166, 0.3); color: var(--text-primary);"
                      transition:slide={{ duration: 150 }}
                    >
                      <span class="text-[10px] font-bold uppercase" style="color: var(--color-primary);">
                        {getServerLabel(b.server_plugin_id)}:
                      </span>
                      <span>{b.managed_account_id}</span>
                      <button
                        type="button"
                        onclick={() => handleRemoveManagedAccount(user.id, b)}
                        class="ml-1 hover:opacity-100 opacity-60 text-xs"
                        style="color: var(--color-danger);"
                        title="Unbind managed account"
                        aria-label="Unbind managed account"
                      >
                        ✕
                      </button>
                    </span>
                  {/each}
                {/if}
              </div>
            </div>

            <!-- Role Switcher Controls -->
            <div class="flex items-center gap-2 shrink-0">
              <span class="text-xs" style="color: var(--text-muted);">Role:</span>
              <div class="inline-flex p-1 rounded-xl border" style="background-color: var(--bg-input); border-color: var(--border-subtle);">
                <button
                  type="button"
                  onclick={() => handleToggleUserRole(user, 'member')}
                  class="px-2.5 py-1 rounded-lg text-xs font-semibold transition-all"
                  style={!isAdmin
                    ? 'background-color: var(--color-primary); color: #020617;'
                    : 'color: var(--text-muted);'}
                >
                  Member
                </button>
                <button
                  type="button"
                  onclick={() => handleToggleUserRole(user, 'admin')}
                  class="px-2.5 py-1 rounded-lg text-xs font-semibold transition-all"
                  style={isAdmin
                    ? 'background-color: var(--color-primary); color: #020617;'
                    : 'color: var(--text-muted);'}
                >
                  Admin
                </button>
              </div>
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
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
      <div>
        <h3 class="text-sm font-bold" style="color: var(--text-primary);">
          API Keys ({apiKeys.length})
        </h3>
        <p class="text-xs mt-0.5" style="color: var(--text-muted);">
          Issue scoped bearer / <code>X-API-Key</code> tokens for headless integrations and scripts.
        </p>
      </div>

      <form onsubmit={handleCreateApiKey} class="flex items-center gap-2">
        <input
          type="text"
          bind:value={newApiKeyName}
          placeholder="Key label (e.g. CLI Automation)"
          class="input-field text-xs py-2"
          style="min-width: 200px;"
        />
        <button
          type="submit"
          disabled={!newApiKeyName.trim() || creatingApiKey}
          class="px-3.5 py-2 rounded-xl text-xs font-bold whitespace-nowrap transition-all active:scale-95 disabled:opacity-40"
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
