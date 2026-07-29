<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { taskManager } from '../../stores/taskManager.js';

  export let streamUrl: string = '/api/v1/system/queue/stream';

  onMount(() => {
    taskManager.connect(streamUrl);
  });

  onDestroy(() => {
    taskManager.disconnect();
  });

  $: runningJobs = $taskManager.running_jobs || [];
  $: pendingJobs = $taskManager.pending_jobs || [];
  $: blockedJobs = $taskManager.blocked_jobs || [];
  $: stats = $taskManager.stats || { total: 0, running: 0, pending: 0, blocked: 0 };
  $: cancellingJobs = $taskManager.cancellingJobs || new Set();

  function handleCancel(jobName: string) {
    taskManager.cancelJob(jobName);
  }

  function formatCategory(cat: string): string {
    if (!cat) return 'General';
    return cat.replace(/_/g, ' ').toUpperCase();
  }
</script>

<div class="task-manager-panel">
  <div class="panel-header">
    <div class="header-left">
      <h3>System Task Manager</h3>
      <span class="active-badge">{stats.running} Running</span>
    </div>
    <div class="stats-summary">
      <span class="stat-pill">Total: {stats.total}</span>
      <span class="stat-pill pending">Pending: {stats.pending}</span>
      <span class="stat-pill blocked" class:active={stats.blocked > 0}>Blocked: {stats.blocked}</span>
    </div>
  </div>

  <!-- RUNNING JOBS SECTION -->
  <div class="section">
    <h4 class="section-title">Active Running Tasks</h4>
    {#if runningJobs.length === 0}
      <div class="empty-state">No tasks currently running</div>
    {:else}
      <div class="jobs-list">
        {#each runningJobs as job (job.name)}
          <div class="job-card running">
            <div class="job-header">
              <div class="job-info">
                <span class="job-name">{job.name}</span>
                <span class="category-badge {job.category}">{formatCategory(job.category)}</span>
              </div>
              <button
                class="cancel-btn"
                disabled={cancellingJobs.has(job.name)}
                on:click={() => handleCancel(job.name)}
              >
                {#if cancellingJobs.has(job.name)}
                  <span class="spinner"></span> Cancelling...
                {:else}
                  Cancel Task
                {/if}
              </button>
            </div>
            <div class="indeterminate-progress"></div>
          </div>
        {/each}
      </div>
    {/if}
  </div>

  <!-- BLOCKED JOBS SECTION -->
  {#if blockedJobs.length > 0}
    <div class="section">
      <h4 class="section-title blocked-title">
        <span class="lock-icon">🔒</span> Blocked Tasks (Concurrency Guard)
      </h4>
      <div class="jobs-list">
        {#each blockedJobs as job (job.name)}
          <div class="job-card blocked">
            <div class="job-header">
              <div class="job-info">
                <span class="job-name">{job.name}</span>
                <span class="category-badge {job.category}">{formatCategory(job.category)}</span>
              </div>
              <span class="blocked-badge">PENDING_BLOCKED</span>
            </div>
            <div class="blocked-reason">
              ⚠️ {job.reason || 'Waiting for database write lock to clear'}
            </div>
          </div>
        {/each}
      </div>
    </div>
  {/if}

  <!-- PENDING JOBS SECTION -->
  <div class="section">
    <h4 class="section-title">Pending Queue ({pendingJobs.length})</h4>
    {#if pendingJobs.length === 0}
      <div class="empty-state">No pending jobs in queue</div>
    {:else}
      <div class="jobs-list">
        {#each pendingJobs as job (job.name)}
          <div class="job-card pending">
            <div class="job-header">
              <div class="job-info">
                <span class="job-name">{job.name}</span>
                <span class="category-badge {job.category}">{formatCategory(job.category)}</span>
              </div>
              <span class="state-label">Queued</span>
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </div>
</div>

<style>
  .task-manager-panel {
    background: #121214;
    border: 1px solid #27272a;
    border-radius: 12px;
    padding: 1.5rem;
    color: #f4f4f5;
    font-family: inherit;
  }

  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #27272a;
    padding-bottom: 1rem;
    margin-bottom: 1.25rem;
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .header-left h3 {
    margin: 0;
    font-size: 1.15rem;
    font-weight: 600;
  }

  .active-badge {
    background: rgba(99, 102, 241, 0.15);
    color: #818cf8;
    font-size: 0.75rem;
    padding: 0.2rem 0.6rem;
    border-radius: 9999px;
    font-weight: 600;
  }

  .stats-summary {
    display: flex;
    gap: 0.5rem;
  }

  .stat-pill {
    background: #18181b;
    border: 1px solid #27272a;
    color: #a1a1aa;
    font-size: 0.75rem;
    padding: 0.2rem 0.5rem;
    border-radius: 6px;
  }

  .stat-pill.blocked.active {
    background: rgba(245, 158, 11, 0.15);
    color: #f59e0b;
    border-color: rgba(245, 158, 11, 0.3);
  }

  .section {
    margin-bottom: 1.5rem;
  }

  .section-title {
    font-size: 0.875rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #a1a1aa;
    margin: 0 0 0.75rem 0;
  }

  .blocked-title {
    color: #f59e0b;
  }

  .empty-state {
    color: #52525b;
    font-size: 0.85rem;
    font-style: italic;
    padding: 0.5rem 0;
  }

  .jobs-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .job-card {
    background: #18181b;
    border: 1px solid #27272a;
    border-radius: 8px;
    padding: 0.875rem 1rem;
    transition: border-color 0.2s ease;
  }

  .job-card.running {
    border-color: #6366f1;
  }

  .job-card.blocked {
    border-color: rgba(245, 158, 11, 0.4);
    background: rgba(245, 158, 11, 0.03);
  }

  .job-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .job-info {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .job-name {
    font-weight: 600;
    font-size: 0.9rem;
    color: #f4f4f5;
  }

  .category-badge {
    font-size: 0.65rem;
    padding: 0.15rem 0.4rem;
    border-radius: 4px;
    background: #27272a;
    color: #d4d4d8;
    text-transform: uppercase;
    font-weight: 700;
  }

  .category-badge.database_write_heavy {
    background: rgba(239, 68, 68, 0.15);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.3);
  }

  .cancel-btn {
    background: rgba(239, 68, 68, 0.15);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.3);
    padding: 0.35rem 0.75rem;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 0.4rem;
    transition: background 0.2s ease;
  }

  .cancel-btn:hover:not(:disabled) {
    background: rgba(239, 68, 68, 0.3);
  }

  .cancel-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .indeterminate-progress {
    height: 4px;
    background: #27272a;
    border-radius: 2px;
    margin-top: 0.75rem;
    overflow: hidden;
    position: relative;
  }

  .indeterminate-progress::after {
    content: '';
    position: absolute;
    top: 0;
    left: -40%;
    width: 40%;
    height: 100%;
    background: linear-gradient(90deg, transparent, #6366f1, transparent);
    animation: indeterminate 1.5s infinite;
  }

  @keyframes indeterminate {
    0% { left: -40%; }
    100% { left: 100%; }
  }

  .blocked-reason {
    font-size: 0.75rem;
    color: #f59e0b;
    margin-top: 0.5rem;
    background: rgba(245, 158, 11, 0.08);
    padding: 0.4rem 0.6rem;
    border-radius: 4px;
  }

  .blocked-badge {
    font-size: 0.7rem;
    font-weight: 700;
    color: #f59e0b;
  }

  .state-label {
    font-size: 0.75rem;
    color: #71717a;
  }

  .spinner {
    width: 10px;
    height: 10px;
    border: 2px solid rgba(239, 68, 68, 0.3);
    border-top-color: #ef4444;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }
</style>
