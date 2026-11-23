<script>
  import { onMount, onDestroy } from "svelte";
  import { plugins } from "../../stores/plugins";
  import { jobs } from "../../stores/jobs";
  import { preferences } from "../../stores/preferences";
  import apiClient from "../../api/client";
  import PlaylistMatchDiagnosticDrawer from "$lib/components/PlaylistMatchDiagnosticDrawer.svelte";
  import Select from "$lib/components/Select.svelte";

  let sourceProvider = "";
  let targetProvider = "";
  let playlists = [];
  let selectedPlaylists = [];
  let loadingPlaylists = false;
  let syncing = false;
  let error = "";
  let success = "";

  // Analysis modal state
  let analysisModalOpen = false;
  let analysisLoading = false;
  let analysisError = "";
  let analysisResult = null;
  let analysisStarted = false;
  let downloadingMissing = false;
  let selectedQuality = "";
  let availableTargetAccounts = [];
  let myTargetProfiles = [];
  let familyTargetProfiles = [];
  let overrideTargetUserId = null;
  let targetProfileMenuOpen = false;

  $: selectedTargetProfileLabel = (() => {
    const all = [...myTargetProfiles, ...familyTargetProfiles, ...availableTargetAccounts];
    const match = all.find(
      (a) => String(a.external_account_id || a.user_id || a.id) === String(overrideTargetUserId)
    );
    if (!match) return '-- Select Target Profile --';
    return match.display_name || match.account_name || match.username || match.name || String(overrideTargetUserId);
  })();

  // Sync config modal state
  let syncConfigModalOpen = false;
  let syncInProgress = false;
  let syncDownloadMissing = false;

  // Sync progress state (integrated into analysis modal)
  let syncEventStream = [];
  let syncProgressEvent = null;
  let syncEventPollingId = null;

  // Matching diagnostics drawer state
  let selectedTrackForDiagnostics = null;
  let isDiagnosticsDrawerOpen = false;
  let analysisFilter = "all"; // 'all' | 'found' | 'missing'
  let analysisSearchQuery = "";

  function isTrackFound(track) {
    if (!track) return false;
    if (track.status === "found") return true;
    const lm = (track.library_match || "").toLowerCase();
    return Boolean(lm) && !lm.includes("not found") && !lm.includes("missing") && !lm.includes("checking");
  }

  $: analysisAllTracks = analysisResult?.tracks || [];
  $: analysisFoundCount =
    analysisResult?.summary?.found_in_library ??
    analysisAllTracks.filter((t) => isTrackFound(t)).length;
  $: analysisMissingCount =
    analysisResult?.summary?.missing_tracks ??
    analysisAllTracks.filter((t) => !isTrackFound(t)).length;
  $: filteredAnalysisTracks = analysisAllTracks
    .map((track, originalIndex) => ({ track, originalIndex }))
    .filter(({ track }) => {
      if (analysisFilter === "found" && !isTrackFound(track)) return false;
      if (analysisFilter === "missing" && isTrackFound(track)) return false;
      const q = analysisSearchQuery.trim().toLowerCase();
      if (q) {
        const title = (track.title || "").toLowerCase();
        const artist = (track.artist || "").toLowerCase();
        const album = (track.album || "").toLowerCase();
        if (!title.includes(q) && !artist.includes(q) && !album.includes(q)) return false;
      }
      return true;
    });

  // Scheduled syncs state
  let scheduledSyncs = [];
  let showScheduleModal = false;
  let scheduleForm = {
    source: "",
    target: "",
    playlists: [],
    interval: 3600,
    download_missing: false,
  };
  let scheduleIntervalOptions = [
    { value: 300, label: "5 minutes" },
    { value: 900, label: "15 minutes" },
    { value: 1800, label: "30 minutes" },
    { value: 3600, label: "1 hour" },
    { value: 21600, label: "6 hours" },
    { value: 43200, label: "12 hours" },
    { value: 86400, label: "24 hours" },
    { value: 604800, label: "1 week" },
  ];

  function getPluginName(pluginId) {
    if (!pluginId) return "";
    const idStr = String(pluginId).toLowerCase();
    const item = Object.values($plugins?.items || {}).find(
      (p) =>
        String(p.plugin_id || "").toLowerCase() === idStr ||
        String(p.id || "").toLowerCase() === idStr ||
        String(p.name || "").toLowerCase() === idStr,
    );
    if (item?.name) return item.name;
    if (item?.title) return item.title;

    const knownNames = {
      "2391116200": "Spotify",
      spotify: "Spotify",
      "3021005569": "Plex",
      plex: "Plex",
      "3782485548": "Tidal",
      tidal: "Tidal",
      "3934388657": "MusicBrainz",
      musicbrainz: "MusicBrainz",
      "1910609384": "AcoustID",
      acoustid: "AcoustID",
      "2305548545": "Jellyfin",
      jellyfin: "Jellyfin",
      "4010168341": "Navidrome",
      navidrome: "Navidrome",
      "2021666874": "Slskd",
      slskd: "Slskd",
      local: "Local Library",
      local_server: "Local Server",
    };
    if (knownNames[idStr]) return knownNames[idStr];

    return String(pluginId);
  }

  async function fetchTargetAccounts() {
    availableTargetAccounts = [];
    myTargetProfiles = [];
    familyTargetProfiles = [];
    if (!targetProvider) return;
    try {
      // 1. Unified family-friendly target profiles endpoint (defaults to caller's own profile)
      try {
        const profRes = await apiClient.get("/core/playlists/target-profiles", {
          params: { provider: targetProvider },
        });
        const myProfs = profRes.data?.my_profiles || [];
        const famProfs = profRes.data?.family_profiles || [];
        if (myProfs.length > 0 || famProfs.length > 0) {
          myTargetProfiles = myProfs;
          familyTargetProfiles = famProfs;
          availableTargetAccounts = [...myProfs, ...famProfs];
          if (!overrideTargetUserId && profRes.data?.default_target_user_id) {
            overrideTargetUserId = profRes.data.default_target_user_id;
          }
          return;
        }
      } catch (e) {
        // Fallback to plugin/system accounts
      }

      try {
        const res = await apiClient.get(
          `/system/plugins/${targetProvider}/accounts`,
        );
        if (
          res.data?.items &&
          Array.isArray(res.data.items) &&
          res.data.items.length > 0
        ) {
          availableTargetAccounts = res.data.items;
          return;
        } else if (Array.isArray(res.data) && res.data.length > 0) {
          availableTargetAccounts = res.data;
          return;
        }
      } catch (e) {
        // Fallback to /system/accounts
      }

      const res = await apiClient.get("/system/accounts");
      if (res.data?.media_users && res.data.media_users.length > 0) {
        availableTargetAccounts = res.data.media_users;
      } else if (res.data?.music_accounts) {
        const filtered = res.data.music_accounts.filter(
          (a) =>
            String(a.service).toLowerCase() ===
            String(targetProvider).toLowerCase(),
        );
        if (filtered.length > 0) {
          availableTargetAccounts = filtered;
        }
      }
    } catch (err) {
      console.warn("[Sync] Failed to fetch target accounts:", err);
    }
  }

  $: qualityProfiles = $preferences.profiles || [];
  $: if (qualityProfiles.length > 0 && !selectedQuality) {
    selectedQuality = qualityProfiles[0]?.name || "";
  }

  $: playlistPlugins = Object.values($plugins.items).filter(
    (p) => (p.capabilities?.supports_playlists ?? "NONE") !== "NONE",
  );

  $: syncTargets = Object.values($plugins.items).filter(
    (p) =>
      // Streaming services (Spotify, Tidal) OR Media servers (Plex, Jellyfin, Navidrome)
      p.capabilities?.supports_playlists === "READ_WRITE" ||
      (p.capabilities?.supports_library_scan ?? false),
  );

  function getPlaylistTargetContext(playlist) {
    if (!playlist) return "";

    return (
      playlist.target_account_name ||
      playlist.target_user_name ||
      playlist.target_profile_name ||
      playlist.target_display_name ||
      (playlist.target_user_id ? playlist.source_account_name : "") ||
      ""
    );
  }

  function formatTargetWithContext(targetLabel, playlistItems = []) {
    if (!targetLabel) return "";

    const contexts = [
      ...new Set(
        (playlistItems || []).map(getPlaylistTargetContext).filter(Boolean),
      ),
    ];

    if (contexts.length === 0) {
      return targetLabel;
    }

    return `${targetLabel} (${contexts.join(", ")})`;
  }

  $: selectedPlaylistItems = playlists.filter((_, index) =>
    selectedPlaylists.includes(index),
  );
  $: selectedTargetLabel = formatTargetWithContext(
    targetProvider,
    selectedPlaylistItems,
  );

  async function loadPlaylists() {
    if (!sourceProvider) {
      console.log("[Sync] No source plugin selected");
      return;
    }

    loadingPlaylists = true;
    error = "";
    playlists = [];
    selectedPlaylists = []; // Clear selections when loading new playlists

    try {
      console.log(`[Sync] Loading playlists for plugin: ${sourceProvider}`);
      const response = await apiClient.get(
        `/system/plugins/${sourceProvider}/playlists`,
      );
      console.log("[Sync] Full response object:", response);
      console.log("[Sync] Response data:", response.data);
      console.log("[Sync] Response data type:", typeof response.data);
      console.log("[Sync] Response data.items:", response.data.items);

      playlists = response.data.items || [];
      console.log("[Sync] Playlists after assignment:", playlists);
      console.log("[Sync] Number of playlists:", playlists.length);
    } catch (err) {
      console.error("[Sync] Error loading playlists:", err);
      error = `Failed to load playlists: ${err.response?.data?.error || err.message}`;
    } finally {
      loadingPlaylists = false;
    }
  }

  async function runAnalysis() {
    if (!sourceProvider || !targetProvider || selectedPlaylists.length === 0) {
      if (!sourceProvider) {
        analysisError = "Please select a source service.";
      } else if (!targetProvider) {
        analysisError = "Please select a target service.";
      } else {
        analysisError = "Please select at least one playlist to analyze.";
      }
      return;
    }
    analysisLoading = true;
    analysisError = "";
    analysisResult = null;
    analysisStarted = true;

    try {
      const selectedDetails = playlists
        .map((p, index) => ({ ...p, index }))
        .filter((p) => selectedPlaylists.includes(p.index))
        .map((p) => {
          const detail = { id: p.id, name: p.name, track_count: p.track_count };
          if (p.account_id !== undefined) {
            detail.account_id = p.account_id;
          }
          if (p.source_account_name !== undefined) {
            detail.source_account_name = p.source_account_name;
          }
          if (p.target_user_id !== undefined) {
            detail.target_user_id = p.target_user_id;
          }
          return detail;
        });

      // Start analysis as a background job
      const startResp = await apiClient.post("/core/playlists/analyze/start", {
        source: sourceProvider,
        target: targetProvider,
        quality_profile: selectedQuality,
        playlists: selectedDetails,
      });

      if (!startResp.data || !startResp.data.job_id) {
        throw new Error("Failed to start analysis job");
      }

      const jobId = startResp.data.job_id;
      analysisResult = null;

      // Poll the job status until finished/failed
      const pollInterval = 3000;
      analysisLoading = true;

      async function pollOnce() {
        try {
          const statusResp = await apiClient.get(
            `/core/playlists/analyze/${jobId}`,
          );
          const d = statusResp.data;
          if (!d) return false;
          if (d.status === "finished") {
            analysisResult = d.result || null;
            if (analysisResult) {
              const autoTargetId =
                analysisResult.target_user_id ||
                analysisResult.summary?.target_user_id;
              if (autoTargetId) {
                overrideTargetUserId = autoTargetId;
              }
            }
            return true;
          }
          if (d.status === "failed") {
            analysisError = d.error || "Analysis job failed";
            return true;
          }
        } catch (e) {
          console.error("Polling error:", e);
        }
        return false;
      }

      // Poll loop
      let finished = false;
      while (!finished) {
        // eslint-disable-next-line no-await-in-loop
        finished = await pollOnce();
        if (!finished) {
          // eslint-disable-next-line no-await-in-loop
          await new Promise((r) => setTimeout(r, pollInterval));
        }
      }
    } catch (err) {
      console.error("[Sync] Analysis error:", err);
      analysisError =
        err.response?.data?.error || err.message || "Analysis failed";
    } finally {
      analysisLoading = false;
    }
  }

  async function downloadMissingTracks() {
    if (!analysisResult || downloadingMissing) return;
    downloadingMissing = true;
    error = "";
    success = "";

    try {
      const response = await apiClient.post(
        "/core/playlists/download-missing",
        {
          missing: analysisResult.missing || [],
        },
      );

      if (response.data.accepted) {
        success = "Download job created. Check Jobs for progress.";
        jobs.load();
      } else {
        error = response.data.error || "Failed to start download job.";
      }
    } catch (err) {
      error = err.response?.data?.error || err.message || "Download failed";
    } finally {
      downloadingMissing = false;
    }
  }

  function openSyncConfigModal() {
    if (
      !analysisResult?.summary?.can_sync &&
      !(analysisResult?.summary?.found_in_library > 0) &&
      !analysisResult?.tracks?.some((t) => t.matched_track_id)
    ) {
      analysisError = "No matched tracks to sync.";
      return;
    }
    syncConfigModalOpen = true;
  }

  function closeSyncConfigModal() {
    syncConfigModalOpen = false;
  }

  async function confirmSync() {
    const validMatches =
      analysisResult?.summary?.matched_pairs?.length > 0
        ? analysisResult.summary.matched_pairs
        : (analysisResult?.tracks || [])
            .filter((t) => t.matched_track_id)
            .map((t) => ({
              track_id: t.matched_track_id,
              matched_track_id: t.matched_track_id,
              target_identifier: t.target_identifier || t.matched_track_id,
              title: t.title,
              artist: t.artist,
              album: t.album,
              duration_ms: t.duration_ms,
              source_title: t.title,
              source_artist: t.artist,
              source_track: t.source_track,
            }));

    if (validMatches.length === 0) {
      analysisError =
        "No tracks from the selected playlist(s) matched your target library. Nothing to sync.";
      return;
    }
    syncInProgress = true;
    analysisError = "";

    try {
      const selectedItems = selectedPlaylists
        .map((i) => playlists[i])
        .filter(Boolean);

      const sourceAccountNames = [
        ...new Set(
          selectedItems.map((p) => p.source_account_name).filter(Boolean),
        ),
      ];
      const targetUserIds = [
        ...new Set(selectedItems.map((p) => p.target_user_id).filter(Boolean)),
      ];

      let sourceAccountName =
        sourceAccountNames.length === 1
          ? sourceAccountNames[0]
          : selectedItems[0]?.source_account_name || undefined;
      let targetUserId =
        targetUserIds.length === 1
          ? targetUserIds[0]
          : selectedItems[0]?.target_user_id || undefined;
      let syncPlaylistName =
        selectedItems.length === 1
          ? selectedItems[0]?.name || "Synced Playlist"
          : selectedItems[0]?.name
            ? `${selectedItems[0].name} (+${selectedItems.length - 1} more)`
            : "Multi-Playlist Sync";

      // Increase timeout proportional to number of selected playlists
      const syncTimeoutMs = Math.max(10000, selectedPlaylists.length * 10000);
      const response = await apiClient.post(
        "/core/playlists/sync",
        {
          source: sourceProvider,
          target_source: targetProvider,
          playlist_name: syncPlaylistName,
          source_account_name: sourceAccountName,
          target_user_id: overrideTargetUserId || targetUserId,
          matches: validMatches,
          download_missing: syncDownloadMissing,
        },
        { timeout: syncTimeoutMs },
      );

      if (response.data.accepted) {
        syncConfigModalOpen = false;
        // Set initial progress state immediately to trigger UI change
        syncProgressEvent = {
          type: "in-progress",
          data: {
            total:
              analysisResult?.summary?.found_in_library || validMatches.length,
            message: "Starting sync...",
          },
        };
        // Keep analysis modal open to show progress
        // Fix the events_path - remove /api/v1 or /api prefix if present since apiClient already has baseURL='/api/v1'
        const rawEventsPath = response.data.events_path || "";
        const eventsPath = rawEventsPath
          .replace(/^\/api\/v1/, "")
          .replace(/^\/api/, "");
        startSyncEventPolling(response.data.job, eventsPath);
      } else {
        analysisError = response.data.error || "Sync failed to start";
      }
    } catch (err) {
      console.error("[Sync] Sync error:", err);
      analysisError = err.response?.data?.error || err.message || "Sync failed";
    } finally {
      syncInProgress = false;
    }
  }

  function startSyncEventPolling(jobName, eventsPath) {
    syncEventStream = [];
    let lastEventId = -1;

    console.log("[Sync Events] Starting polling for job:", jobName);
    console.log("[Sync Events] Events path:", eventsPath);

    const pollEvents = async () => {
      try {
        const separator = eventsPath.includes("?") ? "&" : "?";
        const url = `${eventsPath}${separator}since=${lastEventId}`;
        console.log("[Sync Events] Polling URL:", url);
        const response = await apiClient.get(url);
        const newEvents = response.data.events || [];

        console.log("[Sync Events] Received", newEvents.length, "events");
        if (newEvents.length > 0) {
          console.log(
            "[Sync Events] Latest event:",
            newEvents[newEvents.length - 1],
          );
        }

        syncEventStream = [...syncEventStream, ...newEvents];

        if (newEvents.length > 0) {
          lastEventId = newEvents[newEvents.length - 1].id;
          syncProgressEvent = newEvents[newEvents.length - 1];

          if (
            syncProgressEvent.type === "sync_complete" ||
            syncProgressEvent.type === "sync_error"
          ) {
            console.log("[Sync Events] Sync finished, stopping polling");
            if (syncEventPollingId) {
              clearInterval(syncEventPollingId);
              syncEventPollingId = null;
            }
            setTimeout(() => {
              jobs.load();
              // Auto-download if checkbox was checked and sync was successful
              if (
                syncProgressEvent.type === "sync_complete" &&
                syncDownloadMissing
              ) {
                downloadMissingTracks();
              }
              if (syncProgressEvent.type === "sync_complete") {
                success = "Sync completed!";
              } else {
                analysisError = syncProgressEvent.data?.error || "Sync failed";
              }
            }, 500);
          }
        }
      } catch (err) {
        console.error("[Sync Events] Polling error:", err);
        // Stop polling on error
        if (syncEventPollingId) {
          clearInterval(syncEventPollingId);
          syncEventPollingId = null;
        }
      }
    };

    pollEvents();
    syncEventPollingId = setInterval(pollEvents, 500);
  }

  function closeSyncProgressModal() {
    if (syncEventPollingId) {
      clearInterval(syncEventPollingId);
      syncEventPollingId = null;
    }
    syncEventStream = [];
    syncProgressEvent = null;
  }

  async function loadScheduledSyncs() {
    try {
      const response = await apiClient.get("/core/playlists/sync/scheduled");
      scheduledSyncs = response.data.scheduled_syncs || [];
    } catch (err) {
      console.error("Failed to load scheduled syncs:", err);
    }
  }

  function openScheduleModal() {
    // Convert indices back to playlist details
    const playlistDetails = playlists
      .map((p, index) => ({ ...p, index }))
      .filter((p) => selectedPlaylists.includes(p.index))
      .map((p) => ({
        id: p.id,
        name: p.name,
        track_count: p.track_count,
        ...(p.source_account_name !== undefined && {
          source_account_name: p.source_account_name,
        }),
        ...(p.account_id !== undefined && { account_id: p.account_id }),
        ...(p.target_user_id !== undefined && {
          target_user_id: p.target_user_id,
        }),
      }));

    scheduleForm = {
      source: sourceProvider,
      target: targetProvider,
      playlists: playlistDetails,
      interval: 3600,
      download_missing: false,
    };
    showScheduleModal = true;
  }

  function closeScheduleModal() {
    showScheduleModal = false;
  }

  async function createScheduledSync() {
    try {
      const response = await apiClient.post("/core/playlists/sync/schedule", {
        source: scheduleForm.source,
        target_source: scheduleForm.target,
        playlists: scheduleForm.playlists,
        interval: scheduleForm.interval,
        download_missing: scheduleForm.download_missing,
      });

      if (response.data.accepted) {
        success = `Scheduled sync created! Runs every ${scheduleIntervalOptions.find((o) => o.value === scheduleForm.interval)?.label || scheduleForm.interval + "s"}.`;
        closeScheduleModal();
        loadScheduledSyncs();
      }
    } catch (err) {
      error =
        err.response?.data?.error ||
        err.message ||
        "Failed to create scheduled sync";
    }
  }

  async function deleteScheduledSync(syncId) {
    if (!confirm("Delete this scheduled sync?")) return;
    try {
      await apiClient.delete(`/core/playlists/sync/scheduled/${syncId}`);
      success = "Scheduled sync deleted.";
      loadScheduledSyncs();
    } catch (err) {
      error =
        err.response?.data?.error ||
        err.message ||
        "Failed to delete scheduled sync";
    }
  }

  async function openAnalysisModal() {
    if (!sourceProvider || !targetProvider || selectedPlaylists.length === 0) {
      if (!sourceProvider) {
        error = "Please select a source service.";
      } else if (!targetProvider) {
        error = "Please select a target service.";
      } else {
        error = "Please select at least one playlist to sync.";
      }
      return;
    }
    // Clear stale page-level messages from a previous sync run
    error = "";
    success = "";
    analysisModalOpen = true;

    // Auto-resolve initial target user ID from selected playlist if available
    const initialTargetUserId =
      playlists.find((_, index) => selectedPlaylists.includes(index))
        ?.target_user_id || null;
    overrideTargetUserId = initialTargetUserId;

    await fetchTargetAccounts();

    // If still null after accounts loaded, preselect admin or first account
    if (!overrideTargetUserId && availableTargetAccounts.length > 0) {
      const adminAcc = availableTargetAccounts.find((a) => a.is_admin);
      overrideTargetUserId = adminAcc
        ? adminAcc.user_id || adminAcc.id
        : availableTargetAccounts[0].user_id || availableTargetAccounts[0].id;
    }

    runAnalysis();
  }

  function closeAnalysisModal() {
    analysisModalOpen = false;
    analysisResult = null;
    analysisError = "";
    analysisStarted = false;
    availableTargetAccounts = [];
    overrideTargetUserId = null;
    isDiagnosticsDrawerOpen = false;
    selectedTrackForDiagnostics = null;
    // Also clear any lingering sync-progress state so re-opening always shows a fresh analysis
    if (syncEventPollingId) {
      clearInterval(syncEventPollingId);
      syncEventPollingId = null;
    }
    syncEventStream = [];
    syncProgressEvent = null;
    syncDownloadMissing = false;
  }

  async function startSync() {
    // retain existing direct sync as a fallback (not used by UI now)
    return openAnalysisModal();
  }

  function togglePlaylist(index) {
    if (selectedPlaylists.includes(index)) {
      selectedPlaylists = selectedPlaylists.filter((i) => i !== index);
    } else {
      selectedPlaylists = [...selectedPlaylists, index];
    }
  }

  function toggleTarget(id) {
    if (targetProviders.includes(id)) {
      targetProviders = targetProviders.filter((i) => i !== id);
    } else {
      targetProviders = [...targetProviders, id];
    }
  }

  onMount(() => {
    plugins.load();
    preferences.load();
    loadScheduledSyncs();
  });

  onDestroy(() => {
    if (syncEventPollingId) {
      clearInterval(syncEventPollingId);
      syncEventPollingId = null;
    }
  });
