<script>
  import { onMount } from 'svelte';
  
  let settings = {
    enabled: true,
    auto_delete_low_quality_duplicates: false,
    auto_process_suggestion_engine_ratings: true
  };

  async function loadManagerSettings() {
    try {
      const r = await fetch('/api/manager/settings');
      if (r.ok) {
        const data = await r.json();
        settings = data.settings || settings;
      }
    } catch (e) { console.error(e); }
  }

  async function saveSettings() {
    try {
      await fetch('/api/manager/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(settings) });
      alert('Settings saved');
    } catch (e) { console.error(e); alert('Save failed'); }
  }

  async function runManagerScan() {
    try {
      const r = await fetch('/api/manager/scan', { method: 'POST' });
      if (r.ok) { alert('Scan complete'); }
    } catch (e) { console.error(e); alert('Scan failed'); }
  }

  async function runPruneJob() {
    if (!confirm('Run Prune Job?')) return;
    try {
      const r = await fetch('/api/manager/prune/run', { method: 'POST' });
      if (r.ok) { const j = await r.json(); alert(`Prune completed: ${j.result.deleted_count} deleted`); }
    } catch (e) { console.error(e); alert('Prune failed'); }
  }

  onMount(() => {
    loadManagerSettings();
  });
</script>

<div class="flex flex-col gap-4">
    <div class="flex justify-between items-center mb-4 border-b border-glass-border pb-3">
        <h3 class="text-xl font-bold text-white tracking-tight">Manager Settings</h3>
        <div class="flex gap-2">
            <button class="bg-primary text-black px-4 py-1.5 rounded-global font-bold text-sm hover:scale-95 transition-transform" on:click={saveSettings}>Save</button>
            <button class="bg-surface-hover text-white px-4 py-1.5 rounded-global font-bold text-sm border border-glass-border hover:scale-95 transition-transform" on:click={runManagerScan}>Scan</button>
            <button class="bg-red-500/20 text-red-400 border border-red-500/30 px-4 py-1.5 rounded-global font-bold text-sm hover:scale-95 hover:bg-red-500/30 transition-all" on:click={runPruneJob}>Prune</button>
        </div>
    </div>
    
    <div class="flex flex-col gap-3">
        <label class="flex items-center gap-3 cursor-pointer p-2 hover:bg-surface-hover rounded-global transition-colors">
            <input type="checkbox" bind:checked={settings.enabled} class="w-4 h-4 accent-primary" />
            <span class="text-sm font-semibold text-white">Enable Media Manager</span>
        </label>
        <label class="flex items-center gap-3 cursor-pointer p-2 hover:bg-surface-hover rounded-global transition-colors">
            <input type="checkbox" bind:checked={settings.auto_delete_low_quality_duplicates} class="w-4 h-4 accent-primary" />
            <span class="text-sm font-semibold text-white">Auto Delete Low Quality Duplicates</span>
        </label>
        <label class="flex items-center gap-3 cursor-pointer p-2 hover:bg-surface-hover rounded-global transition-colors">
            <input type="checkbox" bind:checked={settings.auto_process_suggestion_engine_ratings} class="w-4 h-4 accent-primary" />
            <span class="text-sm font-semibold text-white">Auto Process Ratings</span>
        </label>
    </div>
</div>
