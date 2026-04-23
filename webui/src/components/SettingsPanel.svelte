<script>
  import { page } from '$app/stores';
  import { settingsPanel, setActive, closeSettings } from '../stores/settingsPanel';
  import { goto } from '$app/navigation';

  const links = [
    { label: 'Preferences', id: 'preferences' },
    { label: 'Music Services', id: 'music-services' },
    { label: 'Servers', id: 'servers' },
    { label: 'Metadata', id: 'metadata' },
    { label: 'Search', id: 'search' },
    { label: 'Misc', id: 'misc' },
    { label: 'Jobs', id: 'jobs' },
    { label: 'System', id: 'system' }
  ];

  // Use Svelte's auto-subscription by referencing `$settingsPanel`
  // (no manual subscribe needed)

  function handleClick(id) {
    setActive(id);
    // Navigate main content to settings and jump to anchor
    goto(`/settings#${id}`);
  }

  function close() {
    closeSettings();
  }

  // Auto-open panel when route is /settings and set active from URL hash
  $: if ($page.url.pathname.startsWith('/settings')) {
    const hash = $page.url.hash ? $page.url.hash.replace('#', '') : 'preferences';
    settingsPanel.set({ open: true, active: hash });
  }
</script>

{#if $settingsPanel.open}
  <aside class="settings-panel">
    <div class="panel-header">
      <strong>Settings</strong>
      <button class="close active:scale-95 transition-all duration-200" on:click={close}>✕</button>
    </div>
    <nav class="panel-links">
      {#each links as l}
        <button
          class:active={$settingsPanel.active === l.id}
          on:click={() => handleClick(l.id)}
        >
          {l.label}
        </button>
      {/each}
    </nav>
  </aside>
{/if}

<style>
  .settings-panel {
    width: 220px;
    border-left: 1px solid var(--border);
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    background: linear-gradient(180deg, rgba(255,255,255,0.02), transparent);
  }

  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .panel-links {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  button {
    background: transparent;
    border: none;
    text-align: left;
    padding: 8px 10px;
    border-radius: 6px;
    color: var(--muted);
    cursor: pointer;
  }

  button.active {
    background: var(--accent);
    color: var(--background);
  }

  .close {
    cursor: pointer;
    background: transparent;
    border: none;
    color: var(--muted);
  }
</style>
