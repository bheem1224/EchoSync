<script>
    import { createEventDispatcher } from 'svelte';
    import { Trash2, Plus, ArrowRight, Info } from 'lucide-svelte';

    export let mappings = [];

    // Ensure mappings is initialized as an array
    if (!mappings) {
        mappings = [];
    }

    const dispatch = createEventDispatcher();

    function addMapping() {
        mappings = [...mappings, { remote: '', local: '' }];
        dispatch('change', mappings);
    }

    function removeMapping(index) {
        mappings = mappings.filter((_, i) => i !== index);
        dispatch('change', mappings);
    }

    function updateMapping() {
        dispatch('change', mappings);
    }
</script>

<div class="space-y-4">
    <div class="flex items-center gap-2 mb-2">
        <label class="text-sm font-medium text-gray-300">Path Mappings</label>
        <div class="group relative flex items-center">
            <Info class="w-4 h-4 text-gray-500 hover:text-gray-300 cursor-help" />
            <div class="absolute left-full top-1/2 -translate-y-1/2 ml-2 w-64 p-2 bg-gray-800 border border-gray-700 rounded shadow-xl z-50 invisible group-hover:visible text-xs text-gray-300 pointer-events-none">
                Required for Web Player and Metadata Fingerprinting. Maps paths from the remote server (e.g. Docker) to the local filesystem.
            </div>
        </div>
    </div>

    {#if mappings.length === 0}
        <div class="text-sm text-gray-500 italic">No path mappings configured.</div>
    {/if}

    <div class="space-y-3">
        {#each mappings as mapping, i}
            <div class="flex items-center gap-2">
                <div class="flex-1">
                    <input
                        type="text"
                        bind:value={mapping.remote}
                        on:input={updateMapping}
                        placeholder="Remote Path (e.g. /data/music)"
                        class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-md text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                    />
                </div>

                <ArrowRight class="w-4 h-4 text-gray-500 flex-shrink-0" />

                <div class="flex-1">
                    <input
                        type="text"
                        bind:value={mapping.local}
                        on:input={updateMapping}
                        placeholder="Local Path (e.g. /mnt/user/music)"
                        class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-md text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                    />
                </div>

                <button
                    on:click={() => removeMapping(i)}
                    class="p-2 text-gray-400 hover:text-red-400 hover:bg-red-400/10 rounded-md transition-colors"
                    title="Remove mapping"
                >
                    <Trash2 class="w-4 h-4" />
                </button>
            </div>
        {/each}
    </div>

    <button
        on:click={addMapping}
        class="flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300 transition-colors mt-2"
    >
        <Plus class="w-4 h-4" />
        Add Path Mapping
    </button>
</div>
