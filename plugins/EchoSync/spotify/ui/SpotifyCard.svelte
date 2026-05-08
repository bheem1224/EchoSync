<svelte:options
  customElement="spotify-dashboard-card"
/>

<script>
  /**
   * @type {string} apiBase - The base URL for API calls, provided by the dashboard host.
   */
  export let apiBase = "";
  import { onMount } from "svelte";

  let clientId = "";
  let clientSecret = "";
  let redirectUri = "";
  let accounts = [];
  let showAddAccount = false;
  let newAccountName = "";
  let loading = true;
  let savingGlobal = false;
  let credsCollapsed = false;

  const MAX_ACCOUNTS = 25;

  onMount(async () => {
    // Ensure apiBase is trimmed
    apiBase = apiBase.replace(/\/$/, "");
    
    await loadGlobalSettings();
    await loadAccounts();

    // Auto-populate redirect URI if empty
    if (!redirectUri && typeof window !== "undefined") {
      redirectUri = `${window.location.protocol}//${window.location.host}/api/spotify/callback`;
    }

    // Collapse credentials by default if configured
    credsCollapsed = Boolean(
      clientId &&
        clientSecret &&
        redirectUri &&
        accounts.some((a) => a.is_authenticated),
    );
    loading = false;
  });

  async function loadGlobalSettings() {
    try {
      const response = await fetch(`${apiBase}/settings`);
      const data = await response.json();
      if (data?.settings) {
        clientId = data.settings.client_id || "";
        clientSecret = data.settings.client_secret || "";
        redirectUri = data.settings.redirect_uri || "";
      }
    } catch (error) {
      console.error("Failed to load Spotify settings:", error);
    }
  }

  async function saveGlobalSettings() {
    if (!clientId || !clientSecret) {
      alert("Client ID and Secret are required");
      return;
    }

    try {
      savingGlobal = true;
      const resp = await fetch(`${apiBase}/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          client_id: clientId,
          client_secret: clientSecret,
          redirect_uri: redirectUri,
        }),
      });
      
      if (!resp.ok) throw new Error("Save failed");
      
      console.log("Spotify credentials saved");
    } catch (error) {
      console.error("Failed to save Spotify settings:", error);
      alert("Failed to save settings. Check console.");
    } finally {
      savingGlobal = false;
    }
  }

  async function loadAccounts() {
    try {
      const response = await fetch(`${apiBase}/accounts`);
      const data = await response.json();
      accounts = data?.accounts || [];
    } catch (error) {
      console.error("Failed to load Spotify accounts:", error);
      accounts = [];
    }
  }

  async function addAccount() {
    if (!newAccountName.trim()) return;

    if (accounts.length >= MAX_ACCOUNTS) {
      alert(`Maximum ${MAX_ACCOUNTS} accounts allowed`);
      return;
    }

    try {
      const resp = await fetch(`${apiBase}/accounts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          account_name: newAccountName,
          display_name: newAccountName,
        }),
      });
      
      if (!resp.ok) throw new Error("Add failed");
      
      newAccountName = "";
      showAddAccount = false;
      await loadAccounts();
    } catch (error) {
      console.error("Failed to add account:", error);
    }
  }

  async function toggleAccount(accountId, currentlyActive) {
    try {
      const resp = await fetch(`${apiBase}/accounts/${accountId}/activate`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          is_active: !currentlyActive,
        }),
      });
      if (!resp.ok) throw new Error("Toggle failed");
      await loadAccounts();
    } catch (error) {
      console.error("Failed to toggle account:", error);
    }
  }

  async function deleteAccount(accountId, accountName) {
    if (!confirm(`Delete account "${accountName}"?`)) return;

    try {
      const resp = await fetch(`${apiBase}/accounts/${accountId}`, {
        method: "DELETE",
      });
      if (!resp.ok) throw new Error("Delete failed");
      await loadAccounts();
    } catch (error) {
      console.error("Failed to delete account:", error);
    }
  }

  async function authenticate(accountId) {
    if (!clientId || !clientSecret) {
      alert("Please save Client ID and Secret first.");
      return;
    }

    try {
      await saveGlobalSettings();
      const resp = await fetch(`${apiBase}/auth?account_id=${accountId}`);
      const data = await resp.json();
      if (data?.auth_url) {
        window.open(data.auth_url, '_blank', 'noopener,noreferrer');
        // Refresh after a delay to catch the callback
        setTimeout(() => loadAccounts(), 5000);
      }
    } catch (err) {
      console.error("Failed to start OAuth:", err);
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
    <div class="loading-state">
      <div class="spinner"></div>
      <span>Initializing Spotify Nexus...</span>
    </div>
  {:else}
    <!-- Global Credentials -->
    <div class="settings-section">
      <div class="section-header">
        <h3 class="section-title">Global Credentials</h3>
        <button
          class="btn-ghost"
          on:click={() => (credsCollapsed = !credsCollapsed)}
        >
          {credsCollapsed ? "Expand" : "Collapse"}
        </button>
      </div>

      {#if !credsCollapsed}
        <div class="form-grid">
          <div class="form-field">
            <span class="field-label">Client ID</span>
            <input
              type="text"
              bind:value={clientId}
              placeholder="Spotify Developer Client ID"
              class="input-field"
            />
          </div>
          <div class="form-field">
            <span class="field-label">Client Secret</span>
            <div class="password-wrapper">
              <input
                type="password"
                bind:value={clientSecret}
                placeholder="Spotify Developer Client Secret"
                class="input-field"
              />
            </div>
          </div>
          <div class="form-field">
            <span class="field-label">Redirect URI</span>
            <input
              type="text"
              bind:value={redirectUri}
              class="input-field readonly"
              readonly
              disabled
            />
            <span class="helper-text">Whitelist this in Spotify Dashboard</span>
          </div>
          <div class="actions-row">
            <button
              class="btn-primary"
              on:click={saveGlobalSettings}
              disabled={savingGlobal}
            >
              {savingGlobal ? "Saving..." : "Save Credentials"}
            </button>
          </div>
        </div>
      {/if}
    </div>

    <hr class="divider" />

    <!-- Accounts -->
    <div class="settings-section">
      <div class="section-header">
        <h3 class="section-title">
          Accounts ({accounts.length}/{MAX_ACCOUNTS})
        </h3>
        {#if accounts.length < MAX_ACCOUNTS}
          <button
            class="btn-ghost"
            on:click={() => (showAddAccount = !showAddAccount)}
          >
            {showAddAccount ? "Cancel" : "+ Add Account"}
          </button>
        {/if}
      </div>

      {#if showAddAccount}
        <div class="add-account-form">
          <div class="form-field">
            <input
              type="text"
              bind:value={newAccountName}
              placeholder="e.g. My Personal Account"
              class="input-field"
              on:keydown={(e) => e.key === "Enter" && addAccount()}
            />
          </div>
          <div class="actions-row">
            <button class="btn-primary" on:click={addAccount}>Add Account</button>
          </div>
        </div>
      {/if}

      <div class="accounts-list">
        {#each accounts as account}
          <div class="account-item">
            <div class="account-info">
              <div class="account-name">
                {account.display_name || account.account_name}
              </div>
              <div class="account-badges">
                {#if account.is_authenticated}
                  <span class="status-badge success">Authenticated</span>
                {:else}
                  <span class="status-badge warning">Pending Auth</span>
                {/if}
                {#if account.is_active}
                  <span class="status-badge active">Active</span>
                {/if}
              </div>
            </div>
            <div class="account-actions">
              <button
                class="link-btn"
                on:click={() => authenticate(account.id)}
              >
                {account.is_authenticated ? "Re-auth" : "Authorize"}
              </button>
              
              <div class="switch-container">
                 <label class="switch">
                    <input 
                      type="checkbox" 
                      checked={account.is_active} 
                      on:change={() => toggleAccount(account.id, account.is_active)}
                    />
                    <span class="slider round"></span>
                 </label>
              </div>

              <button
                class="btn-danger-icon"
                on:click={() =>
                  deleteAccount(
                    account.id,
                    account.display_name || account.account_name,
                  )}
                title="Delete Account"
              >
                ✕
              </button>
            </div>
          </div>
        {:else}
          <div class="empty-accounts">No Spotify accounts connected.</div>
        {/each}
      </div>
    </div>
  {/if}
</section>

<style>
  .plugin-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius, 16px);
    padding: 28px;
    color: var(--text-primary);
    font-family: 'Inter', sans-serif;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.2);
    transition: transform 0.2s ease;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 28px;
    padding-bottom: 20px;
    border-bottom: 1px solid var(--border-subtle);
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .card-title {
    margin: 0;
    font-size: 22px;
    font-weight: 800;
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, #fff 0%, #a5b4fc 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  .type-badge {
    font-size: 10px;
    padding: 4px 10px;
    background: rgba(20, 184, 166, 0.1);
    color: var(--color-primary);
    border: 1px solid rgba(20, 184, 166, 0.2);
    border-radius: 20px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .settings-section {
    margin-bottom: 32px;
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
  }

  .section-title {
    margin: 0;
    font-size: 14px;
    font-weight: 700;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .form-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 20px;
  }

  @media (min-width: 640px) {
    .form-grid {
      grid-template-columns: 1fr 1fr;
    }
    .actions-row {
      grid-column: span 2;
    }
  }

  .form-field {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .field-label {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-secondary);
    opacity: 0.8;
  }

  .input-field {
    width: 100%;
    padding: 14px 18px;
    background: var(--bg-input, #0f172a);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    color: var(--text-primary);
    font-size: 14px;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  }

  .input-field:focus {
    outline: none;
    border-color: var(--color-primary);
    box-shadow: 0 0 0 4px rgba(20, 184, 166, 0.15);
    background: rgba(255, 255, 255, 0.03);
  }

  .input-field.readonly {
    opacity: 0.6;
    cursor: not-allowed;
    background: rgba(255, 255, 255, 0.02);
  }

  .helper-text {
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 6px;
    font-style: italic;
  }

  .btn-primary {
    padding: 12px 28px;
    background: var(--color-primary);
    color: #000;
    border: none;
    border-radius: 12px;
    font-weight: 700;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 4px 12px rgba(20, 184, 166, 0.2);
  }

  .btn-primary:hover:not(:disabled) {
    filter: brightness(1.1);
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(20, 184, 166, 0.3);
  }

  .btn-primary:active:not(:disabled) {
    transform: translateY(0);
  }

  .btn-primary:disabled {
    opacity: 0.4;
    cursor: not-allowed;
    box-shadow: none;
  }

  .btn-ghost {
    padding: 10px 18px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--border-subtle);
    color: var(--text-primary);
    border-radius: 10px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .btn-ghost:hover {
    background: rgba(255, 255, 255, 0.1);
    border-color: rgba(255, 255, 255, 0.2);
    transform: translateY(-1px);
  }

  .divider {
    border: none;
    border-top: 1px solid var(--border-subtle);
    margin: 32px 0;
    opacity: 0.3;
  }

  .accounts-list {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .account-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--border-subtle);
    border-radius: 16px;
    transition: all 0.3s ease;
  }

  .account-item:hover {
    border-color: rgba(20, 184, 166, 0.3);
    background: rgba(255, 255, 255, 0.05);
    transform: translateX(4px);
  }

  .account-info {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .account-name {
    font-weight: 700;
    font-size: 16px;
    color: #fff;
  }

  .account-badges {
    display: flex;
    gap: 10px;
  }

  .status-badge {
    font-size: 10px;
    padding: 3px 10px;
    border-radius: 6px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  .status-badge.success {
    background: rgba(16, 185, 129, 0.1);
    color: #10b981;
    border: 1px solid rgba(16, 185, 129, 0.2);
  }

  .status-badge.warning {
    background: rgba(245, 158, 11, 0.1);
    color: #f59e0b;
    border: 1px solid rgba(245, 158, 11, 0.2);
  }

  .status-badge.active {
    background: rgba(20, 184, 166, 0.1);
    color: var(--color-primary);
    border: 1px solid rgba(20, 184, 166, 0.2);
  }

  .account-actions {
    display: flex;
    gap: 20px;
    align-items: center;
  }

  .link-btn {
    background: none;
    border: none;
    color: var(--color-primary);
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    padding: 0;
    transition: opacity 0.2s;
  }

  .link-btn:hover {
    opacity: 0.8;
    text-decoration: underline;
  }

  .btn-danger-icon {
    background: rgba(239, 68, 68, 0.1);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.2);
    width: 36px;
    height: 36px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.2s ease;
    font-size: 16px;
  }

  .btn-danger-icon:hover {
    background: #ef4444;
    color: #fff;
    transform: rotate(90deg);
  }

  /* Switch Component */
  .switch {
    position: relative;
    display: inline-block;
    width: 44px;
    height: 24px;
  }

  .switch input {
    opacity: 0;
    width: 0;
    height: 0;
  }

  .slider {
    position: absolute;
    cursor: pointer;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(255, 255, 255, 0.1);
    transition: .4s;
    border: 1px solid var(--border-subtle);
  }

  .slider:before {
    position: absolute;
    content: "";
    height: 18px;
    width: 18px;
    left: 2px;
    bottom: 2px;
    background-color: #94a3b8;
    transition: .4s;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
  }

  input:checked + .slider {
    background-color: var(--color-primary);
    border-color: var(--color-primary);
  }

  input:checked + .slider:before {
    transform: translateX(20px);
    background-color: white;
  }

  .slider.round {
    border-radius: 34px;
  }

  .slider.round:before {
    border-radius: 50%;
  }

  .loading-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 20px;
    padding: 60px;
    color: var(--text-muted);
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 4px solid rgba(20, 184, 166, 0.1);
    border-top-color: var(--color-primary);
    border-radius: 50%;
    animation: spin 0.8s cubic-bezier(0.5, 0, 0.5, 1) infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .add-account-form {
    background: rgba(255, 255, 255, 0.02);
    padding: 20px;
    border-radius: 16px;
    border: 1px dashed var(--border-subtle);
    margin-bottom: 24px;
    animation: fadeIn 0.3s ease-out;
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(-10px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .empty-accounts {
    text-align: center;
    padding: 40px;
    background: rgba(255, 255, 255, 0.02);
    border-radius: 16px;
    border: 1px dashed var(--border-subtle);
    color: var(--text-muted);
    font-style: italic;
  }
</style>





