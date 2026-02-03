<script>
  import { writable } from 'svelte/store';
  import { getConfig, setConfig } from '../../../stores/config';
  import apiClient from '../../../api/client';
  import { feedback } from '../../../stores/feedback';
  import { onMount } from 'svelte';

  // --- Original Stores ---
  const downloadSettings = writable({
    slskdDir: '/app/downloads',
    libraryDir: '/app/Transfer',
    logLevel: 'INFO'
  });

  const appearanceSettings = writable({
    theme: 'dark'
  });

  const qualityProfiles = writable([]);

  const playlistAlgorithm = writable('DefaultPlaylistAlgorithm');
  const availableAlgorithms = writable([]);

  // --- New Logic for Library Import ---
  let autoImport = false;
  let conflictResolution = 'replace';
  let renamingTemplate = '{Artist}/{Album}/{Track} - {Title}.{ext}';
  let previewPath = '';
  let previewLoading = false;
  const tokens = ['{Artist}', '{Album}', '{Title}', '{Year}', '{Track}', '{Format}'];

  let debounceTimer;

  // --- Functions ---

  function addProfile() {
    qualityProfiles.update((profiles) => {
      profiles.push({ name: 'New Profile', formats: [] });
      return profiles;
    });
  }

  function removeProfile(index) {
    qualityProfiles.update((profiles) => {
      profiles.splice(index, 1);
      return profiles;
    });
  }

  async function fetchAlgorithms() {
    try {
      const config = await getConfig();
      availableAlgorithms.set(config.available_algorithms || []);
      playlistAlgorithm.set(config.playlist_algorithm || 'DefaultPlaylistAlgorithm');

      // Load Metadata Config
      const meta = config.metadata_enhancement || {};
      autoImport = meta.auto_import ?? false;
      conflictResolution = meta.conflict_resolution ?? 'replace';
      renamingTemplate = meta.naming_template || '{Artist}/{Album}/{Track} - {Title}.{ext}';
      updatePreview();

      // Load Download Config (attempting to sync with original store if possible)
      // The original code didn't load this, but we should probably try to reflect reality if we can.
      // But to be safe and "restore" strict behavior, I'll leave the store defaults unless explicitly asked.
      // However, for the NEW feature, I must load/save.

    } catch (e) {
      console.error("Failed to load config", e);
    }
  }

  async function saveAlgorithm() {
    await setConfig({ playlist_algorithm: $playlistAlgorithm });
  }

  // New Save for Library Import
  async function saveLibraryImport() {
      try {
          feedback.setLoading(true);
          const config = await getConfig();
          const updates = {
              metadata_enhancement: {
                  ...config.metadata_enhancement,
                  auto_import: autoImport,
                  conflict_resolution: conflictResolution,
                  naming_template: renamingTemplate
              }
          };
          await setConfig(updates);
          feedback.addToast('Library settings saved', 'success');
      } catch (e) {
          feedback.addToast('Failed to save library settings', 'error');
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
      const resp = await apiClient.post('/settings/preview-rename', { template: renamingTemplate });
      previewPath = resp.data.preview;
    } catch (e) {
      console.error(e);
    } finally {
      previewLoading = false;
    }
  }

  function onTemplateInput() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(updatePreview, 500);
  }

  onMount(() => {
      fetchAlgorithms();
  });
</script>

