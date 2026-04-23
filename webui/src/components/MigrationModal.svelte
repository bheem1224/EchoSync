<script>
  import { createEventDispatcher } from 'svelte';
  const dispatch = createEventDispatcher();

  export let message = '';

  async function handleAcknowledge() {
    try {
      // Call backend to clear the migration flag
      const response = await fetch('/api/migration-acknowledge', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to acknowledge migration');
      }

      // Dismiss the modal
      dispatch('dismiss');

      // Hard reload the page to ensure fresh DB state
      setTimeout(() => {
        window.location.reload();
      }, 500);
    } catch (error) {
      console.error('Error acknowledging migration:', error);
      // Still close the modal even if there's an error
      dispatch('dismiss');
      setTimeout(() => {
        window.location.reload();
      }, 500);
    }
  }
</script>

<div class="migration-overlay">
  <div class="migration-modal">
    <div class="migration-header">
      <span class="migration-icon">🚀</span>
      <h2>v2.1.0 Upgrade</h2>
    </div>

    <div class="migration-body">
      <p class="migration-message">
        {message}
      </p>
      <p class="upgrade-note">
        The database rebuild should complete in the background shortly. You'll see your library repopulate as the sync completes.
      </p>
    </div>

    <div class="migration-actions">
      <button class="btn-acknowledge active:scale-95 transition-all duration-200" on:click={handleAcknowledge}>OK</button>
    </div>
  </div>
</div>

<style>
  .migration-overlay {
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
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }

  .migration-modal {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 12px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
    max-width: 500px;
    width: 90%;
    max-height: 80vh;
    overflow-y: auto;
    animation: slideUp 0.3s ease-out;
  }

  @keyframes slideUp {
    from {
      transform: translateY(40px);
      opacity: 0;
    }
    to {
      transform: translateY(0);
      opacity: 1;
    }
  }

  .migration-header {
    padding: 24px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .migration-icon {
    font-size: 32px;
  }

  .migration-header h2 {
    margin: 0;
    font-size: 24px;
    font-weight: 600;
    color: var(--text);
  }

  .migration-body {
    padding: 24px;
  }

  .migration-message {
    margin: 0 0 16px 0;
    font-size: 15px;
    line-height: 1.6;
    color: var(--text);
  }

  .upgrade-note {
    margin: 16px 0 0 0;
    font-size: 13px;
    line-height: 1.5;
    color: var(--text-secondary);
    font-style: italic;
  }

  .migration-actions {
    padding: 24px;
    border-top: 1px solid var(--border);
    display: flex;
    justify-content: flex-end;
    gap: 12px;
  }

  .btn-acknowledge {
    padding: 10px 24px;
    background: var(--accent);
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .btn-acknowledge:hover {
    background: var(--accent-dark);
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 138, 204, 0.3);
  }

  .btn-acknowledge:active {
    transform: translateY(0);
  }
</style>
