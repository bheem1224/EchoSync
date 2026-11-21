<script>
  import { onMount, onDestroy } from "svelte";

  let {
    value = $bindable(""),
    options = [],
    placeholder = "-- Select --",
    disabled = false,
    ariaLabel = "",
    id = "",
    onchange = null,
    compact = false,
  } = $props();

  let open = $state(false);
  let highlightedIndex = $state(-1);
  let containerEl = $state(null);
  let triggerEl = $state(null);
  let menuEl = $state(null);
  let menuStyle = $state("");

  const normalizedOptions = $derived(
    (options || []).map((opt) =>
      typeof opt === "object" && opt !== null
        ? { value: opt.value ?? "", label: opt.label ?? String(opt.value ?? ""), disabled: Boolean(opt.disabled) }
        : { value: opt, label: String(opt), disabled: false },
    ),
  );

  const selectedOption = $derived(
    normalizedOptions.find((o) => String(o.value) === String(value)) || null,
  );

  function updateMenuPosition() {
    if (!triggerEl || typeof window === "undefined") return;
    const rect = triggerEl.getBoundingClientRect();
    const spaceBelow = window.innerHeight - rect.bottom;
    const maxMenuHeight = 240;
    const openUpward = spaceBelow < Math.min(maxMenuHeight, 180) && rect.top > spaceBelow;
    const top = openUpward
      ? Math.max(8, rect.top - Math.min(maxMenuHeight, rect.top - 8) - 4)
      : rect.bottom + 4;
    const maxHeight = openUpward ? Math.min(maxMenuHeight, rect.top - 12) : Math.min(maxMenuHeight, spaceBelow - 12);
    menuStyle = `position: fixed; top: ${top}px; left: ${rect.left}px; width: ${rect.width}px; max-height: ${Math.max(100, maxHeight)}px; z-index: 9999;`;
  }

  function portal(node) {
    if (typeof document !== "undefined" && node.parentNode !== document.body) {
      document.body.appendChild(node);
    }
    return {
      destroy() {
        if (node.parentNode) {
          node.parentNode.removeChild(node);
        }
      },
    };
  }

  function toggleOpen() {
    if (disabled) return;
    open = !open;
    if (open) {
      updateMenuPosition();
      const idx = normalizedOptions.findIndex((o) => String(o.value) === String(value));
      highlightedIndex = idx >= 0 ? idx : 0;
    }
  }

  function close() {
    open = false;
    highlightedIndex = -1;
  }

  function selectOption(opt) {
    if (opt.disabled) return;
    value = opt.value;
    close();
    if (typeof onchange === "function") {
      onchange(opt.value);
    }
  }

  function handleKeydown(e) {
    if (disabled) return;
    if (e.key === "Escape") {
      if (open) {
        e.preventDefault();
        close();
      }
      return;
    }
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      if (!open) {
        toggleOpen();
      } else if (highlightedIndex >= 0 && highlightedIndex < normalizedOptions.length) {
        selectOption(normalizedOptions[highlightedIndex]);
      }
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (!open) {
        toggleOpen();
      } else if (normalizedOptions.length > 0) {
        highlightedIndex = (highlightedIndex + 1) % normalizedOptions.length;
      }
      return;
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      if (!open) {
        toggleOpen();
      } else if (normalizedOptions.length > 0) {
        highlightedIndex =
          (highlightedIndex - 1 + normalizedOptions.length) % normalizedOptions.length;
      }
    }
  }

  function handleDocClick(e) {
    if (!open) return;
    const inTrigger = containerEl && containerEl.contains(e.target);
    const inMenu = menuEl && menuEl.contains(e.target);
    if (!inTrigger && !inMenu) {
      close();
    }
  }

  function handleViewportChange() {
    if (open) updateMenuPosition();
  }

  onMount(() => {
    if (typeof document !== "undefined") {
      document.addEventListener("mousedown", handleDocClick);
      window.addEventListener("resize", handleViewportChange);
      window.addEventListener("scroll", handleViewportChange, true);
    }
  });

  onDestroy(() => {
    if (typeof document !== "undefined") {
      document.removeEventListener("mousedown", handleDocClick);
      window.removeEventListener("resize", handleViewportChange);
      window.removeEventListener("scroll", handleViewportChange, true);
    }
  });
</script>

