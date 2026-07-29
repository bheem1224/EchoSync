<script lang="ts">
  import { onDestroy } from 'svelte';
  import { scanStore } from '../stores/scanStore';
  import { scanService } from '../services/ScanService';

  export let streamUrl: string = '/api/v1/library/scan/stream';
  export let autoConnect: boolean = true;

  if (autoConnect) {
    scanService.connect(streamUrl);
  }

  onDestroy(() => {
    scanService.disconnect();
  });

  $: status = $scanStore.status;
  $: tracksProcessed = $scanStore.tracks_processed ?? 0;
  $: totalTracks = $scanStore.total_tracks ?? 0;
  $: errorsEncountered = $scanStore.errors_encountered ?? 0;
  $: currentPhase = $scanStore.current_phase ?? 'idle';
  $: errorMessage = $scanStore.error_message ?? '';
  $: elapsedTimeMs = $scanStore.elapsed_time_ms ?? 0;

  $: progressPercentage = totalTracks > 0
    ? Math.min(Math.round((tracksProcessed / totalTracks) * 100), 100)
    : null;

  function formatTime(ms: number): string {
    const seconds = (ms / 1000).toFixed(1);
    return `${seconds}s`;
  }
</script>

<div class="scan-container" class:active={status === 'scanning'} class:complete={status === 'complete'} class:error={status === 'failed'}>
  {#if status === 'scanning'}
    <div class="scan-header">
      <div class="pulse-indicator"></div>
      <div class="header-text">
        <h4 class="status-title">Library Scan In Progress</h4>
        <span class="phase-badge">{currentPhase}</span>
      </div>
    </div>

    {#if progressPercentage !== null}
      <div class="progress-bar-wrapper">
        <div class="progress-bar" style="width: {progressPercentage}%"></div>
      </div>
    {:else}
      <div class="indeterminate-bar"></div>
    {/if}

    <div class="metrics-grid">
      <div class="metric-card">
        <span class="metric-value">{tracksProcessed}</span>
        <span class="metric-label">Tracks Processed</span>
      </div>
      <div class="metric-card">
        <span class="metric-value {$scanStore.batch_size ? '' : 'muted'}">{$scanStore.batch_size || '--'}</span>
        <span class="metric-label">Batch Size</span>
      </div>
      <div class="metric-card" class:warning={errorsEncountered > 0}>
        <span class="metric-value">{errorsEncountered}</span>
        <span class="metric-label">Errors</span>
      </div>
    </div>

  {:else if status === 'complete'}
    <div class="complete-card">
      <div class="icon-circle success-icon">✓</div>
      <div class="complete-info">
        <h4>Scan Completed Successfully</h4>
        <p>Processed <strong>{totalTracks}</strong> tracks in <strong>{formatTime(elapsedTimeMs)}</strong>.</p>
        {#if $scanStore.total_errors && $scanStore.total_errors > 0}
          <p class="error-note">Encountered {$scanStore.total_errors} non-fatal error(s) during scan.</p>
        {/if}
      </div>
    </div>

  {:else if status === 'failed'}
    <div class="error-card">
      <div class="icon-circle error-icon">✕</div>
      <div class="error-info">
        <h4>Scan Failed</h4>
        <p class="error-text">{errorMessage || 'An error occurred while scanning the library.'}</p>
      </div>
    </div>

  {:else}
    <div class="idle-card">
      <span class="idle-text">Library Scanner Idle</span>
    </div>
  {/if}
</div>

<style>
  .scan-container {
    background: #18181b;
    border: 1px solid #27272a;
    border-radius: 12px;
    padding: 1.25rem;
    color: #f4f4f5;
    font-family: inherit;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
  }

  .scan-container.active {
    border-color: #6366f1;
    box-shadow: 0 0 20px rgba(99, 102, 241, 0.15);
  }

  .scan-container.complete {
    border-color: #22c55e;
  }

  .scan-container.error {
    border-color: #ef4444;
  }

  .scan-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 1rem;
  }

  .pulse-indicator {
    width: 10px;
    height: 10px;
    background-color: #6366f1;
    border-radius: 50%;
    animation: pulse 1.5s infinite ease-in-out;
  }

  @keyframes pulse {
    0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.7); }
    70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(99, 102, 241, 0); }
    100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(99, 102, 241, 0); }
  }

  .status-title {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
  }

  .phase-badge {
    display: inline-block;
    font-size: 0.75rem;
    background: #27272a;
    color: #a1a1aa;
    padding: 0.15rem 0.5rem;
    border-radius: 9999px;
    margin-top: 0.2rem;
    text-transform: capitalize;
  }

  .progress-bar-wrapper {
    width: 100%;
    height: 8px;
    background: #27272a;
    border-radius: 4px;
    overflow: hidden;
    margin-bottom: 1rem;
  }

  .progress-bar {
    height: 100%;
    background: linear-gradient(90deg, #6366f1, #818cf8);
    transition: width 0.3s ease;
  }

  .indeterminate-bar {
    width: 100%;
    height: 6px;
    background: #27272a;
    position: relative;
    overflow: hidden;
    border-radius: 3px;
    margin-bottom: 1rem;
  }

  .indeterminate-bar::after {
    content: '';
    position: absolute;
    top: 0;
    left: -50%;
    width: 50%;
    height: 100%;
    background: linear-gradient(90deg, transparent, #6366f1, transparent);
    animation: indeterminate 1.5s infinite;
  }

  @keyframes indeterminate {
    0% { left: -50%; }
    100% { left: 100%; }
  }

  .metrics-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.75rem;
  }

  .metric-card {
    background: #09090b;
    border: 1px solid #18181b;
    padding: 0.75rem;
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .metric-value {
    font-size: 1.25rem;
    font-weight: 700;
    color: #f4f4f5;
  }

  .metric-value.muted {
    color: #52525b;
  }

  .metric-label {
    font-size: 0.75rem;
    color: #a1a1aa;
    margin-top: 0.25rem;
  }

  .metric-card.warning .metric-value {
    color: #f59e0b;
  }

  .complete-card, .error-card {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .icon-circle {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    font-size: 1.2rem;
  }

  .success-icon {
    background: rgba(34, 197, 94, 0.15);
    color: #22c55e;
  }

  .error-icon {
    background: rgba(239, 68, 68, 0.15);
    color: #ef4444;
  }

  .complete-info h4, .error-info h4 {
    margin: 0 0 0.25rem 0;
    font-size: 1rem;
  }

  .complete-info p, .error-info p {
    margin: 0;
    font-size: 0.875rem;
    color: #a1a1aa;
  }

  .error-note {
    color: #f59e0b !important;
    margin-top: 0.25rem !important;
  }

  .error-text {
    color: #f87171 !important;
  }

  .idle-card {
    text-align: center;
    color: #71717a;
    font-size: 0.875rem;
    padding: 0.5rem 0;
  }
</style>
