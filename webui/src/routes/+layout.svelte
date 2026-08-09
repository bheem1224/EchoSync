<script>
  import { onMount } from 'svelte';
  import { fade } from 'svelte/transition';
  import { page } from '$app/stores';
  import Sidebar from '../components/Sidebar.svelte';
  import BottomNav from '../components/BottomNav.svelte';
  import ToastNotifications from '../lib/components/ToastNotifications.svelte';
  import Omnibar from '../lib/components/Omnibar.svelte';
  import RestartBanner from '../components/RestartBanner.svelte';
  import BottomPlayer from '../components/BottomPlayer.svelte';
  import EncryptionKeyWarning from '../components/EncryptionKeyWarning.svelte';
  import MigrationModal from '../components/MigrationModal.svelte';
  import { plugins } from '../stores/plugins';
  import { systemStatus } from '../stores/systemStatus';
  import { loadPluginViews } from '../stores/pluginViews';
  import apiClient from '../api/client';
  import { theme } from '../stores/theme';
  import '../app.css';

  let innerWidth;
  let showEncryptionWarning = false;
  let encryptionKeyValue = '';
  let showMigrationModal = false;
  let migrationMessage = '';

  onMount(async () => {
    theme.init();
    plugins.load();
    loadPluginViews();          // fire-and-forget — populates pluginViews store
    systemStatus.startPolling(5000); // Poll every 5 seconds

    
    // Check for encryption key auto-generation warning
    try {
      const response = await apiClient.get('/system/encryption-key-warning');
      if (response.data?.auto_generated) {
        showEncryptionWarning = true;
        encryptionKeyValue = response.data.key_value || '';
      }
    } catch (error) {
      console.error('Failed to check encryption key status:', error);
    }

    // Check for v2.1.0 migration notification
    try {
      const response = await apiClient.get('/system/migration-status');
      if (response.data?.v2_1_migration_triggered) {
        showMigrationModal = true;
        migrationMessage = response.data.message || 'Echosync has been upgraded!';
      }
    } catch (error) {
      console.error('Failed to check migration status:', error);
    }

    return () => {
      systemStatus.stopPolling();
    };
  });

  function dismissEncryptionWarning() {
    showEncryptionWarning = false;
  }

  function dismissMigrationModal() {
    showMigrationModal = false;
  }
</script>

<svelte:window bind:innerWidth />

<div class="h-screen w-full flex flex-col overflow-hidden theme-{$theme.current}" style="background-color: var(--bg-canvas); color: var(--text-primary);">
  <RestartBanner />
  <div class="flex-1 flex overflow-hidden min-h-0">
    {#if innerWidth >= 768}
      <Sidebar />
      <main class="flex-1 overflow-y-auto p-6">
        {#key $page.url}
          <div in:fade={{ duration: 150, delay: 150 }} out:fade={{ duration: 150 }}>
            <slot />
          </div>
        {/key}
      </main>
    {:else}
      <div class="flex-1 flex flex-col min-h-0">
        <header class="flex justify-between items-center p-4 bg-surface border-b border-border-subtle">
          <div class="font-bold text-lg text-text-primary tracking-tight">EchoSync</div>
          <button
            class="p-2 bg-surface-hover rounded-global active:scale-95 transition-all text-text-primary"
            on:click={() => window.dispatchEvent(new CustomEvent('es-omnibar-toggle'))}
          >
            🔍
          </button>
        </header>
        <main class="flex-1 overflow-y-auto p-4">
          {#key $page.url}
            <div in:fade={{ duration: 150, delay: 150 }} out:fade={{ duration: 150 }}>
              <slot />
            </div>
          {/key}
        </main>
        <BottomNav />
      </div>
    {/if}
  </div>

  <!-- Bottom Player Fixed outside main scroll area -->
  <div class="flex-none">
    <BottomPlayer />
  </div>

  <ToastNotifications />
  <Omnibar mode="modal" />
  
  {#if showEncryptionWarning}
    <EncryptionKeyWarning 
      keyValue={encryptionKeyValue} 
      on:dismiss={dismissEncryptionWarning}
    />
  {/if}

  {#if showMigrationModal}
    <MigrationModal 
      message={migrationMessage}
      on:dismiss={dismissMigrationModal}
    />
  {/if}
</div>
