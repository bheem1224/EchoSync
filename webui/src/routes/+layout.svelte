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

<div class="app-shell bg-transparent text-[var(--text)]">
  {#if innerWidth >= 768}
    <Sidebar />
    <main class="app-content flex-1 overflow-y-auto min-h-0">
      {#key $page.url}
        <div in:fade={{ duration: 150, delay: 150 }} out:fade={{ duration: 150 }}>
          <slot />
        </div>
      {/key}
    </main>
  {:else}

    <header class="flex justify-between items-center p-4 bg-surface border-b border-glass-border">
      <div class="font-bold text-lg text-primary tracking-tight">EchoSync</div>
      <button
        class="p-2 bg-surface-hover rounded-global active:scale-95 transition-all text-primary"
        on:click={() => window.dispatchEvent(new CustomEvent('es-omnibar-toggle'))}
      >
        🔍
      </button>
    </header>
    <main class="app-content flex-1 overflow-y-auto min-h-0">

      {#key $page.url}
        <div in:fade={{ duration: 150, delay: 150 }} out:fade={{ duration: 150 }}>
          <slot />
        </div>
      {/key}
    </main>
    <BottomNav />
  {/if}
  <BottomPlayer />
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

<style>
  .app-shell {
    display: flex;
    min-height: 100vh;
    width: 100%;
    position: relative;
    overflow: hidden;
    background: transparent;
    color: var(--text);
  }

  .app-content {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: 24px;
    padding-bottom: 120px; /* Add padding for player */
  }

  @media (max-width: 900px) {
    .app-shell {
      flex-direction: column;
    }

    .app-content {
      padding: 16px;
      padding-bottom: 160px; /* Add padding for player + bottom nav */
    }
  }
</style>
