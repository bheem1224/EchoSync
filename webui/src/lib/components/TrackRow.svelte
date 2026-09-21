<script>
  let {
    track,
    artist = null,
    album = null,
    onPlay = null,
    onplay = null,
    onDelete = null,
    onDeleteEdition = null,
    onFetchMetadata = null,
    openMetadataEditor = null,
    onedit = null,
    onForceUpgrade = null,
    onForceDelete = null,
  } = $props();

  function formatDuration(ms) {
    if (!ms) return "-:--";
    const seconds = Math.floor(ms / 1000);
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  }

  let showMenu = $state(false);
  let menuPos = $state(null); // null for popover attached to button, or { x, y } for contextmenu
  let activeMenuMedia = $state(null);
  let isDrawerOpen = $state(false);

  const sortedMedia = $derived(
    [...(track?.local_media || track?.media || track?.media_files || [])].sort(
      (a, b) => {
        if ((b.bitrate || 0) !== (a.bitrate || 0)) {
          return (b.bitrate || 0) - (a.bitrate || 0);
        }
        if ((b.sample_rate || 0) !== (a.sample_rate || 0)) {
          return (b.sample_rate || 0) - (a.sample_rate || 0);
        }
        return (b.bit_depth || 0) - (a.bit_depth || 0);
      },
    ),
  );

  function toggleMenu(e) {
    if (e) e.stopPropagation();
    activeMenuMedia = null;
    menuPos = null;
    showMenu = !showMenu;
  }

  function closeMenu() {
    showMenu = false;
    menuPos = null;
    activeMenuMedia = null;
  }

  function handleContextMenu(event, media = null) {
    event.preventDefault();
    event.stopPropagation();
    activeMenuMedia = media;
    menuPos = { x: event.clientX, y: event.clientY };
    showMenu = true;
  }

  function handleAction(action) {
    closeMenu();
    if (action === "play") {
      if (onplay) {
        onplay(track.sync_id || track.id);
      } else if (onPlay) {
        onPlay(track, artist, album);
      }
    }
    if (action === "delete" && onDelete) onDelete(track.id, album);
    if (action === "metadata" || action === "edit_metadata") {
      const trackRef = track.sync_id || track.id;
      if (onedit) {
        onedit(trackRef);
      } else if (openMetadataEditor) {
        openMetadataEditor(trackRef);
      } else if (onFetchMetadata) {
        onFetchMetadata(trackRef);
      }
    }
    if (action === "upgrade" && onForceUpgrade) onForceUpgrade(track.id);
    if (action === "force_delete" && onForceDelete) onForceDelete(track.id);
  }

  function handlePlayEdition(mediaId) {
    if (!mediaId || typeof mediaId !== "string") {
      console.error(
        "Cannot play edition: missing canonical media_id NanoID",
        mediaId,
      );
      return;
    }
    const trackRef = track.sync_id || track.id;
    if (onplay) {
      onplay(trackRef, mediaId);
    } else if (onPlay) {
      onPlay(track, artist, album, mediaId);
    }
  }

  function handleEditEdition(mediaId) {
    if (!mediaId || typeof mediaId !== "string") {
      console.error(
        "Cannot edit edition: missing canonical media_id NanoID",
        mediaId,
      );
      return;
    }
    const trackRef = track.sync_id || track.id;
    if (onedit) {
      onedit(trackRef, mediaId);
    } else if (openMetadataEditor) {
      openMetadataEditor(trackRef, mediaId);
    } else if (onFetchMetadata) {
      onFetchMetadata(trackRef, mediaId);
    }
  }

  function handleDeleteEdition(mediaId) {
    if (!mediaId || typeof mediaId !== "string") {
      console.error(
        "Cannot delete edition: missing canonical media_id NanoID",
        mediaId,
      );
      return;
    }
    if (onDeleteEdition) {
      onDeleteEdition(mediaId, track);
      return;
    }
    if (
      confirm(
        "Delete this file edition from disk? This action cannot be undone.",
      )
    ) {
      fetch(`/api/v1/core/library/media/${mediaId}`, { method: "DELETE" })
        .then((res) => {
          if (res.ok) {
            window.dispatchEvent(
              new CustomEvent("echosync:media-deleted", {
                detail: { mediaId, trackId: track?.id },
              }),
            );
          }
        })
        .catch((err) => console.error("Error deleting media edition:", err));
    }
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
  onclick={handleClickOutside}
  oncontextmenu={handleClickOutside}
/>

<div
  class="track-row group hover:bg-white/5 rounded-md px-3 py-2 grid grid-cols-[40px_2fr_1fr_1fr_auto_60px_auto] items-center gap-2 transition-colors relative cursor-pointer"
  oncontextmenu={handleContextMenu}
  onclick={() => handleAction("play")}
  onkeydown={(e) => e.key === "Enter" && handleAction("play")}
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
    onclick={(e) => e.stopPropagation()}
  >
    {track.artist_name || artist?.name || "Artist"}
  </a>

  <a
    href="/library/albums/{track.album_id}"
    class="text-gray-400 text-xs hover:text-blue-400 hover:underline truncate"
    onclick={(e) => e.stopPropagation()}
  >
    {track.album_title || album?.title || "Album"}
  </a>

  <!-- Audio Quality Badges -->
  <div
    class="flex items-center gap-1.5 justify-end opacity-60 group-hover:opacity-100 transition-opacity"
  >
    {#if sortedMedia.length > 0}
      {@const m = sortedMedia[0]}
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

      {#if sortedMedia.length > 1}
        <button
          type="button"
          class="px-2 py-0.5 text-xs font-mono rounded bg-slate-800 hover:bg-slate-700 text-cyan-400 border border-slate-700 flex items-center gap-1 transition-colors"
          onclick={(e) => {
            e.stopPropagation();
            isDrawerOpen = !isDrawerOpen;
          }}
          title="Click to view all {sortedMedia.length} audio editions"
        >
          <span>{m.file_format ? m.file_format.toUpperCase() : "AUDIO"}</span>
          <span class="text-[10px] text-cyan-300 font-bold"
            >+{sortedMedia.length - 1}</span
          >
          <span class="text-[9px] text-slate-400"
            >{isDrawerOpen ? "▲" : "▼"}</span
          >
        </button>
      {:else if m.file_format}
        <span
          class="px-2 py-0.5 text-xs font-mono rounded bg-slate-900 text-slate-400 border border-slate-800"
        >
          {m.file_format.toUpperCase()}
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
      onclick={(e) => {
        e.stopPropagation();
        handleAction("play");
      }}
      title="Play"
    >
      <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"
        ><path d="M8 5v14l11-7z" /></svg
      >
    </button>

    <div class="relative menu-container z-50">
      <button
        class="p-1.5 rounded-full hover:bg-gray-700 text-gray-400 hover:text-white transition-colors active:scale-95"
        onclick={(e) => {
          e.stopPropagation();
          toggleMenu();
        }}
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
            onclick={() => handleAction("play")}
          >
            <span>▶️</span> Play
          </button>
          <button
            class="w-full text-left px-4 py-2 hover:bg-gray-700 text-white flex items-center gap-2 active:scale-95 transition-all duration-200"
            onclick={() => handleAction("metadata")}
          >
            <span>✏️</span> Edit Metadata
          </button>
          <button
            class="w-full text-left px-4 py-2 hover:bg-gray-700 text-blue-300 flex items-center gap-2 active:scale-95 transition-all duration-200"
            onclick={() => handleAction("upgrade")}
          >
            <span>⬆️</span> Force Upgrade
          </button>
          <div class="border-t border-gray-700 my-1"></div>
          <button
            class="w-full text-left px-4 py-2 hover:bg-red-900/50 text-red-400 flex items-center gap-2 active:scale-95 transition-all duration-200"
            onclick={() => handleAction("delete")}
          >
            <span>🗑️</span> Delete
            <span>🗑️</span>
            {sortedMedia.length > 1 ? "Delete Track (All Editions)" : "Delete"}
          </button>
          <button
            class="w-full text-left px-4 py-2 hover:bg-red-900/50 text-red-500 flex items-center gap-2 active:scale-95 transition-all duration-200"
            onclick={() => handleAction("force_delete")}
          >
            <span>⚠️</span> Force System Delete
          </button>
        </div>
      {/if}
    </div>
  </div>

  {#if isDrawerOpen && sortedMedia.length > 1}
    <div
      class="col-span-full bg-slate-950/80 border-t border-b border-slate-800/60 p-3 pl-12 flex flex-col gap-2 mt-2 -mx-3 -mb-2 cursor-default"
      onclick={(e) => e.stopPropagation()}
      role="region"
      aria-label="Available File Editions"
    >
      <div
        class="text-[11px] font-semibold uppercase tracking-wider text-slate-400"
      >
        Available File Editions ({sortedMedia.length})
      </div>
      {#each sortedMedia as media, idx}
        <div
          class="flex items-center justify-between py-1.5 px-3 rounded-lg bg-slate-900/60 border border-slate-800/40 hover:border-slate-700/60 transition-colors"
          oncontextmenu={(e) => handleContextMenu(e, media)}
        >
          <div class="flex items-center gap-3">
            <span class="text-xs font-bold font-mono text-cyan-400"
              >{media.file_format ? media.file_format.toUpperCase() : ""}</span
            >
            <span class="text-xs text-slate-300 font-mono">
              {media.bitrate ? `${media.bitrate} kbps` : "VBR"} · {media.sample_rate
                ? `${media.sample_rate / 1000} kHz`
                : ""} · {media.bit_depth ? `${media.bit_depth}-bit` : ""}
            </span>
            <span
              class="text-[11px] text-slate-500 truncate max-w-md"
              title={media.file_path}
            >
              {media.file_path ? media.file_path.split(/[\\/]/).pop() : ""}
            </span>
            {#if idx === 0}
              <span
                class="px-1.5 py-0.2 text-[9px] font-semibold bg-emerald-950/80 text-emerald-400 border border-emerald-800/50 rounded"
                >DEFAULT</span
              >
            {/if}
          </div>
          <div class="flex items-center gap-2">
            <button
              type="button"
              class="px-2.5 py-1 text-xs font-medium rounded bg-cyan-600 hover:bg-cyan-500 text-white transition-colors flex items-center gap-1"
              onclick={(e) => {
                e.stopPropagation();
                handlePlayEdition(media.media_id || media.id);
                if (!media?.media_id) {
                  console.error(
                    "Cannot play edition: missing canonical media_id NanoID",
                    media,
                  );
                  return;
                }
                handlePlayEdition(media.media_id);
              }}
            >
              ▶ Play
            </button>
            <button
              type="button"
              class="px-2.5 py-1 text-xs font-medium rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors flex items-center gap-1"
              onclick={(e) => {
                e.stopPropagation();
                handleEditEdition(media.media_id || media.id);
                if (!media?.media_id) {
                  console.error(
                    "Cannot edit edition: missing canonical media_id NanoID",
                    media,
                  );
                  return;
                }
                handleEditEdition(media.media_id);
              }}
            >
              ✏ Edit
            </button>
            <button
              type="button"
              class="px-2.5 py-1 text-xs font-medium rounded bg-red-950/60 hover:bg-red-900/80 text-red-300 border border-red-800/50 transition-colors flex items-center gap-1"
              onclick={(e) => {
                e.stopPropagation();
                if (!media?.media_id) {
                  console.error(
                    "Cannot delete edition: missing canonical media_id NanoID",
                    media,
                  );
                  return;
                }
                handleDeleteEdition(media.media_id);
              }}
              title="Delete this file edition from disk"
            >
              🗑 Delete
            </button>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

{#if showMenu && menuPos}
  <div
    class="context-menu fixed bg-gray-800 border border-gray-700 rounded-lg shadow-2xl z-[9999] overflow-hidden text-sm w-56 py-1"
    style="left: {menuPos.x}px; top: {menuPos.y}px;"
  >
    {#if activeMenuMedia}
      <button
        class="w-full text-left px-4 py-2 hover:bg-gray-700 text-blue-400 flex items-center gap-2 active:scale-95 transition-all duration-200"
        onclick={() => {
          const mId = activeMenuMedia.media_id;
          closeMenu();
          if (!mId) {
            console.error(
              "Cannot play edition: missing canonical media_id NanoID",
              activeMenuMedia,
            );
            return;
          }
          handlePlayEdition(mId);
        }}
      >
        <span>▶️</span> Play This Edition
      </button>
      <button
        class="w-full text-left px-4 py-2 hover:bg-gray-700 text-white flex items-center gap-2 active:scale-95 transition-all duration-200"
        onclick={() => {
          const mId = activeMenuMedia.media_id;
          closeMenu();
          if (!mId) {
            console.error(
              "Cannot edit edition: missing canonical media_id NanoID",
              activeMenuMedia,
            );
            return;
          }
          handleEditEdition(mId);
        }}
      >
        <span>✏️</span> Edit Edition Metadata
      </button>
      <div class="border-t border-gray-700 my-1"></div>
      <button
        class="w-full text-left px-4 py-2 hover:bg-red-900/50 text-red-400 flex items-center gap-2 active:scale-95 transition-all duration-200"
        onclick={() => {
          const mId = activeMenuMedia.media_id;
          closeMenu();
          if (!mId) {
            console.error(
              "Cannot delete edition: missing canonical media_id NanoID",
              activeMenuMedia,
            );
            return;
          }
          handleDeleteEdition(mId);
        }}
      >
        <span>🗑️</span> Delete File Edition
      </button>
      <button
        class="w-full text-left px-4 py-2 hover:bg-red-900/50 text-red-500 flex items-center gap-2 active:scale-95 transition-all duration-200"
        onclick={() => handleAction("delete")}
      >
        <span>⚠️</span> Delete Track (All Editions)
      </button>
    {:else}
      <button
        class="w-full text-left px-4 py-2 hover:bg-gray-700 text-blue-400 flex items-center gap-2 active:scale-95 transition-all duration-200"
        onclick={() => handleAction("play")}
      >
        <span>▶️</span> Play
      </button>
      <button
        class="w-full text-left px-4 py-2 hover:bg-gray-700 text-white flex items-center gap-2 active:scale-95 transition-all duration-200"
        onclick={() => handleAction("metadata")}
      >
        <span>✏️</span> Edit Metadata
      </button>
      <button
        class="w-full text-left px-4 py-2 hover:bg-gray-700 text-blue-300 flex items-center gap-2 active:scale-95 transition-all duration-200"
        onclick={() => handleAction("upgrade")}
      >
        <span>⬆️</span> Force Upgrade
      </button>
      <div class="border-t border-gray-700 my-1"></div>
      <button
        class="w-full text-left px-4 py-2 hover:bg-red-900/50 text-red-400 flex items-center gap-2 active:scale-95 transition-all duration-200"
        onclick={() => handleAction("delete")}
      >
        <span>🗑️</span>
        {sortedMedia.length > 1 ? "Delete Track (All Editions)" : "Delete"}
      </button>
      <button
        class="w-full text-left px-4 py-2 hover:bg-red-900/50 text-red-500 flex items-center gap-2 active:scale-95 transition-all duration-200"
        onclick={() => handleAction("force_delete")}
      >
        <span>⚠️</span> Force System Delete
      </button>
    {/if}
  </div>
{/if}
