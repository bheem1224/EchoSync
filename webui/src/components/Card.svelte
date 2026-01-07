<script>
  export let title = '';
</script>

<div class="card">
  {#if title}
    <h2>{title}</h2>
  {/if}
  <slot></slot>
</div>

<style>
  .card {
    background-color: var(--bg-card, #14181f);
    border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
    border-radius: 12px;
    padding: 24px;
    margin: 16px 0;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  }

  h2 {
    color: var(--text-main, #ffffff);
    margin: 0 0 12px;
    font-size: 1.5em;
    font-weight: bold;
  }
</style>