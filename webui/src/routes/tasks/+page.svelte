<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import SystemHealthCard from '../../lib/components/dashboard/SystemHealthCard.svelte';
  import ProcessSupervisorTable from '../../lib/components/dashboard/ProcessSupervisorTable.svelte';
  import JobsSettings from '../../components/JobsSettings.svelte';

  let activeTab: 'processes' | 'jobs' = 'processes';

  onMount(() => {
    const tabParam = $page.url.searchParams.get('tab');
    if (tabParam === 'jobs') {
      activeTab = 'jobs';
    }
  });

  function selectTab(tab: 'processes' | 'jobs') {
    activeTab = tab;
  }
</script>

<svelte:head>
  <title>Task Manager • EchoSync</title>
</svelte:head>

<section class="min-h-full space-y-6">
  <!-- Page Header -->
  <header class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-gray-800 pb-5">
    <div>
      <h1 class="text-2xl font-bold tracking-tight text-gray-100 flex items-center gap-2.5">
        <span class="text-amber-400 text-xl">⚡</span> Task Manager
      </h1>
      <p class="text-sm text-gray-400 mt-1">
        Monitor system health, process ownership, active worker threads, and scheduled background operations.
      </p>
    </div>

    <!-- Navigation Tabs -->
    <div class="flex items-center gap-1 bg-gray-900/90 border border-gray-800 p-1 rounded-xl shadow-inner self-start sm:self-auto">
      <button
        on:click={() => selectTab('processes')}
        class={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg transition-all ${
          activeTab === 'processes'
            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm'
            : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/60'
        }`}
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
          <line x1="8" y1="21" x2="16" y2="21" />
          <line x1="12" y1="17" x2="12" y2="21" />
        </svg>
        Processes & Health
      </button>

      <button
        on:click={() => selectTab('jobs')}
        class={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg transition-all ${
          activeTab === 'jobs'
            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm'
            : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/60'
        }`}
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
        Scheduled Jobs
      </button>
    </div>
  </header>

  <!-- Tab 1: Processes & Health -->
  {#if activeTab === 'processes'}
    <div class="space-y-6">
      <SystemHealthCard />
      <ProcessSupervisorTable />
    </div>
  {/if}

  <!-- Tab 2: Scheduled Jobs -->
  {#if activeTab === 'jobs'}
    <div>
      <JobsSettings />
    </div>
  {/if}
</section>
