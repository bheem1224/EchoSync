<script>
  import { onMount, onDestroy } from "svelte";
  import apiClient from "../../../api/client";
  import { feedback } from "../../../stores/feedback";

  let logs = $state([]);
  let availableFiles = $state([]);
  let activeFile = $state("");
  let selectedSource = $state("app.log");
  let selectedLevels = $state(new Set(["INFO", "WARNING", "ERROR", "CRITICAL"]));
  let levelCounts = $state({ VERBOSE: 0, DEBUG: 0, INFO: 0, WARNING: 0, ERROR: 0, CRITICAL: 0 });
  let totalEntries = $state(0);
  let filteredEntries = $state(0);
  let logDir = $state("");

  let loggerFilter = $state("");
  let searchQuery = $state("");
  let useRegex = $state(false);
  let limit = $state(300);
  let newestFirst = $state(true);
  let autoRefresh = $state(true);
  let loading = $state(true);
  let errorMsg = $state("");
  let expandedLines = $state(new Set());

  let pollTimer = null;
  let searchDebounce = null;

  const LEVELS = ["VERBOSE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"];

  function levelBadgeStyle(lvl) {
    switch (lvl) {
      case "CRITICAL":
      case "ERROR":
        return "background: rgba(239, 68, 68, 0.16); color: #f87171; border-color: rgba(239, 68, 68, 0.35);";
      case "WARNING":
        return "background: rgba(245, 158, 11, 0.16); color: #fbbf24; border-color: rgba(245, 158, 11, 0.35);";
      case "INFO":
        return "background: rgba(20, 184, 166, 0.16); color: var(--color-primary, #14b8a6); border-color: rgba(20, 184, 166, 0.35);";
      case "DEBUG":
        return "background: rgba(59, 130, 246, 0.16); color: #60a5fa; border-color: rgba(59, 130, 246, 0.35);";
      default:
        return "background: rgba(148, 163, 184, 0.14); color: var(--text-secondary, #94a3b8); border-color: var(--border-subtle);";
    }
  }

  async function fetchLogs(silent = false) {
    if (!silent) loading = true;
    errorMsg = "";
    try {
      const params = new URLSearchParams();
      if (selectedSource) params.set("source", selectedSource);
      if (selectedLevels.size > 0 && selectedLevels.size < LEVELS.length) {
        params.set("level", Array.from(selectedLevels).join(","));
      }
      if (loggerFilter.trim()) params.set("logger_name", loggerFilter.trim());
      if (searchQuery.trim()) params.set("search", searchQuery.trim());
      if (useRegex) params.set("regex", "true");
      params.set("limit", String(limit));

      const res = await apiClient.get(`/system/logs?${params.toString()}`);
      const data = res.data || {};
      const incoming = Array.isArray(data.logs) ? data.logs : [];
      logs = newestFirst ? [...incoming].reverse() : incoming;
      availableFiles = data.available_files || [];
      activeFile = data.active_file || "";
      if (activeFile && !selectedSource) {
        selectedSource = activeFile;
      }
      levelCounts = data.level_counts || levelCounts;
      totalEntries = data.total_entries ?? incoming.length;
      filteredEntries = data.filtered_entries ?? incoming.length;
      logDir = data.log_dir || "";
    } catch (err) {
      errorMsg = err?.response?.data?.detail || err?.message || "Failed to fetch logs";
    } finally {
      loading = false;
    }
  }

  function toggleLevel(lvl) {
    const next = new Set(selectedLevels);
    if (next.has(lvl)) {
      next.delete(lvl);
    } else {
      next.add(lvl);
    }
    selectedLevels = next;
    fetchLogs();
  }

  function selectAllLevels() {
    selectedLevels = new Set(LEVELS);
    fetchLogs();
  }

  function toggleExpand(key) {
    const next = new Set(expandedLines);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    expandedLines = next;
  }

  function scheduleSearch() {
    clearTimeout(searchDebounce);
    searchDebounce = setTimeout(() => fetchLogs(), 220);
  }

  function handleSourceChange(e) {
    selectedSource = e.target.value;
    if (selectedSource === "debug.log" || selectedSource === "echosync-verbose.log") {
      selectedLevels = new Set(LEVELS);
    }
    fetchLogs();
  }

  function toggleOrder() {
    newestFirst = !newestFirst;
    logs = [...logs].reverse();
  }

  async function copyFilteredLogs() {
    const text = logs
      .map((entry) => {
        const header = `${entry.timestamp} - ${entry.logger} - ${entry.level}${entry.location ? ` - ${entry.location}` : ""} - ${entry.message}`;
        return entry.details ? `${header}\n${entry.details}` : header;
      })
      .join("\n");
    try {
      await navigator.clipboard.writeText(text);
      feedback.addToast(`Copied ${logs.length} log entries`, "success");
    } catch {
      feedback.addToast("Failed to copy logs to clipboard", "error");
    }
  }

  function downloadLogFile() {
    const src = encodeURIComponent(selectedSource || activeFile || "app.log");
    window.open(`/api/v1/system/logs/download?source=${src}`, "_blank");
  }

  function startPolling() {
    stopPolling();
    if (autoRefresh) {
      pollTimer = setInterval(() => fetchLogs(true), 2500);
    }
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  $effect(() => {
    if (autoRefresh) {
      startPolling();
    } else {
      stopPolling();
    }
    return () => stopPolling();
  });

  onMount(() => {
    fetchLogs();
  });

  onDestroy(() => {
    stopPolling();
    clearTimeout(searchDebounce);
  });
</script>

<svelte:head>
  <title>Logs • EchoSync</title>
</svelte:head>

<div class="logs-page">
  <header class="logs-header">
    <div>
      <p class="eyebrow">System Diagnostics</p>
      <h1>Application Logs</h1>
      {#if logDir}
        <p class="sub-meta">
          Source: <code>{activeFile || selectedSource}</code> in <code>{logDir}</code>
          • Showing <strong>{logs.length}</strong> of {filteredEntries} matched ({totalEntries} parsed)
        </p>
      {/if}
    </div>

    <div class="header-actions">
      <button
        type="button"
        class="action-btn"
        class:active={autoRefresh}
        onclick={() => (autoRefresh = !autoRefresh)}
        aria-label={autoRefresh ? "Pause live log tail" : "Resume live log tail"}
      >
        {autoRefresh ? "● Live Tail (2.5s)" : "❚❚ Paused"}
      </button>

      <button type="button" class="action-btn" onclick={toggleOrder}>
        {newestFirst ? "↓ Newest First" : "↑ Oldest First"}
      </button>

      <button type="button" class="action-btn" onclick={() => fetchLogs()}>
        ↻ Refresh
      </button>

      <button type="button" class="action-btn" onclick={copyFilteredLogs} disabled={logs.length === 0}>
        Copy View
      </button>

      <button type="button" class="action-btn primary" onclick={downloadLogFile} disabled={!activeFile}>
        Download .log
      </button>
    </div>
  </header>

  <section class="toolbar-card">
    <div class="toolbar-row">
      <label class="control-group">
        <span class="control-label">Log File</span>
        <select
          class="control-select"
          value={selectedSource}
          onchange={handleSourceChange}
          aria-label="Select log file"
        >
          {#if availableFiles.length === 0}
            <option value="app.log">app.log</option>
          {:else}
            {#each availableFiles as file (file)}
              <option value={file}>{file}</option>
            {/each}
          {/if}
        </select>
      </label>

      <label class="control-group flex-1">
        <span class="control-label">Search Message / Stack</span>
        <div class="search-wrap">
          <input
            type="text"
            class="control-input"
            placeholder="Filter by text, error, track, plugin..."
            bind:value={searchQuery}
            oninput={scheduleSearch}
            aria-label="Search logs"
          />
          <button
            type="button"
            class="regex-toggle"
            class:active={useRegex}
            onclick={() => {
              useRegex = !useRegex;
              fetchLogs();
            }}
            title="Toggle Regular Expression search"
            aria-label="Toggle regex search"
          >
            .*
          </button>
        </div>
      </label>

      <label class="control-group">
        <span class="control-label">Logger</span>
        <input
          type="text"
          class="control-input"
          placeholder="e.g. plex_routes"
          bind:value={loggerFilter}
          oninput={scheduleSearch}
          aria-label="Filter by logger name"
        />
      </label>

      <label class="control-group">
        <span class="control-label">Limit</span>
        <select
          class="control-select"
          bind:value={limit}
          onchange={() => fetchLogs()}
          aria-label="Maximum log lines"
        >
          <option value={200}>200 lines</option>
          <option value={300}>300 lines</option>
          <option value={500}>500 lines</option>
          <option value={1000}>1000 lines</option>
          <option value={2000}>2000 lines</option>
        </select>
      </label>
    </div>

    <div class="level-pills">
      <button
        type="button"
        class="level-pill"
        class:active={selectedLevels.size === LEVELS.length}
        onclick={selectAllLevels}
      >
        ALL ({totalEntries})
      </button>
      {#each LEVELS as lvl (lvl)}
        <button
          type="button"
          class="level-pill"
          class:active={selectedLevels.has(lvl)}
          style={selectedLevels.has(lvl) ? levelBadgeStyle(lvl) : ""}
          onclick={() => toggleLevel(lvl)}
        >
          {lvl} ({levelCounts[lvl] || 0})
        </button>
      {/each}

      {#if loggerFilter || searchQuery}
        <button
          type="button"
          class="clear-filters-btn"
          onclick={() => {
            loggerFilter = "";
            searchQuery = "";
            fetchLogs();
          }}
        >
          Clear Filters ✕
        </button>
      {/if}
    </div>
  </section>

  {#if errorMsg}
    <div class="error-banner" role="alert">
      ⚠ {errorMsg}
    </div>
  {/if}

  <section class="log-stream-card">
    {#if loading && logs.length === 0}
      <div class="empty-state">Loading application logs...</div>
    {:else if logs.length === 0}
      <div class="empty-state">
        No log entries match the current filters.
      </div>
    {:else}
      <div class="log-list" role="log" aria-live="off">
        {#each logs as entry (`${entry.line}-${entry.timestamp}`)}
          {@const entryKey = `${entry.line}-${entry.timestamp}`}
          {@const isExpanded = expandedLines.has(entryKey)}
          <div class="log-entry" class:has-details={Boolean(entry.details)}>
            <div class="log-main">
              <span class="log-ts">{entry.timestamp || "—"}</span>
              <span class="log-level" style={levelBadgeStyle(entry.level)}>
                {entry.level}
              </span>
              <button
                type="button"
                class="log-logger"
                title="Click to filter by this logger"
                onclick={() => {
                  loggerFilter = entry.logger;
                  fetchLogs();
                }}
              >
                {entry.logger}
              </button>
              <span class="log-msg">{entry.message}</span>
              {#if entry.location}
                <span class="log-loc">{entry.location}</span>
              {/if}
              {#if entry.details}
                <button
                  type="button"
                  class="details-toggle"
                  onclick={() => toggleExpand(entryKey)}
                  aria-label={isExpanded ? "Collapse stack trace" : "Expand stack trace"}
                >
                  {isExpanded ? "Hide Trace ▴" : "Stack Trace ▾"}
                </button>
              {/if}
            </div>
            {#if entry.details && isExpanded}
              <pre class="log-details">{entry.details}</pre>
            {/if}
          </div>
        {/each}
      </div>
    {/if}
  </section>
</div>

<style>
  .logs-page {
    padding: 24px;
    max-width: 1500px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 16px;
    color: var(--text-primary, #f8fafc);
  }

  .logs-header {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: flex-end;
    gap: 16px;
  }

  .eyebrow {
    margin: 0 0 4px;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--color-primary, #14b8a6);
  }

  h1 {
    margin: 0;
    font-size: 26px;
    font-weight: 800;
  }

  .sub-meta {
    margin: 6px 0 0;
    font-size: 12px;
    color: var(--text-secondary, #94a3b8);
  }

  .sub-meta code {
    background: var(--bg-surface-elevated, rgba(255, 255, 255, 0.06));
    padding: 2px 6px;
    border-radius: 5px;
    font-size: 11px;
  }

  .header-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .action-btn {
    padding: 8px 13px;
    border-radius: 9px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    background: var(--bg-surface-elevated, rgba(255, 255, 255, 0.06));
    border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.1));
    color: var(--text-primary, #f8fafc);
    transition: all 0.15s ease;
  }

  .action-btn:hover:not(:disabled) {
    border-color: var(--color-primary, #14b8a6);
  }

  .action-btn:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .action-btn.active {
    background: rgba(20, 184, 166, 0.15);
    border-color: rgba(20, 184, 166, 0.45);
    color: var(--color-primary, #14b8a6);
  }

  .action-btn.primary {
    background: var(--color-primary, #14b8a6);
    color: #020617;
    border-color: transparent;
    font-weight: 700;
  }

  .toolbar-card {
    background: var(--bg-surface, rgba(15, 23, 42, 0.8));
    border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
    border-radius: 14px;
    padding: 14px 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .toolbar-row {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    align-items: flex-end;
  }

  .control-group {
    display: flex;
    flex-direction: column;
    gap: 5px;
    min-width: 150px;
  }

  .control-group.flex-1 {
    flex: 1 1 260px;
    min-width: 220px;
  }

  .control-label {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-secondary, #94a3b8);
  }

  .control-input,
  .control-select {
    padding: 8px 11px;
    border-radius: 8px;
    background: var(--bg-input, rgba(2, 6, 23, 0.6));
    border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.1));
    color: var(--text-primary, #f8fafc);
    font-size: 13px;
    box-sizing: border-box;
    width: 100%;
  }

  .control-input:focus,
  .control-select:focus {
    outline: none;
    border-color: var(--color-primary, #14b8a6);
  }

  .search-wrap {
    display: flex;
    gap: 6px;
    align-items: center;
  }

  .regex-toggle {
    padding: 8px 10px;
    border-radius: 8px;
    font-family: monospace;
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
    background: var(--bg-surface-elevated, rgba(255, 255, 255, 0.05));
    border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.1));
    color: var(--text-secondary, #94a3b8);
  }

  .regex-toggle.active {
    background: rgba(20, 184, 166, 0.18);
    border-color: var(--color-primary, #14b8a6);
    color: var(--color-primary, #14b8a6);
  }

  .level-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
  }

  .level-pill {
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
    background: var(--bg-surface-elevated, rgba(255, 255, 255, 0.04));
    border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
    color: var(--text-secondary, #94a3b8);
    transition: all 0.15s ease;
  }

  .level-pill.active {
    border-color: var(--color-primary, #14b8a6);
    color: var(--text-primary, #f8fafc);
  }

  .clear-filters-btn {
    margin-left: auto;
    padding: 4px 10px;
    border-radius: 8px;
    font-size: 11px;
    font-weight: 600;
    background: rgba(239, 68, 68, 0.12);
    border: 1px solid rgba(239, 68, 68, 0.3);
    color: #f87171;
    cursor: pointer;
  }

  .error-banner {
    padding: 10px 14px;
    border-radius: 10px;
    background: rgba(239, 68, 68, 0.12);
    border: 1px solid rgba(239, 68, 68, 0.35);
    color: #fca5a5;
    font-size: 13px;
  }

  .log-stream-card {
    background: var(--bg-surface, rgba(15, 23, 42, 0.85));
    border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
    border-radius: 14px;
    overflow: hidden;
  }

  .empty-state {
    padding: 40px 20px;
    text-align: center;
    color: var(--text-secondary, #94a3b8);
    font-size: 13px;
  }

  .log-list {
    max-height: 68vh;
    overflow-y: auto;
    font-family: "JetBrains Mono", "Fira Code", ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 12px;
    line-height: 1.5;
  }

  .log-entry {
    border-bottom: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.05));
    padding: 6px 12px;
  }

  .log-entry:hover {
    background: rgba(255, 255, 255, 0.03);
  }

  .log-main {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 8px;
  }

  .log-ts {
    color: var(--text-muted, #64748b);
    font-size: 11px;
    flex-shrink: 0;
  }

  .log-level {
    font-size: 10px;
    font-weight: 800;
    padding: 1px 6px;
    border-radius: 4px;
    border: 1px solid transparent;
    flex-shrink: 0;
  }

  .log-logger {
    background: var(--bg-surface-elevated, rgba(255, 255, 255, 0.06));
    border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
    color: var(--text-secondary, #cbd5e1);
    border-radius: 4px;
    padding: 0 6px;
    font-size: 11px;
    cursor: pointer;
    flex-shrink: 0;
  }

  .log-logger:hover {
    border-color: var(--color-primary, #14b8a6);
    color: var(--color-primary, #14b8a6);
  }

  .log-msg {
    color: var(--text-primary, #f1f5f9);
    word-break: break-word;
    flex: 1 1 300px;
  }

  .log-loc {
    color: var(--text-muted, #64748b);
    font-size: 11px;
    margin-left: auto;
  }

  .details-toggle {
    background: none;
    border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.14));
    color: var(--color-primary, #14b8a6);
    border-radius: 4px;
    padding: 1px 6px;
    font-size: 10px;
    font-weight: 700;
    cursor: pointer;
  }

  .log-details {
    margin: 8px 0 4px;
    padding: 10px 12px;
    border-radius: 8px;
    background: rgba(2, 6, 23, 0.75);
    border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
    color: #fca5a5;
    overflow-x: auto;
    white-space: pre-wrap;
    font-size: 11px;
  }
</style>
