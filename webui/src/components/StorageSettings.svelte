<script>
  import { onMount } from 'svelte';
  import FileBrowser from './FileBrowser.svelte';
  import ConfirmDialog from './ConfirmDialog.svelte';
  import { settings } from '../stores/settings';

  let data = {};
  let showBrowser = false;
  let browserStart = '';
  let browserField = null; // which field opened the browser
  let showConfigWarning = false;

  function proceedToConfigPicker() {
    showConfigWarning = false;
    browserField = 'config_dir';
    browserStart = data.config_dir || 'config';
    showBrowser = true;
  }

  function cancelConfigEdit() {
    showConfigWarning = false;
  }

  // subscribe to settings store to read current values
  let current;
  const unsub = settings.subscribe((v) => (current = v));

  onMount(async () => {
    await settings.load();
    const storage = current?.data?.storage || {};
    data = {
      download_dir: storage.download_dir || '',
      library_dir: storage.library_dir || '',
      log_dir: storage.log_dir || '',
      config_dir: storage.config_dir || ''
    };
  });

  export async function save() {
    const patch = {
      storage: {
        download_dir: data.download_dir,
        library_dir: data.library_dir,
        log_dir: data.log_dir,
        config_dir: data.config_dir
      }
    };
    await settings.save(patch);
  }
</script>

<section class="storage card">
  <div class="card-header">
    <h3>Storage Locations</h3>
  </div>

  <div class="form">
      <label class="field">
          <span class="field-label">Download</span>
          <input class="dark-input input" type="text" bind:value={data.download_dir} placeholder="/app/downloads" />
          <button class="dark-btn active:scale-95 transition-all duration-200" aria-label="Browse download directory" on:click={() => { browserField='download_dir'; browserStart = data.download_dir || 'downloads'; showBrowser = true; }}>Browse</button>
        </label>

    <label class="field">
      <span class="field-label">Library</span>
      <input class="dark-input input" type="text" bind:value={data.library_dir} placeholder="/app/library" />
      <button class="dark-btn active:scale-95 transition-all duration-200" aria-label="Browse library directory" on:click={() => { browserField='library_dir'; browserStart = data.library_dir || 'data'; showBrowser = true; }}>Browse</button>
    </label>

    <label class="field">
      <span class="field-label">Log</span>
      <input class="dark-input input" type="text" bind:value={data.log_dir} placeholder="/app/logs" />
      <button class="dark-btn active:scale-95 transition-all duration-200" aria-label="Browse log directory" on:click={() => { browserField='log_dir'; browserStart = data.log_dir || 'logs'; showBrowser = true; }}>Browse</button>
    </label>

    <label class="field">
      <span class="field-label">Config</span>
      <input class="dark-input input" type="text" bind:value={data.config_dir} placeholder="/app/config" />
      <button class="dark-btn active:scale-95 transition-all duration-200" aria-label="Browse config directory" on:click={() => { showConfigWarning = true; }}>Browse</button>
    </label>

    <!-- Save moved to page header. Use exported `save()` from parent via component ref. -->
  </div>
</section>

{#if showBrowser}
  <FileBrowser startPath={browserStart} on:select={(e) => {
    const p = e.detail?.path;
    if (p && browserField) data[browserField] = p;
    showBrowser = false;
    browserField = null;
  }} on:close={() => { showBrowser = false; browserField = null; }} />
{/if}

{#if showConfigWarning}
    <ConfirmDialog 
        title="⚠️ Severe Warning: Configuration Path"
        confirmText="I understand, let me pick a folder"
        cancelText="Cancel"
        danger={true}
        on:confirm={proceedToConfigPicker}
        on:cancel={cancelConfigEdit}
    >
        <div class="flex flex-col gap-3 text-sm mt-2">
            <p>Changing this path will <strong>NOT</strong> move your existing database or encryption keys.</p>
            <p>If you change this path, you must ensure it is permanently mapped in your <code>docker-compose.yml</code> file, or your configuration will be permanently lost on the next restart.</p>
            <p class="text-red-400 font-bold">EchoSync will require a full restart to bind to the new database location.</p>
        </div>
    </ConfirmDialog>
{/if}

<style>
  .storage { padding: 12px }
  .storage .form { display:flex; flex-direction:column; gap:10px; padding-left:8px }
  .field { display:flex; gap:8px; align-items:center }
  .field-label { width:160px; color:var(--muted); padding-left:8px }
  .dark-input { flex:1; padding:8px; border-radius:12px; background: rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.03); color:var(--text); }
  .dark-btn { padding:8px 10px; border-radius:12px; background: rgba(0,0,0,0.6); color:#fff; border:none }
  .actions { margin-top:8px }
  .save-btn { background: #0b0b0b; color: #fff; padding:10px 14px; border-radius:14px; border:none }
</style>
