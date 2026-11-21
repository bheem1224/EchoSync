<script>
  let {
    open = $bindable(false),
    title = "",
    eyebrow = "",
    maxWidth = "560px",
    onclose = null,
    children,
    footer,
  } = $props();

  function handleClose() {
    open = false;
    if (typeof onclose === "function") {
      onclose();
    }
  }

  function handleKeydown(e) {
    if (open && e.key === "Escape") {
      handleClose();
    }
  }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open}
  <div
    class="es-modal-backdrop"
    role="presentation"
    onclick={(e) => {
      if (e.target === e.currentTarget) handleClose();
    }}
  >
    <div
      class="es-modal"
      style={`max-width: ${maxWidth};`}
      role="dialog"
      aria-modal="true"
      aria-label={title || "Dialog"}
    >
      {#if title || eyebrow}
        <header class="es-modal-header">
          <div>
            {#if eyebrow}
              <p class="es-modal-eyebrow">{eyebrow}</p>
            {/if}
            {#if title}
              <h2 class="es-modal-title">{title}</h2>
            {/if}
          </div>
          <button
            type="button"
            class="es-modal-close"
            onclick={handleClose}
            aria-label="Close modal"
          >
            ✕
          </button>
        </header>
      {/if}

      <div class="es-modal-body">
        {@render children?.()}
      </div>

      {#if footer}
        <footer class="es-modal-footer">
          {@render footer()}
        </footer>
      {/if}
    </div>
  </div>
{/if}

<style>
  .es-modal-backdrop {
    position: fixed;
    inset: 0;
    z-index: 100;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 16px;
    background: rgba(0, 0, 0, 0.72);
    backdrop-filter: blur(6px);
  }

  .es-modal {
    width: 100%;
    max-height: 90vh;
    display: flex;
    flex-direction: column;
    border-radius: 16px;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    color: var(--text-primary);
    box-shadow: var(--shadow);
    overflow: hidden;
  }

  .es-modal-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    padding: 18px 20px;
    border-bottom: 1px solid var(--border-subtle);
  }

  .es-modal-eyebrow {
    margin: 0 0 4px;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--color-primary);
  }

  .es-modal-title {
    margin: 0;
    font-size: 18px;
    font-weight: 800;
    color: var(--text-primary);
  }

  .es-modal-close {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    border: 1px solid var(--border-subtle);
    background: var(--bg-surface-elevated);
    color: var(--text-secondary);
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .es-modal-close:hover {
    color: var(--text-primary);
    border-color: var(--color-primary);
  }

  .es-modal-body {
    padding: 20px;
    overflow-y: auto;
    flex: 1 1 auto;
  }

  .es-modal-footer {
    padding: 14px 20px;
    border-top: 1px solid var(--border-subtle);
    display: flex;
    justify-content: flex-end;
    gap: 10px;
  }
</style>
