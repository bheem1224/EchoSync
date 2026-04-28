<script>
  import { onMount } from "svelte";
  import TabbedQueues from "./TabbedQueues.svelte";
  import AccountBuilder from "./AccountBuilder.svelte";
  import apiClient from "../../../api/client";
  import { feedback } from "../../../stores/feedback";

  // ── Settings state ────────────────────────────────────────────────────────
  let settingsOpen = false; // Collapsed by default per spec
  let showAccountsModal = false;

  let settings = {
    enabled: true,
    automation_level: 1,
    upgrade_quality_profile_id: null,
    auto_delete_low_quality_duplicates: false,
    auto_process_suggestion_engine_ratings: true,
  };

  let qualityProfiles = [];
  let savingSettings = false;

  onMount(async () => {
    await Promise.all([loadSettings(), loadProfiles()]);
  });

  async function loadSettings() {
    try {
      const res = await apiClient.get("/manager/settings");
      if (res.data?.settings) {
        settings = { ...settings, ...res.data.settings };
      }
    } catch (e) {
      console.error("Failed to load manager settings", e);
    }
  }

  async function loadProfiles() {
    try {
      const res = await apiClient.get("/quality-profiles");
      qualityProfiles = res.data?.profiles || [];
    } catch (e) {
      console.error("Failed to load quality profiles", e);
    }
  }

  async function saveSettings() {
    savingSettings = true;
    try {
      await apiClient.post("/manager/settings", settings);
      feedback.addToast("Settings saved", "success");
    } catch (e) {
      feedback.addToast("Failed to save settings", "error");
    } finally {
      savingSettings = false;
    }
  }

  const levelDescriptions = {
    1: "Auto-routes Hygiene actions (duplicate & quality) to Pending Actions.",
    2: "Level 1 + Upgrade Suggestions are auto-routed.",
    3: "Level 2 + Delete Suggestions are auto-routed (full automation).",
  };
</script>

<svelte:head>
  <title>Media Manager | EchoSync</title>
</svelte:head>

<div
  class="h-full w-full flex flex-col text-white p-6 md:p-10 gap-6 overflow-hidden"
