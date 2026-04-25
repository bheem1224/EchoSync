<script>
  import { onMount } from "svelte";
  import ManagerSettings from "../../../components/ManagerSettings.svelte";
  import ManagerQueues from "../../../components/ManagerQueues.svelte";
  import ProviderSettings from "../../../components/ProviderSettings.svelte";
  import DownloadQueueViewer from "../../../components/DownloadQueueViewer.svelte";
  import SystemSettings from "../../../components/SystemSettings.svelte";

  let layout = null;
  let activeView = null;
  let sidebarOpen = false;

  const componentMap = {
      'echosync-manager-settings': ManagerSettings,
      'echosync-manager-queues': ManagerQueues,
      'echosync-plex-card': ProviderSettings,
      'echosync-download-queue': DownloadQueueViewer,
      'echosync-system-metrics': SystemSettings
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
          class="btn-primary flex items-center gap-2 px-4 py-2 bg-primary text-black font-bold rounded-full hover:scale-95 transition-transform"
          on:click={() => (sidebarOpen = true)}
        >
          Sidebar Overlay
        </button>
      {/if}
    </header>

    <div
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 items-start"
    >
      {#if activeView.sections}
        {#each activeView.sections as section}
          <div class="flex flex-col gap-4">
            <h2 class="text-lg font-semibold text-muted">{section.title}</h2>

            {#if section.cards}
              {#each section.cards as card}
                {#if componentMap[card.type]}
                  <div class="bg-surface border border-glass-border rounded-global block w-full p-4 overflow-hidden shadow-2xl">
                    <svelte:component this={componentMap[card.type]} />
                  </div>
                {:else}
                  <svelte:element
                    this={card.type}
                    class="bg-surface border border-glass-border rounded-global block w-full p-4 overflow-hidden shadow-2xl"
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
