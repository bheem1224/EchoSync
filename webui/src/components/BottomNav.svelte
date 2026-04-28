<script>
  import { goto } from '$app/navigation';
  const items = [
    { id: 'dashboard', label: 'Dashboard', href: '/' },
    { id: 'sync', label: 'Sync', href: '/sync' },
    { id: 'search', label: 'Search', href: '/search' },
    { id: 'settings', label: 'Settings', href: '/settings' }
  ];
  function nav(href) { goto(href); }
</script>

<nav class="bottom-nav">
  {#each items as it}
    <button class="nav-btn active:scale-95 transition-all duration-200" on:click={() => nav(it.href)}>{it.label}</button>
  {/each}
</nav>

<style>
  .bottom-nav { 
    display:flex; 
    gap:6px; 
    padding:8px; 
    justify-content:space-around; 
    background: var(--bg-sidebar);
    border-top: 1px solid var(--border-subtle);
    width: 100%;
  }
  .nav-btn { background:transparent; color:var(--text-main); border:none; padding:10px 12px; min-width:56px; min-height:44px; font-size: 12px; font-weight: 600; }
</style>
