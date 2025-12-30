<script>
  import { onMount, onDestroy } from 'svelte';
  import JobStatus from '../../components/JobStatus.svelte';
  import { providers } from '../../stores/providers';
  import { jobs } from '../../stores/jobs';
  import { health } from '../../stores/health';

  let pollHandle = null;
  let healthPollHandle = null;

  onMount(async () => {
    await Promise.all([
      providers.load(), 
      jobs.load(),
      health.load()
    ]);
    pollHandle = jobs.poll(5000);
    healthPollHandle = health.poll(30000);
  });

  onDestroy(() => {
    if (pollHandle) clearInterval(pollHandle);
    if (healthPollHandle) clearInterval(healthPollHandle);
  });

  $: providerList = Object.values($providers?.items ?? []);
  $: systemStatus = $health.status;
  $: serviceHealth = $health.services;
</script>

<svelte:head>
  <title>Dashboard • SoulSync</title>
</svelte:head>

<section class="page">
  <header class="page__header">
    <div>
      <p class="eyebrow">Overview</p>
      <h1>Dashboard</h1>
      <p class="sub">System health and active operations.</p>
    </div>
    <div class="status-pill {systemStatus}">
      <span class="dot"></span>
      System {systemStatus}
    </div>
  </header>

  <div class="grid">
    <div class="card span-2">
      <div class="card__header">
        <h2>Music Services</h2>
        <span class="badge">{providerList.length}</span>
      </div>
      {#if providerList.length === 0}
        <div class="empty-state">
          <p class="muted">No providers configured.</p>
          <a href="/settings#music-services" class="btn btn--small">Configure Providers</a>
        </div>
      {:else}
        <ul class="provider-list">
          {#each providerList as provider}
            {@const health = serviceHealth[provider.id]}
            <li>
              <div class="provider-info">
                <div class="provider-main">
                  <strong>{provider.name}</strong>
                  <span class="status-tag {health?.status || 'unknown'}">
                    {health?.status || 'unknown'}
                  </span>
                </div>
                <p class="muted small">{provider.id}</p>
                {#if health?.message}
                  <p class="health-msg">{health.message}</p>
                {/if}
              </div>
              <div class="caps">
                {#if provider.capabilities?.supports_playlists !== 'NONE'}
                  <span class="chip">Playlists</span>
                {/if}
                {#if provider.capabilities?.search?.tracks}
                  <span class="chip">Search</span>
                {/if}
                {#if provider.capabilities?.supports_sync}
                  <span class="chip">Sync</span>
                {/if}
              </div>
            </li>
          {/each}
        </ul>
      {/if}
    </div>

    <div class="card">
      <div class="card__header">
        <h2>Active Jobs</h2>
      </div>
      <JobStatus />
    </div>

    <div class="card">
      <div class="card__header">
        <h2>System Health</h2>
      </div>
      <div class="health-grid">
        {#each Object.entries(serviceHealth) as [id, data]}
          {#if !providerList.find(p => p.id === id)}
            <div class="health-item">
              <span class="status-dot {data.status}"></span>
              <span class="health-name">{id}</span>
              <span class="health-status">{data.status}</span>
            </div>
          {/if}
        {/each}
      </div>
    </div>
  </div>
</section>

<style>
  .page {
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .page__header {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
  }

  .status-pill {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 20px;
    font-size: 13px;
    font-weight: 600;
    text-transform: capitalize;
  }

  .status-pill.healthy { color: var(--accent); }
  .status-pill.degraded { color: #f59e0b; }
  .status-pill.unhealthy { color: #ef4444; }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: currentColor;
    box-shadow: 0 0 10px currentColor;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
    gap: 24px;
  }

  .card {
    background: var(--glass);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
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

  .card__header h2 {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
  }

  .badge {
    background: var(--accent);
    color: #000;
    border-radius: 6px;
    padding: 2px 8px;
    font-weight: 700;
    font-size: 11px;
  }

  .provider-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .provider-list li {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding: 16px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
  }

  .provider-main {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 4px;
  }

  .status-tag {
    font-size: 10px;
    text-transform: uppercase;
    font-weight: 800;
    padding: 2px 6px;
    border-radius: 4px;
    background: rgba(255, 255, 255, 0.1);
  }

  .status-tag.healthy { color: var(--accent); background: rgba(15, 239, 136, 0.1); }
  .status-tag.degraded { color: #f59e0b; background: rgba(245, 158, 11, 0.1); }
  .status-tag.unhealthy { color: #ef4444; background: rgba(239, 68, 68, 0.1); }

  .health-msg {
    font-size: 12px;
    color: #94a3b8;
    margin: 4px 0 0;
  }

  .chip {
    font-size: 11px;
    background: rgba(255, 255, 255, 0.05);
    padding: 4px 8px;
    border-radius: 6px;
    color: #cbd5e1;
  }

  .health-grid {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .health-item {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 14px;
  }

  .status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #4b5563;
  }

  .status-dot.healthy { background: var(--accent); box-shadow: 0 0 8px var(--accent); }
  .status-dot.degraded { background: #f59e0b; box-shadow: 0 0 8px #f59e0b; }
  .status-dot.unhealthy { background: #ef4444; box-shadow: 0 0 8px #ef4444; }

  .health-name { flex: 1; color: #e2e8f0; text-transform: capitalize; }
  .health-status { font-size: 12px; color: #94a3b8; text-transform: uppercase; }

  .empty-state {
    text-align: center;
    padding: 40px 20px;
  }

  .btn {
    display: inline-block;
    padding: 8px 16px;
    background: var(--accent);
    color: #000;
    border-radius: 8px;
    text-decoration: none;
    font-weight: 600;
    font-size: 14px;
    margin-top: 12px;
    transition: transform 0.2s;
  }

  .btn:hover { transform: translateY(-2px); }

  .span-2 { grid-column: span 2; }

  @media (max-width: 1100px) {
    .span-2 { grid-column: span 1; }
  }

  .small { font-size: 12px; }
  .muted { color: #94a3b8; }
</style>

