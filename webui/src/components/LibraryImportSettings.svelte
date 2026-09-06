<script>
  import { onMount } from "svelte";
  import { settings } from "../stores/settings";

  let data = $state({
    auto_import_enabled: false,
    renaming_template: "{Artist}/{Album}/{Track} - {Title}.{ext}",
    group_singles: true,
    prefer_canonical_studio_album: true,
  });

  const tokens = ["Artist", "Album", "Title", "Year", "Track", "Format"];

  const previewData = {
    Artist: "Daft Punk",
    Album: "Random Access Memories",
    Title: "Get Lucky",
    Year: "2013",
    Track: "01",
    Format: "flac",
    ext: "flac",
  };

  let preview = $derived.by(() => {
    let p = data.renaming_template || "";
    for (const [key, val] of Object.entries(previewData)) {
      p = p.replace(new RegExp(`{${key}}`, "g"), val);
    }
    return "/Music/" + p;
  });

  onMount(async () => {
    await settings.load();
    const metaConfig = $settings?.data?.metadata_enhancement || {};
    const importConfig = $settings?.data?.library_import || {};
    data = {
      auto_import_enabled: metaConfig.auto_import ?? false,
      renaming_template:
        metaConfig.naming_template ??
        "{Artist}/{Album}/{Track} - {Title}.{ext}",
      group_singles: importConfig.group_singles ?? true,
      prefer_canonical_studio_album:
        metaConfig.prefer_canonical_studio_album ?? true,
    };
  });

  function addToken(token) {
    data.renaming_template += `{${token}}`;
  }

  export async function save() {
    const patch = {
      metadata_enhancement: {
        auto_import: data.auto_import_enabled,
        conflict_resolution: "keep_both", // Enforce 'keep_both' in backend logic
        naming_template: data.renaming_template,
        prefer_canonical_studio_album: data.prefer_canonical_studio_album,
      },
      library_import: {
        group_singles: data.group_singles,
      },
    };
    await settings.save(patch);
  }

  export function getCurrentPattern() {
    return data.renaming_template;
  }

  export function getCurrentSinglesPattern() {
    return data.renaming_template;
  }
</script>

<section class="library-import card">
  <div class="card-header">
    <h3>Library Import & Renaming</h3>
  </div>

  <div class="form">
    <!-- Row 1: Auto-Import -->
    <div class="row-auto-import">
      <span class="label-bold">Auto-Import</span>
      <label class="switch">
        <input type="checkbox" bind:checked={data.auto_import_enabled} />
        <span class="slider round"></span>
      </label>
    </div>

    <!-- Row 2: Renaming Pattern -->
    <div class="field stack">
      <span class="field-label">Renaming Pattern</span>
      <div class="input-group">
        <input
          class="dark-input input"
          type="text"
          bind:value={data.renaming_template}
        />

        <div class="tokens">
          {#each tokens as token}
            <button
              type="button"
              class="token-btn active:scale-95 transition-all duration-200"
              onclick={() => addToken(token)}>{token}</button
            >
          {/each}
        </div>

        <div class="preview-terminal">
          <span class="preview-text">Preview: {preview}</span>
        </div>
      </div>
    </div>

    <!-- Invariant Toggles -->
    <div class="toggles-group">
      <!-- Row 3: Group Standalone Singles -->
      <div class="row-toggle">
        <div class="toggle-info">
          <span class="label-bold">Group Standalone Singles</span>
          <p class="description-text">
            Consolidate non-album singles and standalone recordings into a
            dedicated 'Singles' directory under each artist.
          </p>
        </div>
        <label class="switch">
          <input type="checkbox" bind:checked={data.group_singles} />
          <span class="slider round"></span>
        </label>
      </div>

      <!-- Row 4: Prefer Canonical Studio Album -->
      <div class="row-toggle">
        <div class="toggle-info">
          <span class="label-bold">Prefer Canonical Studio Album</span>
          <p class="description-text">
            Realign tracks sourced from multi-artist compilations and repacks to
            their original canonical studio albums, preserving compilation
            provenance in custom tags.
          </p>
        </div>
        <label class="switch">
          <input
            type="checkbox"
            bind:checked={data.prefer_canonical_studio_album}
          />
          <span class="slider round"></span>
        </label>
      </div>
    </div>
  </div>
</section>

<style>
  .library-import {
    padding: 12px;
  }
  .library-import .form {
    display: flex;
    flex-direction: column;
    gap: 20px;
    padding-left: 8px;
    padding-right: 8px;
  }

  /* Row 1 Styles */
  .row-auto-import {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .label-bold {
    font-weight: 600;
    color: var(--text-main);
    font-size: 1rem;
  }

  /* Switch Styles */
  .switch {
    position: relative;
    display: inline-block;
    width: 40px;
    height: 24px;
    flex-shrink: 0;
  }
  .switch input {
    opacity: 0;
    width: 0;
    height: 0;
  }
  .slider {
    position: absolute;
    cursor: pointer;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: #333;
    transition: 0.4s;
    border-radius: 24px;
  }
  .slider:before {
    position: absolute;
    content: "";
    height: 18px;
    width: 18px;
    left: 3px;
    bottom: 3px;
    background-color: white;
    transition: 0.4s;
    border-radius: 50%;
  }
  input:checked + .slider {
    background-color: var(--primary, #10b981);
  }
  input:checked + .slider:before {
    transform: translateX(16px);
  }

  /* Row 2 & 3 Styles */
  .field.stack {
    display: flex;
    flex-direction: column;
    gap: 8px;
    align-items: flex-start;
  }
  .field-label {
    color: var(--muted);
    font-size: 0.9rem;
    margin-bottom: 4px;
  }

  .input-group {
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .dark-input {
    width: 100%;
    padding: 10px;
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: var(--text);
    box-sizing: border-box;
    font-family: monospace;
    font-size: 0.95rem;
  }
  .dark-input:focus {
    outline: none;
    border-color: var(--primary, #10b981);
  }

  .tokens {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }
  .token-btn {
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 6px;
    color: var(--text-main);
    padding: 4px 10px;
    font-size: 0.8rem;
    cursor: pointer;
    transition: all 0.2s;
  }
  .token-btn:hover {
    background: rgba(255, 255, 255, 0.2);
    transform: translateY(-1px);
  }

  /* Terminal Preview */
  .preview-terminal {
    width: 100%;
    background: #111827; /* bg-gray-900 */
    color: #d1d5db; /* text-gray-300 */
    font-family: monospace; /* font-mono */
    font-size: 0.875rem; /* text-sm */
    padding: 12px; /* p-3 */
    border-radius: 6px; /* rounded */
    box-sizing: border-box;
    border: 1px solid rgba(255, 255, 255, 0.1);
  }
  .preview-text {
    word-break: break-all;
  }

  /* Invariant Toggles */
  .toggles-group {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding-top: 12px;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
  }

  .row-toggle {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
  }
  .toggle-info {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .description-text {
    font-size: 0.8rem;
    color: var(--muted, #94a3b8);
    margin: 0;
    line-height: 1.4;
  }
</style>