<div class="es-select" class:compact bind:this={containerEl}>
  <button
    type="button"
    {id}
    bind:this={triggerEl}
    class="es-select-trigger"
    class:open
    {disabled}
    aria-label={ariaLabel || placeholder}
    aria-haspopup="listbox"
    aria-expanded={open}
    onclick={toggleOpen}
    onkeydown={handleKeydown}
  >
    <span class="es-select-value" class:placeholder={!selectedOption}>
      {selectedOption ? selectedOption.label : placeholder}
    </span>
    <span class="es-select-caret" aria-hidden="true">▾</span>
  </button>

  {#if open}
    <ul
      use:portal
      bind:this={menuEl}
      class="es-select-menu"
      class:compact
      style={menuStyle}
      role="listbox"
      aria-label={ariaLabel || placeholder}
    >
      {#each normalizedOptions as opt, idx (`${String(opt.value)}-${idx}`)}
        {@const isSelected = String(opt.value) === String(value)}
        <li
          role="option"
          aria-selected={isSelected}
          aria-disabled={opt.disabled}
          class="es-select-option"
          class:selected={isSelected}
          class:highlighted={idx === highlightedIndex}
          class:disabled={opt.disabled}
          onmouseenter={() => (highlightedIndex = idx)}
          onclick={() => selectOption(opt)}
          onkeydown={(e) => e.key === "Enter" && selectOption(opt)}
        >
          <span>{opt.label}</span>
          {#if isSelected}
            <span class="es-select-check" aria-hidden="true">✓</span>
          {/if}
        </li>
      {:else}
        <li class="es-select-empty">No options available</li>
      {/each}
    </ul>
  {/if}
</div>

<style>
  .es-select {
    position: relative;
    width: 100%;
    min-width: 0;
  }

  .es-select-trigger {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 9px 12px;
    border-radius: 10px;
    background: var(--bg-input);
    border: 1px solid var(--border-subtle);
    color: var(--text-primary);
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    text-align: left;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
    box-sizing: border-box;
  }

  .es-select.compact .es-select-trigger {
    padding: 6px 10px;
    font-size: 12px;
    border-radius: 8px;
  }

  .es-select-trigger:hover:not(:disabled) {
    border-color: var(--color-primary);
  }

  .es-select-trigger.open,
  .es-select-trigger:focus-visible {
    outline: none;
    border-color: var(--color-primary);
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--color-primary) 25%, transparent);
  }

  .es-select-trigger:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .es-select-value {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .es-select-value.placeholder {
    color: var(--text-muted);
  }

  .es-select-caret {
    flex-shrink: 0;
    color: var(--text-muted);
    font-size: 11px;
    transition: transform 0.15s ease;
  }

  .es-select-trigger.open .es-select-caret {
    transform: rotate(180deg);
    color: var(--color-primary);
  }

  :global(.es-select-menu) {
    margin: 0;
    padding: 4px;
    list-style: none;
    overflow-y: auto;
    border-radius: 10px;
    background: var(--bg-surface-elevated);
    border: 1px solid var(--border-subtle);
    box-shadow: var(--shadow, 0 16px 40px rgba(0, 0, 0, 0.45));
  }

  :global(.es-select-menu .es-select-option) {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 8px 10px;
    border-radius: 7px;
    font-size: 13px;
    color: var(--text-primary);
    cursor: pointer;
    transition: background-color 0.12s ease, color 0.12s ease;
  }

  :global(.es-select-menu.compact .es-select-option) {
    padding: 6px 8px;
    font-size: 12px;
  }

  :global(.es-select-menu .es-select-option.highlighted) {
    background: color-mix(in srgb, var(--color-primary) 14%, transparent);
  }

  :global(.es-select-menu .es-select-option.selected) {
    background: color-mix(in srgb, var(--color-primary) 22%, transparent);
    color: var(--color-primary);
    font-weight: 600;
  }

  :global(.es-select-menu .es-select-option.disabled) {
    opacity: 0.45;
    cursor: not-allowed;
  }

  :global(.es-select-menu .es-select-check) {
    font-size: 11px;
    flex-shrink: 0;
  }

  :global(.es-select-menu .es-select-empty) {
    padding: 10px;
    text-align: center;
    font-size: 12px;
    color: var(--text-muted);
  }
</style>
