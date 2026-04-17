<script>
  import JobsSettings from '../../../components/JobsSettings.svelte';
</script>

<svelte:head>
  <title>Jobs • Echosync</title>
</svelte:head>

<section class="page">
  <JobsSettings />
</section>

<style>
  .page {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }
</style>
