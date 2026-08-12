<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import {
    fetchProcesses,
    killProcess,
    type ProcessOwner,
    type ProcessListResponse
  } from '../../api/systemTasks';

  interface RichProcess extends ProcessOwner {
    registration_id: string;
    parent_id?: string;
    category: string;
    is_killable: boolean;
    cpu_percent: number;
    memory_bytes: number;
    wasm_instance_id?: string;
  }

  let processes: RichProcess[] = [];
  let processesByCategory: Record<string, RichProcess[]> = {};
  let total = 0;
  let loading = true;
  let error = '';
  let lastFetched: Date | null = null;
  let eventSource: EventSource | null = null;

  // Per-row kill state: 'idle' | 'confirming' | 'killing' | 'done'
  let killState: Record<string, 'idle' | 'confirming' | 'killing' | 'done'> = {};
  let killError: Record<string, string> = {};

  function connectStream() {
    loading = true;
    eventSource = new EventSource('/api/v1/system/tasks/processes/stream');
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        processes = data.processes || [];
        total = data.total || 0;
        lastFetched = new Date();
        error = '';
        loading = false;
        
        processesByCategory = processes.reduce((acc, p) => {
          const cat = p.category || 'Worker Thread';
          if (!acc[cat]) acc[cat] = [];
          acc[cat].push(p);
          return acc;
        }, {} as Record<string, RichProcess[]>);
      } catch (err) {
        console.error("Failed to parse SSE", err);
      }
    };
    eventSource.onerror = () => {
      error = "Connection lost. Reconnecting...";
      loading = false;
    };
  }

  function startKill(regId: string) {
    killState = { ...killState, [regId]: 'confirming' };
  }

  function cancelKill(regId: string) {
    killState = { ...killState, [regId]: 'idle' };
  }

  async function confirmKill(regId: string) {
    killState = { ...killState, [regId]: 'killing' };
    killError = { ...killError, [regId]: '' };
    try {
      await killProcess(regId);
      killState = { ...killState, [regId]: 'done' };
    } catch (err: any) {
      killError = {
        ...killError,
        [regId]: err?.response?.data?.detail ?? err?.message ?? 'Kill failed'
      };
      killState = { ...killState, [regId]: 'idle' };
    }
  }

  function formatDuration(started_at: string): string {
    if (!started_at) return '—';
    const delta = (Date.now() - new Date(started_at).getTime()) / 1000;
    if (delta < 60) return `${Math.round(delta)}s`;
    if (delta < 3600) return `${Math.floor(delta / 60)}m ${Math.round(delta % 60)}s`;
    return `${Math.floor(delta / 3600)}h ${Math.floor((delta % 3600) / 60)}m`;
  }

  function formatBytes(bytes: number) {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  function ownerTypeBadgeClass(type: string): string {
    switch (type) {
      case 'plugin':     return 'badge-plugin';
      case 'core':       return 'badge-core';
      case 'system_job': return 'badge-system';
      default:           return 'badge-unknown';
    }
  }

  onMount(() => {
    connectStream();
  });

  onDestroy(() => {
    if (eventSource) {
      eventSource.close();
    }
  });
</script>

<div class="supervisor-card">
  <!-- ── Header ── -->
  <div class="supervisor-header">
    <div class="header-left">
      <h3 class="card-title">Process Supervisor</h3>
      <span class="count-badge">{total} Active Registered</span>
    </div>
    <div class="header-right">
      {#if lastFetched}
        <span class="last-fetched">Updated {lastFetched.toLocaleTimeString()}</span>
      {/if}
      <button class="refresh-btn" on:click={() => { if (eventSource) { eventSource.close(); connectStream(); } }} title="Reconnect Stream">
        <svg xmlns="http://www.w3.org/2000/svg" class="btn-icon" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="23 4 23 10 17 10" />
          <polyline points="1 20 1 14 7 14" />
          <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
        </svg>
        Reconnect
      </button>
    </div>
  </div>

  <!-- ── Error ── -->
  {#if error}
    <div class="error-bar">{error}</div>
  {/if}

  <!-- ── Loading ── -->
  {#if loading && processes.length === 0}
    <div class="skeleton-wrap">
      {#each [0, 1] as _}
        <div class="skeleton-row"></div>
      {/each}
    </div>

  <!-- ── Empty ── -->
  {:else if processes.length === 0}
    <div class="empty-state">
      <svg xmlns="http://www.w3.org/2000/svg" class="empty-icon" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
        <rect x="2" y="3" width="20" height="14" rx="2" />
        <line x1="8" y1="21" x2="16" y2="21" />
        <line x1="12" y1="17" x2="12" y2="21" />
      </svg>
      <p>No active worker processes or threads registered in supervisor.</p>
    </div>

  <!-- ── Table ── -->
  {:else}
    <div class="table-wrap">
      <table class="proc-table">
        <thead>
          <tr>
            <th>Task</th>
            <th>Owner</th>
            <th>Type</th>
            <th>PID / Thread</th>
            <th>Memory</th>
            <th>CPU</th>
            <th class="th-right">Action</th>
          </tr>
        </thead>
        <tbody>
          {#each Object.entries(processesByCategory) as [categoryName, categoryProcs]}
            <tr class="category-header">
              <td colspan="7">{categoryName}</td>
            </tr>
            {#each categoryProcs as proc (proc.registration_id ?? `${proc.owner_id}_${proc.pid}`)}
              {@const regId = proc.registration_id ?? proc.owner_id}
              {@const state = killState[regId] ?? 'idle'}
              {@const err   = killError[regId] ?? ''}
              <tr class="proc-row"
                class:row-killing={state === 'killing'}
                class:row-done={state === 'done'}>
  
                <!-- Task -->
                <td class="td-task">
                  <span class="task-name">{proc.task_name}</span>
                  {#if proc.wasm_instance_id}
                    <div class="wasm-id">WASM: {proc.wasm_instance_id.substring(0,8)}</div>
                  {/if}
                </td>
  
                <!-- Owner -->
                <td class="td-owner">
                  <span class="mono-sm">{proc.owner_id}</span>
                </td>
  
                <!-- Type -->
                <td>
                  <span class="type-badge {ownerTypeBadgeClass(proc.owner_type)}">
                    {proc.owner_type.replace('_', ' ')}
                  </span>
                </td>
  
                <!-- PID / Thread -->
                <td class="mono-sm td-dim">
                  {#if proc.pid}
                    PID: {proc.pid}
                  {/if}
                  {#if proc.thread_id}
                    <br/>TID: {proc.thread_id}
                  {/if}
                  {#if !proc.pid && !proc.thread_id}
                    —
                  {/if}
                </td>
  
                <!-- Memory -->
                <td class="mono-sm">{formatBytes(proc.memory_bytes)}</td>
  
                <!-- CPU -->
                <td class="mono-sm">{proc.cpu_percent.toFixed(1)}%</td>
  
                <!-- Kill action -->
                <td class="td-action">
                  {#if !proc.is_killable}
                    <span class="td-dim text-xs">Core Process</span>
                  {:else if state === 'idle'}
                    <button class="kill-btn"
                      on:click={() => startKill(regId)}
                      title="Safely kill and flush DB sessions">
                      Kill
                    </button>
  
                  {:else if state === 'confirming'}
                    <div class="confirm-row">
                      <span class="confirm-label">Sure?</span>
                      <button class="btn-yes" on:click={() => confirmKill(regId)}>Yes, kill</button>
                      <button class="btn-no"  on:click={() => cancelKill(regId)}>Cancel</button>
                    </div>
  
                  {:else if state === 'killing'}
                    <span class="state-killing">
                      <span class="mini-spin"></span> Killing…
                    </span>
  
                  {:else if state === 'done'}
                    <span class="state-done">✓ Killed</span>
                  {/if}
  
                  {#if err}
                    <div class="kill-err">{err}</div>
                  {/if}
                </td>
              </tr>
            {/each}
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>

<style>
  /* ── Card shell ── */
  .supervisor-card {
    background: rgb(15 15 17 / 0.9);
    border: 1px solid #27272a;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    color: #f4f4f5;
  }

  /* ── Header ── */
  .supervisor-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1rem;
    flex-wrap: wrap;
    gap: 0.5rem;
  }
  .header-left  { display: flex; align-items: center; gap: 0.65rem; }
  .header-right { display: flex; align-items: center; gap: 0.65rem; }

  .card-title {
    margin: 0;
    font-size: 1rem;
    font-weight: 700;
    color: #e4e4e7;
    letter-spacing: -0.01em;
  }
  .count-badge {
    background: #27272a;
    color: #a1a1aa;
    border: 1px solid #3f3f46;
    padding: 0.15rem 0.55rem;
    border-radius: 99px;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.02em;
  }
  .last-fetched { font-size: 0.68rem; color: #52525b; }

  .refresh-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    background: #27272a;
    border: 1px solid #3f3f46;
    color: #a1a1aa;
    padding: 0.28rem 0.65rem;
    border-radius: 6px;
    font-size: 0.72rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
  }
  .refresh-btn:hover { background: #3f3f46; color: #e4e4e7; }
  .btn-icon { width: 12px; height: 12px; }

  /* ── Error bar ── */
  .error-bar {
    background: rgb(239 68 68 / 0.1);
    border: 1px solid rgb(239 68 68 / 0.3);
    color: #f87171;
    border-radius: 8px;
    padding: 0.45rem 0.75rem;
    font-size: 0.78rem;
    margin-bottom: 0.75rem;
  }

  /* ── Skeleton ── */
  .skeleton-wrap { display: flex; flex-direction: column; gap: 0.5rem; }
  .skeleton-row {
    height: 44px;
    background: linear-gradient(90deg, #27272a 25%, #3f3f46 50%, #27272a 75%);
    background-size: 200% 100%;
    border-radius: 8px;
    animation: shimmer 1.5s infinite;
  }
  @keyframes shimmer {
    0%   { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }

  /* ── Empty ── */
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 2.25rem 1rem;
    color: #52525b;
    font-size: 0.8rem;
    font-style: italic;
    text-align: center;
  }
  .empty-icon { width: 30px; height: 30px; opacity: 0.35; }

  /* ── Table ── */
  .table-wrap { overflow-x: auto; }
  .proc-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.8rem;
  }
  .proc-table th {
    text-align: left;
    color: #71717a;
    font-size: 0.67rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    padding: 0.5rem 0.75rem;
    border-bottom: 1px solid #27272a;
    white-space: nowrap;
  }
  .th-right { text-align: right; }

  .category-header {
    background: #1f1f22;
  }
  .category-header td {
    padding: 0.5rem 0.75rem;
    font-weight: 700;
    color: #a1a1aa;
    text-transform: uppercase;
    font-size: 0.7rem;
    border-bottom: 1px solid #27272a;
    letter-spacing: 0.05em;
  }

  .proc-row {
    border-bottom: 1px solid #18181b;
    transition: background 0.12s;
  }
  .proc-row:last-child { border-bottom: none; }
  .proc-row:hover      { background: rgb(24 24 27 / 0.7); }
  .proc-row.row-killing { opacity: 0.55; }
  .proc-row.row-done    { opacity: 0.35; }

  .proc-table td { padding: 0.6rem 0.75rem; vertical-align: middle; }

  .task-name { font-weight: 600; color: #e4e4e7; }
  .wasm-id { font-size: 0.65rem; color: #a1a1aa; font-family: ui-monospace, monospace; }
  .mono-sm   { font-family: ui-monospace, monospace; font-size: 0.75rem; color: #a1a1aa; }
  .td-dim    { color: #71717a !important; }
  .td-task   { max-width: 200px; }
  .td-owner  { max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .td-action { text-align: right; white-space: nowrap; }

  .text-xs { font-size: 0.7rem; }

  /* ── Type badges ── */
  .type-badge {
    display: inline-block;
    padding: 0.12rem 0.42rem;
    border-radius: 4px;
    font-size: 0.62rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    white-space: nowrap;
  }
  .badge-plugin  { background: rgb(139 92 246/0.14); color:#a78bfa; border:1px solid rgb(139 92 246/0.3); }
  .badge-core    { background: rgb(59 130 246/0.14);  color:#60a5fa; border:1px solid rgb(59 130 246/0.3); }
  .badge-system  { background: rgb(16 185 129/0.14);  color:#34d399; border:1px solid rgb(16 185 129/0.3); }
  .badge-unknown { background: #27272a; color:#71717a; border:1px solid #3f3f46; }

  /* ── Duration ── */
  .duration-pill {
    display: inline-block;
    background: #18181b;
    border: 1px solid #27272a;
    color: #a1a1aa;
    padding: 0.1rem 0.45rem;
    border-radius: 99px;
    font-variant-numeric: tabular-nums;
    font-size: 0.72rem;
  }

  /* ── Kill controls ── */
  .kill-btn {
    background: rgb(239 68 68/0.12);
    color: #f87171;
    border: 1px solid rgb(239 68 68/0.3);
    padding: 0.22rem 0.6rem;
    border-radius: 5px;
    font-size: 0.7rem;
    font-weight: 700;
    cursor: pointer;
    transition: background 0.14s, transform 0.1s;
    letter-spacing: 0.02em;
  }
  .kill-btn:hover { background: rgb(239 68 68/0.22); transform: scale(1.04); }

  .confirm-row   { display: inline-flex; align-items: center; gap: 0.3rem; }
  .confirm-label { font-size: 0.7rem; color: #f59e0b; font-weight: 700; }

  .btn-yes, .btn-no {
    padding: 0.18rem 0.48rem;
    border-radius: 4px;
    font-size: 0.68rem;
    font-weight: 700;
    cursor: pointer;
    border: 1px solid;
    transition: background 0.13s;
  }
  .btn-yes { background: rgb(239 68 68/0.18); color: #fca5a5; border-color: rgb(239 68 68/0.35); }
  .btn-yes:hover { background: rgb(239 68 68/0.3); }
  .btn-no  { background: #27272a; color: #a1a1aa; border-color: #3f3f46; }
  .btn-no:hover  { background: #3f3f46; }

  .state-killing {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    font-size: 0.7rem;
    color: #f59e0b;
    font-weight: 600;
  }
  .state-done { font-size: 0.7rem; color: #34d399; font-weight: 700; }

  .kill-err {
    font-size: 0.65rem;
    color: #f87171;
    margin-top: 0.15rem;
    text-align: right;
  }

  .mini-spin {
    width: 10px;
    height: 10px;
    border: 2px solid rgb(245 158 11/0.25);
    border-top-color: #f59e0b;
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
    display: inline-block;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
