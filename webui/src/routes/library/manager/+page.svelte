<script>
  import { onMount } from "svelte";
  import ManagerSettings from "../../../components/ManagerSettings.svelte";
  import ManagedAccounts from "../../../components/ManagedAccounts.svelte";
  import DuplicateResolutionCard from "../../../components/DuplicateResolutionCard.svelte";
  import PendingActionsCard from "../../../components/PendingActionsCard.svelte";
  import AccountLinker from "../../../components/AccountLinker.svelte";

  let layout = null;
  let activeView = null;
  let sidebarOpen = false;

  const componentMap = {
      'echosync-manager-settings': ManagerSettings,
      'echosync-managed-accounts': ManagedAccounts,
      'echosync-duplicate-resolution': DuplicateResolutionCard,
      'echosync-pending-actions': PendingActionsCard,
      'echosync-account-linker': AccountLinker,
  };

  onMount(async () => {
    try {
      // Fetch the YAML layout from the backend
      const res = await fetch("/api/dashboard/layout");
      if (res.ok) {
        layout = await res.json();
        // Find the manager view, or default to the first available view
        activeView =
          layout.dashboard.views.find((v) => v.id === "manager") ||
          layout.dashboard.views[0];
      }
    } catch (err) {
      console.error("Failed to load Lovelace layout:", err);
    }
  });
</script>

{#if activeView}
  <div
    class="h-full w-full flex flex-col gap-6 relative text-white bg-transparent"
  >
    <header class="flex justify-between items-center">
      <h1 class="text-2xl font-bold">{activeView.title}</h1>
      {#if activeView.sidebar?.enabled}
        <button
          class="flex items-center justify-center w-10 h-10 bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.1)] text-white rounded-full hover:bg-[rgba(255,255,255,0.1)] transition-colors"
          title="Account Linker"
          on:click={() => (sidebarOpen = true)}
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"></path></svg>
        </button>
      {/if}
    </header>

    <div
      class="grid grid-cols-1 md:grid-cols-2 gap-6 items-start"
    >
      {#if activeView.sections}
        {#each activeView.sections as section}
          <div class="flex flex-col gap-4 {section.fullWidth ? 'md:col-span-2' : ''}">
            {#if section.title}
              <h2 class="text-lg font-semibold text-muted">{section.title}</h2>
            {/if}

            {#if section.cards}
              {#each section.cards as card}
                {#if componentMap[card.type]}
                  <div class="card p-4 overflow-hidden">
                    <svelte:component this={componentMap[card.type]} />
                  </div>
                {:else}
                  <svelte:element
                    this={card.type}
                    class="card p-4 overflow-hidden block w-full"
                  ></svelte:element>
                {/if}
              {/each}
            {/if}
          </div>
        {/each}
      {/if}
    </div>

    {#if activeView.sidebar?.enabled && sidebarOpen}
      <div
        class="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 cursor-pointer"
        on:click={() => (sidebarOpen = false)}
        role="button"
        tabindex="0"
        on:keydown={(e) => e.key === "Escape" && (sidebarOpen = false)}
      ></div>

      <div
        class="fixed top-0 right-0 h-screen w-96 z-50 bg-surface backdrop-blur-xl border-l border-glass-border shadow-2xl flex flex-col p-6 overflow-y-auto transform transition-transform"
      >
        <div class="flex justify-between items-center mb-6">
          <h2 class="text-xl font-bold">Options</h2>
          <button
            class="text-muted hover:text-white text-2xl"
            on:click={() => (sidebarOpen = false)}>✕</button
          >
        </div>

        <div class="flex flex-col gap-4">
          {#if activeView.sidebar.cards}
            {#each activeView.sidebar.cards as card}
              {#if componentMap[card.type]}
                <div class="bg-card border border-glass-border rounded-global block w-full p-4">
                  <svelte:component this={componentMap[card.type]} />
                </div>
              {:else}
                <svelte:element
                  this={card.type}
                  class="bg-card border border-glass-border rounded-global block w-full p-4"
                ></svelte:element>
              {/if}
            {/each}
          {/if}
        </div>
      </div>
    {/if}
  </div>
{:else}
  <div class="flex items-center justify-center h-64 text-muted">
    <p>Loading YAML Dashboard Layout...</p>
  </div>
{/if}
