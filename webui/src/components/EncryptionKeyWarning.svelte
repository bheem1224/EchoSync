<script>
  import { createEventDispatcher } from 'svelte';
  const dispatch = createEventDispatcher();
  
  export let keyValue = '';
  


  function copyToClipboard() {
    navigator.clipboard.writeText(keyValue).then(() => {
      window.dispatchEvent(new CustomEvent('es-toast', { detail: { message: 'Encryption Key Copied!', type: 'success' } }));
    });
  }

  function dismiss() {
    dispatch('dismiss');
  }
</script>

<div class="warning-overlay">
  <div class="warning-modal">
    <div class="warning-header">
      <span class="warning-icon">⚠️</span>
      <h2>Encryption Key Auto-Generated</h2>
    </div>
    
    <div class="warning-body">
      <p class="warning-message">
        No MASTER_KEY environment variable was found, so an encryption key was automatically generated.
        <strong>All encrypted settings will be lost on container restart</strong> unless you save this key.
      </p>
      
      <div class="key-section">
        <label>Your Encryption Key:</label>
        <div class="key-display">
          <textarea readonly>{keyValue}</textarea>
          <button class="copy-btn active:scale-95 transition-all duration-200" on:click={copyToClipboard}>
            Copy
          </button>
        </div>
      </div>

      <div class="instructions">
        <h3>To persist your settings:</h3>
        <ol>
          <li>Copy the encryption key above</li>
          <li>Add it to your container environment variables:
            <code>MASTER_KEY={keyValue}</code>
          </li>
          <li>Restart the container</li>
        </ol>
        <p class="note">
          <strong>Note:</strong> This key is also saved to <code>.env</code> file in the config directory.
        </p>
      </div>
    </div>

    <div class="warning-actions">
      <button class="btn-acknowledge active:scale-95 transition-all duration-200" on:click={dismiss}>I Understand</button>
    </div>
  </div>
</div>

<style>
  .warning-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.8);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 5000;
    animation: fadeIn 0.2s ease-out;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  .warning-modal {
    background: var(--bg-card, #1a1a1a);
    border: 2px solid #f59e0b;
    border-radius: 12px;
    width: 90%;
    max-width: 650px;
    max-height: 90vh;
    overflow-y: auto;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
    animation: slideUp 0.3s ease-out;
  }

  @keyframes slideUp {
    from { transform: translateY(20px); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
  }

  .warning-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 20px 24px;
    border-bottom: 1px solid rgba(245, 158, 11, 0.2);
    background: rgba(245, 158, 11, 0.1);
  }

  .warning-icon {
    font-size: 32px;
  }

  .warning-header h2 {
    margin: 0;
    font-size: 22px;
    font-weight: 600;
    color: #f59e0b;
  }

  .warning-body {
    padding: 24px;
  }

  .warning-message {
    margin: 0 0 20px 0;
    line-height: 1.6;
    color: var(--text, #fff);
  }

  .warning-message strong {
    color: #f59e0b;
  }

  .key-section {
    margin-bottom: 24px;
  }

  .key-section label {
    display: block;
    margin-bottom: 8px;
    font-weight: 600;
    color: var(--text, #fff);
  }

  .key-display {
    display: flex;
    gap: 8px;
  }

  .key-display textarea {
    flex: 1;
    font-family: 'Courier New', monospace;
    font-size: 12px;
    padding: 12px;
    background: rgba(0, 0, 0, 0.3);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    color: #10b981;
    resize: none;
    height: 80px;
    word-break: break-all;
  }

  .copy-btn {
    padding: 8px 16px;
    background: #10b981;
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 600;
    transition: background 0.2s;
    height: fit-content;
  }

  .copy-btn:hover {
    background: #059669;
  }

  .instructions {
    background: rgba(59, 130, 246, 0.1);
    border: 1px solid rgba(59, 130, 246, 0.3);
    border-radius: 8px;
    padding: 16px;
  }

  .instructions h3 {
    margin: 0 0 12px 0;
    font-size: 16px;
    color: #3b82f6;
  }

  .instructions ol {
    margin: 0 0 12px 0;
    padding-left: 20px;
  }

  .instructions li {
    margin-bottom: 8px;
    line-height: 1.5;
  }

  .instructions code {
    background: rgba(0, 0, 0, 0.4);
    padding: 2px 6px;
    border-radius: 3px;
    font-family: 'Courier New', monospace;
    font-size: 12px;
    color: #10b981;
    word-break: break-all;
  }

  .note {
    margin: 0;
    font-size: 13px;
    color: var(--muted, #999);
  }

  .warning-actions {
    padding: 16px 24px;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    display: flex;
    justify-content: flex-end;
  }

  .btn-acknowledge {
    background: #f59e0b;
    color: white;
    border: none;
    padding: 10px 24px;
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s;
  }

  .btn-acknowledge:hover {
    background: #d97706;
  }
</style>
