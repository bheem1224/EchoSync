<script lang="ts">
  import { fade, slide } from 'svelte/transition';
  import {
    assignUserRoles,
    bindExternalAccount,
    deleteUser,
    listAvailableExternalAccounts,
    listExternalAccounts,
    listUsers,
    resetUserPassword,
    unbindExternalAccount,
    type AuthUser,
    type AvailableExternalAccount,
    type ExternalAccountBinding,
  } from '../../api/client';
  import { feedback } from '../../stores/feedback';

  let {
    isOpen = false,
    user = null,
    allUsers = [],
    onClose = () => {},
    onUpdated = () => {},
  }: {
    isOpen?: boolean;
    user?: AuthUser | null;
    allUsers?: AuthUser[];
    onClose?: () => void;
    onUpdated?: () => void;
  } = $props();

  const PROVIDER_OPTIONS = [
    { id: 'spotify', label: 'Spotify', category: 'streaming' as const },
    { id: 'tidal', label: 'Tidal', category: 'streaming' as const },
    { id: 'listenbrainz', label: 'ListenBrainz', category: 'streaming' as const },
    { id: 'plex', label: 'Plex', category: 'media_server' as const },
    { id: 'jellyfin', label: 'Jellyfin', category: 'media_server' as const },
    { id: 'navidrome', label: 'Navidrome', category: 'media_server' as const },
  ];

  let localUsers = $state<AuthUser[]>([]);
  let activeUserId = $state<string>('');
  let bindings = $state<ExternalAccountBinding[]>([]);
  let availableStreaming = $state<AvailableExternalAccount[]>([]);
  let availableMedia = $state<AvailableExternalAccount[]>([]);
  let loading = $state(false);
  let saving = $state(false);

  let selectedProvider = $state<string>('spotify');
  let externalIdInput = $state('');
  let displayNameInput = $state('');
  let newPasswordInput = $state('');
  let showResetPassword = $state(false);

  const activeUser = $derived(
    user || localUsers.find((u) => u.id === activeUserId) || null
  );
  const activeIsAdmin = $derived((activeUser?.roles || []).includes('admin'));

  const matchingAvailable = $derived.by(() => {
    const pool = [...availableStreaming, ...availableMedia];
    return pool.filter((a) => a.provider === selectedProvider);
  });

  async function hydrate() {
    if (!isOpen) return;
    loading = true;
    try {
      const [availRes, usersList] = await Promise.all([
        listAvailableExternalAccounts().catch(() => ({ streaming: [], media_server: [] })),
        allUsers.length > 0 ? Promise.resolve(allUsers) : listUsers().then((r) => r.users || []).catch(() => []),
      ]);
      availableStreaming = availRes.streaming || [];
      availableMedia = availRes.media_server || [];
      localUsers = usersList;
      if (user) {
        activeUserId = user.id;
      } else if (!activeUserId && usersList.length > 0) {
        activeUserId = usersList[0].id;
      }
      if (activeUserId) {
        const res = await listExternalAccounts(activeUserId).catch(() => ({ external_accounts: [] }));
        bindings = res.external_accounts || [];
      }
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    if (isOpen) {
      activeUserId = user?.id || '';
      hydrate();
    }
  });

  async function selectUser(uid: string) {
    activeUserId = uid;
    const res = await listExternalAccounts(uid).catch(() => ({ external_accounts: [] }));
    bindings = res.external_accounts || [];
  }

  async function handleBind(e: Event) {
    e.preventDefault();
    if (!activeUserId || !externalIdInput.trim() || saving) return;
    saving = true;
    try {
      const meta = PROVIDER_OPTIONS.find((p) => p.id === selectedProvider);
      const res = await bindExternalAccount(activeUserId, {
        provider: selectedProvider,
        external_account_id: externalIdInput.trim(),
        display_name: displayNameInput.trim() || externalIdInput.trim(),
        category: meta?.category,
      });
      bindings = res.external_accounts || [];
      externalIdInput = '';
      displayNameInput = '';
      feedback.addToast('External account bound to user', 'success');
      onUpdated();
    } catch (err: any) {
      feedback.addToast(err?.response?.data?.detail || 'Failed to bind account', 'error');
    } finally {
      saving = false;
    }
  }

  async function handleQuickBind(avail: AvailableExternalAccount) {
    if (!activeUserId || saving) return;
    saving = true;
    try {
      const meta = PROVIDER_OPTIONS.find((p) => p.id === avail.provider);
      const res = await bindExternalAccount(activeUserId, {
        provider: avail.provider,
        external_account_id: avail.external_account_id,
        display_name: avail.display_name,
        category: meta?.category,
        plugin_id: avail.plugin_id,
      });
      bindings = res.external_accounts || [];
      feedback.addToast(`Bound ${avail.display_name} (${avail.provider})`, 'success');
      onUpdated();
    } catch (err: any) {
      feedback.addToast(err?.response?.data?.detail || 'Failed to bind account', 'error');
    } finally {
      saving = false;
    }
  }

  async function handleUnbind(b: ExternalAccountBinding) {
    if (!activeUserId || saving) return;
    saving = true;
    try {
      const res = await unbindExternalAccount(activeUserId, b.provider, b.external_account_id);
      bindings = res.external_accounts || [];
      feedback.addToast('Unbound external account', 'success');
      onUpdated();
    } catch (err: any) {
      feedback.addToast(err?.response?.data?.detail || 'Failed to unbind account', 'error');
    } finally {
      saving = false;
    }
  }

  async function handleRoleChange(role: 'admin' | 'member') {
    if (!activeUser) return;
    try {
      await assignUserRoles(activeUser.id, [role]);
      feedback.addToast(`Updated role to ${role}`, 'success');
      onUpdated();
    } catch (err: any) {
      feedback.addToast(err?.response?.data?.detail || 'Failed to update role', 'error');
    }
  }

  async function handleResetPassword(e: Event) {
    e.preventDefault();
    if (!activeUser || newPasswordInput.length < 8) return;
    saving = true;
    try {
      await resetUserPassword(activeUser.id, newPasswordInput);
      newPasswordInput = '';
      showResetPassword = false;
      feedback.addToast(`Password updated for ${activeUser.username}`, 'success');
    } catch (err: any) {
      feedback.addToast(err?.response?.data?.detail || 'Failed to reset password', 'error');
    } finally {
      saving = false;
    }
  }

  async function handleDeleteUser() {
    if (!activeUser) return;
    if (!confirm(`Delete user "${activeUser.username}"? This cannot be undone.`)) return;
    try {
      await deleteUser(activeUser.id);
      feedback.addToast(`Deleted user ${activeUser.username}`, 'success');
      onUpdated();
      onClose();
    } catch (err: any) {
      feedback.addToast(err?.response?.data?.detail || 'Failed to delete user', 'error');
    }
  }
