<script>
  import { onMount } from 'svelte';
  import Sidebar from '../components/Sidebar.svelte';
  import BottomNav from '../components/BottomNav.svelte';
  import Toast from '../components/Toast.svelte';
  import AudioPlayer from '../components/AudioPlayer.svelte';
  import { providers } from '../stores/providers';
  import '../app.css';

  let innerWidth;

  onMount(() => {
    providers.load();
  });
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
  <AudioPlayer />
  <Toast />
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
