<script>
  import { onMount, createEventDispatcher } from 'svelte';
  import { fade, slide } from 'svelte/transition';
  import apiClient from '../api/client';
  import { systemStatus } from '../stores/systemStatus';
  
  const dispatch = createEventDispatcher();
  
  let isRestarting = false;
  let countdown = 0;
  
  async function handleRestart() {
    try {
      isRestarting = true;
      await apiClient.post('/restart');
      
      // Wait 3 seconds for the container to die
      setTimeout(() => {
        // Poll the health endpoint until it comes back online
        const interval = setInterval(async () => {
          try {
            // Using raw fetch to avoid interceptors that might redirect to login during downtime
            let res = await apiClient.get('/v1/system/health');
            if (res.status === 200) {
              clearInterval(interval);
              window.location.reload(); // Now refresh!
            }
          } catch (e) {
            // Server is down, keep waiting...
            console.debug('Waiting for server to come back online...');
          }
        }, 2000);
      }, 3000);

    } catch (error) {
      console.error('Restart failed:', error);
      isRestarting = false;
      window.dispatchEvent(new CustomEvent('es-toast', { 
        detail: { 
          message: 'Failed to initiate restart. Please try manually.', 
          type: 'error' 
        } 
      }));
    }
  }
</script>

{#if $systemStatus.restart_pending || $systemStatus.status === 'offline'}
  <div 
    class="restart-banner" 
    class:restarting={isRestarting}
    class:offline={$systemStatus.status === 'offline'}
    transition:slide={{ duration: 300 }}
  >
    <div class="banner-content">
      <div class="status-indicator">
        <div class="pulse-ring"></div>
        <div class="pulse-dot"></div>
      </div>
      
      <div class="message-container">
        <h3>{$systemStatus.status === 'offline' ? 'Connection Lost' : 'Restart Required'}</h3>
        <p>{$systemStatus.status === 'offline' ? 'EchoSync server is unreachable. Attempting to reconnect...' : 'A system update or plugin change has been applied. Restart EchoSync to activate all changes.'}</p>
      </div>

      <div class="actions">
        {#if isRestarting || $systemStatus.status === 'offline'}
          <div class="restarting-state" in:fade>
            <span class="spinner"></span>
            <span>{isRestarting ? 'Restarting...' : 'Reconnecting...'}</span>
          </div>
        {:else}
          <button 
            class="restart-btn active:scale-95" 
            on:click={handleRestart}
            disabled={isRestarting}
          >
            Restart Now
          </button>
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  .restart-banner {
    background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
    color: white;
    padding: 12px 24px;
    z-index: 9999;
    box-shadow: 0 4px 25px rgba(217, 119, 6, 0.4);
    border-bottom: 1px solid rgba(255, 255, 255, 0.2);
    position: relative;
    overflow: hidden;
  }

  .restart-banner::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: url("data:image/svg+xml,%3Csvg width='100' height='100' viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M11 18c3.866 0 7-3.134 7-7s-3.134-7-7-7-7 3.134-7 7 3.134 7 7 7zm48 25c3.866 0 7-3.134 7-7s-3.134-7-7-7-7 3.134-7 7 3.134 7 7 7zm-43-7c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zm63 31c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zM34 90c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zm56-76c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM12 86c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zm66-3c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zm-40-39c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zm30 38c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2z' fill='%23ffffff' fill-opacity='0.05' fill-rule='evenodd'/%3E%3C/svg%3E");
    pointer-events: none;
  }

  .banner-content {
    display: flex;
    align-items: center;
    gap: 20px;
    max-width: 1400px;
    margin: 0 auto;
    position: relative;
    z-index: 1;
  }

  .status-indicator {
    position: relative;
    width: 24px;
    height: 24px;
    flex-shrink: 0;
  }

  .pulse-dot {
    width: 12px;
    height: 12px;
    background: white;
    border-radius: 50%;
    position: absolute;
    top: 6px;
    left: 6px;
  }

  .pulse-ring {
    border: 3px solid white;
    border-radius: 50%;
    height: 100%;
    width: 100%;
    position: absolute;
    left: 0;
    top: 0;
    animation: pulse 1.5s ease-out infinite;
    opacity: 0;
  }

  @keyframes pulse {
    0% { transform: scale(0.5); opacity: 0; }
    50% { opacity: 0.5; }
    100% { transform: scale(1.5); opacity: 0; }
  }

  .message-container {
    flex: 1;
  }

  h3 {
    margin: 0;
    font-size: 16px;
    font-weight: 700;
    letter-spacing: -0.01em;
    text-transform: uppercase;
  }

  p {
    margin: 2px 0 0 0;
    font-size: 13px;
    opacity: 0.9;
    font-weight: 500;
  }

  .actions {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .restart-btn {
    background: white;
    color: #d97706;
    border: none;
    padding: 8px 20px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  .restart-btn:hover {
    background: #fff;
    transform: translateY(-2px);
    box-shadow: 0 6px 15px rgba(0, 0, 0, 0.15);
  }

  .restarting-state {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 14px;
    font-weight: 600;
    background: rgba(0, 0, 0, 0.1);
    padding: 6px 16px;
    border-radius: 8px;
  }

  .spinner {
    width: 16px;
    height: 16px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .restarting {
    filter: brightness(0.95);
  }

  @media (max-width: 768px) {
    .banner-content {
      flex-direction: column;
      text-align: center;
      gap: 12px;
    }
    
    .status-indicator {
      display: none;
    }

    .restart-btn {
      width: 100%;
    }
  }
</style>
