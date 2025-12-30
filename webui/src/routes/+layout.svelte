<script>
  import { onMount } from 'svelte';
  import Sidebar from '../components/Sidebar.svelte';
  import { providers } from '../stores/providers';
  import '../app.css';

  onMount(() => {
    providers.load();
  });
</script>

<div class="app-shell">
  <Sidebar />
  <main class="app-content">
    <slot />
  </main>
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
  }

  @media (max-width: 900px) {
    .app-shell {
      flex-direction: column;
    }

    .app-content {
      padding: 16px;
    }
  }
</style>
