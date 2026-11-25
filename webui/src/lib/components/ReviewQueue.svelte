<svelte:options
  customElement={{
    tag: "echosync-review-queue",
    shadow: "none",
  }}
/>

<script lang="ts">
  import { onMount } from "svelte";
  import {
    Search,
    RefreshCw,
    RotateCcw,
    ArrowUpDown,
    SlidersHorizontal,
    X,
    FileAudio
  } from "lucide-svelte";
  import apiClient from "../../api/client";
  import MetadataReviewModal from "./MetadataReviewModal.svelte";

  let loading = true;
  let error = "";
  let tasks: any[] = [];
  let rowActionState: Record<number, string> = {};
  let retryingQueue = false;

  // Filtering & Sorting state
  let searchQuery = "";
  let confidenceFilter: "all" | "high" | "medium" | "low" = "all";
  let sourceFilter: "all" | "downloads" | "library" = "all";
  let sortBy: "conf_desc" | "conf_asc" | "name_asc" | "name_desc" | "newest" | "oldest" = "conf_desc";

  let showReviewModal = false;
  let selectedTask: any = null;

  function getConfidenceTier(score: number | null | undefined): "high" | "medium" | "low" {
    const val = Number(score || 0);
    if (val >= 0.85) return "high";
    if (val >= 0.6) return "medium";
    return "low";
  }

  function getSourceBucket(filePath: string | null | undefined): "downloads" | "library" | "other" {
    const normalized = String(filePath || "").replace(/\\/g, "/").toLowerCase();
    if (normalized.includes("/downloads/")) return "downloads";
    if (normalized.includes("/library/")) return "library";
    return "other";
  }

  function getFilename(filePath: string | null | undefined): string {
    if (!filePath) return "Unknown file";
    const normalized = String(filePath).replace(/\\/g, "/");
    const parts = normalized.split("/");
    return parts[parts.length - 1] || normalized;
  }

  function getProposedArtist(task: any): string {
    return task?.detected_metadata?.artist || task?.proposed_metadata?.artist || "Unknown Artist";
  }

  function getProposedTitle(task: any): string {
    return task?.detected_metadata?.title || task?.proposed_metadata?.title || "Unknown Title";
  }

  function getReadableSyncLabel(task: any): string {
    const rawSyncId = task?.sync_id;
    if (!rawSyncId) return "";
    try {
      if (typeof rawSyncId !== "string") return String(rawSyncId);
      if (rawSyncId.startsWith("ss:track:meta:")) {
        const b64 = rawSyncId.split("?")[0].replace("ss:track:meta:", "");
        const jsonStr = atob(b64);
        const data = JSON.parse(jsonStr);
        return `${data.artist} - ${data.title}`;
      }
      if (rawSyncId.startsWith("ss:track:acoustid:")) {
        return `AcoustID: ${rawSyncId.replace("ss:track:acoustid:", "").split("?")[0]}`;
      }
    } catch {}
    return rawSyncId;
  }

  $: counts = {
    all: tasks.length,
    high: tasks.filter((t) => getConfidenceTier(t.confidence_score) === "high").length,
    medium: tasks.filter((t) => getConfidenceTier(t.confidence_score) === "medium").length,
    low: tasks.filter((t) => getConfidenceTier(t.confidence_score) === "low").length,
  };

  $: filteredTasks = tasks
    .filter((task) => {
      if (confidenceFilter !== "all" && getConfidenceTier(task.confidence_score) !== confidenceFilter) {
        return false;
      }
      if (sourceFilter !== "all" && getSourceBucket(task.file_path) !== sourceFilter) {
        return false;
      }
      const q = searchQuery.trim().toLowerCase();
      if (q) {
        const haystack = [
          getFilename(task.file_path),
          task.file_path || "",
          getProposedArtist(task),
          getProposedTitle(task),
        ]
          .join(" ")
          .toLowerCase();
        if (!haystack.includes(q)) return false;
      }
      return true;
    })
    .sort((a, b) => {
      const ca = Number(a.confidence_score || 0);
      const cb = Number(b.confidence_score || 0);
      const na = getFilename(a.file_path).toLowerCase();
      const nb = getFilename(b.file_path).toLowerCase();
      const ta = new Date(a.updated_at || a.created_at || 0).getTime() || Number(a.id || 0);
      const tb = new Date(b.updated_at || b.created_at || 0).getTime() || Number(b.id || 0);

      switch (sortBy) {
        case "conf_desc":
          return cb - ca || na.localeCompare(nb);
        case "conf_asc":
          return ca - cb || na.localeCompare(nb);
        case "name_asc":
          return na.localeCompare(nb);
        case "name_desc":
          return nb.localeCompare(na);
        case "newest":
          return tb - ta;
        case "oldest":
          return ta - tb;
        default:
          return 0;
      }
    });

  $: hasActiveFilters =
    searchQuery.trim().length > 0 || confidenceFilter !== "all" || sourceFilter !== "all";

  function clearFilters() {
    searchQuery = "";
    confidenceFilter = "all";
    sourceFilter = "all";
  }

  async function retryAllPending() {
    if (retryingQueue) return;
    retryingQueue = true;
    try {
      await apiClient.post("/system/jobs/run", {
        name: "retry_aged_review_tasks",
        job_name: "retry_aged_review_tasks",
        params: { force_check: true },
      });
      setTimeout(() => {
        loadQueue();
      }, 1500);
    } catch (err: any) {
      console.error("Failed to trigger retry job:", err);
      error =
        err?.response?.data?.error ||
        err?.message ||
        "Failed to trigger retry job";
    } finally {
      retryingQueue = false;
    }
  }

  function openReviewModal(task: any) {
    selectedTask = task;
    showReviewModal = true;
  }

  function setRowState(taskId: number, state: string) {
    if (!taskId) return;
    rowActionState = {
      ...rowActionState,
      [taskId]: state,
    };
  }

  function clearRowState(taskId: number) {
    if (!taskId) return;
    const next = { ...rowActionState };
    delete next[taskId];
    rowActionState = next;
  }

  function getStateLabel(state: string) {
    if (state === "approving") return "Approving...";
    if (state === "saving") return "Saving...";
    if (state === "saved") return "Saved";
    return "";
  }

  function closeReviewModal() {
    showReviewModal = false;
    selectedTask = null;
  }

  async function handleModalSaveDraft(e: any) {
    const { proposedMetadata, item } = e.detail || {};
    if (!item) return;
    const taskId = item.id;

    setRowState(taskId, "saving");
    try {
      const payload = { ...item.proposed_metadata, ...proposedMetadata };
      await apiClient.put(`/core/metadata_review/${taskId}`, payload);

      tasks = tasks.map((task) =>
        task.id === taskId
          ? {
              ...task,
              detected_metadata: { ...payload },
              proposed_metadata: { ...payload },
            }
          : task,
      );

      setRowState(taskId, "saved");
      setTimeout(() => clearRowState(taskId), 1200);
    } catch (err) {
      console.error("Failed to save draft:", err);
      clearRowState(taskId);
    }
  }

  async function handleModalApprove(e: any) {
    const { item } = e.detail || {};
    const taskId = item?.id || selectedTask?.id;
    if (!taskId) return;

    tasks = tasks.filter((t) => t.id !== taskId);
    clearRowState(taskId);
    closeReviewModal();
  }

  async function handleModalReject(e: any) {
    const { item } = e.detail || {};
    const taskId = item?.id || selectedTask?.id;
    if (!taskId) return;

    tasks = tasks.filter((t) => t.id !== taskId);
    clearRowState(taskId);
    closeReviewModal();
  }

  async function loadQueue() {
    loading = true;
    error = "";
    try {
      const response = await apiClient.get("/core/metadata_review");
      tasks = Array.isArray(response.data?.tasks) ? response.data.tasks : [];
    } catch (err: any) {
      console.error("Failed to load review queue:", err);
      error =
        err?.response?.data?.error ||
        err?.message ||
        "Failed to load review queue";
    } finally {
      loading = false;
    }
  }

  onMount(loadQueue);
