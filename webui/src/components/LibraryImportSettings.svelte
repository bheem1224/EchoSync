<script>
  import { onMount, onDestroy } from 'svelte';
  import { settings } from '../stores/settings';

  let data = {
    auto_import_enabled: false,
    conflict_resolution: 'skip',
    renaming_template: '{Artist}/{Album}/{Track} - {Title}.{ext}'
  };

  const tokens = ['Artist', 'Album', 'Title', 'Year', 'Track', 'Format'];
  const previewData = {
    Artist: 'Daft Punk',
    Album: 'Random Access Memories',
    Title: 'Get Lucky',
    Year: '2013',
    Track: '01',
    Format: 'flac',
    ext: 'flac'
  };

  let preview = '';

  // subscribe to settings store to read current values
  let current;
  const unsub = settings.subscribe((v) => {
    current = v;
  });

  onDestroy(() => {
    if (unsub) unsub();
  });

  onMount(async () => {
    await settings.load();
    const config = current?.data?.metadata_enhancement || {};
    data = {
      auto_import_enabled: config.auto_import ?? false,
      conflict_resolution: config.conflict_resolution ?? 'skip',
      renaming_template: config.naming_template ?? '{Artist}/{Album}/{Track} - {Title}.{ext}'
    };
  });

  $: {
    let p = data.renaming_template;
    for (const [key, val] of Object.entries(previewData)) {
      p = p.replace(new RegExp(`{${key}}`, 'g'), val);
    }
    preview = p;
  }

  function addToken(token) {
    data.renaming_template += `{${token}}`;
  }

  export async function save() {
    const patch = {
      metadata_enhancement: {
        auto_import: data.auto_import_enabled,
        conflict_resolution: data.conflict_resolution,
        naming_template: data.renaming_template
      }
    };
    await settings.save(patch);
  }
</script>

<section class="library-import card">
  <div class="card-header">
    <h3>Library Import & Renaming</h3>
  </div>

  <div class="form">
    <label class="field checkbox-field">
      <span class="field-label">Auto-Import</span>
      <div class="checkbox-wrapper">
        <input type="checkbox" bind:checked={data.auto_import_enabled} />
        <span class="description">Automatically rename and move files with high match confidence (&gt;90%).</span>
      </div>
    </label>

    <label class="field">
      <span class="field-label">Conflict Resolution</span>
      <select class="dark-input input" bind:value={data.conflict_resolution}>
        <option value="skip">Skip</option>
        <option value="replace">Replace</option>
        <option value="keep_both">Keep Both</option>
      </select>
    </label>

    <div class="field stack">
      <span class="field-label">Renaming Pattern</span>
      <div class="input-group">
        <input class="dark-input input" type="text" bind:value={data.renaming_template} />
        <div class="tokens">
          {#each tokens as token}
            <button class="token-btn" on:click={() => addToken(token)}>{token}</button>
          {/each}
        </div>
      </div>
    </div>

    <div class="preview-box">
      <span class="preview-label">Preview:</span>
      <code>{preview}</code>
    </div>

  </div>
</section>

<style>
  .library-import { padding: 12px }
  .library-import .form { display:flex; flex-direction:column; gap:16px; padding-left:8px }
  .field { display:flex; gap:8px; align-items:center }
  .field.stack { flex-direction: column; align-items: flex-start; }
  .field-label { width:160px; color:var(--muted); padding-left:8px; flex-shrink: 0; }

  .dark-input { flex:1; padding:8px; border-radius:12px; background: rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.03); color:var(--text); width: 100%; box-sizing: border-box; }

  .checkbox-field { align-items: flex-start; }
  .checkbox-wrapper { display: flex; flex-direction: column; gap: 4px; }
  .description { font-size: 0.85em; color: var(--muted); }

  .input-group { width: 100%; display: flex; flex-direction: column; gap: 8px; }
  .tokens { display: flex; gap: 6px; flex-wrap: wrap; }
  .token-btn {
    background: rgba(255,255,255,0.1);
    border: none;
    border-radius: 4px;
    color: var(--text-main);
    padding: 4px 8px;
    font-size: 0.85em;
    cursor: pointer;
    transition: background 0.2s;
  }
  .token-btn:hover { background: rgba(255,255,255,0.2); }

  .preview-box {
    margin-top: -8px;
    margin-left: 176px; /* Align with input start (160px label + 8px gap + 8px padding) */
    background: rgba(0,0,0,0.3);
    padding: 8px;
    border-radius: 6px;
    font-family: monospace;
    font-size: 0.9em;
    color: var(--text-highlight);
    border: 1px solid rgba(255,255,255,0.05);
  }
  .preview-label { color: var(--muted); margin-right: 8px; font-size: 0.9em; }

  @media (max-width: 600px) {
    .preview-box { margin-left: 0; }
    .field { flex-direction: column; align-items: stretch; }
    .field-label { width: auto; padding-left: 0; margin-bottom: 4px; }
  }
</style>
