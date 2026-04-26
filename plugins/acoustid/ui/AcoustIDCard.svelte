<svelte:options customElement={{
  tag: 'acoustid-settings-card',
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

  let apiKey = '';
  let keyConfigured = false;
  let showKey = false;

  let autoContribute = false;

  // ── Lifecycle ──────────────────────────────────────────────────────────────
  onMount(async () => {
    await loadConfig();
    loading = false;
  });

  async function loadConfig() {
    try {
      const base = apiBase || '';
      const res = await fetch(`${base}/api/plugins/acoustid/config`);
      if (res.ok) {
        const data = await res.json();
        keyConfigured = data.api_key_configured ?? false;
        autoContribute = data.auto_contribute ?? false;
        // Never pre-fill the key; show a placeholder if one is stored.
        if (keyConfigured) apiKey = '';
      }
    } catch (err) {
      console.error('[AcoustIDSettingsCard] Failed to load config:', err);
    }
  }

  async function saveConfig() {
    const payload = { auto_contribute: autoContribute };

    // Only send the key if the user actually typed something
    if (apiKey.trim()) {
      payload.api_key = apiKey.trim();
    } else if (!keyConfigured) {
      error = 'An API Key is required for fingerprinting.';
      return;
    }

    error = '';
    saving = true;
    saved = false;

    try {
      const base = apiBase || '';
      const res = await fetch(`${base}/api/plugins/acoustid/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        const data = await res.json();
        keyConfigured = data.api_key_configured ?? keyConfigured;
        apiKey = '';
        saved = true;
        // Dispatch a DOM event
        dispatchEvent(new CustomEvent('acoustid-config-saved', {
          bubbles: true,
          composed: true,
          detail: { api_key_configured: keyConfigured, auto_contribute: autoContribute }
        }));
        setTimeout(() => (saved = false), 3000);
      } else {
        const data = await res.json().catch(() => ({}));
        error = data.error || 'Failed to save configuration.';
      }
    } catch (err) {
      console.error('[AcoustIDSettingsCard] Save error:', err);
      error = 'Network error while saving. Please try again.';
    } finally {
      saving = false;
    }
  }
</script>

<section class="mb-4 p-6 bg-surface backdrop-blur-md border border-glass-border rounded-global">

  <!-- Header -->
  <div class="flex items-center gap-3 mb-5 pb-3 border-b border-glass-border">
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-sky-400">
      <path d="M2 12c.6.5 1.2 1 2.5 1s2.5-1 3.5-2c1-1 2.2-2 3.5-2s2.5 1 3.5 2c1 1 2.2 2 3.5 2s1.9-.5 2.5-1"/>
      <path d="M2 18c.6.5 1.2 1 2.5 1s2.5-1 3.5-2c1-1 2.2-2 3.5-2s2.5 1 3.5 2c1 1 2.2 2 3.5 2s1.9-.5 2.5-1"/>
      <path d="M2 6c.6.5 1.2 1 2.5 1s2.5-1 3.5-2c1-1 2.2-2 3.5-2s2.5 1 3.5 2c1 1 2.2 2 3.5 2s1.9-.5 2.5-1"/>
    </svg>
    <div>
      <h2 class="m-0 text-xl font-semibold leading-tight">AcoustID Configuration</h2>
      <p class="m-0 text-xs text-secondary mt-0.5">Audio fingerprinting service</p>
    </div>
    <span class="ml-auto text-[12px] px-2 py-1 rounded-[4px] bg-sky-500/20 text-sky-400">Fingerprinting</span>
  </div>

  {#if loading}
    <div class="p-5 text-center text-secondary animate-pulse">Loading configuration…</div>
  {:else}

    <!-- API Key -->
    <div class="mb-6">
      <label class="block text-sm font-medium mb-1" for="acoustid-api-key">
        AcoustID API Key
        {#if keyConfigured}
          <span class="ml-2 text-[11px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400">● Configured</span>
        {/if}
      </label>
      <p class="text-xs text-secondary mb-2">
        Get your free API key from
        <a href="https://acoustid.org/new-application" target="_blank" rel="noopener noreferrer" class="text-sky-400 hover:underline">
          acoustid.org/new-application
        </a>.
        Required to identify songs by their audio signature.
      </p>
      <div class="relative flex items-center">
        <input
          id="acoustid-api-key"
          type={showKey ? 'text' : 'password'}
          bind:value={apiKey}
          placeholder={keyConfigured ? '••••••••  (leave blank to keep current)' : 'Enter your AcoustID API key'}
          class="w-full px-3 py-2 pr-10 bg-black/30 border border-glass-border rounded-global text-sm text-primary box-border focus:outline-none focus:border-sky-400 transition-colors"
        />
        <button
          type="button"
          class="absolute right-2 bg-transparent border-none cursor-pointer text-base p-1 opacity-50 hover:opacity-100 transition-opacity"
          on:click={() => (showKey = !showKey)}
          title={showKey ? 'Hide key' : 'Show key'}
          aria-label={showKey ? 'Hide key' : 'Show key'}
        >
          {showKey ? '🙈' : '👁️'}
        </button>
      </div>
    </div>

    <!-- Auto-Contribute Toggle -->
    <div class="mb-6 p-4 rounded-global border border-glass-border bg-white/[0.03]">
      <div class="flex items-center justify-between gap-4">
        <div class="flex-1">
          <p class="m-0 text-sm font-semibold">Auto-Contribute Fingerprints</p>
        </div>

        <!-- Toggle Switch -->
        <button
          type="button"
          role="switch"
          aria-checked={autoContribute}
          class="relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none
            {autoContribute ? 'bg-sky-500' : 'bg-white/20'}"
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
        When enabled, EchoSync will automatically submit acoustic fingerprints of your music to the 
        AcoustID database to help identify tracks for other community members.
      </p>
      {#if autoContribute}
        <p class="mt-2 text-[11px] text-amber-400/80 bg-amber-500/10 border border-amber-500/20 rounded px-2 py-1.5">
          ⚠ Submissions are anonymous but require a valid API key. Fingerprints are generated locally and uploaded during background library enrichment.
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
        class="px-5 py-2 bg-sky-600 hover:bg-sky-500 text-white font-medium rounded-global transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
        on:click={saveConfig}
        disabled={saving}
      >
        {saving ? 'Saving…' : 'Save Settings'}
      </button>
    </div>

  {/if}
</section>
