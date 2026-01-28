<script>
  import { onMount, onDestroy } from 'svelte';
  import apiClient from '../api/client';
  import { feedback } from '../stores/feedback';

  let jobs = [];
  let loading = true;
  let refreshInterval;
  let editingInterval = null;
  let newInterval = '';

  // Category definitions
  const categories = {
    user: { label: 'User Tasks', order: 1, description: 'User-configured tasks and plugin operations' },
    soulsync: { label: 'SoulSync Tasks', order: 2, description: 'Recurring background tasks managed by SoulSync' },
    system: { label: 'System Tasks', order: 3, description: 'Core system operations and maintenance' }
  };

  onMount(async () => {
    await loadJobs();
    // Refresh every 10 seconds
    refreshInterval = setInterval(loadJobs, 10000);
  });

  onDestroy(() => {
    if (refreshInterval) clearInterval(refreshInterval);
  });

  async function loadJobs() {
    try {
      const response = await apiClient.get('/jobs');
      if (response.data && response.data.items) {
        jobs = response.data.items.map(job => ({
          ...job,
          category: categorizeJob(job)
        }));
      }
      loading = false;
    } catch (error) {
      console.error('Failed to load jobs:', error);
      feedback.addToast('Failed to load jobs', 'error');
      loading = false;
    }
  }

  function categorizeJob(job) {
    // Categorize based on tags
    if (job.tags && job.tags.includes('system')) return 'system';
    if (job.tags && job.tags.includes('soulsync')) return 'soulsync';
    if (job.plugin || (job.tags && job.tags.includes('user'))) return 'user';
    
    // Fallback: heuristic based on job name
    if (job.name.startsWith('health_check') || job.name.startsWith('system:')) return 'system';
    if (job.name.startsWith('download:') || job.name.startsWith('scan:') || job.name.startsWith('provider:')) return 'soulsync';
    
    return 'user';
  }

  function formatTimestamp(timestamp) {
    if (!timestamp) return 'Never';
    const date = new Date(timestamp * 1000);
    const now = Date.now();
    const diff = now - date.getTime();
    
    // Less than 1 hour: show relative
    if (diff < 3600000) {
      const minutes = Math.floor(diff / 60000);
      return minutes < 1 ? 'Just now' : `${minutes}m ago`;
    }
    
    // Today: show time
    if (date.toDateString() === new Date().toDateString()) {
      return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
    }
    
    // Otherwise: show date and time
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true });
  }

  function formatNextRun(timestamp) {
    if (!timestamp) return 'Not scheduled';
    const date = new Date(timestamp * 1000);
    const now = Date.now();
    const diff = date.getTime() - now;
    
    if (diff < 0) return 'Pending';
    
    // Less than 1 hour: show relative
    if (diff < 3600000) {
      const minutes = Math.floor(diff / 60000);
      return minutes < 1 ? 'Now' : `in ${minutes}m`;
    }
    
    // Less than 24 hours: show hours
    if (diff < 86400000) {
      const hours = Math.floor(diff / 3600000);
      return `in ${hours}h`;
    }
    
    // Otherwise: show days
    const days = Math.floor(diff / 86400000);
    return `in ${days}d`;
  }

  function formatInterval(seconds) {
    if (!seconds) return 'One-time';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
    return `${Math.floor(seconds / 86400)}d`;
  }

  async function runJob(jobName) {
    try {
      await apiClient.post('/jobs/run', { name: jobName });
      feedback.addToast(`Job "${jobName}" started`, 'success');
      await loadJobs(); // Refresh to show updated status
    } catch (error) {
      console.error(`Failed to run job ${jobName}:`, error);
      feedback.addToast(`Failed to run job: ${error.response?.data?.error || error.message}`, 'error');
    }
  }

  function startEditInterval(job) {
    editingInterval = job.name;
    newInterval = job.interval_seconds ? String(job.interval_seconds / 60) : '60'; // Show in minutes
  }

  function cancelEditInterval() {
    editingInterval = null;
    newInterval = '';
  }

  async function saveInterval(jobName) {
    const intervalSeconds = parseInt(newInterval) * 60;
    
    if (intervalSeconds < 60) {
      feedback.addToast('Interval must be at least 1 minute', 'error');
      return;
    }

    try {
      await apiClient.post(`/jobs/${jobName}/interval`, { interval_seconds: intervalSeconds });
      feedback.addToast('Interval updated', 'success');
      editingInterval = null;
      newInterval = '';
      await loadJobs();
    } catch (error) {
      console.error(`Failed to update interval for ${jobName}:`, error);
      feedback.addToast(`Failed to update interval: ${error.response?.data?.error || error.message}`, 'error');
    }
  }

  $: jobsByCategory = Object.keys(categories).reduce((acc, cat) => {
    acc[cat] = jobs.filter(j => j.category === cat).sort((a, b) => a.name.localeCompare(b.name));
    return acc;
  }, {});
