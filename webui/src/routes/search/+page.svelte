<script>
  import OmniSearch from '$lib/components/OmniSearch.svelte';
</script>

<svelte:head>
  <title>Search • EchoSync</title>
</svelte:head>

<section class="page">
  <OmniSearch inline={true} />
</section>

<style>
  .page {
    max-width: 1000px;
    margin: 0 auto;
    width: 100%;
  }
</style>
