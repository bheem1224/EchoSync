<script>
  import { page } from '$app/stores';
  import { providers } from '../stores/providers';
  import { metadataQueue } from '../stores/metadataQueue';
  import { openSettings } from '../stores/settingsPanel';
  import { pluginViews } from '../stores/pluginViews';
  import { sidebarPrefs, LOCKED_ROUTES } from '../stores/preferences';
  import { onMount } from 'svelte';

  let providerCapabilities = $state([]);

  onMount(() => {
    metadataQueue.fetchCount();
  });

  // Sync provider capabilities reactively
  $effect(() => {
    if ($providers.loaded) {
      providerCapabilities = Object.values($providers.items)
        .filter((p) => !p.disabled)
        .map((p) => p.capabilities);
    }
  });

  // ── Core nav links definition ──────────────────────────────────────────
  // LOCKED = always visible, user cannot hide them.
  // dynamic = user can toggle visibility in Preferences.
  const ALL_NAV_LINKS = [
    { label: 'Dashboard', href: '/dashboard', icon: '🏠',  locked: false },
    { label: 'Sync',      href: '/sync',      icon: '🔄',  locked: true  },
    { label: 'Search',    href: '/search',    icon: '🔍',  locked: false,
      guard: () => providerCapabilities.some((c) => c?.search?.tracks) },
    { label: 'Discover',  href: '/discover',  icon: '✨',  locked: false },
    { label: 'Library',   href: '/library',   icon: '🎵',  locked: true  },
  ];

  // ── Derived: visible nav links (respects sidebarPrefs.hiddenRoutes) ──
  const hiddenSet    = $derived(new Set($sidebarPrefs?.hiddenRoutes ?? []));
  const visibleLinks = $derived(ALL_NAV_LINKS.filter(link =>
    link.locked || !hiddenSet.has(link.href)
  ));

  // ── Derived: pinned plugin views ──────────────────────────────────────
  const pinnedIds   = $derived($sidebarPrefs?.pinnedViews ?? []);
  const allViews    = $derived($pluginViews);
  const pinnedViews = $derived(pinnedIds
    .map(id => allViews.find(v => v.id === id))
    .filter(Boolean));

  // ── Settings links ────────────────────────────────────────────────────
  const settingsLinks = $derived([
    { label: 'Preferences',       href: '/settings/preferences' },
    { label: '── Providers',      href: null, divider: true },
    { label: 'Music Services',    href: '/settings/music-services' },
    { label: 'Servers',           href: '/settings/servers' },
    { label: 'Download Clients',  href: '/settings/download-clients' },
    { label: '── Plugins',        href: null, divider: true },
    { label: 'Plugin Store',      href: '/settings/plugin-store' },
    { label: '── Other',          href: null, divider: true },
    { label: 'Metadata',          href: '/settings/metadata' },
    { label: 'Search',            href: '/settings/search' },
    { label: 'Misc',              href: '/settings/misc' },
    { label: 'Jobs',              href: '/settings/jobs' },
    { label: 'System',            href: '/settings/system' },
  ]);

  let settingsOpen = $state(false);

  const isActive   = (href) => $page.url.pathname.startsWith(href);

  function toggleSettings() {
    settingsOpen = !settingsOpen;
    if (settingsOpen) openSettings('preferences');
    else openSettings();
  }
</script>