>
  <!-- ── Page Header ────────────────────────────────────────────────────── -->
  <header class="flex justify-between items-center flex-shrink-0">
    <div class="flex flex-col">
      <div
        class="text-[10px] uppercase font-black tracking-[0.3em] text-primary mb-1"
      >
        Media Management
      </div>
      <h1 class="text-3xl font-black tracking-tight flex items-center gap-3">
        Media Manager
        <span class="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
      </h1>
    </div>

    <div class="flex items-center gap-3">
      <!-- Consensus status -->
      <div class="hidden md:flex flex-col items-end mr-2">
        <span class="text-[10px] text-muted uppercase font-bold"
          >Consensus Status</span
        >
        <span class="text-xs text-emerald-400 font-bold">Synchronized</span>
      </div>

      <!-- Accounts Button -->
      <button
        id="open-accounts-modal-btn"
        class="flex items-center gap-2 px-4 py-2 rounded-xl bg-surface/60 border border-glass-border hover:border-primary/60 hover:bg-primary/10 transition-all text-sm font-bold text-muted hover:text-white"
        on:click={() => (showAccountsModal = true)}
        title="Manage Account Mappings"
      >
        <svg
          class="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"
          />
        </svg>
        <span class="hidden sm:inline">Accounts</span>
      </button>

      <!-- Settings cog -->
      <button
        class="w-10 h-10 rounded-full bg-surface border border-glass-border flex items-center justify-center hover:border-primary/50 transition-colors"
        on:click={() => (settingsOpen = !settingsOpen)}
        title="Manager Settings"
      >
        <svg
          class="w-5 h-5 text-muted transition-transform duration-300 {settingsOpen
            ? 'rotate-90'
            : ''}"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
          />
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
          />
        </svg>
      </button>
    </div>
  </header>

  <!-- ── Collapsible Settings Accordion ────────────────────────────────── -->
  {#if settingsOpen}
    <div
      class="flex-shrink-0 bg-surface/30 backdrop-blur-sm border border-glass-border rounded-2xl p-6 animate-in"
    >
      <div class="flex items-center justify-between mb-5">
        <h2 class="text-base font-bold text-white flex items-center gap-2">
          <span class="text-primary">⚙</span> Manager Settings
        </h2>
        <button
          class="text-[11px] text-muted hover:text-white transition-colors"
          on:click={() => (settingsOpen = false)}
        >
          Close ✕
        </button>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <!-- Col 1: Enable toggle -->
        <div class="flex flex-col gap-5">
          <div class="flex items-center justify-between">
            <span class="text-sm font-bold text-white"
              >Enable Media Manager</span
            >
            <label class="switch">
              <input
                type="checkbox"
                id="mm-enable-toggle"
                bind:checked={settings.enabled}
              />
              <span class="slider round"></span>
            </label>
          </div>
        </div>

        <!-- Col 2: Quality Profile -->
        <div class="flex flex-col gap-5">
          <div class="flex flex-col gap-2">
            <label
              for="quality-profile-select"
              class="text-sm font-bold text-white"
              >Quality Profile Enforcer</label
            >
            <select
              id="quality-profile-select"
              bind:value={settings.upgrade_quality_profile_id}
              class="bg-black/40 border border-glass-border rounded-lg px-3 py-2 text-sm text-white focus:border-primary outline-none transition-colors"
              disabled={!settings.enabled}
            >
              <option value={null}>None</option>
              {#each qualityProfiles as p}
                <option value={p.id}>{p.name}</option>
              {/each}
            </select>
          </div>
        </div>

        <!-- Col 3: Automation Level + User Actions tooltip -->
        <div class="flex flex-col gap-5">
          {#if settings.enabled}
            <div class="flex flex-col gap-2">
              <label
                for="automation-level-select"
                class="text-sm font-bold text-white">Automation Level</label
              >
              <select
                id="automation-level-select"
                bind:value={settings.automation_level}
                class="bg-black/40 border border-glass-border rounded-lg px-3 py-2 text-sm text-white focus:border-primary outline-none transition-colors"
              >
                <option value={1}>Level 1 — Hygiene Only</option>
                <option value={2}>Level 2 — + Upgrade Suggestions</option>
                <option value={3}>Level 3 — Full Automation</option>
              </select>
              <p class="text-[11px] text-muted leading-relaxed">
                {levelDescriptions[settings.automation_level]}
              </p>
            </div>
          {/if}

          <div
            class="flex items-start gap-2 bg-black/20 border border-glass-border rounded-lg p-3"
          >
            <span class="text-primary mt-0.5 flex-shrink-0">ⓘ</span>
            <div class="flex flex-col gap-1">
              <span class="text-xs font-bold text-white/80">User Actions</span>
              <p class="text-[11px] text-muted leading-relaxed">
                A ½ star rating requests a Delete. A 1 star rating requests an
                Upgrade. (Half-stars must be enabled in Plex/Jellyfin.
                Thresholds editable in config.json)
              </p>
            </div>
          </div>
        </div>
      </div>

      <div class="flex justify-end mt-5 pt-4 border-t border-glass-border">
        <button
          id="save-manager-settings-btn"
          class="px-5 py-2 bg-primary text-black text-sm font-black rounded-xl hover:scale-95 transition-all disabled:opacity-50"
          on:click={saveSettings}
          disabled={savingSettings}
        >
          {savingSettings ? "Saving…" : "Save Settings"}
        </button>
      </div>
    </div>
  {/if}

  <!-- ── Tabbed Queues (fills remaining space) ──────────────────────────── -->
  <main
    class="flex-grow min-h-0 bg-surface/20 backdrop-blur-sm border border-glass-border rounded-[2rem] p-8 shadow-2xl overflow-hidden flex flex-col"
  >
    <TabbedQueues />
  </main>
</div>

<!-- ── Account Builder Modal ──────────────────────────────────────────── -->
{#if showAccountsModal}
  <AccountBuilder on:close={() => (showAccountsModal = false)} />
{/if}

<style>
  :global(body) {
    background-color: #050505;
    background-image: radial-gradient(
        circle at 0% 0%,
        rgba(29, 185, 84, 0.05) 0%,
        transparent 50%
      ),
      radial-gradient(
        circle at 100% 100%,
        rgba(0, 229, 255, 0.05) 0%,
        transparent 50%
      );
  }

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
    background-color: rgba(255, 255, 255, 0.08);
    border-radius: 24px;
    transition: 0.3s;
    border: 1px solid rgba(255, 255, 255, 0.1);
  }
  .slider:before {
    position: absolute;
    content: "";
    height: 18px;
    width: 18px;
    left: 2px;
    bottom: 2px;
    background-color: rgba(255, 255, 255, 0.5);
    border-radius: 50%;
    transition: 0.3s;
  }
  input:checked + .slider {
    background-color: var(--color-primary);
    border-color: var(--color-primary);
  }
  input:checked + .slider:before {
    transform: translateX(20px);
    background-color: #000;
  }

  .animate-in {
    animation: slideDown 0.2s ease-out;
  }
  @keyframes slideDown {
    from {
      opacity: 0;
      transform: translateY(-8px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
</style>