</script>

{#if isOpen}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div
    class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm"
    onclick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    transition:fade={{ duration: 150 }}
    role="dialog"
    aria-modal="true"
  >
    <div
      class="w-full max-w-2xl max-h-[88vh] rounded-2xl border shadow-2xl flex flex-col overflow-hidden"
      style="background-color: var(--bg-surface, #0f172a); border-color: var(--border-subtle);"
    >
      <!-- Header -->
      <div class="px-6 py-4 border-b flex items-center justify-between shrink-0" style="border-color: var(--border-subtle);">
        <div>
          <span class="text-[10px] font-bold uppercase tracking-widest" style="color: var(--color-primary);">
            External Account Binding
          </span>
          <h3 class="text-lg font-bold mt-0.5" style="color: var(--text-primary);">
            {activeUser ? `Manage ${activeUser.username}` : 'Link External Accounts'}
          </h3>
        </div>
        <button
          type="button"
          onclick={onClose}
          class="w-8 h-8 rounded-lg flex items-center justify-center border transition-colors hover:bg-white/10"
          style="border-color: var(--border-subtle); color: var(--text-muted);"
          aria-label="Close modal"
        >
          ✕
        </button>
      </div>

      <!-- Body -->
      <div class="p-6 overflow-y-auto space-y-6">
        {#if !user && localUsers.length > 0}
          <div>
            <span class="block text-xs font-semibold mb-1.5" style="color: var(--text-secondary);">
              EchoSync User
            </span>
            <div class="flex flex-wrap gap-1.5">
              {#each localUsers as u (u.id)}
                <button
                  type="button"
                  onclick={() => selectUser(u.id)}
                  class="px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all"
                  style={activeUserId === u.id
                    ? 'background: rgba(20, 184, 166, 0.16); border-color: var(--color-primary); color: var(--color-primary);'
                    : 'background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-secondary);'}
                >
                  {u.username}
                </button>
              {/each}
            </div>
          </div>
        {/if}

        <!-- Current Bindings -->
        <div class="space-y-2">
          <h4 class="text-xs font-bold uppercase tracking-wider" style="color: var(--text-secondary);">
            Bound External Accounts ({bindings.length})
          </h4>
          {#if loading}
            <p class="text-xs italic" style="color: var(--text-muted);">Loading bindings…</p>
          {:else if bindings.length === 0}
            <p class="text-xs italic" style="color: var(--text-muted);">No streaming or media server accounts bound yet.</p>
          {:else}
            <div class="flex flex-wrap gap-2">
              {#each bindings as b (`${b.provider}:${b.external_account_id}`)}
                <span
                  class="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium border"
                  style="background-color: var(--bg-surface-elevated); border-color: rgba(20, 184, 166, 0.35); color: var(--text-primary);"
                  transition:slide={{ duration: 120 }}
                >
                  <span class="text-[10px] font-bold uppercase" style="color: var(--color-primary);">
                    {b.provider}:
                  </span>
                  <span>{b.display_name || b.external_account_id}</span>
                  <button
                    type="button"
                    onclick={() => handleUnbind(b)}
                    class="opacity-70 hover:opacity-100 text-xs"
                    style="color: var(--color-danger, #f87171);"
                    title="Unbind account"
                  >
                    ✕
                  </button>
                </span>
              {/each}
            </div>
          {/if}
        </div>

        <!-- Add New Binding -->
        <form onsubmit={handleBind} class="space-y-4 p-4 rounded-xl border" style="background-color: var(--bg-input); border-color: var(--border-subtle);">
          <div>
            <span class="block text-xs font-semibold mb-1.5" style="color: var(--text-secondary);">
              1. Select Provider
            </span>
            <div class="flex flex-wrap gap-1.5">
              {#each PROVIDER_OPTIONS as prov (prov.id)}
                <button
                  type="button"
                  onclick={() => (selectedProvider = prov.id)}
                  class="px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all"
                  style={selectedProvider === prov.id
                    ? 'background: rgba(20, 184, 166, 0.16); border-color: var(--color-primary); color: var(--color-primary);'
                    : 'background-color: var(--bg-surface); border-color: var(--border-subtle); color: var(--text-secondary);'}
                >
                  {prov.label}
                </button>
              {/each}
            </div>
          </div>

          {#if matchingAvailable.length > 0}
            <div>
              <span class="block text-xs font-semibold mb-1.5" style="color: var(--text-secondary);">
                Discovered {selectedProvider} Accounts (Click to Bind)
              </span>
              <div class="flex flex-wrap gap-1.5">
                {#each matchingAvailable as avail (`${avail.provider}:${avail.external_account_id}`)}
                  <button
                    type="button"
                    onclick={() => handleQuickBind(avail)}
                    disabled={saving}
                    class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors hover:border-teal-400"
                    style="background-color: var(--bg-surface-elevated); border-color: var(--border-subtle); color: var(--text-primary);"
                  >
                    <span>+ {avail.display_name}</span>
                    {#if avail.is_managed}
                      <span
                        class="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider"
                        style="background: rgba(20, 184, 166, 0.16); color: var(--color-primary);"
                      >
                        MANAGED
                      </span>
                    {/if}
                  </button>
                {/each}
              </div>
            </div>
          {/if}

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label for="ext-acct-id" class="block text-xs font-semibold mb-1" style="color: var(--text-secondary);">
                Account ID / Username
              </label>
              <input
                id="ext-acct-id"
                type="text"
                bind:value={externalIdInput}
                required
                placeholder="e.g. abhay_spotify or plex-user-id"
                class="input-field w-full"
              />
            </div>
            <div>
              <label for="ext-acct-name" class="block text-xs font-semibold mb-1" style="color: var(--text-secondary);">
                Display Name (Optional)
              </label>
              <input
                id="ext-acct-name"
                type="text"
                bind:value={displayNameInput}
                placeholder="e.g. Abhay's Spotify"
                class="input-field w-full"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={!activeUserId || !externalIdInput.trim() || saving}
            class="px-4 py-2 rounded-xl text-xs font-bold transition-all active:scale-95 disabled:opacity-40"
            style="background-color: var(--color-primary); color: #020617;"
          >
            {saving ? 'Binding…' : '🔗 Bind External Account'}
          </button>
        </form>

        <!-- Role, Password Reset & Delete User -->
        {#if activeUser}
          <div class="pt-4 border-t space-y-4" style="border-color: var(--border-subtle);">
            <div class="flex flex-wrap items-center justify-between gap-3">
              <div class="flex items-center gap-2">
                <span class="text-xs font-semibold" style="color: var(--text-secondary);">Role:</span>
                <div class="inline-flex p-1 rounded-xl border" style="background-color: var(--bg-input); border-color: var(--border-subtle);">
                  <button
                    type="button"
                    onclick={() => handleRoleChange('member')}
                    class="px-2.5 py-1 rounded-lg text-xs font-semibold transition-all"
                    style={!activeIsAdmin ? 'background-color: var(--color-primary); color: #020617;' : 'color: var(--text-muted);'}
                  >
                    Member
                  </button>
                  <button
                    type="button"
                    onclick={() => handleRoleChange('admin')}
                    class="px-2.5 py-1 rounded-lg text-xs font-semibold transition-all"
                    style={activeIsAdmin ? 'background-color: var(--color-primary); color: #020617;' : 'color: var(--text-muted);'}
                  >
                    Admin
                  </button>
                </div>
              </div>

              <div class="flex items-center gap-2">
                {#if activeUser.auth_provider === 'local'}
                  <button
                    type="button"
                    onclick={() => (showResetPassword = !showResetPassword)}
                    class="px-3 py-1.5 rounded-lg text-xs font-semibold border"
                    style="border-color: var(--border-subtle); color: var(--text-secondary);"
                  >
                    {showResetPassword ? 'Cancel Password Reset' : 'Reset Password'}
                  </button>
                {/if}
                <button
                  type="button"
                  onclick={handleDeleteUser}
                  class="px-3 py-1.5 rounded-lg text-xs font-semibold border"
                  style="border-color: rgba(239, 68, 68, 0.4); color: #fca5a5;"
                >
                  Delete User
                </button>
              </div>
            </div>

            {#if showResetPassword}
              <form onsubmit={handleResetPassword} class="flex items-center gap-2">
                <input
                  type="password"
                  bind:value={newPasswordInput}
                  minlength="8"
                  maxlength="512"
                  placeholder="New password / passphrase (min 8 chars)"
                  class="input-field flex-1"
                  required
                />
                <button
                  type="submit"
                  disabled={newPasswordInput.length < 8 || saving}
                  class="px-3.5 py-2 rounded-xl text-xs font-bold disabled:opacity-40"
                  style="background-color: var(--color-primary); color: #020617;"
                >
                  Update Password
                </button>
              </form>
            {/if}
          </div>
        {/if}
      </div>
    </div>
  </div>
{/if}
