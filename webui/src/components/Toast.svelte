<script>
  import { feedback } from '../stores/feedback';
  let state;
  const unsub = feedback.subscribe((v) => (state = v));
  import { onDestroy } from 'svelte';
  onDestroy(() => unsub && typeof unsub === 'function' && unsub());
</script>

<div class="toast-container">
  {#if state?.toasts}
    {#each state.toasts as t}
      <div class="toast {t.type}">{t.message}</div>
    {/each}
  {/if}
</div>

<style>
  /* Uses .toast and .toast-container styles from app.css */
</style>
