<script>
  import { onMount } from 'svelte';
  import apiClient from '../api/client';

  export let providerId;
  export let providerName;

  let settings = {};
  let schema = [];
  let loading = true;
  let saving = false;
  let error = '';
  let success = '';

  async function loadSettings() {
    loading = true;
    error = '';
    try {
      const response = await apiClient.get(`/providers/${providerId}/settings`);
      settings = response.data.settings || {};
      schema = response.data.schema || [];
      
      // Initialize missing settings with defaults from schema
      schema.forEach(field => {
        if (settings[field.key] === undefined && field.default !== undefined) {
          settings[field.key] = field.default;
        }
      });
    } catch (err) {
      error = `Failed to load settings: ${err.response?.data?.error || err.message}`;
    } finally {
      loading = false;
    }
  }

  async function saveSettings() {
    saving = true;
    error = '';
    success = '';
    try {
      await apiClient.post(`/api/providers/${providerId}/settings`, settings);
      success = 'Settings saved successfully!';
      setTimeout(() => success = '', 3000);
    } catch (err) {
      error = `Save failed: ${err.response?.data?.error || err.message}`;
    } finally {
      saving = false;
    }
  }

  onMount(loadSettings);
</script>

<div class="provider-settings">
  <div class="header">
    <h3>{providerName} Configuration</h3>
    <span class="id-badge">{providerId}</span>
  </div>

  {#if loading}
    <div class="loading">
      <div class="spinner spinner--small"></div>
      <span>Loading configuration...</span>
    </div>
  {:else if schema.length === 0}
    <p class="muted">No configurable settings for this provider.</p>
  {:else}
    <form on:submit|preventDefault={saveSettings}>
      <div class="fields">
        {#each schema as field}
          <div class="form-group">
            <label for="{providerId}-{field.key}">{field.label}</label>
            {#if field.type === 'password'}
              <input type="password" 
                     id="{providerId}-{field.key}" 
                     bind:value={settings[field.key]} 
                     placeholder={field.sensitive ? '••••••••' : ''} />
            {:else if field.type === 'number'}
              <input type="number" 
                     id="{providerId}-{field.key}" 
                     bind:value={settings[field.key]} />
            {:else}
              <input type="text" 
                     id="{providerId}-{field.key}" 
                     bind:value={settings[field.key]} />
            {/if}
          </div>
        {/each}
      </div>

      <div class="footer">
        {#if error}
          <span class="error-msg">{error}</span>
        {/if}
        {#if success}
          <span class="success-msg">{success}</span>
        {/if}
        <button type="submit" class="btn btn--primary" disabled={saving}>
          {#if saving}Saving...{:else}Save Changes{/if}
        </button>
      </div>
    </form>
  {/if}
</div>

<style>
  .provider-settings {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
  }

  .header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 20px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    padding-bottom: 12px;
  }

  .header h3 {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
  }

  .id-badge {
    font-size: 10px;
    background: rgba(255, 255, 255, 0.1);
    padding: 2px 6px;
    border-radius: 4px;
    color: #94a3b8;
    text-transform: uppercase;
  }

  .fields {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 20px;
    margin-bottom: 20px;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  label {
    font-size: 13px;
    font-weight: 500;
    color: #cbd5e1;
  }

  input {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 10px 12px;
    color: #fff;
    font-size: 14px;
    outline: none;
    transition: border-color 0.2s;
  }

  input:focus {
    border-color: var(--accent);
  }

  .footer {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 16px;
  }

  .btn--primary {
    background: var(--accent);
    color: #000;
    padding: 8px 20px;
    border-radius: 8px;
    font-weight: 700;
    font-size: 14px;
    border: none;
    cursor: pointer;
  }

  .btn--primary:disabled {
    opacity: 0.5;
  }

  .error-msg { color: #ef4444; font-size: 13px; }
  .success-msg { color: var(--accent); font-size: 13px; font-weight: 600; }

  .loading {
    display: flex;
    align-items: center;
    gap: 12px;
    color: #94a3b8;
    font-size: 14px;
  }

  .spinner--small {
    width: 16px;
    height: 16px;
    border: 2px solid rgba(255, 255, 255, 0.1);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .muted { color: #94a3b8; font-size: 14px; }
</style>
