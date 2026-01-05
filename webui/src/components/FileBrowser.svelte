<script>
  import { createEventDispatcher, onMount } from 'svelte';
  const dispatch = createEventDispatcher();

  export let startPath = '';
  let currentPath = startPath;
  let editablePath = startPath;
  let entries = [];
  let rootKey = null;
  let loading = false;
  let error = null;
  let selected = null;

  async function fetchPath(path) {
    loading = true;
    error = null;
    try {
      const res = await fetch(`/api/browse?path=${encodeURIComponent(path)}`);
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error || res.statusText);
      }
      const data = await res.json();
      currentPath = data.path;
      editablePath = currentPath;
      rootKey = data.root;
      entries = data.entries || [];
      selected = null;
    } catch (e) {
      error = String(e.message || e);
      entries = [];
    } finally {
      loading = false;
    }
  }

  function selectEntry(entry, nav=false) {
    // single click selects; double-click navigates
    selected = entry.path;
    if (nav && entry.is_dir) fetchPath(entry.path);
  }

  function getParentPath(p) {
    if (!p) return null;
    // Normalize separators to '/'
    let np = p.replace(/\\\\/g, '/').replace(/\\/g, '/');
    // Remove trailing slash unless it's just the root like 'C:/' or '/'
    if (np.length > 1 && np.endsWith('/')) np = np.slice(0, -1);
    // Windows drive-only like 'C:'
    if (/^[A-Za-z]:$/.test(np)) return np + '/';
    const parts = np.split('/');
    if (parts.length <= 1) return np; // already root
    parts.pop();
    let parent = parts.join('/');
    if (parent === '') parent = '/';
    // Convert single-letter drive back to 'C:/' form
    if (/^[A-Za-z]:$/.test(parent)) parent += '/';
    return parent;
  }

  function goUp() {
    if (!currentPath) return;
    const parent = getParentPath(currentPath);
    if (parent && parent !== currentPath) fetchPath(parent);
  }

  function chooseCurrent() {
    const pathToReturn = selected || editablePath || currentPath;
    dispatch('select', { path: pathToReturn });
  }

  function close() {
    dispatch('close');
  }

  onMount(async () => {
    // If startPath empty, request roots and pick downloads if present
    if (!startPath) {
      const rootsRes = await fetch('/api/browse');
      if (rootsRes.ok) {
        const d = await rootsRes.json();
        const downloads = (d.roots || []).find(r => r.key === 'downloads');
        const pick = downloads ? downloads.key : (d.roots && d.roots[0] && d.roots[0].key) || '';
        await fetchPath(pick);
      } else {
        await fetchPath('');
      }
    } else {
      await fetchPath(startPath);
    }
  });
</script>

<div class="file-browser-overlay">
  <div class="file-browser">
    <div class="fb-header">
      <div class="fb-title">Browse</div>
      <div class="fb-actions">
        <button class="dark-btn" on:click={goUp} disabled={loading}>Up</button>
        <button class="dark-btn" on:click={chooseCurrent} disabled={loading}>Select</button>
        <button class="dark-btn" on:click={close}>Close</button>
      </div>
    </div>

    <div class="fb-path-row">
      <input class="fb-path-input" bind:value={editablePath} on:keydown={(e) => { if (e.key === 'Enter') fetchPath(editablePath); }} />
      <button class="dark-btn fb-go" on:click={() => fetchPath(editablePath)} disabled={loading}>Go</button>
    </div>
    {#if error}
      <div class="fb-error">{error}</div>
    {/if}

    <div class="fb-list">
      {#if loading}
        <div class="fb-loading">Loading…</div>
      {:else}
        {#each entries as e}
          <div class="fb-entry" on:click={() => { if (e.is_dir) fetchPath(e.path); else selected = e.path; }}>
            <span class="fb-name">{e.is_dir ? '📁' : '📄'} {e.name}</span>
            <span class="fb-meta">{e.is_dir ? 'Folder' : ''}</span>
          </div>
        {/each}
      {/if}
    </div>
  </div>
</div>

<style>
  .file-browser-overlay{position:fixed;inset:0;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;z-index:60}
  .file-browser{width:720px;max-width:95%;background:var(--surface);border-radius:12px;padding:12px;color:var(--text)}
  .fb-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
  .fb-title{font-weight:600}
  .fb-actions button{margin-left:8px}
  .fb-path-row{display:flex;gap:8px;align-items:center;margin-bottom:8px}
  .fb-path-input{flex:1;padding:8px;border-radius:8px;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.03);color:var(--text);font-size:14px}
  .fb-go{padding:8px 10px}
  .fb-list{max-height:340px;overflow:auto;border-top:1px solid rgba(255,255,255,0.03);padding-top:8px}
  .fb-entry{display:flex;justify-content:space-between;align-items:center;padding:8px;border-radius:8px}
  .fb-entry:hover{background:rgba(255,255,255,0.02);cursor:pointer}
  .fb-name{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .fb-error{color:var(--accent);padding:8px}
</style>
