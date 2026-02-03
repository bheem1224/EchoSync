<script>
  import { onMount } from 'svelte';
  import { getConfig, setConfig } from '../../../stores/config';
  import { feedback } from '../../../stores/feedback';
  import apiClient from '../../../api/client';

  let config = {};
  let loaded = false;

  // Metadata Enhancement Settings
  let autoImport = false;
  let conflictResolution = 'replace';
  let renamingTemplate = '{Artist}/{Album}/{Track} - {Title}.{ext}';

  // Preview
  let previewPath = '';
  let previewLoading = false;

  // Download Settings
  let slskdDir = '/app/downloads';
  let libraryDir = '/app/Transfer';
  let logLevel = 'INFO';

  // Appearance
  let theme = 'dark';

  const tokens = ['{Artist}', '{Album}', '{Title}', '{Year}', '{Track}', '{Format}'];

  onMount(async () => {
    try {
      config = await getConfig();

      const meta = config.metadata_enhancement || {};
      autoImport = meta.auto_import ?? false;
      conflictResolution = meta.conflict_resolution ?? 'replace';
      renamingTemplate = meta.naming_template || '{Artist}/{Album}/{Track} - {Title}.{ext}';

      const dl = config.storage || {};
      slskdDir = dl.download_dir || '/app/downloads';
      libraryDir = dl.library_dir || '/app/Transfer';

      const log = config.logging || {};
      logLevel = log.level || 'INFO';

      loaded = true;
      updatePreview();
    } catch (e) {
      console.error('Failed to load preferences', e);
      feedback.addToast('Failed to load preferences', 'error');
    }
  });

  async function save() {
    try {
      feedback.setLoading(true);
      const updates = {
        metadata_enhancement: {
          ...config.metadata_enhancement,
          auto_import: autoImport,
          conflict_resolution: conflictResolution,
          naming_template: renamingTemplate
        },
        storage: {
           ...config.storage,
           download_dir: slskdDir,
           library_dir: libraryDir
        },
        logging: {
            ...config.logging,
            level: logLevel
        }
      };

      await setConfig(updates);
      feedback.addToast('Preferences saved', 'success');
      // refresh local config
      config = await getConfig();
    } catch (e) {
      console.error('Failed to save preferences', e);
      feedback.addToast('Failed to save preferences', 'error');
    } finally {
      feedback.setLoading(false);
    }
  }

  function addToken(token) {
    renamingTemplate += token;
    updatePreview();
  }

  async function updatePreview() {
    if (!renamingTemplate) return;
    previewLoading = true;
    try {
      const resp = await apiClient.post('/settings/preview-rename', {
        template: renamingTemplate
      });
      previewPath = resp.data.preview;
    } catch (e) {
      console.error('Preview failed', e);
    } finally {
      previewLoading = false;
    }
  }

  // Debounce preview update on input
  let debounceTimer;
  function onTemplateInput() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(updatePreview, 500);
  }
</script>

<svelte:head>
  <title>Preferences • SoulSync</title>
</svelte:head>

<div class="page">
  <header class="page__header">
    <h1>Preferences</h1>
    <button class="btn-primary" on:click={save}>Save Changes</button>
  </header>

  {#if loaded}
    <div class="grid">
        <!-- Library Import & Renaming -->
        <section class="card">
            <h2>Library Import & Renaming</h2>

            <div class="field-row">
                <label class="switch-label">
                    <input type="checkbox" bind:checked={autoImport} />
                    <span class="label-text">Auto-Import High Confidence Matches</span>
                </label>
                <p class="help-text">Automatically rename and move files with high match confidence (&gt;90%).</p>
            </div>

            <div class="field">
                <label>Conflict Resolution</label>
                <select bind:value={conflictResolution}>
                    <option value="replace">Replace Existing</option>
                    <option value="skip">Skip</option>
                    <option value="keep_both">Keep Both</option>
                </select>
            </div>

            <div class="field">
                <label>Renaming Pattern</label>
                <div class="renaming-builder">
                    <input type="text" bind:value={renamingTemplate} on:input={onTemplateInput} class="code-input" />
                    <div class="tokens">
                        {#each tokens as token}
                            <button class="token-btn" on:click={() => addToken(token)}>{token}</button>
                        {/each}
                    </div>
                </div>
            </div>

            <div class="preview-box">
                <span class="preview-label">Preview:</span>
                {#if previewLoading}
                    <span class="muted">Generating...</span>
                {:else}
                    <code class="preview-code">{previewPath}</code>
                {/if}
            </div>
        </section>

        <!-- Download Settings -->
        <section class="card">
            <h2>Download Settings</h2>
            <div class="field">
                <label>Download Directory</label>
                <input type="text" bind:value={slskdDir} />
            </div>
            <div class="field">
                <label>Library Directory</label>
                <input type="text" bind:value={libraryDir} />
            </div>
            <div class="field">
                <label>Log Level</label>
                <select bind:value={logLevel}>
                    <option value="DEBUG">DEBUG</option>
                    <option value="INFO">INFO</option>
                    <option value="WARNING">WARNING</option>
                    <option value="ERROR">ERROR</option>
                </select>
            </div>
        </section>

        <!-- Appearance -->
        <section class="card">
            <h2>Appearance</h2>
            <div class="field">
                <label>Theme</label>
                <select bind:value={theme}>
                    <option value="dark">Dark</option>
                    <option value="light">Light</option>
                </select>
            </div>
        </section>
    </div>
  {:else}
    <div class="loading">Loading preferences...</div>
  {/if}
</div>

<style>
  .page {
    padding: 20px;
    max-width: 900px;
    margin: 0 auto;
  }

  .page__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
  }

  h1 { margin: 0; font-size: 24px; }
  h2 { margin: 0 0 16px 0; font-size: 18px; border-bottom: 1px solid var(--border); padding-bottom: 8px; }

  .grid {
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px;
  }

  .field {
    margin-bottom: 16px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .field-row {
    margin-bottom: 16px;
  }

  label { font-weight: 500; font-size: 14px; }

  input[type="text"], select {
    padding: 8px 12px;
    background: var(--input-bg);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text);
    font-family: inherit;
  }

  .code-input {
    font-family: monospace;
  }

  .tokens {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-top: 8px;
  }

  .token-btn {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
    cursor: pointer;
    font-family: monospace;
    color: var(--accent);
  }

  .token-btn:hover {
    background: var(--hover-bg);
  }

  .preview-box {
    margin-top: 12px;
    padding: 12px;
    background: rgba(0,0,0,0.2);
    border-radius: 4px;
    font-family: monospace;
    font-size: 13px;
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .preview-label { color: var(--muted); }
  .preview-code { color: var(--success, #4ade80); }

  .switch-label {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
  }

  .help-text {
    margin: 4px 0 0 24px; /* Align with text */
    font-size: 12px;
    color: var(--muted);
  }

  .btn-primary {
    background: var(--accent);
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    cursor: pointer;
    font-weight: 500;
  }

  .btn-primary:hover {
    filter: brightness(1.1);
  }

  .loading {
    text-align: center;
    padding: 40px;
    color: var(--muted);
  }

  .muted { color: var(--muted); }
</style>
