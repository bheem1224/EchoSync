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

<nav class="bottom-nav card">
  {#each items as it}
    <button class="nav-btn" on:click={() => nav(it.href)}>{it.label}</button>
  {/each}
</nav>

<style>
  .bottom-nav { position:fixed; left:0; right:0; bottom:0; display:flex; gap:6px; padding:8px; justify-content:space-around; border-radius:14px 14px 0 0 }
  .nav-btn { background:transparent; color:var(--text-main); border:none; padding:10px 12px; min-width:56px; min-height:44px }
</style>
