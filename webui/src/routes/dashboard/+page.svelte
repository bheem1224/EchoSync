<script>
  // Side-effect import: registers <echosync-system-overview> custom element
  import '../../components/core/SystemOverview.svelte';

  let activeViewIndex = 0;

  async function loadDashboard() {
    // 1. Fetch manifest and inject scripts
    // Fetch UI registry and manager ui-beta opt state
    const [manifestRes, uiBetaRes] = await Promise.all([
      fetch('/api/ui/registry', { credentials: 'include' }),
      fetch('/api/manager/ui-beta', { credentials: 'include' }).catch(() => null)
    ]);

    if (!manifestRes.ok) throw new Error('Failed to fetch UI registry');
    const manifestData = await manifestRes.json();

    let betaOpt = false;
    let devMode = false;
    if (uiBetaRes && uiBetaRes.ok) {
      try {
        const uiData = await uiBetaRes.json();
        betaOpt = !!uiData.beta_opt_in;
        devMode = !!uiData.dev_mode;
      } catch (e) {
        // ignore
      }
    }

    if (manifestData) {
      const scriptsToLoad = new Set();
      for (const [category, components] of Object.entries(manifestData)) {
        if (!Array.isArray(components)) continue;
        for (const comp of components) {
          if (comp.entry && comp.entry.endsWith('.js') && !comp.is_core) {
            // Natively track paths using exactly the plugin_id
            const absoluteUrl = (comp.entry.startsWith('http') || comp.entry.startsWith('/'))
              ? comp.entry
              : `/api/system/plugins/${comp.plugin_id}/ui/${comp.entry.replace(/^\//, '')}`;
            scriptsToLoad.add(absoluteUrl);
          }
        }
      }

      await Promise.all(Array.from(scriptsToLoad).map(src => {
        return new Promise((resolve) => {
          if (document.querySelector(`script[src^="${CSS.escape ? CSS.escape(src) : src}"]`)) {
            return resolve();
          }
          const script = document.createElement('script');
          script.type = 'module';
          script.src = src;
          script.onload = () => resolve();
          script.onerror = () => {
            console.error(`[Dashboard] Script injection failed for path: ${src} (HTTP 404)`);
            resolve(); // Gracefully catch error so it doesn't freeze the pipeline
          };
          document.head.appendChild(script);
        });
      }));
    }

    // 2. Fetch layout
    const layoutRes = await fetch('/api/system/dashboard', { credentials: 'include' });
    if (!layoutRes.ok) throw new Error('Failed to fetch dashboard layout');
    return await layoutRes.json();
  }

  $: dashboardPromise = loadDashboard();

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
  {#await dashboardPromise}
    <!-- Main loading spinner while fetching layout -->
    <div class="flex items-center justify-center h-64">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-accent"></div>
    </div>
  {:then layout}
    {#if layout && layout.views && layout.views.length > 0}
      <!-- Tab bar for multiple views -->
      {#if layout.views.length > 1}
        <div class="border-b border-glass-border mb-6">
          <nav class="-mb-px flex space-x-8" aria-label="Tabs">
            {#each layout.views as view, i}
              <button
                on:click={() => (activeViewIndex = i)}
                class="{activeViewIndex === i ? 'border-accent text-accent' : 'border-transparent text-white/70 hover:text-white hover:border-glass-border'} whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors"
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
        <h2 class="text-2xl font-bold leading-7 text-white sm:truncate sm:text-3xl sm:tracking-tight mb-4">
          {currentView.title}
        </h2>

        <!-- Lovelace Layout: Sections containing Cards -->
        <div class="flex flex-col md:flex-row gap-6 items-start">
          {#each currentView.sections || [] as section}
            <div class="flex-1 flex flex-col gap-6 w-full min-w-[300px]">
              {#each section.cards || [] as card}
                <div class="rounded-global bg-surface border border-glass-border text-white backdrop-blur-md min-h-[150px] overflow-hidden flex flex-col transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-green-500/10 active:translate-y-0 active:scale-95 w-full">
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
          {/each}
        </div>
      </div>
    {:else}
      <div class="bg-warning-bg border-l-4 border-warning-border p-4">
        <p class="text-warning-text">No dashboard layout views configured.</p>
      </div>
    {/if}
  {:catch layoutError}
    <div class="bg-error-bg border-l-4 border-error-border p-4 mb-4">
      <p class="text-error-text">Error loading dashboard: {layoutError.message}</p>
    </div>
  {/await}
</div>