<nav class="sidebar glass">
  <!-- ── Logo ───────────────────────────────────────────────────────────── -->
  <div class="sidebar-header">
    <div class="logo">EchoSync</div>
    <p class="app-subtitle">Music Sync &amp; Manager</p>
  </div>

  <!-- ── Main navigation ────────────────────────────────────────────────── -->
  <div class="section">
    {#each visibleLinks as link (link.href)}
      {#if !link.guard || link.guard()}
        <a
          class="nav-item"
          class:active={isActive(link.href)}
          href={link.href}
          aria-label={link.label}
        >
          <span class="icon" aria-hidden="true">{link.icon}</span>
          <span>{link.label}</span>
          {#if link.locked}
            <span class="lock-badge" title="Cannot be hidden" aria-hidden="true">🔒</span>
          {/if}
        </a>
      {/if}
    {/each}

    <!-- ── Pinned plugin views ─────────────────────────────────────────── -->
    {#if pinnedViews.length > 0}
      <div class="pinned-section-label" aria-label="Pinned Plugin Views">Plugins</div>
      {#each pinnedViews as view (view.id)}
        <a
          class="nav-item nav-item--plugin"
          class:active={$page.url.pathname === view.href}
          href={view.href}
          title={view.title}
        >
          <span class="icon" aria-hidden="true">{view.icon}</span>
          <span class="nav-item__label">{view.title}</span>
          <span class="plugin-badge" aria-hidden="true">↗</span>
        </a>
      {/each}
    {/if}
  </div>

  <!-- ── Settings flyout ────────────────────────────────────────────────── -->
  <div class="section">
    <a
      role="button"
      class="nav-item settings-item"
      href="/settings/preferences"
      on:click|preventDefault={toggleSettings}
      class:active={!settingsOpen && isActive('/settings')}
    >
      <span class="icon">⚙️</span>
      <span>Settings</span>
      <span class="chevron" aria-hidden="true">{settingsOpen ? '▾' : '▸'}</span>
    </a>

    {#if settingsOpen}
      <div class="settings-links">
        {#each settingsLinks as link}
          {#if link.divider}
            <span class="settings-section-label">{link.label.replace(/^── /, '')}</span>
          {:else if link.href}
            <a
              class="nav-sub"
              href={link.href}
              class:active={$page.url.pathname === link.href}
            >
              {link.label}
              {#if link.badge > 0}
                <span class="badge">{link.badge}</span>
              {/if}
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
    background:
      radial-gradient(circle at 20% 20%, rgba(15, 239, 136, 0.08), transparent 35%),
      radial-gradient(circle at 100% 0%,  rgba(14, 165, 233, 0.08), transparent 30%),
      var(--glass);
  }

  .sidebar-header {
    border-bottom: 1px solid var(--border);
    padding-bottom: 12px;
  }
  .logo { font-weight: 800; letter-spacing: 0.5px; color: var(--accent); }
  .app-subtitle { margin: 4px 0 0; color: var(--muted); font-size: 13px; }

  .section { margin-top: 20px; }

  /* ── Nav items ────────────────────────────────────────────────────── */
  .nav-item {
    display: flex; align-items: center; gap: 8px;
    padding: 8px 12px; border-radius: 8px;
    text-decoration: none; color: var(--text);
    transition: background 0.2s;
    position: relative;
  }
  .nav-item:hover { background: rgba(255,255,255,0.05); }
  .nav-item.active { background: var(--accent); color: var(--background); }

  .nav-item--plugin { font-size: 13px; }
  .nav-item__label  { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  .icon  { flex-shrink: 0; width: 20px; text-align: center; }
  .chevron { margin-left: auto; font-size: 10px; opacity: 0.6; }
  .lock-badge { margin-left: auto; font-size: 9px; opacity: 0.35; }
  .plugin-badge { margin-left: auto; font-size: 9px; opacity: 0.4; }

  /* ── Pinned plugin section label ──────────────────────────────────── */
  .pinned-section-label {
    display: block;
    font-size: 9px; font-weight: 900; letter-spacing: 0.18em;
    text-transform: uppercase; color: var(--muted);
    padding: 14px 12px 4px;
    pointer-events: none; user-select: none;
  }

  /* ── Settings flyout ──────────────────────────────────────────────── */
  .settings-item { cursor: pointer; }
  .settings-links { margin-top: 8px; display: flex; flex-direction: column; gap: 6px; }
  .settings-section-label {
    display: block; font-size: 10px; font-weight: 700;
    letter-spacing: 0.08em; text-transform: uppercase;
    color: var(--muted); padding: 10px 12px 2px;
    pointer-events: none; user-select: none;
  }
  .nav-sub {
    display: flex; align-items: center;
    padding: 8px 12px; border-radius: 12px;
    text-decoration: none; color: var(--muted);
    font-size: 13px; transition: background 0.2s;
  }
  .nav-sub:hover  { background: rgba(255,255,255,0.05); color: var(--text); }
  .nav-sub.active { background: var(--accent); color: var(--background); }

  .badge {
    margin-left: auto; background: #ef4444; color: white;
    font-size: 10px; font-weight: bold;
    padding: 2px 6px; border-radius: 10px; min-width: 16px; text-align: center;
  }
</style>