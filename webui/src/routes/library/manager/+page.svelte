<script>
  import TabbedQueues from './TabbedQueues.svelte';
  import ManagerSidebar from './ManagerSidebar.svelte';
</script>

<svelte:head>
  <title>Media Manager | EchoSync</title>
</svelte:head>

<div class="h-full w-full flex flex-col gap-6 text-white p-6 md:p-10">
  <!-- Page Header -->
  <header class="flex justify-between items-center mb-4">
    <div class="flex flex-col">
      <div class="text-[10px] uppercase font-black tracking-[0.3em] text-primary mb-1">Media Management</div>
      <h1 class="text-3xl font-black tracking-tight flex items-center gap-3">
        Media Manager
        <span class="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
      </h1>
    </div>
    
    <div class="flex items-center gap-4">
      <div class="hidden md:flex flex-col items-end mr-4">
        <span class="text-[10px] text-muted uppercase font-bold">Consensus Status</span>
        <span class="text-xs text-emerald-400 font-bold">Synchronized</span>
      </div>
      <div class="w-10 h-10 rounded-full bg-surface border border-glass-border flex items-center justify-center hover:border-primary/50 transition-colors cursor-pointer">
        <svg class="w-5 h-5 text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
      </div>
    </div>
  </header>

  <!-- Main Layout Grid -->
  <div class="flex-grow grid grid-cols-1 lg:grid-cols-10 gap-8 min-h-0">
    <!-- Left Column: Queues (70%) -->
    <main class="lg:col-span-7 flex flex-col min-h-0 bg-surface/20 backdrop-blur-sm border border-glass-border rounded-[2rem] p-8 shadow-2xl">
      <TabbedQueues />
    </main>

    <!-- Right Column: Account Builder (30%) -->
    <div class="lg:col-span-3 flex flex-col min-h-0">
      <div class="flex-grow rounded-[2rem] overflow-hidden border border-glass-border shadow-2xl">
        <ManagerSidebar />
      </div>
    </div>
  </div>
</div>

<style>
  :global(body) {
    background-color: #050505;
    background-image: 
      radial-gradient(circle at 0% 0%, rgba(29, 185, 84, 0.05) 0%, transparent 50%),
      radial-gradient(circle at 100% 100%, rgba(0, 229, 255, 0.05) 0%, transparent 50%);
  }
</style>