</script>

<svelte:head>
  <title>Sync • Echosync</title>
</svelte:head>

<section class="page">
  <header class="page__header">
    <div>
      <p class="eyebrow">Operations</p>
      <h1>Sync Playlists</h1>
      <p class="sub">Transfer and synchronize playlists between services.</p>
    </div>
  </header>

  <div class="sync-container">
    <div class="setup-grid">
      <!-- Step 1: Source -->
      <div class="card">
        <div class="card__header">
          <span class="step-num">1</span>
          <h2>Source Service</h2>
        </div>
        <div class="form-group">
          <label for="source">Select where to sync from:</label>
          <Select
            id="source"
            ariaLabel="Source Service"
            placeholder="-- Select Source --"
            bind:value={sourceProvider}
            onchange={() => {
              console.log("[Debug] Source plugin selected:", sourceProvider);
              loadPlaylists();
            }}
            options={[
              { value: "", label: "-- Select Source --" },
              ...playlistPlugins.map((p) => ({ value: p.plugin_id, label: p.name })),
            ]}
          />
        </div>
      </div>

      <!-- Step 2: Targets -->
      <div class="card">
        <div class="card__header">
          <span class="step-num">2</span>
          <h2>Target Services</h2>
        </div>
        <div class="form-group">
          <label for="target">Select sync target:</label>
          <Select
            id="target"
            ariaLabel="Target Service"
            placeholder="-- Select Target --"
            bind:value={targetProvider}
            options={[
              { value: "", label: "-- Select Target --" },
              ...syncTargets
                .filter((p) => p.plugin_id !== sourceProvider)
                .map((p) => ({ value: p.plugin_id, label: p.name })),
            ]}
          />
          {#if syncTargets.length === 0}
            <p class="muted small">No target services available.</p>
          {/if}
        </div>
      </div>
    </div>

    <!-- Step 3: Playlists -->
    <div class="card playlists-card">
      <div class="card__header">
        <span class="step-num">3</span>
        <h2>Select Playlists</h2>
        {#if selectedPlaylists.length > 0}
          <span class="badge">{selectedPlaylists.length} selected</span>
        {/if}
      </div>

      {#if !sourceProvider}
        <div class="empty-state">
          <p class="muted">Select a source service to view playlists.</p>
        </div>
      {:else if loadingPlaylists}
        <div class="empty-state">
          <div class="spinner"></div>
          <p>Loading playlists...</p>
        </div>
      {:else if playlists.length === 0}
        <div class="empty-state">
          <p class="muted">No playlists found for this plugin.</p>
        </div>
      {:else}
        <div class="playlists-grid">
          {#each playlists as playlist, index}
            <button
              class="playlist-item active:scale-95 transition-all duration-200"
              class:selected={selectedPlaylists.includes(index)}
              on:click={() => togglePlaylist(index)}
            >
              <div class="playlist-info">
                <strong>{playlist.name}</strong>
                {#if playlist.track_count !== undefined}
                  <span class="muted small">{playlist.track_count} tracks</span>
                {/if}
              </div>
              <div class="playlist-meta-bottom-right">
                {#if playlist.source_account_name}
                  <span class="account-hint muted small"
                    >{playlist.source_account_name}</span
                  >
                {/if}
              </div>
              <div class="checkbox">
                {#if selectedPlaylists.includes(index)}
                  <svg viewBox="0 0 20 20" fill="currentColor">
                    <path
                      fill-rule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clip-rule="evenodd"
                    />
                  </svg>
                {/if}
              </div>
            </button>
          {/each}
        </div>
      {/if}
    </div>

    <div class="actions">
      {#if error}
        <p class="error-msg">{error}</p>
      {/if}
      {#if success}
        <p class="success-msg">{success}</p>
      {/if}
      <button
        class="btn btn--primary active:scale-95 transition-all duration-200"
        disabled={syncing}
        on:click={openAnalysisModal}
      >
        {#if syncing}
          Preparing...
        {:else}
          Sync Playlist
        {/if}
      </button>
      <button
        type="button"
        class="btn btn--secondary active:scale-95 transition-all duration-200"
        on:click={openScheduleModal}
      >
        ⏰ Create Schedule
      </button>
    </div>
  </div>

  <!-- Scheduled Syncs Section -->
  <div class="scheduled-syncs-section">
    <div class="section-header">
      <h2>Scheduled Syncs</h2>
      <button
        type="button"
        class="btn btn--accent active:scale-95 transition-all duration-200"
        on:click={openScheduleModal}
      >
        + Create Schedule
      </button>
    </div>

    {#if scheduledSyncs.length > 0}
      <div class="syncs-table">
        <div class="table-header">
          <div class="col-source">Source</div>
          <div class="col-target">Target</div>
          <div class="col-interval">Interval</div>
          <div class="col-playlists">Playlists</div>
          <div class="col-actions">Actions</div>
        </div>
        {#each scheduledSyncs as sync (sync.id)}
          <div class="table-row">
            <div class="col-source">{sync.source}</div>
            <div class="col-target">
              {formatTargetWithContext(sync.target, sync.playlists)}
            </div>
            <div class="col-interval">
              {scheduleIntervalOptions.find((o) => o.value === sync.interval)
                ?.label || sync.interval + "s"}
            </div>
            <div class="col-playlists">{sync.playlists.length}</div>
            <div class="col-actions">
              <button
                type="button"
                class="btn btn--small active:scale-95 transition-all duration-200"
                on:click={() => deleteScheduledSync(sync.id)}
              >
                Delete
              </button>
            </div>
          </div>
        {/each}
      </div>
    {:else}
      <p class="empty-state">
        No scheduled syncs yet. Create one to automate your playlists!
      </p>
    {/if}
  </div>
</section>

{#if analysisModalOpen}
  <div
    class="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/80 backdrop-blur-md"
    on:click={closeAnalysisModal}
    role="dialog"
    aria-modal="true"
  >
    <div
      class="bg-[#0b0c0f] border border-white/[0.08] rounded-2xl shadow-2xl flex flex-col h-[88vh] max-h-[88vh] overflow-hidden transition-all duration-200 {isDiagnosticsDrawerOpen ? 'w-full max-w-[1400px]' : 'w-full max-w-6xl'}"
      on:click|stopPropagation
    >
      <!-- Row 1: Pinned Top Header Bar -->
      <div class="px-5 py-3 bg-[#0e1014] border-b border-white/[0.07] shrink-0 flex items-center justify-between gap-4">
        <div class="flex items-center gap-2.5 min-w-0">
          <div class="w-7 h-7 rounded-lg bg-white/[0.05] border border-white/[0.08] flex items-center justify-center text-cyan-400 shrink-0">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
            </svg>
          </div>
          <span class="text-sm font-semibold text-zinc-100 tracking-tight">Playlist Sync</span>
          <span class="text-zinc-600 text-sm">/</span>
          <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md bg-white/[0.04] border border-white/[0.08] text-xs font-medium text-zinc-300 truncate">
            {#if syncProgressEvent}
              Syncing to {getPluginName(targetProvider)}
            {:else}
              <span>{getPluginName(analysisResult?.source || sourceProvider)}</span>
              <span class="text-cyan-400">→</span>
              <span>{getPluginName(analysisResult?.target || targetProvider)}</span>
            {/if}
          </span>
        </div>

        <div class="flex items-center gap-2.5 shrink-0">
          {#if !syncProgressEvent && availableTargetAccounts.length > 0}
            <div class="relative">
              <button
                type="button"
                class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium bg-[#14161b] hover:bg-[#1a1d24] border border-white/[0.09] text-zinc-200 transition-colors"
                on:click={() => (targetProfileMenuOpen = !targetProfileMenuOpen)}
                title="Target profile"
              >
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                <span>{selectedTargetProfileLabel}</span>
                <svg class="w-3.5 h-3.5 text-zinc-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {#if targetProfileMenuOpen}
                <div
                  class="absolute right-0 mt-1.5 w-64 rounded-xl border border-white/[0.1] bg-[#14161c] shadow-2xl z-50 py-1.5 max-h-64 overflow-y-auto"
                >
                  {#if myTargetProfiles.length > 0 || familyTargetProfiles.length > 0}
                    {#if myTargetProfiles.length > 0}
                      <div class="px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-cyan-400">
                        My Profiles
                      </div>
                      {#each myTargetProfiles as acc}
                        <button
                          type="button"
                          class="w-full text-left px-3 py-1.5 text-xs text-zinc-200 flex items-center justify-between hover:bg-white/[0.06] transition-colors"
                          on:click={() => {
                            overrideTargetUserId = acc.external_account_id;
                            targetProfileMenuOpen = false;
                          }}
                        >
                          <span>{acc.display_name || acc.username}</span>
                          <span class="text-[10px] uppercase text-zinc-500">{acc.provider}</span>
                        </button>
                      {/each}
                    {/if}
                    {#if familyTargetProfiles.length > 0}
                      <div class="px-3 py-1 mt-1 text-[10px] font-bold uppercase tracking-wider border-t border-white/[0.07] text-zinc-400">
                        Family Profiles
                      </div>
                      {#each familyTargetProfiles as acc}
                        <button
                          type="button"
                          class="w-full text-left px-3 py-1.5 text-xs text-zinc-200 flex items-center justify-between hover:bg-white/[0.06] transition-colors"
                          on:click={() => {
                            overrideTargetUserId = acc.external_account_id;
                            targetProfileMenuOpen = false;
                          }}
                        >
                          <span>{acc.username} — {acc.display_name || acc.external_account_id}</span>
                          <span class="text-[10px] uppercase text-zinc-500">{acc.provider}</span>
                        </button>
                      {/each}
                    {/if}
                  {:else}
                    {#each availableTargetAccounts as acc}
                      {@const val = acc.user_id || acc.id}
                      <button
                        type="button"
                        class="w-full text-left px-3 py-1.5 text-xs text-zinc-200 flex items-center justify-between hover:bg-white/[0.06] transition-colors"
                        on:click={() => {
                          overrideTargetUserId = val;
                          targetProfileMenuOpen = false;
                        }}
                      >
                        <span>{acc.display_name || acc.account_name || acc.username || acc.name}</span>
                        {#if acc.is_admin}
                          <span class="text-[10px] font-bold uppercase text-cyan-400">Admin</span>
                        {/if}
                      </button>
                    {/each}
                  {/if}
                </div>
              {/if}
            </div>
          {/if}

          <div class="h-4 w-px bg-white/[0.08]"></div>
          <button
            type="button"
            class="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-white/[0.06] transition-colors"
            on:click={closeAnalysisModal}
            aria-label="Close Modal"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      {#if !syncProgressEvent}
        <!-- Row 2: Pinned Stats, Quality Profile & Primary Actions Bar (Never Scrolls Away) -->
        <div class="px-5 py-2.5 bg-[#0d0f13] border-b border-white/[0.07] shrink-0 flex flex-wrap items-center justify-between gap-3">
          <div class="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs">
            <div class="flex items-center gap-1.5">
              <span class="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">Total</span>
              <span class="font-mono font-semibold text-zinc-100">{analysisResult?.summary?.total_tracks ?? analysisAllTracks.length ?? "–"}</span>
            </div>
            <span class="text-zinc-700">•</span>
            <div class="flex items-center gap-1.5">
              <span class="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">Matched</span>
              <span class="font-mono font-semibold text-emerald-400">{analysisFoundCount}</span>
            </div>
            <span class="text-zinc-700">•</span>
            <div class="flex items-center gap-1.5">
              <span class="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">Missing</span>
              <span class="font-mono font-semibold text-rose-400">{analysisMissingCount}</span>
            </div>
            <span class="text-zinc-700 hidden sm:inline">•</span>
            <div class="flex items-center gap-2 min-w-[180px]">
              <span class="text-[11px] text-zinc-500 whitespace-nowrap">Profile:</span>
              <Select
                compact={true}
                ariaLabel="Target Quality for Missing Tracks"
                bind:value={selectedQuality}
                options={qualityProfiles.length === 0
                  ? [{ value: "", label: "No profiles configured" }]
                  : qualityProfiles.map((profile) => ({
                      value: profile.name,
                      label: profile.name,
                    }))}
              />
            </div>
          </div>

          <div class="flex items-center gap-2 shrink-0">
            <button
              type="button"
              class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-zinc-300 hover:text-white bg-white/[0.03] hover:bg-white/[0.07] border border-white/[0.08] transition-colors disabled:opacity-40"
              on:click={runAnalysis}
              disabled={analysisLoading}
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5 {analysisLoading ? 'animate-spin' : ''}" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              <span>{analysisLoading ? "Analyzing…" : analysisStarted ? "Re-analyze" : "Begin Analysis"}</span>
            </button>

            <button
              type="button"
              class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-zinc-200 hover:text-white bg-[#14161b] hover:bg-[#1c1f26] border border-white/[0.1] transition-colors disabled:opacity-40"
              on:click={downloadMissingTracks}
              disabled={!analysisResult || downloadingMissing || analysisMissingCount === 0}
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              <span>{downloadingMissing ? "Starting…" : `Download Missing (${analysisMissingCount})`}</span>
            </button>

            <button
              type="button"
              class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-cyan-500 hover:bg-cyan-400 text-zinc-950 transition-colors disabled:opacity-40 shadow-sm"
              on:click={confirmSync}
              disabled={!overrideTargetUserId ||
                !(
                  (analysisResult?.summary?.matched_pairs?.length ?? 0) > 0 ||
                  analysisFoundCount > 0 ||
                  (analysisResult?.tracks?.some((t) => t.matched_track_id) ?? false)
                )}
            >
              <span>Sync to {getPluginName(analysisResult?.target || targetProvider) || "Target"}</span>
              <span class="px-1.5 py-0.5 rounded bg-zinc-950/20 font-mono text-[11px]">{analysisFoundCount}</span>
            </button>
          </div>
        </div>
      {/if}

      <!-- Main Dual-Pane Workspace (Independently Scrollable Track Table + Docked Diagnostics Drawer) -->
      <div class="flex-1 min-h-0 flex flex-row overflow-hidden">
        {#if !syncProgressEvent}
          <!-- Left Pane: Filter Bar + Sticky Table Header + Scrollable Rows -->
          <div class="flex-1 min-h-0 flex flex-col overflow-hidden bg-[#0b0c0f]">
            <!-- Row 3: Pinned Filter & Search Bar -->
            <div class="px-5 py-2 bg-[#0c0d11] border-b border-white/[0.06] shrink-0 flex flex-wrap items-center justify-between gap-3">
              <div class="flex items-center gap-2">
                <span class="text-[11px] text-zinc-500 font-medium">Filter:</span>
                <div class="inline-flex items-center p-0.5 rounded-lg bg-[#13151a] border border-white/[0.07]">
                  <button
                    type="button"
                    class="px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors {analysisFilter === 'all' ? 'bg-white/[0.1] text-white' : 'text-zinc-400 hover:text-zinc-200'}"
                    on:click={() => (analysisFilter = "all")}
                  >
                    All ({analysisAllTracks.length})
                  </button>
                  <button
                    type="button"
                    class="px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors {analysisFilter === 'found' ? 'bg-emerald-500/15 text-emerald-300' : 'text-zinc-400 hover:text-zinc-200'}"
                    on:click={() => (analysisFilter = "found")}
                  >
                    Found ({analysisFoundCount})
                  </button>
                  <button
                    type="button"
                    class="px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors {analysisFilter === 'missing' ? 'bg-rose-500/15 text-rose-300' : 'text-zinc-400 hover:text-zinc-200'}"
                    on:click={() => (analysisFilter = "missing")}
                  >
                    Missing ({analysisMissingCount})
                  </button>
                </div>
              </div>

              <div class="flex items-center gap-3">
                <div class="relative">
                  <input
                    type="text"
                    bind:value={analysisSearchQuery}
                    placeholder="Filter tracks or artists…"
                    class="w-48 sm:w-56 pl-7 pr-2.5 py-1 rounded-lg text-xs bg-[#13151a] border border-white/[0.08] text-zinc-200 placeholder:text-zinc-500 focus:outline-none focus:border-cyan-500/50 transition-colors"
                  />
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5 text-zinc-500 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </div>
                <span class="text-[11px] text-zinc-500 hidden lg:inline">Select row to inspect matching</span>
              </div>
            </div>

            {#if analysisError}
              <div class="mx-5 mt-3 px-3 py-2 rounded-lg bg-rose-950/40 border border-rose-500/30 text-xs text-rose-300 shrink-0">
                {analysisError}
              </div>
            {/if}

            <!-- Pinned Table Column Header -->
            <div class="grid grid-cols-[44px_minmax(0,1.4fr)_minmax(0,1fr)_72px_118px_90px] items-center gap-3 px-5 py-2 bg-[#0c0d11] border-b border-white/[0.06] text-[11px] font-medium text-zinc-500 shrink-0 select-none">
              <span class="text-right pr-1">#</span>
              <span>Track</span>
              <span>Artist</span>
              <span class="text-right">Duration</span>
              <span>Status</span>
              <span class="text-right">Download</span>
            </div>

            <!-- Independently Scrollable Track Rows -->
            <div class="flex-1 min-h-0 overflow-y-auto scrollbar-thin scrollbar-thumb-zinc-700/80 scrollbar-track-transparent">
              {#if analysisLoading}
                <div class="py-16 text-center text-xs text-zinc-400">
                  Analyzing playlist tracks against local library…
                </div>
              {:else if filteredAnalysisTracks.length > 0}
                <div class="divide-y divide-white/[0.04]">
                  {#each filteredAnalysisTracks as { track, originalIndex }}
                    {@const found = isTrackFound(track)}
                    {@const selected = selectedTrackForDiagnostics === track && isDiagnosticsDrawerOpen}
                    <button
                      type="button"
                      class="w-full grid grid-cols-[44px_minmax(0,1.4fr)_minmax(0,1fr)_72px_118px_90px] items-center gap-3 px-5 py-2.5 text-left text-xs transition-colors {selected ? 'bg-white/[0.06] ring-1 ring-inset ring-cyan-500/30' : 'hover:bg-white/[0.025]'}"
                      on:click={() => {
                        selectedTrackForDiagnostics = track;
                        isDiagnosticsDrawerOpen = true;
                      }}
                    >
                      <span class="font-mono text-[11px] text-zinc-500 text-right pr-1 tabular-nums">
                        {String(originalIndex + 1).padStart(2, "0")}
                      </span>
                      <div class="min-w-0">
                        <div class="font-medium text-zinc-100 truncate" title={track.title}>{track.title}</div>
                        {#if track.album}
                          <div class="text-[11px] text-zinc-500 truncate" title={track.album}>{track.album}</div>
                        {/if}
                      </div>
                      <span class="text-zinc-400 truncate" title={track.artist}>{track.artist}</span>
                      <span class="font-mono text-[11px] text-zinc-400 text-right tabular-nums">{track.duration || "–"}</span>
                      <span class="inline-flex items-center gap-1.5 text-[11px] font-medium truncate {found ? 'text-emerald-400' : 'text-rose-400'}">
                        <span class="w-1.5 h-1.5 rounded-full shrink-0 {found ? 'bg-emerald-400' : 'bg-rose-400'}"></span>
                        <span class="truncate">{track.library_match || (found ? "Found" : "Missing")}</span>
                      </span>
                      <span class="text-[11px] text-zinc-500 text-right truncate">{track.download_status || "–"}</span>
                    </button>
                  {/each}
                </div>
              {:else}
                <div class="py-16 text-center text-xs text-zinc-500">
                  {analysisAllTracks.length > 0
                    ? "No tracks match the current filter."
                    : "No track details available yet."}
                </div>
              {/if}
            </div>

            <!-- Pinned Footer Status Strip -->
            <div class="px-5 py-2 bg-[#0e1014] border-t border-white/[0.06] shrink-0 flex items-center justify-between text-[11px] text-zinc-500">
              <span>Target quality applies only to newly downloaded missing tracks.</span>
              <span class="hidden sm:inline">AcoustID &amp; duration validation active</span>
            </div>
          </div>
        {:else}
          <!-- Sync Progress Section -->
          {@const syncedEvents = syncEventStream.filter((e) => e.type === "track_synced")}
          {@const failedEvents = syncEventStream.filter((e) => e.type === "track_failed")}
          {@const totalSyncTracks = syncProgressEvent.data?.total || analysisResult?.summary?.found_in_library || 0}
          {@const pendingSyncTracks = Math.max(0, totalSyncTracks - syncedEvents.length - failedEvents.length)}
          {@const syncedPct = totalSyncTracks > 0 ? Math.min(100, (syncedEvents.length / totalSyncTracks) * 100) : 0}
          {@const failedPct = totalSyncTracks > 0 ? Math.min(100 - syncedPct, (failedEvents.length / totalSyncTracks) * 100) : 0}
          <div class="flex-1 min-h-0 flex flex-col overflow-hidden bg-[#0b0c0f]">
            <div class="p-6 pb-4 shrink-0 space-y-4">
              <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div class="bg-[#12141a] border border-white/[0.07] rounded-xl p-3.5">
                  <div class="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">Total Tracks</div>
                  <div class="text-xl font-bold font-mono text-zinc-100 mt-1">{totalSyncTracks}</div>
                </div>
                <div class="bg-[#12141a] border border-white/[0.07] rounded-xl p-3.5">
                  <div class="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">Synced</div>
                  <div class="text-xl font-bold font-mono text-emerald-400 mt-1">{syncedEvents.length}</div>
                </div>
                <div class="bg-[#12141a] border {failedEvents.length > 0 ? 'border-rose-500/30' : 'border-white/[0.07]'} rounded-xl p-3.5">
                  <div class="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">Failed</div>
                  <div class="text-xl font-bold font-mono text-rose-400 mt-1">{failedEvents.length}</div>
                </div>
                <div class="bg-[#12141a] border border-white/[0.07] rounded-xl p-3.5">
                  <div class="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">Pending</div>
                  <div class="text-xl font-bold font-mono text-zinc-300 mt-1">{pendingSyncTracks}</div>
                </div>
              </div>

              <!-- Segmented Progress Bar (Green = Synced, Rose = Failed) -->
              {#if totalSyncTracks > 0}
                <div class="bg-[#12141a] border border-white/[0.07] rounded-xl p-3.5 space-y-2">
                  <div class="flex items-center justify-between text-xs font-medium">
                    {#if syncProgressEvent.type === "sync_complete"}
                      {#if failedEvents.length > 0}
                        <span class="text-amber-400">⚠ Completed with {failedEvents.length} failed track{failedEvents.length === 1 ? '' : 's'}</span>
                      {:else}
                        <span class="text-emerald-400">✓ Completed cleanly</span>
                      {/if}
                    {:else}
                      <span class="text-zinc-300">
                        Syncing… {Math.round(syncedPct + failedPct)}% ({syncedEvents.length + failedEvents.length}/{totalSyncTracks})
                      </span>
                    {/if}
                    <span class="font-mono text-[11px] text-zinc-400">
                      {syncedEvents.length} synced{failedEvents.length > 0 ? ` · ${failedEvents.length} failed` : ''}
                    </span>
                  </div>
                  <div class="h-2 w-full bg-white/[0.06] rounded-full overflow-hidden flex">
                    <div class="h-full bg-emerald-500 transition-all duration-300" style="width: {syncedPct}%"></div>
                    {#if failedPct > 0}
                      <div class="h-full bg-rose-500 transition-all duration-300" style="width: {failedPct}%"></div>
                    {/if}
                  </div>
                </div>
              {/if}
            </div>

            <!-- Failed Tracks & Activity Log -->
            <div class="flex-1 min-h-0 overflow-y-auto px-6 pb-6 space-y-4 scrollbar-thin scrollbar-thumb-zinc-700/80 scrollbar-track-transparent">
              {#if failedEvents.length > 0}
                <div class="bg-[#12141a] border border-rose-500/25 rounded-xl overflow-hidden">
                  <div class="px-4 py-2.5 bg-rose-950/20 border-b border-rose-500/20 flex items-center justify-between">
                    <span class="text-xs font-semibold text-rose-300">Failed Tracks ({failedEvents.length})</span>
                    <span class="text-[11px] text-rose-400/80">Could not be added to target playlist</span>
                  </div>
                  <div class="divide-y divide-white/[0.04]">
                    {#each failedEvents as ev, i}
                      <div class="px-4 py-2.5 flex items-start justify-between gap-4 text-xs">
                        <div class="min-w-0">
                          <div class="font-medium text-zinc-100 truncate">
                            {ev.data?.title || ev.title || `Track #${i + 1}`}
                          </div>
                          <div class="text-[11px] text-zinc-400 truncate">
                            {ev.data?.artist || ev.artist || "Unknown Artist"}
                          </div>
                        </div>
                        <div class="text-[11px] text-rose-400 text-right max-w-md break-words">
                          {ev.data?.error || ev.error || "Not found on target media server"}
                        </div>
                      </div>
                    {/each}
                  </div>
                </div>
              {:else if syncProgressEvent.type === "sync_complete"}
                <div class="bg-[#12141a] border border-emerald-500/20 rounded-xl p-6 text-center text-xs text-zinc-400">
                  All {syncedEvents.length} tracks were synced to {getPluginName(targetProvider)} with zero errors.
                </div>
              {/if}
            </div>
          </div>
        {/if}

        {#if isDiagnosticsDrawerOpen}
          <PlaylistMatchDiagnosticDrawer
            isOpen={isDiagnosticsDrawerOpen}
            track={selectedTrackForDiagnostics}
            onClose={() => {
              isDiagnosticsDrawerOpen = false;
            }}
          />
        {/if}
      </div>
    </div>
  </div>
{/if}

<!-- Sync Config Modal -->
{#if syncConfigModalOpen}
  <div class="modal-backdrop" role="presentation"></div>
  <div class="modal sync-config-modal">
    <div class="modal-header">
      <h2>Configure Sync</h2>
      <button
        type="button"
        class="close-btn active:scale-95 transition-all duration-200"
        on:click={closeSyncConfigModal}>✕</button
      >
    </div>

    <div class="modal-body">
      <div class="config-summary">
        <div class="config-row">
          <span class="config-label">Source:</span>
          <span class="config-value">{sourceProvider}</span>
        </div>
        <div class="config-row">
          <span class="config-label">Target:</span>
          <span class="config-value"
            >{selectedTargetLabel || targetProvider}</span
          >
        </div>
        <div class="config-row">
          <span class="config-label">Playlists:</span>
          <span class="config-value">{selectedPlaylists.length} selected</span>
        </div>
        <div class="config-row">
          <span class="config-label">Matched Tracks:</span>
          <span class="config-value"
            >{analysisResult?.summary?.matched_pairs?.length || 0}</span
          >
        </div>
        <div class="config-row">
          <span class="config-label">Missing Tracks:</span>
          <span class="config-value"
            >{analysisResult?.summary?.missing_tracks || 0}</span
          >
        </div>
      </div>

      <div class="config-options flex items-center gap-3">
        <label class="switch">
          <input type="checkbox" bind:checked={syncDownloadMissing} />
          <span class="slider"></span>
        </label>
        <span>Download missing tracks after sync</span>
      </div>
    </div>

    <div class="modal-footer">
      <button
        type="button"
        class="btn active:scale-95 transition-all duration-200"
        on:click={closeSyncConfigModal}>Cancel</button
      >
      <button
        type="button"
        class="btn btn--accent active:scale-95 transition-all duration-200"
        on:click={confirmSync}
        disabled={syncInProgress}
      >
        {syncInProgress ? "Starting Sync…" : "Start Sync"}
      </button>
    </div>
  </div>
{/if}

<!-- Sync Progress Modal -->

<!-- Schedule Modal -->
{#if showScheduleModal}
  <div class="modal-backdrop" role="presentation"></div>
  <div class="modal schedule-modal">
    <div class="modal-header">
      <h2>Create Scheduled Sync</h2>
      <button
        type="button"
        class="close-btn active:scale-95 transition-all duration-200"
        on:click={closeScheduleModal}>✕</button
      >
    </div>

    <div class="modal-body">
      <div class="form-group">
        <label for="schedule-source">Source Service:</label>
        <Select
          id="schedule-source"
          ariaLabel="Schedule Source Service"
          bind:value={scheduleForm.source}
          options={playlistPlugins.map((p) => ({ value: p.plugin_id, label: p.name }))}
        />
      </div>

      <div class="form-group">
        <label for="schedule-target">Target Service:</label>
        <Select
          id="schedule-target"
          ariaLabel="Schedule Target Service"
          bind:value={scheduleForm.target}
          options={syncTargets.map((p) => ({ value: p.plugin_id, label: p.name }))}
        />
      </div>

      <div class="form-group">
        <label for="schedule-interval">Repeat Interval:</label>
        <Select
          id="schedule-interval"
          ariaLabel="Schedule Repeat Interval"
          bind:value={scheduleForm.interval}
          options={scheduleIntervalOptions}
        />
      </div>

      <div class="form-group flex items-center gap-3">
        <label class="switch">
          <input type="checkbox" bind:checked={scheduleForm.download_missing} />
          <span class="slider"></span>
        </label>
        <span>Download missing tracks after sync</span>
      </div>

      <div class="bg-[rgba(59,130,246,0.1)] rounded-md p-3">
        <p class="text-xs text-muted m-0">
          Note: This will sync {scheduleForm.playlists.length} selected playlist(s)
          to {formatTargetWithContext(
            scheduleForm.target,
            scheduleForm.playlists,
          )} every {scheduleIntervalOptions.find(
            (o) => o.value === scheduleForm.interval,
          )?.label || scheduleForm.interval + "s"}.
        </p>
        {#if scheduleForm.playlists.length > 0}
          <div
            class="mt-2 max-h-[120px] overflow-y-auto custom-scrollbar bg-black/20 border border-[rgba(255,255,255,0.05)] rounded p-2"
          >
            <ul class="m-0 pl-4 text-xs text-muted list-disc">
              {#each scheduleForm.playlists as pl}
                <li class="py-0.5">{pl.name}</li>
              {/each}
            </ul>
          </div>
        {/if}
      </div>
    </div>

    <div class="modal-footer">
      <button
        type="button"
        class="btn active:scale-95 transition-all duration-200"
        on:click={closeScheduleModal}>Cancel</button
      >
      <button
        type="button"
        class="btn btn--accent active:scale-95 transition-all duration-200"
        on:click={createScheduledSync}>Create Schedule</button
      >
    </div>
  </div>
{/if}

<style>
  .page {
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .sync-container {
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .setup-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
  }

  @media (max-width: 800px) {
    .setup-grid {
      grid-template-columns: 1fr;
    }
  }

  .card {
    background: var(--glass);
    backdrop-filter: blur(12px);
    border: 1px solid var(--glass-border);
    border-radius: 14px;
    padding: 20px;
  }

  .card__header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 20px;
  }

  .step-num {
    width: 24px;
    height: 24px;
    background: var(--accent);
    color: #000;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 800;
    font-size: 12px;
  }

  .card__header h2 {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
    color: var(--text);
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .form-group label {
    color: var(--text);
    font-size: 14px;
    font-weight: 500;
  }

  select {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 12px 16px;
    color: var(--text);
    font-size: 14px;
    outline: none;
    cursor: pointer;
    appearance: none;
    -webkit-appearance: none;
    -moz-appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg width='12' height='8' viewBox='0 0 12 8' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1.5L6 6.5L11 1.5' stroke='%23ffffff' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 12px center;
    padding-right: 36px;
  }

  select option {
    background: #1a1a1a;
    color: var(--text);
    padding: 8px;
  }

  select:hover {
    border-color: rgba(255, 255, 255, 0.2);
    background: rgba(255, 255, 255, 0.08);
  }

  select:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(15, 239, 136, 0.1);
  }

  .playlists-grid {
    padding: 2px 6px;
    border-radius: 4px;
    color: #94a3b8;
  }

  .playlists-card {
    min-height: 300px;
  }

  .playlists-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 12px;
  }

  .playlist-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    text-align: left;
    cursor: pointer;
    transition: all 0.2s;
    color: var(--text);
    font-family: inherit;
  }

  .playlist-item:hover {
    background: rgba(255, 255, 255, 0.06);
    border-color: rgba(255, 255, 255, 0.1);
    transform: translateY(-1px);
  }

  .playlist-item.selected {
    background: rgba(15, 239, 136, 0.12);
    border-color: var(--accent);
    border-width: 2px;
    box-shadow: 0 0 20px rgba(15, 239, 136, 0.2);
  }

  .playlist-item.selected:hover {
    background: rgba(15, 239, 136, 0.18);
    border-color: var(--accent);
  }

  .playlist-info {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .playlist-meta-bottom-right {
    margin-left: auto;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    justify-content: flex-end;
  }

  .account-hint {
    font-size: 0.75rem;
    opacity: 0.6;
    margin-right: 8px;
  }

  .checkbox {
    width: 20px;
    height: 20px;
    border: 2px solid rgba(255, 255, 255, 0.2);
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--accent);
  }

  .selected .checkbox {
    border-color: var(--accent);
    background: var(--accent);
    color: #000;
  }

  .actions {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    padding: 20px;
    background: rgba(255, 255, 255, 0.02);
    border-radius: 14px;
  }

  .btn,
  .btn--primary {
    background: var(--accent);
    color: #000;
    padding: 12px 24px;
    border-radius: 10px;
    font-weight: 600;
    font-size: 14px;
    border: none;
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn {
    background: rgba(255, 255, 255, 0.08);
    color: var(--text);
  }

  .btn:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.12);
    transform: translateY(-1px);
  }

  .btn--primary:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 4px 20px rgba(15, 239, 136, 0.3);
  }

  .btn--primary:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .error-msg {
    color: #ef4444;
    font-size: 14px;
  }
  .success-msg {
    color: var(--accent);
    font-size: 14px;
    font-weight: 600;
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px 20px;
    color: #94a3b8;
  }

  .spinner {
    width: 30px;
    height: 30px;
    border: 3px solid rgba(255, 255, 255, 0.1);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 16px;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  .badge {
    background: rgba(15, 239, 136, 0.1);
    color: var(--text);
    border: 1px solid var(--accent);
    border-radius: 6px;
    padding: 2px 8px;
    font-weight: 700;
    font-size: 11px;
  }

  .muted {
    color: #94a3b8;
  }
  .small {
    font-size: 12px;
  }

  /* Analysis modal */
  .modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.55);
    backdrop-filter: blur(4px);
    z-index: 20;
  }
  .modal {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: min(1000px, 96vw);
    max-height: 90vh;
    background: rgba(10, 10, 10, 0.98);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    padding: 24px;
    z-index: 30;
    display: flex;
    flex-direction: column;
    gap: 16px;
    overflow: hidden;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
    transition:
      width 0.3s cubic-bezier(0.16, 1, 0.3, 1),
      max-width 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .modal.modal--expanded {
    width: min(1500px, 96vw);
  }

  .modal-content-container {
    display: flex;
    flex-direction: row;
    flex: 1;
    min-height: 0;
    overflow: hidden;
    gap: 20px;
  }
  .modal__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    padding-bottom: 16px;
  }

  .modal__header h2 {
    color: var(--text);
    margin: 0;
  }

  .modal__header .eyebrow {
    color: var(--accent);
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin: 0 0 4px 0;
  }

  .modal__header .sub {
    color: var(--muted);
    font-size: 13px;
    margin: 4px 0 0 0;
  }

  .target-account-selector {
    margin-top: 8px;
  }

  .target-account-selector select {
    background: rgba(15, 23, 42, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 6px;
    color: var(--text);
    padding: 4px 8px;
    font-size: 12px;
    outline: none;
  }

  .target-account-selector select:focus {
    border-color: var(--accent);
  }
  .modal__body {
    display: flex;
    flex-direction: column;
    gap: 16px;
    flex: 1;
    min-width: 0;
    min-height: 0;
    overflow-y: auto;
  }
  .close-btn {
    background: rgba(255, 255, 255, 0.05);
    border: none;
    color: var(--muted);
    font-size: 24px;
    cursor: pointer;
    width: 32px;
    height: 32px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
  }

  .close-btn:hover {
    background: rgba(255, 255, 255, 0.1);
    color: var(--text);
  }
  .summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px;
  }
  .summary-card {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    padding: 12px;
  }
  .summary-card .label {
    color: var(--muted);
    font-size: 12px;
    margin-bottom: 4px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-weight: 600;
  }
  .summary-card .value {
    font-size: 24px;
    font-weight: 700;
    color: var(--text);
  }
  .summary-card .highlight {
    color: #fbbf24;
  }

  .controls-row {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    gap: 12px;
    align-items: center;
  }
  .control {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .control label {
    color: var(--text);
    font-size: 13px;
    font-weight: 500;
  }
  .control.buttons {
    flex-direction: row;
    align-items: center;
    gap: 10px;
  }
  .controls-row select {
    min-width: 180px;
  }
  .tracks-table-wrapper {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    margin-top: 1.5rem;
  }

  .tracks-table {
    width: 100%;
  }

  .table-header {
    position: sticky;
    top: 0;
    background: rgba(15, 23, 42, 0.95);
    z-index: 10;
  }

  .table-row {
    display: grid;
    grid-template-columns: 40px 1.5fr 1.2fr 90px 140px 160px;
    gap: 8px;
    padding: 10px 12px;
    align-items: center;
  }

  .table-row.interactive {
    cursor: pointer;
    transition:
      background 0.15s ease,
      outline-color 0.15s ease;
  }

  .table-row.interactive:hover {
    background: rgba(255, 255, 255, 0.05);
  }

  .table-row.selected {
    background: rgba(99, 102, 241, 0.15) !important;
    outline: 1px solid rgba(99, 102, 241, 0.5);
    border-radius: 6px;
  }

  .table-row span {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .match-badge {
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 600;
  }

  .match-badge.found {
    background: rgba(74, 222, 128, 0.1);
    color: #4ade80;
  }

  .match-badge.fuzzy {
    background: rgba(250, 204, 21, 0.1);
    color: #facc15;
  }

  .match-badge.partial {
    background: rgba(96, 165, 250, 0.1);
    color: #60a5fa;
  }

  .match-badge.missing {
    background: rgba(239, 68, 68, 0.1);
    color: #ef4444;
  }

  /* Sync Config Modal */
  .sync-config-modal {
    width: min(600px, 96vw);
    max-height: 70vh;
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    padding-bottom: 12px;
  }

  .modal-header h2 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
    color: var(--text);
  }

  .close-btn {
    background: none;
    border: none;
    color: var(--text-secondary);
    font-size: 20px;
    cursor: pointer;
    padding: 4px 8px;
    border-radius: 4px;
    transition: all 0.2s;
  }

  .close-btn:hover {
    background: rgba(255, 255, 255, 0.1);
    color: var(--text);
  }

  .modal-body {
    flex: 1;
    overflow-y: auto;
    padding: 12px 0;
  }

  .modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    padding-top: 12px;
  }

  .config-summary {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 12px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    margin-bottom: 16px;
  }

  .config-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 14px;
  }

  .config-label {
    color: var(--text-secondary);
    font-weight: 500;
  }

  .config-value {
    color: var(--text);
    font-weight: 600;
  }

  .config-options {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 12px;
    background: rgba(255, 255, 255, 0.02);
    border-radius: 8px;
  }

  .config-options label {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    color: var(--text);
    cursor: pointer;
  }

  .config-options input[type="checkbox"] {
    cursor: pointer;
  }

  .progress-bar-container {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin: 24px 0 16px 0;
    padding: 12px;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 8px;
    border: 1px solid rgba(59, 130, 246, 0.2);
  }

  .progress-label {
    font-size: 13px;
    color: var(--text-secondary);
    font-weight: 600;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .progress-bar {
    width: 100%;
    height: 12px;
    background: rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    overflow: hidden;
    border: 1px solid rgba(59, 130, 246, 0.3);
  }

  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #3b82f6 0%, #0ea5e9 100%);
    border-radius: 6px;
    transition:
      width 0.3s ease,
      background 0.3s ease;
    box-shadow: 0 0 10px rgba(59, 130, 246, 0.4);
  }

  .progress-fill.complete {
    background: linear-gradient(90deg, #22c55e 0%, #16a34a 100%);
    box-shadow: 0 0 10px rgba(34, 197, 94, 0.4);
  }

  /* Scheduled Syncs */
  .scheduled-syncs-section {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 20px;
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
  }

  .section-header h2 {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
    color: var(--text);
  }

  .syncs-table {
    display: flex;
    flex-direction: column;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    overflow: hidden;
  }

  .syncs-table .table-header {
    display: grid;
    grid-template-columns: 150px 150px 150px 120px 100px;
    gap: 0;
    background: rgba(255, 255, 255, 0.05);
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    padding: 12px 16px;
    font-weight: 600;
    font-size: 13px;
    color: var(--text-secondary);
  }

  .syncs-table .table-row {
    display: grid;
    grid-template-columns: 150px 150px 150px 120px 100px;
    gap: 0;
    align-items: center;
    padding: 12px 16px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    font-size: 14px;
    color: var(--text);
  }

  .syncs-table .table-row:last-child {
    border-bottom: none;
  }

  .syncs-table .table-row:hover {
    background: rgba(255, 255, 255, 0.02);
  }

  .col-source,
  .col-target,
  .col-interval,
  .col-playlists,
  .col-actions {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .empty-state {
    text-align: center;
    padding: 40px 20px;
    color: var(--text-secondary);
    font-size: 14px;
  }

  /* Schedule Modal */
  .schedule-modal {
    width: min(500px, 96vw);
    max-height: 80vh;
  }

  .schedule-modal .modal-body {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .info-text {
    font-size: 12px;
    color: var(--text-secondary);
    margin: 0;
    padding: 12px;
    background: rgba(59, 130, 246, 0.1);
    border-radius: 6px;
  }

  .btn--small {
    padding: 4px 12px;
    font-size: 12px;
  }
</style>