</script>

<div class="flex flex-col h-full min-h-0 bg-background">
  <!-- Header -->
  <div class="flex flex-wrap items-center justify-between gap-4 px-5 pt-5 pb-3">
    <div>
      <p class="text-[11px] uppercase tracking-widest text-teal-400/90 font-semibold">
        Metadata Workflow
      </p>
      <div class="flex items-center gap-2.5 mt-0.5">
        <h2 class="text-2xl font-bold text-slate-50 m-0 tracking-tight">Review Queue</h2>
        <span class="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-slate-800/90 text-slate-300 border border-white/[0.08]">
          {filteredTasks.length}{hasActiveFilters ? ` / ${tasks.length}` : ""}
        </span>
      </div>
    </div>

    <div class="flex items-center gap-2">
      <button
        type="button"
        class="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-teal-500 hover:bg-teal-400 text-slate-950 transition-all active:scale-95 disabled:opacity-50 shadow-sm shadow-teal-500/20"
        on:click={retryAllPending}
        disabled={retryingQueue || loading}
      >
        <RotateCcw class="w-3.5 h-3.5 {retryingQueue ? 'animate-spin' : ''}" />
        {retryingQueue ? "Triggering..." : "Retry All Pending"}
      </button>
      <button
        type="button"
        class="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-slate-800/80 hover:bg-slate-700/80 text-slate-200 border border-white/[0.08] transition-all active:scale-95 disabled:opacity-50"
        on:click={loadQueue}
        disabled={loading}
      >
        <RefreshCw class="w-3.5 h-3.5 {loading ? 'animate-spin' : ''}" />
        {loading ? "Refreshing..." : "Refresh"}
      </button>
    </div>
  </div>

  <!-- Filter & Sort Toolbar -->
  <div class="mx-5 mb-3 p-3 rounded-xl bg-slate-900/75 backdrop-blur-md border border-white/[0.08] flex flex-col gap-3">
    <div class="flex flex-wrap items-center gap-2.5">
      <!-- Search input -->
      <div class="relative flex-1 min-w-[220px]">
        <Search class="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
        <input
          type="text"
          bind:value={searchQuery}
          placeholder="Filter by filename, path, artist, or title..."
          class="w-full pl-9 pr-8 py-2 bg-slate-950/90 border border-white/10 rounded-lg text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-teal-500/40 focus:border-teal-500/60"
        />
        {#if searchQuery}
          <button
            type="button"
            aria-label="Clear search"
            class="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
            on:click={() => (searchQuery = "")}
          >
            <X class="w-3.5 h-3.5" />
          </button>
        {/if}
      </div>

      <!-- Source filter -->
      <div class="inline-flex items-center rounded-lg bg-slate-950/80 p-0.5 border border-white/[0.08]">
        {#each [
          { id: "all", label: "All Sources" },
          { id: "downloads", label: "Downloads" },
          { id: "library", label: "Library" }
        ] as src}
          <button
            type="button"
            class="px-2.5 py-1.5 rounded-md text-[11px] font-semibold transition-all {sourceFilter === src.id
              ? 'bg-slate-800 text-teal-300 shadow-sm'
              : 'text-slate-400 hover:text-slate-200'}"
            on:click={() => (sourceFilter = src.id as any)}
          >
            {src.label}
          </button>
        {/each}
      </div>

      <!-- Sort dropdown -->
      <div class="inline-flex items-center gap-1.5 bg-slate-950/80 border border-white/10 rounded-lg px-2.5 py-1.5">
        <ArrowUpDown class="w-3.5 h-3.5 text-slate-400 shrink-0" />
        <select
          aria-label="Sort review queue"
          bind:value={sortBy}
          class="bg-transparent text-xs font-medium text-slate-200 focus:outline-none cursor-pointer"
        >
          <option value="conf_desc" class="bg-slate-900 text-slate-100">Confidence: High → Low</option>
          <option value="conf_asc" class="bg-slate-900 text-slate-100">Confidence: Low → High</option>
          <option value="name_asc" class="bg-slate-900 text-slate-100">Filename: A → Z</option>
          <option value="name_desc" class="bg-slate-900 text-slate-100">Filename: Z → A</option>
          <option value="newest" class="bg-slate-900 text-slate-100">Newest First</option>
          <option value="oldest" class="bg-slate-900 text-slate-100">Oldest First</option>
        </select>
      </div>
    </div>

    <!-- Confidence Tier Pills -->
    <div class="flex flex-wrap items-center justify-between gap-2">
      <div class="flex flex-wrap items-center gap-1.5">
        <button
          type="button"
          class="px-2.5 py-1 rounded-full text-[11px] font-semibold border transition-all {confidenceFilter === 'all'
            ? 'bg-teal-500/20 text-teal-200 border-teal-400/50'
            : 'bg-slate-950/60 text-slate-400 border-white/[0.08] hover:text-slate-200'}"
          on:click={() => (confidenceFilter = "all")}
        >
          All <span class="opacity-75 ml-0.5">({counts.all})</span>
        </button>

        <button
          type="button"
          class="px-2.5 py-1 rounded-full text-[11px] font-semibold border transition-all {confidenceFilter === 'high'
            ? 'bg-emerald-500/20 text-emerald-200 border-emerald-400/50'
            : 'bg-emerald-500/5 text-emerald-300/80 border-emerald-500/20 hover:bg-emerald-500/15'}"
          on:click={() => (confidenceFilter = "high")}
        >
          High ≥85% <span class="opacity-80 ml-0.5">({counts.high})</span>
        </button>

        <button
          type="button"
          class="px-2.5 py-1 rounded-full text-[11px] font-semibold border transition-all {confidenceFilter === 'medium'
            ? 'bg-amber-500/20 text-amber-200 border-amber-400/50'
            : 'bg-amber-500/5 text-amber-300/80 border-amber-500/20 hover:bg-amber-500/15'}"
          on:click={() => (confidenceFilter = "medium")}
        >
          Medium 60–84% <span class="opacity-80 ml-0.5">({counts.medium})</span>
        </button>

        <button
          type="button"
          class="px-2.5 py-1 rounded-full text-[11px] font-semibold border transition-all {confidenceFilter === 'low'
            ? 'bg-rose-500/20 text-rose-200 border-rose-400/50'
            : 'bg-rose-500/5 text-rose-300/80 border-rose-500/20 hover:bg-rose-500/15'}"
          on:click={() => (confidenceFilter = "low")}
        >
          Low &lt;60% <span class="opacity-80 ml-0.5">({counts.low})</span>
        </button>
      </div>

      {#if hasActiveFilters}
        <button
          type="button"
          class="inline-flex items-center gap-1 text-[11px] font-medium text-slate-400 hover:text-teal-300 transition-colors"
          on:click={clearFilters}
        >
          <X class="w-3 h-3" />
          Reset filters
        </button>
      {/if}
    </div>
  </div>

  <!-- Table Container -->
  <div
    class="mx-5 mb-5 flex-1 min-h-0 overflow-y-auto rounded-xl bg-slate-900/60 backdrop-blur-md border border-white/[0.08]"
  >
    {#if loading}
      <div class="p-10 text-center text-sm text-slate-400">Loading review queue...</div>
    {:else if error}
      <div class="p-8 text-center text-sm text-rose-300 bg-rose-500/10 border-b border-rose-500/20">{error}</div>
    {:else if tasks.length === 0}
      <div class="p-10 text-center text-sm text-slate-400 italic">
        No pending metadata review tasks.
      </div>
    {:else if filteredTasks.length === 0}
      <div class="p-10 text-center">
        <p class="text-sm text-slate-300 font-medium">No tasks match your active filters.</p>
        <button
          type="button"
          class="mt-2 text-xs font-semibold text-teal-400 hover:text-teal-300"
          on:click={clearFilters}
        >
          Reset all filters
        </button>
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="min-w-full text-left border-collapse">
          <thead class="bg-slate-950/70 sticky top-0 z-10">
            <tr
              class="text-slate-400 text-[11px] uppercase tracking-wider border-b border-white/[0.08]"
            >
              <th class="px-4 py-3 font-semibold">File</th>
              <th class="px-4 py-3 font-semibold">Proposed Artist / Title</th>
              <th class="px-4 py-3 font-semibold">Confidence</th>
              <th class="px-4 py-3 font-semibold text-right">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-white/[0.05] bg-transparent">
            {#each filteredTasks as task (task.id)}
              {@const tier = getConfidenceTier(task.confidence_score)}
              {@const srcBucket = getSourceBucket(task.file_path)}
              <tr class="hover:bg-slate-800/45 transition-colors">
                <td class="px-4 py-3">
                  <div class="flex items-center gap-2">
                    <FileAudio class="w-4 h-4 text-teal-400/70 shrink-0" />
                    <span class="text-sm text-slate-100 font-medium truncate max-w-md" title={getFilename(task.file_path)}>
                      {getFilename(task.file_path)}
                    </span>
                    {#if srcBucket === "downloads"}
                      <span class="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-sky-500/15 text-sky-300 border border-sky-500/25 shrink-0">
                        Downloads
                      </span>
                    {:else if srcBucket === "library"}
                      <span class="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-indigo-500/15 text-indigo-300 border border-indigo-500/25 shrink-0">
                        Library
                      </span>
                    {/if}
                  </div>
                  <div class="text-xs text-slate-500 truncate max-w-md mt-0.5 pl-6" title={task.file_path}>
                    {task.file_path}
                  </div>
                </td>

                <td class="px-4 py-3">
                  <div class="text-sm text-slate-200 font-medium">
                    {getProposedArtist(task)}
                  </div>
                  <div class="text-xs text-slate-400 mt-0.5">
                    {getProposedTitle(task)}
                  </div>
                  {#if task?.sync_id}
                    <div
                      class="text-[11px] text-teal-400/80 truncate max-w-xs mt-1"
                      title={task.sync_id}
                    >
                      {getReadableSyncLabel(task)}
                    </div>
                  {/if}
                </td>

                <td class="px-4 py-3">
                  <span
                    class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border {tier === 'high'
                      ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/35'
                      : tier === 'medium'
                        ? 'bg-amber-500/15 text-amber-300 border-amber-500/35'
                        : 'bg-rose-500/15 text-rose-300 border-rose-500/35'}"
                  >
                    <span
                      class="w-1.5 h-1.5 rounded-full {tier === 'high'
                        ? 'bg-emerald-400'
                        : tier === 'medium'
                          ? 'bg-amber-400'
                          : 'bg-rose-400'}"
                    ></span>
                    {tier === "high" ? "High" : tier === "medium" ? "Medium" : "Low"}
                    <span class="opacity-85 tabular-nums">
                      {Math.round((task.confidence_score || 0) * 100)}%
                    </span>
                  </span>
                </td>

                <td class="px-4 py-3 text-right">
                  <div class="inline-flex items-center gap-2 justify-end w-full">
                    {#if rowActionState[task.id]}
                      <span
                        class="inline-flex items-center px-2 py-1 rounded-full text-xs font-semibold bg-slate-800 border border-white/10 text-teal-300"
                      >
                        {getStateLabel(rowActionState[task.id])}
                      </span>
                    {/if}
                    <button
                      type="button"
                      class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-teal-500/15 hover:bg-teal-500/25 text-teal-200 border border-teal-500/30 transition-all active:scale-95"
                      on:click={() => openReviewModal(task)}
                    >
                      <SlidersHorizontal class="w-3.5 h-3.5" />
                      Review &amp; Edit
                    </button>
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </div>
</div>

{#if showReviewModal && selectedTask}
  <MetadataReviewModal
    task={selectedTask}
    on:close={() => closeReviewModal()}
    on:saved={(e) =>
      handleModalSaveDraft({
        detail: {
          proposedMetadata: e.detail?.metadata || e.detail?.proposedMetadata,
          item: selectedTask,
        },
      })}
    on:approved={(e) =>
      handleModalApprove({
        detail: {
          proposedMetadata: e.detail?.metadata || e.detail?.proposedMetadata,
          item: selectedTask,
        },
      })}
    on:rejected={(e) => handleModalReject({ detail: { item: selectedTask } })}
  />
{/if}