<div class="preferences">
  <h1>Preferences</h1>

  <!-- New Card: Library Import & Renaming -->
  <section class="card">
    <h2>Library Import & Renaming</h2>

    <label class="switch-label">
        <input type="checkbox" bind:checked={autoImport} />
        <span class="label-text">Auto-Import High Confidence Matches</span>
    </label>
    <p class="help-text">Automatically rename and move files with high match confidence (&gt;90%).</p>

    <label>
        Conflict Resolution:
        <select bind:value={conflictResolution}>
            <option value="replace">Replace Existing</option>
            <option value="skip">Skip</option>
            <option value="keep_both">Keep Both</option>
        </select>
    </label>

    <label>
        Renaming Pattern:
        <div class="renaming-builder">
            <input type="text" bind:value={renamingTemplate} on:input={onTemplateInput} class="code-input" />
            <div class="tokens">
                {#each tokens as token}
                    <button class="token-btn" on:click={() => addToken(token)}>{token}</button>
                {/each}
            </div>
        </div>
    </label>

    <div class="preview-box">
        <span class="preview-label">Preview:</span>
        {#if previewLoading}
            <span class="muted">Generating...</span>
        {:else}
            <code class="preview-code">{previewPath}</code>
        {/if}
    </div>

    <div class="actions">
        <button on:click={saveLibraryImport}>Save Library Settings</button>
    </div>
  </section>

  <!-- Restored Original Cards -->
  <section class="card">
    <h2>Download Settings</h2>
    <label>
      Slskd Download Dir:
      <input type="text" bind:value={$downloadSettings.slskdDir} />
      <button>Browse</button>
    </label>
    <label>
      Library Dir:
      <input type="text" bind:value={$downloadSettings.libraryDir} />
      <button>Browse</button>
    </label>
    <label>
      Log Level:
      <select bind:value={$downloadSettings.logLevel}>
        <option value="DEBUG">DEBUG</option>
        <option value="INFO">INFO</option>
        <option value="WARNING">WARNING</option>
        <option value="ERROR">ERROR</option>
      </select>
    </label>
  </section>

  <section class="card">
    <h2>Appearance</h2>
    <label>
      Theme:
      <select bind:value={$appearanceSettings.theme}>
        <option value="dark">Dark</option>
        <option value="light">Light</option>
      </select>
    </label>
  </section>

  <section class="card">
    <h2>Quality Profiles</h2>
    <button on:click={addProfile}>Add</button>
    {#each $qualityProfiles as profile, index}
      <div>
        <input type="text" bind:value={profile.name} />
        <button on:click={() => removeProfile(index)}>Remove</button>
      </div>
    {/each}
  </section>

  <section class="card">
    <h2>Playlist Algorithm</h2>
    <label>
      Select Algorithm:
      <select bind:value={$playlistAlgorithm}>
        {#each $availableAlgorithms as algorithm}
          <option value={algorithm}>{algorithm}</option>
        {/each}
      </select>
    </label>
    <button on:click={saveAlgorithm}>Save</button>
  </section>
</div>

<style>
  .preferences {
    padding: 16px;
  }

  .card {
    margin-bottom: 24px;
    padding: 16px;
    border: 1px solid #ccc;
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .profiles {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .profile {
    border: 1px solid #ccc;
    padding: 8px;
    border-radius: 8px;
  }

  /* Additional Styles for New Components */
  label {
      display: flex;
      flex-direction: column;
      gap: 6px;
      font-weight: 500;
      color: var(--text);
  }

  .switch-label {
      flex-direction: row;
      align-items: center;
      cursor: pointer;
  }

  .help-text {
      margin: -8px 0 0 24px;
      font-size: 12px;
      color: #888;
  }

  input[type="text"], select {
      padding: 8px;
      border: 1px solid #ccc;
      border-radius: 4px;
      background: var(--input-bg, #fff);
      color: var(--text, #000);
  }

  button {
      padding: 8px 16px;
      cursor: pointer;
      background: #eee;
      border: 1px solid #ccc;
      border-radius: 4px;
      color: #333;
  }

  button:hover {
      background: #ddd;
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
      font-size: 12px;
      padding: 4px 8px;
      background: #f5f5f5;
  }

  .preview-box {
      background: rgba(0,0,0,0.1);
      padding: 12px;
      border-radius: 4px;
      font-family: monospace;
      font-size: 13px;
      display: flex;
      gap: 8px;
      align-items: center;
  }

  .preview-code { color: #22c55e; }
  .muted { color: #888; }
</style>
