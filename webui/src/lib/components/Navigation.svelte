<script>
  import { isDownloadDrawerOpen, toggleDownloadDrawer } from '../../stores/ui';
  import { activeDownloadCount } from '../../stores/downloads';
  import { metadataQueue } from '../../stores/metadataQueue';
  import { page } from '$app/stores';

  export let title = "EchoSync";
  export let showSearch = true;
</script>

<header class="global-navbar flex justify-between items-center px-4 sm:px-6 py-2.5 bg-surface/70 backdrop-blur-md border-b border-border-subtle z-30 select-none">
  <div class="flex items-center gap-3">
    {#if title}
      <span class="font-bold text-base sm:text-lg text-text-primary tracking-tight">{title}</span>
    {/if}

    {#if showSearch}
      <button
        class="search-trigger flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-hover hover:bg-surface-active text-text-muted hover:text-text-primary text-xs border border-border-subtle transition-all active:scale-95"
        on:click={() => window.dispatchEvent(new CustomEvent('es-omnibar-toggle'))}
        title="Search / Omnibar (Ctrl+K)"
      >
        <span class="search-icon">🔍</span>
        <span class="search-label hidden sm:inline">Search library, actions, ? for web...</span>
        <kbd class="shortcut-badge hidden md:inline px-1.5 py-0.5 text-[10px] bg-background/50 rounded border border-border-subtle text-text-muted">Ctrl+K</kbd>
      </button>
    {/if}
  </div>

  <div class="header-actions flex items-center gap-1.5 sm:gap-2">
    <!-- Download Manager Trigger -->
    <button 
      class="btn btn-ghost btn-circle btn-sm relative p-2 min-w-[44px] min-h-[44px] sm:min-w-[36px] sm:min-h-[36px] rounded-full hover:bg-surface-hover active:scale-95 transition-all text-text-primary flex items-center justify-center" 
      title="Download Manager (Ctrl+J)"
      on:click={toggleDownloadDrawer}
      aria-label="Toggle Download Manager"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
        <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
      </svg>
      {#if $activeDownloadCount > 0}
        <span class="badge badge-xs badge-accent absolute -top-1 -right-1 animate-pulse min-w-[18px] h-[18px] px-1 rounded-full bg-indigo-500 text-white text-[10px] font-bold flex items-center justify-center shadow-lg shadow-indigo-500/30">
          {$activeDownloadCount}
        </span>
      {/if}
    </button>

    <!-- Task Manager Trigger -->
    <a 
      href="/tasks" 
      class="p-2 min-w-[44px] min-h-[44px] sm:min-w-[36px] sm:min-h-[36px] rounded-full hover:bg-surface-hover active:scale-95 transition-all text-text-primary flex items-center justify-center"
      title="Task Manager"
      aria-label="Task Manager"
    >
      <span class="text-base">⚡</span>
    </a>

    <!-- Settings Trigger -->
    <a 
      href="/settings/preferences" 
      class="p-2 min-w-[44px] min-h-[44px] sm:min-w-[36px] sm:min-h-[36px] rounded-full hover:bg-surface-hover active:scale-95 transition-all text-text-primary flex items-center justify-center"
      title="Settings"
      aria-label="Settings"
    >
      <span class="text-base">⚙️</span>
    </a>
  </div>
</header>

<style>
  .global-navbar {
    border-bottom: 1px solid var(--border, rgba(255, 255, 255, 0.08));
    background: rgba(18, 18, 24, 0.65);
    backdrop-filter: blur(12px);
  }
  .search-trigger {
    color: var(--muted, #94a3b8);
  }
  .search-trigger:hover {
    color: var(--text, #f8fafc);
  }
</style>
