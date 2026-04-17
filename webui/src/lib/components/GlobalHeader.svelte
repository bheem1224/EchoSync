<script>
  import { unreadAlerts, activeDownloads } from '../../stores/headerStatus';
  import DownloadQueueDrawer from './DownloadQueueDrawer.svelte';

  export let toggleNotificationDrawer = () => {};
  let queueDrawerOpen = false;

  function toggleQueueDrawer() {
    queueDrawerOpen = !queueDrawerOpen;
  }
</script>

<header class="sticky top-0 z-40 border-b border-gray-800 bg-gray-900 text-white">
  <div class="mx-auto flex h-16 w-full items-center justify-between px-4 sm:px-6 lg:px-8">
    <h1 class="text-xl font-bold tracking-tight">Echosync</h1>

    <div class="flex items-center gap-2 sm:gap-3">
      <button
        type="button"
        class="relative inline-flex h-10 w-10 items-center justify-center rounded-full text-gray-200 transition hover:bg-gray-800 hover:text-white"
        on:click={toggleNotificationDrawer}
        aria-label="Open notifications"
        title="Notifications"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" class="h-5 w-5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0018 9.75v-.7A6 6 0 006 9.05v.7a8.967 8.967 0 00-2.311 6.022 23.85 23.85 0 005.454 1.31m5.714 0a3 3 0 11-5.714 0m5.714 0H9.143" />
        </svg>

        {#if $unreadAlerts > 0}
          <span class="absolute right-2 top-2 h-2.5 w-2.5 rounded-full bg-red-500"></span>
          <span class="absolute right-2 top-2 h-2.5 w-2.5 animate-ping rounded-full bg-red-500"></span>
        {/if}
      </button>

      <button
        type="button"
        class="relative inline-flex h-10 w-10 items-center justify-center rounded-full text-gray-200 transition hover:bg-gray-800 hover:text-white"
        on:click={toggleQueueDrawer}
        aria-label="Open download queue"
        title="Download Queue"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" class="h-5 w-5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3 7.5A2.5 2.5 0 015.5 5h13A2.5 2.5 0 0121 7.5v9A2.5 2.5 0 0118.5 19h-13A2.5 2.5 0 013 16.5v-9z" />
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 8.5v6m0 0l-2.25-2.25M12 14.5l2.25-2.25" />
        </svg>

        {#if $activeDownloads > 0}
          <span class="absolute -right-1 -top-1 inline-flex min-h-5 min-w-5 items-center justify-center rounded-full bg-indigo-500 px-1 text-[10px] font-semibold leading-none text-white">
            {$activeDownloads}
          </span>
        {/if}
      </button>
    </div>
  </div>
</header>

<DownloadQueueDrawer bind:isOpen={queueDrawerOpen} />
