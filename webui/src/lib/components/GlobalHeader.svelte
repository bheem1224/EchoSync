<script>
  import { metadataQueue } from '../../stores/metadataQueue';
  import { isDownloadDrawerOpen, toggleDownloadDrawer } from '../../stores/ui';
  import { activeDownloadCount } from '../../stores/downloads';

  export let toggleNotificationDrawer = () => {};
</script>

<header class="sticky top-0 z-40 border-b border-border-subtle bg-surface/80 backdrop-blur-md text-text-primary">
  <div class="mx-auto flex h-14 w-full items-center justify-between px-4 sm:px-6 lg:px-8">
    <h1 class="text-lg font-bold tracking-tight text-text-primary">EchoSync</h1>

    <div class="flex items-center gap-2 sm:gap-3">
      <button
        type="button"
        class="relative inline-flex h-9 w-9 items-center justify-center rounded-full text-text-muted transition hover:bg-surface-hover hover:text-text-primary active:scale-95"
        on:click={toggleNotificationDrawer}
        aria-label="Open notifications"
        title="Notifications"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" class="h-5 w-5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0018 9.75v-.7A6 6 0 006 9.05v.7a8.967 8.967 0 00-2.311 6.022 23.85 23.85 0 005.454 1.31m5.714 0a3 3 0 11-5.714 0m5.714 0H9.143" />
        </svg>

        {#if $metadataQueue.count > 0}
          <span class="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-red-500"></span>
          <span class="absolute right-1.5 top-1.5 h-2 w-2 animate-ping rounded-full bg-red-500"></span>
        {/if}
      </button>

      <button
        type="button"
        class="relative inline-flex h-9 w-9 items-center justify-center rounded-full text-text-muted transition hover:bg-surface-hover hover:text-text-primary active:scale-95"
        on:click={toggleDownloadDrawer}
        aria-label="Open download manager"
        title="Download Manager (Ctrl+J)"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" class="h-5 w-5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
        </svg>

        {#if $activeDownloadCount > 0}
          <span class="absolute -right-1 -top-1 inline-flex min-h-4 min-w-4 items-center justify-center rounded-full bg-indigo-500 px-1 text-[10px] font-bold leading-none text-white animate-pulse">
            {$activeDownloadCount}
          </span>
        {/if}
      </button>
    </div>
  </div>
</header>
