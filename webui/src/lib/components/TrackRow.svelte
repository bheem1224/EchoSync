<script>
    export let track;
    export let artist;
    export let album;
    export let onPlay;
    export let onDelete;
    export let onFetchMetadata;
    export let onForceUpgrade;
    export let onForceDelete;

    function formatDuration(ms) {
        if (!ms) return '-:--';
        const seconds = Math.floor(ms / 1000);
        const m = Math.floor(seconds / 60);
        const s = seconds % 60;
        return `${m}:${s.toString().padStart(2, '0')}`;
    }

    let showMenu = false;

    function toggleMenu() {
        showMenu = !showMenu;
    }

    function closeMenu() {
        showMenu = false;
    }

    function handleAction(action) {
        closeMenu();
        if (action === 'play') onPlay(track, artist, album);
        if (action === 'delete') onDelete(track.id, album);
        if (action === 'metadata') onFetchMetadata(track.id);
        if (action === 'upgrade') onForceUpgrade(track.id);
        if (action === 'force_delete') onForceDelete(track.id);
    }

    // Simple click outside handler
    function handleClickOutside(event) {
        if (showMenu && !event.target.closest('.menu-container')) {
            showMenu = false;
        }
    }
</script>

<svelte:window on:click={handleClickOutside} />

<div class="track-row group hover:bg-white/5 rounded-md px-3 py-2 grid grid-cols-[40px_1fr_60px_auto] items-center gap-2 transition-colors">
    <span class="text-gray-500 text-xs font-mono">{track.track_number || '-'}</span>
    <span class="text-white text-sm font-medium truncate">{track.title}</span>
    <span class="text-gray-500 text-xs font-mono text-right">{formatDuration(track.duration)}</span>

    <div class="flex justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
            class="p-1.5 rounded-full hover:bg-blue-500/20 text-blue-400 transition-colors active:scale-95"
            on:click={() => handleAction('play')}
            title="Play"
        >
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
        </button>

        <div class="relative menu-container">
            <button
                class="p-1.5 rounded-full hover:bg-gray-700 text-gray-400 hover:text-white transition-colors active:scale-95"
                on:click|stopPropagation={toggleMenu}
                title="Options"
            >
                <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12 8c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z"/></svg>
            </button>

            {#if showMenu}
                <div class="absolute right-0 top-full mt-1 w-48 bg-gray-800 border border-gray-700 rounded-lg shadow-xl z-50 overflow-hidden text-sm">
                    <button class="w-full text-left px-4 py-2 hover:bg-gray-700 text-white flex items-center gap-2 active:scale-95 transition-all duration-200" on:click={() => handleAction('metadata')}>
                        <span>🔍</span> Fetch Metadata
                    </button>
                    <button class="w-full text-left px-4 py-2 hover:bg-gray-700 text-blue-300 flex items-center gap-2 active:scale-95 transition-all duration-200" on:click={() => handleAction('upgrade')}>
                        <span>⬆️</span> Force Upgrade
                    </button>
                    <div class="border-t border-gray-700 my-1"></div>
                    <button class="w-full text-left px-4 py-2 hover:bg-red-900/50 text-red-400 flex items-center gap-2 active:scale-95 transition-all duration-200" on:click={() => handleAction('delete')}>
                        <span>🗑</span> Delete
                    </button>
                    <button class="w-full text-left px-4 py-2 hover:bg-red-900/50 text-red-500 flex items-center gap-2 active:scale-95 transition-all duration-200" on:click={() => handleAction('force_delete')}>
                        <span>⚠️</span> Force System Delete
                    </button>
                </div>
            {/if}
        </div>
    </div>
</div>
