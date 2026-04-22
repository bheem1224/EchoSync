<script>
  import { onMount } from 'svelte';

  let layout = null;
  let isLoadingLayout = true;
  let layoutError = null;
  let activeViewIndex = 0;

  onMount(async () => {
    try {
      // 1. Fetch manifest and inject scripts
      const manifestRes = await fetch('/api/system/plugins/ui-manifest', { credentials: 'include' });
      if (!manifestRes.ok) throw new Error('Failed to fetch UI manifest');
      const manifestData = await manifestRes.json();

      if (manifestData && Array.isArray(manifestData.plugins)) {
        for (const plugin of manifestData.plugins) {
          if (plugin.assets && plugin.assets.js) {
            const script = document.createElement('script');
            script.type = 'module';
            script.src = plugin.assets.js;
            document.head.appendChild(script);
          }
        }
      }

      // 2. Fetch layout
      const layoutRes = await fetch('/api/system/dashboard', { credentials: 'include' });
      if (!layoutRes.ok) throw new Error('Failed to fetch dashboard layout');
      const layoutData = await layoutRes.json();
      layout = layoutData;
    } catch (err) {
      console.error(err);
      layoutError = err.message;
    } finally {
      isLoadingLayout = false;
    }
  });

  // Helper to wait for custom element or timeout
  function waitForComponent(tagName, timeoutMs = 3000) {
    return Promise.race([
      customElements.whenDefined(tagName).then(() => true),
      new Promise((_, reject) =>
        setTimeout(() => reject(new Error(`Timeout waiting for component ${tagName}`)), timeoutMs)
      )
    ]);
  }
</script>

<div class="p-6">
  {#if isLoadingLayout}
    <!-- Main loading spinner while fetching layout -->
    <div class="flex items-center justify-center h-64">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-accent"></div>
    </div>
  {:else if layoutError}
    <div class="bg-error-bg border-l-4 border-error-border p-4 mb-4">
      <p class="text-error-text">Error loading dashboard: {layoutError}</p>
    </div>
  {:else if layout && layout.views && layout.views.length > 0}
    <!-- Tab bar for multiple views -->
    {#if layout.views.length > 1}
      <div class="border-b border-border mb-6">
        <nav class="-mb-px flex space-x-8" aria-label="Tabs">
          {#each layout.views as view, i}
            <button
              on:click={() => (activeViewIndex = i)}
              class="{activeViewIndex === i ? 'border-accent text-accent' : 'border-transparent text-secondary hover:text-primary hover:border-border'} whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm"
            >
              {view.title}
            </button>
          {/each}
        </nav>
      </div>
    {/if}

    <!-- View Content -->
    {@const currentView = layout.views[activeViewIndex]}

    <div class="mb-6">
      <h2 class="text-2xl font-bold leading-7 text-primary sm:truncate sm:text-3xl sm:tracking-tight mb-4">
        {currentView.title}
      </h2>

      <!-- Responsive grid layout -->
      <div class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {#each currentView.cards as card}
          <div class="col-span-1 rounded-global bg-surface shadow min-h-[150px] overflow-hidden flex flex-col">
            {#await waitForComponent(card.type)}
              <!-- Skeleton placeholder -->
              <div class="p-4 flex-1 flex flex-col animate-pulse">
                <div class="h-4 bg-surface-hover rounded-global w-1/2 mb-4"></div>
                <div class="h-10 bg-surface-hover rounded-global w-full mb-2"></div>
                <div class="h-10 bg-surface-hover rounded-global w-3/4"></div>
              </div>
            {:then _}
              <!-- Loaded Web Component -->
              <svelte:element this={card.type} class="flex-1 w-full h-full block" />
            {:catch err}
              <!-- Error fallback -->
              <div class="p-4 bg-error-bg flex-1 flex flex-col items-center justify-center text-center">
                <svg class="h-8 w-8 text-error-border mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p class="text-sm font-medium text-error-text">Component Failed to Load</p>
                <p class="text-xs text-error-text opacity-80 mt-1">{card.type}</p>
              </div>
            {/await}
          </div>
        {/each}
      </div>
    </div>
  {:else}
    <div class="bg-warning-bg border-l-4 border-warning-border p-4">
      <p class="text-warning-text">No dashboard layout views configured.</p>
    </div>
  {/if}
</div>
