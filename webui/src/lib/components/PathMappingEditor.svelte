<svelte:options customElement={{
  tag: 'echosync-path-mapping-editor',
  shadow: 'none'
}} />

<script>
    export let mappings = "[]";

    // Reactively parse the prop since it will come as a string attribute
    $: parsedMappings = typeof mappings === 'string' ? JSON.parse(mappings || "[]") : mappings || [];

    // Local state to bind to inputs
    let localMappings = [];

    $: {
        localMappings = [...parsedMappings];
    }

    let formRef;

    function dispatchUpdate() {
        if (formRef) {
            formRef.dispatchEvent(new CustomEvent('es-path-update', {
                detail: localMappings,
                bubbles: true,
                composed: true
            }));
        }
    }

    function addMapping() {
        localMappings = [...localMappings, { remote: '', local: '' }];
        dispatchUpdate();
    }

    function removeMapping(index) {
        localMappings = localMappings.filter((_, i) => i !== index);
        dispatchUpdate();
    }

    function updateMapping() {
        dispatchUpdate();
    }
</script>

<div bind:this={formRef} class="flex flex-col gap-4 p-6 bg-surface backdrop-blur-md border border-glass-border rounded-global">
    <div class="flex items-center gap-2 mb-2">
        <label class="text-sm font-medium text-primary">Path Mappings</label>
        <div class="group relative flex items-center">
            <!-- Info SVG -->
            <svg class="w-4 h-4 text-secondary hover:text-primary cursor-help transition-colors" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
            <div class="absolute left-full top-1/2 -translate-y-1/2 ml-2 w-64 p-2 bg-surface backdrop-blur-md border border-glass-border rounded-global shadow-xl z-50 invisible group-hover:visible text-xs text-primary pointer-events-none">
                Required for Web Player and Metadata Fingerprinting. Maps paths from the remote server (e.g. Docker) to the local filesystem.
            </div>
        </div>
    </div>

    {#if localMappings.length === 0}
        <div class="text-sm text-secondary italic">No path mappings configured.</div>
    {/if}

    <div class="flex flex-col gap-3">
        {#each localMappings as mapping, i}
            <div class="flex items-center gap-2">
                <div class="flex-1">
                    <input
                        type="text"
                        bind:value={mapping.remote}
                        on:input={updateMapping}
                        placeholder="Remote Path (e.g. /data/music)"
                        class="w-full px-3 py-2 bg-background border border-border rounded-global text-sm text-primary placeholder-secondary focus:outline-none focus:border-accent transition-colors"
                    />
                </div>

                <!-- ArrowRight SVG -->
                <svg class="w-4 h-4 text-secondary flex-shrink-0" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>

                <div class="flex-1">
                    <input
                        type="text"
                        bind:value={mapping.local}
                        on:input={updateMapping}
                        placeholder="Local Path (e.g. /mnt/user/music)"
                        class="w-full px-3 py-2 bg-background border border-border rounded-global text-sm text-primary placeholder-secondary focus:outline-none focus:border-accent transition-colors"
                    />
                </div>

                <button
                    type="button"
                    on:click={() => removeMapping(i)}
                    class="p-2 text-secondary hover:text-error-text hover:bg-error-bg rounded-global transition-colors"
                    title="Remove mapping"
                >
                    <!-- Trash2 SVG -->
                    <svg class="w-4 h-4" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/></svg>
                </button>
            </div>
        {/each}
    </div>

    <button
        type="button"
        on:click={addMapping}
        class="flex items-center gap-2 text-sm text-accent hover:opacity-80 transition-opacity mt-2 self-start focus:outline-none active:scale-95"
    >
        <!-- Plus SVG -->
        <svg class="w-4 h-4" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M12 5v14"/></svg>
        Add Path Mapping
    </button>
</div>

<style>
  .bg-error-bg {
    background-color: var(--es-error-bg);
  }
  .text-error-text {
    color: var(--es-error-text);
  }
</style>
