<svelte:options customElement={{
  tag: 'musicbrainz-settings-card',
  shadow: 'none'
}} />

<script>
  export let apiBase = '';

  import { onMount } from 'svelte';

  // ── State ─────────────────────────────────────────────────────────────────
  let loading = true;
  let saving = false;
  let saved = false;
  let error = '';

  let userToken = '';
  let tokenConfigured = false;
  let showToken = false;

  let autoContribute = false;

  // ── Lifecycle ──────────────────────────────────────────────────────────────
  onMount(async () => {
    await loadConfig();
    loading = false;
  });

  async function loadConfig() {
    try {
      const base = apiBase || '';
      const res = await fetch(`${base}/api/plugins/musicbrainz/config`);
      if (res.ok) {
        const data = await res.json();
        tokenConfigured = data.token_configured ?? false;
        autoContribute = data.auto_contribute ?? false;
        // Never pre-fill the token; show a placeholder if one is stored.
        if (tokenConfigured) userToken = '';
      }
    } catch (err) {
      console.error('[MusicBrainzSettingsCard] Failed to load config:', err);
    }
  }

  async function saveConfig() {
    const payload = { auto_contribute: autoContribute };

    // Only send the token if the user actually typed something
    if (userToken.trim()) {
      payload.user_token = userToken.trim();
    } else if (!tokenConfigured) {
      error = 'A User Token is required to enable contributions.';
      return;
    }

    error = '';
    saving = true;
    saved = false;

    try {
      const base = apiBase || '';
      const res = await fetch(`${base}/api/plugins/musicbrainz/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        const data = await res.json();
        tokenConfigured = data.token_configured ?? tokenConfigured;
        userToken = '';
        saved = true;
        // Dispatch a DOM event so the host page can react if needed
        dispatchEvent(new CustomEvent('musicbrainz-config-saved', {
          bubbles: true,
          composed: true,
          detail: { auto_contribute: autoContribute, token_configured: tokenConfigured }
        }));
        setTimeout(() => (saved = false), 3000);
      } else {
        const data = await res.json().catch(() => ({}));
        error = data.error || 'Failed to save configuration.';
      }
    } catch (err) {
      console.error('[MusicBrainzSettingsCard] Save error:', err);
      error = 'Network error while saving. Please try again.';
    } finally {
      saving = false;
    }
  }
</script>

<section class="mb-4 p-6 bg-surface backdrop-blur-md border border-glass-border rounded-global">

  <!-- Header -->
  <div class="flex items-center gap-3 mb-5 pb-3 border-b border-glass-border">
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-[#ba6415]">
      <circle cx="12" cy="12" r="10"/>
      <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
      <line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>
    <div>
      <h2 class="m-0 text-xl font-semibold leading-tight">MusicBrainz Configuration</h2>
      <p class="m-0 text-xs text-secondary mt-0.5">Contribution & API settings</p>
    </div>
    <span class="ml-auto text-[12px] px-2 py-1 rounded-[4px] bg-[#ba6415]/20 text-[#ba6415]">Metadata</span>
  </div>

  {#if loading}
    <div class="p-5 text-center text-secondary animate-pulse">Loading configuration…</div>
  {:else}

    <!-- User Token -->
    <div class="mb-6">
      <label class="block text-sm font-medium mb-1" for="mb-user-token">
        User Token / API Key
        {#if tokenConfigured}
          <span class="ml-2 text-[11px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400">● Configured</span>
        {/if}
      </label>
      <p class="text-xs text-secondary mb-2">
        Obtain your personal access token from
        <a href="https://musicbrainz.org/account/applications" target="_blank" rel="noopener noreferrer" class="text-[#ba6415] hover:underline">
          musicbrainz.org/account/applications
        </a>.
        Required for community contributions and ISRC submissions.
      </p>
      <div class="relative flex items-center">
        <input
          id="mb-user-token"
          type={showToken ? 'text' : 'password'}
          bind:value={userToken}
          placeholder={tokenConfigured ? '••••••••  (leave blank to keep current)' : 'Enter your MusicBrainz user token'}
          class="w-full px-3 py-2 pr-10 bg-black/30 border border-glass-border rounded-global text-sm text-primary box-border focus:outline-none focus:border-[#ba6415] transition-colors"
        />
        <button
          type="button"
          class="absolute right-2 bg-transparent border-none cursor-pointer text-base p-1 opacity-50 hover:opacity-100 transition-opacity"
          on:click={() => (showToken = !showToken)}
          title={showToken ? 'Hide token' : 'Show token'}
          aria-label={showToken ? 'Hide token' : 'Show token'}
        >
          {showToken ? '🙈' : '👁️'}
        </button>
      </div>
    </div>

    <!-- Auto-Contribute Toggle -->
    <div class="mb-6 p-4 rounded-global border border-glass-border bg-white/[0.03]">
      <div class="flex items-center justify-between gap-4">
        <div class="flex-1">
          <p class="m-0 text-sm font-semibold">Auto-Contribute Missing Data</p>
        </div>

        <!-- Toggle Switch -->
        <button
          type="button"
          role="switch"
          aria-checked={autoContribute}
          class="relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none
            {autoContribute ? 'bg-[#ba6415]' : 'bg-white/20'}"
          on:click={() => (autoContribute = !autoContribute)}
          aria-label="Toggle auto-contribute"
        >
          <span
            class="pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow ring-0 transition-transform duration-200 ease-in-out
              {autoContribute ? 'translate-x-5' : 'translate-x-0'}"
          ></span>
        </button>
      </div>
      <p class="mt-2 text-xs text-secondary leading-relaxed">
        When enabled, EchoSync will automatically submit missing acoustic fingerprints (AcoustID) and 
        metadata corrections back to the MusicBrainz database during imports.
      </p>
      {#if autoContribute}
        <p class="mt-2 text-[11px] text-amber-400/80 bg-amber-500/10 border border-amber-500/20 rounded px-2 py-1.5">
          ⚠ A valid User Token is required for contributions. Submissions happen in the background and are governed by MusicBrainz's contribution guidelines.
        </p>
      {/if}
    </div>

    <!-- Error / Success feedback -->
    {#if error}
      <div class="mb-4 px-3 py-2 rounded-global bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
        ⚠ {error}
      </div>
    {/if}
    {#if saved}
      <div class="mb-4 px-3 py-2 rounded-global bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm">
        ✓ Configuration saved successfully.
      </div>
    {/if}

    <!-- Save Button -->
    <div class="flex justify-end">
      <button
        class="px-5 py-2 bg-[#ba6415] hover:bg-[#ba6415]/90 text-white font-medium rounded-global transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
        on:click={saveConfig}
        disabled={saving}
      >
        {saving ? 'Saving…' : 'Save Settings'}
      </button>
    </div>

  {/if}
</section>
