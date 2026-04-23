<script>
  import { onMount } from 'svelte';
  import Sidebar from '../components/Sidebar.svelte';
  import BottomNav from '../components/BottomNav.svelte';
  import ToastNotifications from '../lib/components/ToastNotifications.svelte';
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

<div class="app-shell">
  {#if innerWidth >= 768}
    <Sidebar />
    <main class="app-content">
      <slot />
    </main>
  {:else}
    <main class="app-content">
      <slot />
    </main>
    <BottomNav />
  {/if}
  <BottomPlayer />
  <ToastNotifications />
  
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
    background: transparent;
    color: var(--text);
  }

  .app-content {
    flex: 1;
    padding: 24px;
    padding-bottom: 100px; /* Add padding for player */
  }

  @media (max-width: 900px) {
    .app-shell {
      flex-direction: column;
    }

    .app-content {
      padding: 16px;
      padding-bottom: 140px; /* Add padding for player + bottom nav */
    }
  }
</style>
