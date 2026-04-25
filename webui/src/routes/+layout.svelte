<script>
  import { onMount } from 'svelte';
  import { fade } from 'svelte/transition';
  import { page } from '$app/stores';
  import Sidebar from '../components/Sidebar.svelte';
  import BottomNav from '../components/BottomNav.svelte';
  import ToastNotifications from '../lib/components/ToastNotifications.svelte';
  import Omnibar from '../lib/components/Omnibar.svelte';
  import BottomPlayer from '../components/BottomPlayer.svelte';
  import EncryptionKeyWarning from '../components/EncryptionKeyWarning.svelte';
  import MigrationModal from '../components/MigrationModal.svelte';
  import { providers } from '../stores/providers';
  import apiClient from '../api/client';
  import '../app.css';

  let innerWidth;
  let showEncryptionWarning = false;
  let encryptionKeyValue = '';
  let showMigrationModal = false;
  let migrationMessage = '';

  onMount(async () => {
    providers.load();
    
    // Check for encryption key auto-generation warning
    try {
      const response = await apiClient.get('/encryption-key-warning');
      if (response.data?.auto_generated) {
        showEncryptionWarning = true;
        encryptionKeyValue = response.data.key_value || '';
      }
    } catch (error) {
      console.error('Failed to check encryption key status:', error);
    }

    // Check for v2.1.0 migration notification
    try {
      const response = await apiClient.get('/migration-status');
      if (response.data?.v2_1_migration_triggered) {
        showMigrationModal = true;
        migrationMessage = response.data.message || 'Echosync has been upgraded!';
      }
    } catch (error) {
      console.error('Failed to check migration status:', error);
    }
  });

  function dismissEncryptionWarning() {
    showEncryptionWarning = false;
  }

  function dismissMigrationModal() {
    showMigrationModal = false;
  }
</script>

<svelte:window bind:innerWidth />

<div class="h-screen w-full flex flex-col overflow-hidden bg-transparent text-white">
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
        <header class="flex justify-between items-center p-4 bg-surface border-b border-glass-border">
          <div class="font-bold text-lg text-white tracking-tight">EchoSync</div>
          <button
            class="p-2 bg-surface-hover rounded-global active:scale-95 transition-all text-white"
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
  <Omnibar />
  
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
