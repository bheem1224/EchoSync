<script>
  export let track;
  export let artist = null;
  export let album = null;
  export let onPlay = null;
  export let onDelete = null;
  export let onFetchMetadata = null;
  export let openMetadataEditor = null;
  export let onForceUpgrade = null;
  export let onForceDelete = null;

  function formatDuration(ms) {
    if (!ms) return "-:--";
    const seconds = Math.floor(ms / 1000);
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  }

  let showMenu = false;
  let menuPos = null; // null for popover attached to button, or { x, y } for contextmenu

  function toggleMenu(e) {
    if (e) e.stopPropagation();
    menuPos = null;
    showMenu = !showMenu;
  }

  function closeMenu() {
    showMenu = false;
    menuPos = null;
  }

  function handleContextMenu(event) {
    event.preventDefault();
    event.stopPropagation();
    menuPos = { x: event.clientX, y: event.clientY };
    showMenu = true;
  }

  function handleAction(action) {
    closeMenu();
    if (action === "play" && onPlay) onPlay(track, artist, album);
    if (action === "delete" && onDelete) onDelete(track.id, album);
    if (action === "metadata" || action === "edit_metadata") {
      const trackRef = track.sync_id || track.id;
      if (openMetadataEditor) {
        openMetadataEditor(trackRef);
      } else if (onFetchMetadata) {
        onFetchMetadata(trackRef);
      }
    }
    if (action === "upgrade" && onForceUpgrade) onForceUpgrade(track.id);
    if (action === "force_delete" && onForceDelete) onForceDelete(track.id);
  }

  // Simple click outside handler
  function handleClickOutside(event) {
    if (
      showMenu &&
      !event.target.closest(".menu-container") &&
      !event.target.closest(".context-menu")
    ) {
      closeMenu();
    }
  }
</script>

<svelte:window
  on:click={handleClickOutside}
  on:contextmenu={handleClickOutside}
/>

<div
  class="track-row group hover:bg-white/5 rounded-md px-3 py-2 grid grid-cols-[40px_2fr_1fr_1fr_auto_60px_auto] items-center gap-2 transition-colors relative cursor-pointer"
  on:contextmenu={handleContextMenu}
  role="row"
  tabindex="0"
