<script>
  import { createEventDispatcher } from 'svelte';
  const dispatch = createEventDispatcher();
  export let title = 'Confirm';
  export let message = '';
  export let confirmText = 'Confirm';
  export let cancelText = 'Cancel';
  export let danger = false;

  function confirm() { dispatch('confirm'); }
  function cancel() { dispatch('cancel'); }
</script>

<div class="cd-overlay">
  <div class="cd-modal">
    <div class="cd-header">{title}</div>
    <div class="cd-body">{message}</div>
    <div class="cd-actions">
      <button class="cd-cancel active:scale-95 transition-all duration-200" on:click={cancel}>{cancelText}</button>
      <button class:danger on:click={confirm}>{confirmText}</button>
    </div>
  </div>
</div>

<style>
  .cd-overlay{position:fixed;inset:0;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;z-index:3000}
  .cd-modal{background:var(--bg-card);padding:16px;border-radius:10px;width:420px;color:var(--text)}
  .cd-header{font-weight:600;margin-bottom:8px}
  .cd-body{margin-bottom:12px;color:var(--muted)}
  .cd-actions{display:flex;justify-content:flex-end;gap:8px}
  .cd-cancel{background:transparent;border:1px solid rgba(255,255,255,0.04);padding:8px 12px;border-radius:8px}
  .danger{background:#b91c1c;color:#fff;border:none;padding:8px 12px;border-radius:8px}
</style>
