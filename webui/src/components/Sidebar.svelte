<script>
  import { page } from '$app/stores';
  import { providers } from '../stores/providers';
  import { openSettings } from '../stores/settingsPanel';
  import { goto } from '$app/navigation';

  let providerCapabilities = [];
  let settingsOpen = false; // Default to collapsed

  $: {
    if ($providers.loaded) {
      providerCapabilities = Object.values($providers.items)
        .filter((p) => !p.disabled) // Exclude disabled providers
        .map((p) => p.capabilities);
    }
  }

  const settingsLinks = [
    { label: 'Preferences', href: '/settings#preferences' },
    // Use the dedicated route for Music Services
    { label: 'Music Services', href: '/settings/music-services' },
    { label: 'Servers', href: '/settings/servers' },
    { label: 'Download Clients', href: '/settings/download-clients' },
    { label: 'Metadata', href: '/settings/metadata' },
    { label: 'Search', href: '/settings/search' },
    { label: 'Misc', href: '/settings/misc' },
    { label: 'Jobs', href: '/settings/jobs' },
    { label: 'System', href: '/settings/system' }
  ];

  const navLinks = [
    { label: 'Dashboard', href: '/dashboard', icon: '🏠' },
    { label: 'Sync', href: '/sync', icon: '🔄' },
    { label: 'Search', href: '/search', icon: '🔍', guard: () => providerCapabilities.some((c) => c?.search?.tracks) },
    { label: 'Discover', href: '/discover', icon: '✨' },
    { label: 'Library', href: '/library', icon: '🎵' }
  ];

  const isActive = (href) => $page.url.pathname.startsWith(href);

  function toggleSettings() {
    // toggle only the settings panel state and open preferences; rely on native anchor href for navigation
    settingsOpen = !settingsOpen;
    if (settingsOpen) {
      openSettings('preferences');
    } else {
      openSettings();
    }
  }
</script>

<nav class="sidebar glass">
  <div class="sidebar-header">
    <div class="logo">SoulSync</div>
    <p class="app-subtitle">Music Sync & Manager</p>
  </div>

  <div class="section">
    {#each navLinks as link}
      <a class:active={isActive(link.href)} class="nav-item" href={link.href}>
        <span class="icon">{link.icon}</span>
        <span>{link.label}</span>
      </a>
    {/each}
  </div>

  <div class="section">
    <a
      role="button"
      class="nav-item settings-item"
      href="/settings#preferences"
      on:click={toggleSettings}
      class:active={isActive('/settings') || settingsOpen}
    >
      <span class="icon">⚙️</span>
      <span>Settings</span>
      <span class="chevron">{settingsOpen ? '▾' : '▸'}</span>
    </a>

    {#if settingsOpen}
      <div class="settings-links">
        {#each settingsLinks as link}
          {#if link.href.includes('#')}
            <a
              class="nav-sub"
              href={link.href}
              class:active={$page.url.pathname.startsWith('/settings') && $page.url.hash === ('#' + link.href.split('#')[1])}
            >
              {link.label}
            </a>
          {:else}
            <a
              class="nav-sub"
              href={link.href}
              class:active={$page.url.pathname === link.href}
            >
              {link.label}
            </a>
          {/if}
        {/each}
      </div>
    {/if}
  </div>
</nav>

<style>
  .sidebar {
    width: 240px;
    padding: 18px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    background: radial-gradient(circle at 20% 20%, rgba(15, 239, 136, 0.08), transparent 35%),
      radial-gradient(circle at 100% 0%, rgba(14, 165, 233, 0.08), transparent 30%),
      var(--glass);
  }

  .sidebar-header {
    border-bottom: 1px solid var(--border);
    padding-bottom: 12px;
  }

  .logo {
    font-weight: 800;
    letter-spacing: 0.5px;
    color: var(--accent);
  }

  .app-subtitle {
    margin: 4px 0 0;
    color: var(--muted);
    font-size: 13px;
  }

  .section {
    margin-top: 20px;
  }

  .section-title {
    font-size: 12px;
    color: var(--muted);
    margin-bottom: 8px;
  }

  .settings-toggle {
    display: flex;
    justify-content: space-between;
    cursor: pointer;
    color: var(--text);
  }

  .settings-links {
    margin-top: 8px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .nav-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    border-radius: 8px;
    text-decoration: none;
    color: var(--text);
    transition: background 0.2s;
  }

  .nav-item.active {
    background: var(--accent);
    color: var(--background);
  }

  .nav-sub {
    padding: 8px 12px;
    border-radius: 12px;
    text-decoration: none;
    color: var(--muted);
    transition: background 0.2s;
  }

  .nav-sub.active {
    background: var(--accent);
    color: var(--background);
  }
</style>