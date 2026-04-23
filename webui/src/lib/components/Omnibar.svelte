<script>
  import { onMount, tick } from 'svelte';
  import { goto } from '$app/navigation';

  let isOpen = false;
  let searchQuery = '';
  let selectedIndex = 0;
  let inputRef;

  const allActions = [
    { title: 'Dashboard', path: '/dashboard', icon: '🏠' },
    { title: 'Search', path: '/search', icon: '🔍' },
    { title: 'Library Manager', path: '/library/manager', icon: '📚' },
    { title: 'Review Queue', path: '/library/review-queue', icon: '📝' },
    { title: 'Sync Queue', path: '/sync', icon: '🔄' },
    { title: 'Settings: General', path: '/settings/system', icon: '⚙️' },
    { title: 'Settings: Preferences', path: '/settings/preferences', icon: '🎨' },
    { title: 'Settings: Metadata', path: '/settings/metadata', icon: '🏷️' },
    { title: 'Settings: Downloads', path: '/settings/downloads', icon: '⬇️' },
    { title: 'Settings: Music Services', path: '/settings/music-services', icon: '🎵' },
    { title: 'Settings: Download Clients', path: '/settings/download-clients', icon: '📥' },
    { title: 'Settings: Servers', path: '/settings/servers', icon: '🖥️' },
    { title: 'Settings: Plugin Store', path: '/settings/plugin-store', icon: '🧩' },
    { title: 'Settings: Background Jobs', path: '/settings/jobs', icon: '⏱️' },
    { title: 'Settings: Misc', path: '/settings/misc', icon: '🛠️' }
  ];

  $: filteredActions = allActions.filter(action =>
    action.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  $: {
    if (searchQuery) {
      selectedIndex = 0;
    }
  }

  function handleKeydown(e) {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      isOpen = !isOpen;
      if (isOpen) {
        searchQuery = '';
        selectedIndex = 0;
        tick().then(() => inputRef && inputRef.focus());
      }
    } else if (isOpen) {
      if (e.key === 'Escape') {
        e.preventDefault();
        isOpen = false;
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        selectedIndex = (selectedIndex + 1) % filteredActions.length;
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        selectedIndex = (selectedIndex - 1 + filteredActions.length) % filteredActions.length;
      } else if (e.key === 'Enter') {
        e.preventDefault();
        executeAction();
      }
    }
  }

  function executeAction() {
    if (filteredActions.length > 0) {
      const action = filteredActions[selectedIndex];
      isOpen = false;
      goto(action.path);
    }
  }

  function handleClick(index) {
    selectedIndex = index;
    executeAction();
  }

  function handleOverlayClick(e) {
    if (e.target === e.currentTarget) {
      isOpen = false;
    }
  }
</script>

<svelte:window on:keydown={handleKeydown} />

{#if isOpen}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div
    class="fixed inset-0 bg-black/50 backdrop-blur-sm z-[9999] flex justify-center items-start pt-[15vh] px-4 animate-fade-in"
    on:click={handleOverlayClick}
  >
    <div class="w-full max-w-2xl bg-surface border border-glass-border rounded-global shadow-2xl overflow-hidden flex flex-col transform transition-all animate-scale-in">
      <div class="flex items-center px-4 border-b border-glass-border">
        <span class="text-secondary text-xl mr-2">🔍</span>
        <input
          bind:this={inputRef}
          bind:value={searchQuery}
          type="text"
          placeholder="Type a command or search..."
          class="flex-1 py-4 bg-transparent outline-none text-primary text-lg placeholder-secondary"
        />
        <div class="text-xs text-secondary bg-surface-hover px-2 py-1 rounded border border-glass-border flex items-center gap-1 font-mono">
          <span>ESC</span>
        </div>
      </div>

      {#if filteredActions.length > 0}
        <div class="max-h-[60vh] overflow-y-auto py-2">
          {#each filteredActions as action, i}
            <button
              class="w-full text-left px-4 py-3 flex items-center gap-3 transition-colors focus:outline-none {i === selectedIndex ? 'bg-surface-hover text-accent border-l-2 border-accent' : 'text-primary hover:bg-surface-hover/50 border-l-2 border-transparent'}"
              on:click={() => handleClick(i)}
              on:mousemove={() => selectedIndex = i}
            >
              <span class="text-xl">{action.icon}</span>
              <span class="font-medium flex-1">{action.title}</span>
              {#if i === selectedIndex}
                <span class="text-xs text-accent/70 font-mono">⏎</span>
              {/if}
            </button>
          {/each}
        </div>
      {:else}
        <div class="py-12 px-4 text-center text-secondary">
          No results found for "{searchQuery}"
        </div>
      {/if}
      <div class="px-4 py-2 border-t border-glass-border bg-black/20 flex justify-between items-center text-xs text-secondary">
        <div class="flex items-center gap-4">
          <span class="flex items-center gap-1"><kbd class="bg-surface-hover border border-glass-border rounded px-1 font-mono">↑</kbd><kbd class="bg-surface-hover border border-glass-border rounded px-1 font-mono">↓</kbd> to navigate</span>
          <span class="flex items-center gap-1"><kbd class="bg-surface-hover border border-glass-border rounded px-1 font-mono">↵</kbd> to select</span>
        </div>
        <span>EchoSync Omnibar</span>
      </div>
    </div>
  </div>
{/if}

<style>
  .animate-fade-in {
    animation: fadeIn 0.15s ease-out forwards;
  }
  .animate-scale-in {
    animation: scaleIn 0.1s ease-out forwards;
    transform-origin: top center;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @keyframes scaleIn {
    from { opacity: 0; transform: scale(0.98); }
    to { opacity: 1; transform: scale(1); }
  }

  /* Styling scrollbar for glass effect */
  ::-webkit-scrollbar {
    width: 6px;
  }
  ::-webkit-scrollbar-track {
    background: transparent;
  }
  ::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 10px;
  }
  ::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.2);
  }
</style>