</script>

<svelte:head>
  <title>Jobs • SoulSync</title>
</svelte:head>

<div class="jobs-container">
  <div class="jobs-header">
    <div>
      <h2>Scheduled Jobs</h2>
      <p class="subtitle">Manage recurring tasks and background operations</p>
    </div>
    <button class="btn-refresh" on:click={loadJobs} disabled={loading}>
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="23 4 23 10 17 10"></polyline>
        <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
      </svg>
      Refresh
    </button>
  </div>

  {#if loading}
    <div class="loading">Loading jobs...</div>
  {:else}
    {#each Object.entries(categories).sort((a, b) => a[1].order - b[1].order) as [catId, catInfo]}
      {#if jobsByCategory[catId]?.length > 0}
        <div class="job-category">
          <div class="category-header">
            <h3>{catInfo.label}</h3>
            <span class="category-count">{jobsByCategory[catId].length}</span>
          </div>
          <p class="category-description">{catInfo.description}</p>

          <div class="jobs-list">
            {#each jobsByCategory[catId] as job}
              <div class="job-card" class:running={job.running} class:error={job.last_error}>
                <div class="job-main">
                  <div class="job-info">
                    <div class="job-name">
                      {job.name}
                      {#if job.running}
                        <span class="status-badge running">Running</span>
                      {:else if !job.enabled}
                        <span class="status-badge disabled">Disabled</span>
                      {:else if job.last_error}
                        <span class="status-badge error">
                          Error
                          {#if job.total_failures > 1}
                            <span class="failure-count">({job.total_failures})</span>
                          {/if}
                        </span>
                      {/if}
                    </div>
                    
                    <div class="job-meta">
                      {#if job.total_successes > 0}
                        <span class="meta-item success">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="20 6 9 17 4 12"></polyline>
                          </svg>
                          {job.total_successes} successful run{job.total_successes !== 1 ? 's' : ''}
                        </span>
                      {/if}
                      
                      {#if job.last_success || job.last_finished}
                        <span class="meta-item">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="12" r="10"></circle>
                            <polyline points="12 6 12 12 16 14"></polyline>
                          </svg>
                          Last run: {formatTimestamp(job.last_success || job.last_finished)}
                        </span>
                      {/if}
                      
                      {#if job.next_run && job.enabled}
                        <span class="meta-item">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"></path>
                          </svg>
                          Next run: {formatNextRun(job.next_run)}
                        </span>
                      {/if}
                      
                      {#if job.interval_seconds}
                        <span class="meta-item interval">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 10H3M21 6H3M21 14H3M21 18H3"></path>
                          </svg>
                          Interval: {formatInterval(job.interval_seconds)}
                        </span>
                      {/if}
                    </div>

                    {#if job.last_error}
                      <div class="job-error">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                          <circle cx="12" cy="12" r="10"></circle>
                          <line x1="12" y1="8" x2="12" y2="12"></line>
                          <line x1="12" y1="16" x2="12.01" y2="16"></line>
                        </svg>
                        <div class="error-content">
                          <div class="error-message">{job.last_error}</div>
                          {#if job.last_error_time}
                            <div class="error-time">Failed {formatTimestamp(job.last_error_time)}</div>
                          {/if}
                        </div>
                      </div>
                    {/if}
                  </div>

                  <div class="job-actions">
                    {#if editingInterval === job.name}
                      <div class="interval-edit">
                        <input
                          type="number"
                          bind:value={newInterval}
                          min="1"
                          placeholder="Minutes"
                          class="interval-input"
                        />
                        <button class="btn-icon success" on:click={() => saveInterval(job.name)} title="Save">
                          ✓
                        </button>
                        <button class="btn-icon" on:click={cancelEditInterval} title="Cancel">
                          ✕
                        </button>
                      </div>
                    {:else}
                      <button
                        class="btn-action"
                        on:click={() => runJob(job.name)}
                        disabled={job.running}
                        title="Run now"
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                          <polygon points="5 3 19 12 5 21 5 3"></polygon>
                        </svg>
                        Run
                      </button>
                      
                      {#if catId === 'user' && job.interval_seconds}
                        <button
                          class="btn-action"
                          on:click={() => startEditInterval(job)}
                          title="Edit interval"
                        >
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                          </svg>
                          Edit
                        </button>
                      {/if}
                    {/if}
                  </div>
                </div>
              </div>
            {/each}
          </div>
        </div>
      {/if}
    {/each}
  {/if}
</div>

<style>
  .jobs-container {
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .jobs-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
  }

  .jobs-header h2 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
    color: var(--text);
  }

  .subtitle {
    margin: 4px 0 0;
    font-size: 14px;
    color: var(--muted);
  }

  .btn-refresh {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text);
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn-refresh:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.1);
  }

  .btn-refresh:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .loading {
    padding: 40px;
    text-align: center;
    color: var(--muted);
  }

  .job-category {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .category-header {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .category-header h3 {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    color: var(--text);
  }

  .category-count {
    padding: 2px 8px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    font-size: 12px;
    color: var(--muted);
  }

  .category-description {
    margin: 0;
    font-size: 13px;
    color: var(--muted);
  }

  .jobs-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .job-card {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 16px;
    transition: all 0.2s;
  }

  .job-card:hover {
    background: rgba(255, 255, 255, 0.05);
    border-color: rgba(255, 255, 255, 0.2);
  }

  .job-card.running {
    border-color: rgba(0, 230, 118, 0.4);
    background: rgba(0, 230, 118, 0.05);
  }

  .job-card.error {
    border-color: rgba(248, 113, 113, 0.4);
  }

  .job-main {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 16px;
  }

  .job-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .job-name {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    font-weight: 500;
    color: var(--text);
  }

  .status-badge {
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .status-badge.running {
    background: rgba(0, 230, 118, 0.2);
    color: #00e676;
  }

  .status-badge.disabled {
    background: rgba(255, 255, 255, 0.1);
    color: var(--muted);
  }

  .status-badge.error {
    background: rgba(248, 113, 113, 0.2);
    color: #f87171;
  }

  .job-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
  }

  .meta-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: var(--muted);
  }

  .meta-item svg {
    opacity: 0.6;
  }

  .meta-item.interval {
    color: var(--accent);
  }

  .meta-item.success {
    color: #10b981;
  }

  .failure-count {
    font-weight: 600;
    margin-left: 2px;
  }

  .job-error {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 10px 12px;
    background: rgba(248, 113, 113, 0.1);
    border: 1px solid rgba(248, 113, 113, 0.3);
    border-radius: 6px;
  }

  .job-error svg {
    flex-shrink: 0;
    margin-top: 2px;
    color: #f87171;
  }

  .error-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .error-message {
    font-size: 12px;
    color: #f87171;
    line-height: 1.4;
    word-break: break-word;
  }

  .error-time {
    font-size: 11px;
    color: rgba(248, 113, 113, 0.7);
    font-style: italic;
  }

  .job-actions {
    display: flex;
    gap: 8px;
  }

  .btn-action {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    color: var(--text);
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
    white-space: nowrap;
  }

  .btn-action:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.1);
    border-color: rgba(255, 255, 255, 0.2);
  }

  .btn-action:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .interval-edit {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .interval-input {
    width: 80px;
    padding: 6px 10px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    color: var(--text);
    font-size: 13px;
  }

  .btn-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    padding: 0;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    color: var(--text);
    font-size: 16px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn-icon:hover {
    background: rgba(255, 255, 255, 0.1);
  }

  .btn-icon.success {
    background: rgba(0, 230, 118, 0.1);
    border-color: rgba(0, 230, 118, 0.3);
    color: #00e676;
  }

  .btn-icon.success:hover {
    background: rgba(0, 230, 118, 0.2);
  }

  @media (max-width: 768px) {
    .job-main {
      flex-direction: column;
    }

    .job-actions {
      width: 100%;
      justify-content: flex-end;
    }
  }
</style>
