<script>
  import { onMount } from 'svelte';
  import Sidebar from '../components/Sidebar.svelte';
  import BottomNav from '../components/BottomNav.svelte';
  import Toast from '../components/Toast.svelte';
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
  let showDevModeBanner = false;

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
        migrationMessage = response.data.message || 'SoulSync has been upgraded!';
      }
    } catch (error) {
      console.error('Failed to check migration status:', error);
    }

    try {
      const response = await apiClient.get('/status');
      showDevModeBanner = Boolean(response.data?.dev_mode);
    } catch (error) {
      console.error('Failed to check runtime mode:', error);
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
      {#if showDevModeBanner}
        <div class="dev-mode-banner" role="alert" aria-live="polite">
          <strong>Development Mode Enabled</strong>
          <span>DEV_MODE is active. This web UI is running in a development-only configuration and should not be used in production.</span>
        </div>
      {/if}
      <slot />
    </main>
  {:else}
    <main class="app-content">
      {#if showDevModeBanner}
        <div class="dev-mode-banner" role="alert" aria-live="polite">
          <strong>Development Mode Enabled</strong>
          <span>DEV_MODE is active. This web UI is running in a development-only configuration and should not be used in production.</span>
        </div>
      {/if}
      <slot />
    </main>
    <BottomNav />
  {/if}
  <BottomPlayer />
  <Toast />
  
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

  .dev-mode-banner {
    position: sticky;
    top: 0;
    z-index: 30;
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 16px;
    padding: 12px 16px;
    border: 1px solid rgba(239, 68, 68, 0.35);
    border-radius: 12px;
    background:
      linear-gradient(135deg, rgba(127, 29, 29, 0.95), rgba(69, 10, 10, 0.92));
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.28);
    color: #fee2e2;
    backdrop-filter: blur(8px);
  }

  .dev-mode-banner strong {
    color: #fecaca;
    font-size: 13px;
    letter-spacing: 0.02em;
    text-transform: uppercase;
    white-space: nowrap;
  }

  .dev-mode-banner span {
    font-size: 14px;
    line-height: 1.4;
  }

  @media (max-width: 900px) {
    .app-shell {
      flex-direction: column;
    }

    .app-content {
      padding: 16px;
      padding-bottom: 140px; /* Add padding for player + bottom nav */
    }

    .dev-mode-banner {
      flex-direction: column;
      align-items: flex-start;
      gap: 6px;
    }
  }
</style>
