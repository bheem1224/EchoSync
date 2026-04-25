<script>
  import { onMount } from 'svelte';
  
  let settings = {
    enabled: true,
    auto_delete_low_quality_duplicates: false,
    auto_process_suggestion_engine_ratings: true,
    auto_delete_staged_queue: false,
    auto_upgrade_staged_queue: false,
    delete_threshold: 1,
    upgrade_threshold: 2,
    upgrade_quality_profile: 'Default'
  };

  let collapsed = false;

  async function loadManagerSettings() {
    try {
      const r = await fetch('/api/manager/settings');
      if (r.ok) {
        const data = await r.json();
        settings = { ...settings, ...data.settings };
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

<div class="flex flex-col">
    <div class="flex items-center justify-between mb-6 border-b border-glass-border pb-3 cursor-pointer" on:click={() => collapsed = !collapsed}>
        <div class="flex items-center gap-2">
            <span class="text-xl">⚙️</span>
            <h3 class="text-lg font-bold text-white tracking-tight">Manager Settings</h3>
        </div>
        <button class="text-muted hover:text-white text-sm font-semibold transition-colors">
            {collapsed ? 'Show ▼' : 'Hide ▲'}
        </button>
    </div>
    
    {#if !collapsed}
    <div class="grid grid-cols-1 md:grid-cols-3 gap-x-8 gap-y-6 mb-6">
        <div class="flex flex-col gap-6">
            <div class="flex items-center justify-between">
                <span class="text-sm font-bold text-white">Enable Media Manager</span>
                <label class="switch">
                    <input type="checkbox" bind:checked={settings.enabled} />
                    <span class="slider round"></span>
                </label>
            </div>
            <div class="flex items-center justify-between">
                <span class="text-sm font-bold text-white flex items-center gap-2">Auto Delete Staged Queue <span class="text-muted cursor-help">ⓘ</span></span>
                <label class="switch">
                    <input type="checkbox" bind:checked={settings.auto_delete_staged_queue} />
                    <span class="slider round"></span>
                </label>
            </div>
            <div class="flex items-center gap-3">
                <span class="text-xs text-muted">Delete Threshold:</span>
                <input type="number" bind:value={settings.delete_threshold} class="bg-[#08080a] border border-[rgba(255,255,255,0.08)] rounded px-2 py-1 text-sm text-white w-16 focus:border-primary outline-none" />
            </div>
        </div>

        <div class="flex flex-col gap-6">
            <div class="flex items-center justify-between">
                <span class="text-sm font-bold text-white flex items-center gap-2">Auto-Delete Low Quality Duplicates <span class="text-muted cursor-help">ⓘ</span></span>
                <label class="switch">
                    <input type="checkbox" bind:checked={settings.auto_delete_low_quality_duplicates} />
                    <span class="slider round"></span>
                </label>
            </div>
            <div class="flex items-center justify-between">
                <span class="text-sm font-bold text-white flex items-center gap-2">Auto Upgrade Staged Queue <span class="text-muted cursor-help">ⓘ</span></span>
                <label class="switch">
                    <input type="checkbox" bind:checked={settings.auto_upgrade_staged_queue} />
                    <span class="slider round"></span>
                </label>
            </div>
            <div class="flex items-center gap-3">
                <span class="text-xs text-muted">Upgrade Threshold:</span>
                <input type="number" bind:value={settings.upgrade_threshold} class="bg-[#08080a] border border-[rgba(255,255,255,0.08)] rounded px-2 py-1 text-sm text-white w-16 focus:border-primary outline-none" />
            </div>
        </div>

        <div class="flex flex-col gap-6">
            <div class="flex items-center justify-between">
                <span class="text-sm font-bold text-white flex items-center gap-2">Auto-Process Suggestion Engine Ratings <span class="text-muted cursor-help">ⓘ</span></span>
                <label class="switch">
                    <input type="checkbox" bind:checked={settings.auto_process_suggestion_engine_ratings} />
                    <span class="slider round"></span>
                </label>
            </div>
            <div class="flex flex-col gap-2">
                <span class="text-xs text-muted">Upgrade Quality Profile:</span>
                <select bind:value={settings.upgrade_quality_profile} class="bg-[#08080a] border border-[rgba(255,255,255,0.08)] rounded px-2 py-1.5 text-sm text-white focus:border-primary outline-none w-full max-w-[200px]">
                    <option>Default</option>
                </select>
            </div>
        </div>
    </div>

    <div class="flex flex-col lg:flex-row items-stretch lg:items-end justify-between gap-4 mt-2">
        <div class="bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.05)] rounded-lg p-4 max-w-3xl text-[11px] text-muted leading-relaxed">
            <span class="font-bold text-white/70">Duplicate Resolution:</span> Detects duplicate tracks, keeps the highest quality copy (bitrate and file size), and deletes inferior versions when auto-delete is enabled.<br/>
            <span class="font-bold text-white/70 mt-1 inline-block">Suggestion Engine Thresholds:</span> Scores 1-2 (0.5 to 1 star equivalent) are scheduled for end-of-month deletion. Scores 3-4 are scheduled for weekly upgrades, unless vetoed by an administrator.
        </div>
        
        <div class="flex flex-wrap gap-3">
            <button class="bg-primary text-black px-4 py-2 rounded-lg font-bold text-sm hover:scale-95 hover:bg-[#0d9488] transition-all" on:click={saveSettings}>Save Settings</button>
            <button class="bg-transparent border border-[rgba(255,255,255,0.08)] text-white px-4 py-2 rounded-lg font-bold text-sm hover:border-[rgba(255,255,255,0.18)] hover:scale-95 transition-all" on:click={runManagerScan}>Run Manager Scan</button>
            <button class="bg-[#b04242]/20 border border-[#b04242]/30 text-[#ef4444] px-4 py-2 rounded-lg font-bold text-sm hover:scale-95 hover:bg-[#b04242]/30 transition-all" on:click={runPruneJob}>Run Prune Job</button>
        </div>
    </div>
    {/if}
</div>
