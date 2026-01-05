<script>
  export let title = '';
</script>

<div class="card">
  <h2>{title}</h2>
  <slot></slot>
</div>

<style>
  .card {
    border: 1px solid #ccc;
    border-radius: 8px;
    padding: 16px;
    margin: 16px 0;
    background-color: #fff;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }

  h2 {
    margin: 0 0 8px;
    font-size: 1.5em;
  }
</style>