>
  <span class="text-gray-500 text-xs font-mono"
    >{track.track_number || "-"}</span
  >
  <span class="text-white text-sm font-medium truncate">{track.title}</span>

  <a
    href="/library/artists/{track.artist_id}"
    class="text-gray-400 text-xs hover:text-blue-400 hover:underline truncate"
    on:click|stopPropagation
  >
    {track.artist_name || artist?.name || "Artist"}
  </a>

  <a
    href="/library/albums/{track.album_id}"
    class="text-gray-400 text-xs hover:text-blue-400 hover:underline truncate"
    on:click|stopPropagation
  >
    {track.album_title || album?.title || "Album"}
  </a>

  <!-- Audio Quality Badges -->
  <div
    class="flex items-center gap-1.5 justify-end opacity-60 group-hover:opacity-100 transition-opacity"
  >
    {#if track.media && track.media.length > 0}
      {@const m = track.media[0]}
      {#if m.channels}
        <span
          class="px-1.5 py-0.5 rounded bg-blue-900/40 text-blue-300 text-[10px] font-semibold tracking-wider whitespace-nowrap"
        >
          {m.channels === 2
            ? "Stereo"
            : m.channels === 6
              ? "5.1"
              : m.channels + " Ch"}
        </span>
      {/if}
      {#if m.file_format}
        <span
          class="px-1.5 py-0.5 rounded bg-gray-800 text-gray-300 border border-gray-700 text-[10px] font-medium tracking-wider whitespace-nowrap"
        >
          {m.file_format}
        </span>
      {/if}
      {#if m.bit_depth}
        <span
          class="px-1.5 py-0.5 rounded bg-gray-800 text-gray-300 border border-gray-700 text-[10px] font-medium tracking-wider whitespace-nowrap"
        >
          {m.bit_depth}-bit
        </span>
      {/if}
      {#if m.sample_rate}
        <span
          class="px-1.5 py-0.5 rounded bg-gray-800 text-gray-300 border border-gray-700 text-[10px] font-medium tracking-wider whitespace-nowrap"
        >
          {m.sample_rate / 1000}kHz
        </span>
      {/if}
      {#if m.bitrate}
        <span
          class="px-1.5 py-0.5 rounded bg-gray-800 text-gray-300 border border-gray-700 text-[10px] font-medium tracking-wider whitespace-nowrap"
        >
          {m.bitrate} kbps
        </span>
      {/if}
    {:else if track.media_ids && track.media_ids.length > 0}
      <span class="w-10 h-4 rounded bg-gray-800 animate-pulse"></span>
      <span class="w-12 h-4 rounded bg-gray-800 animate-pulse"></span>
      <span class="w-8 h-4 rounded bg-gray-800 animate-pulse"></span>
    {/if}
  </div>

  <span class="text-gray-500 text-xs font-mono text-right"
    >{formatDuration(track.duration)}</span
  >

  <div
    class="flex justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity"
  >
    <button
      class="p-1.5 rounded-full hover:bg-blue-500/20 text-blue-400 transition-colors active:scale-95"
      on:click|stopPropagation={() => handleAction("play")}
      title="Play"
    >
      <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"
        ><path d="M8 5v14l11-7z" /></svg
      >
    </button>

    <div class="relative menu-container z-50">
      <button
        class="p-1.5 rounded-full hover:bg-gray-700 text-gray-400 hover:text-white transition-colors active:scale-95"
        on:click|stopPropagation={toggleMenu}
        title="Options"
      >
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"
          ><path
            d="M12 8c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z"
          /></svg
        >
      </button>

      {#if showMenu && !menuPos}
        <div
          class="absolute right-0 top-full mt-1 w-48 bg-gray-800 border border-gray-700 rounded-lg shadow-2xl z-50 overflow-hidden text-sm py-1"
        >
          <button
            class="w-full text-left px-4 py-2 hover:bg-gray-700 text-blue-400 flex items-center gap-2 active:scale-95 transition-all duration-200"
            on:click={() => handleAction("play")}
          >
            <span>▶️</span> Play
          </button>
          <button
            class="w-full text-left px-4 py-2 hover:bg-gray-700 text-white flex items-center gap-2 active:scale-95 transition-all duration-200"
            on:click={() => handleAction("metadata")}
          >
            <span>✏️</span> Edit Metadata
          </button>
          <button
            class="w-full text-left px-4 py-2 hover:bg-gray-700 text-blue-300 flex items-center gap-2 active:scale-95 transition-all duration-200"
            on:click={() => handleAction("upgrade")}
          >
            <span>⬆️</span> Force Upgrade
          </button>
          <div class="border-t border-gray-700 my-1"></div>
          <button
            class="w-full text-left px-4 py-2 hover:bg-red-900/50 text-red-400 flex items-center gap-2 active:scale-95 transition-all duration-200"
            on:click={() => handleAction("delete")}
          >
            <span>🗑️</span> Delete
          </button>
          <button
            class="w-full text-left px-4 py-2 hover:bg-red-900/50 text-red-500 flex items-center gap-2 active:scale-95 transition-all duration-200"
            on:click={() => handleAction("force_delete")}
          >
            <span>⚠️</span> Force System Delete
          </button>
        </div>
      {/if}
    </div>
  </div>
</div>

{#if showMenu && menuPos}
  <div
    class="context-menu fixed bg-gray-800 border border-gray-700 rounded-lg shadow-2xl z-[9999] overflow-hidden text-sm w-48 py-1"
    style="left: {menuPos.x}px; top: {menuPos.y}px;"
  >
    <button
      class="w-full text-left px-4 py-2 hover:bg-gray-700 text-blue-400 flex items-center gap-2 active:scale-95 transition-all duration-200"
      on:click={() => handleAction("play")}
    >
      <span>▶️</span> Play
    </button>
    <button
      class="w-full text-left px-4 py-2 hover:bg-gray-700 text-white flex items-center gap-2 active:scale-95 transition-all duration-200"
      on:click={() => handleAction("metadata")}
    >
      <span>✏️</span> Edit Metadata
    </button>
    <button
      class="w-full text-left px-4 py-2 hover:bg-gray-700 text-blue-300 flex items-center gap-2 active:scale-95 transition-all duration-200"
      on:click={() => handleAction("upgrade")}
    >
      <span>⬆️</span> Force Upgrade
    </button>
    <div class="border-t border-gray-700 my-1"></div>
    <button
      class="w-full text-left px-4 py-2 hover:bg-red-900/50 text-red-400 flex items-center gap-2 active:scale-95 transition-all duration-200"
      on:click={() => handleAction("delete")}
    >
      <span>🗑️</span> Delete
    </button>
    <button
      class="w-full text-left px-4 py-2 hover:bg-red-900/50 text-red-500 flex items-center gap-2 active:scale-95 transition-all duration-200"
      on:click={() => handleAction("force_delete")}
    >
      <span>⚠️</span> Force System Delete
    </button>
  </div>
{/if}
