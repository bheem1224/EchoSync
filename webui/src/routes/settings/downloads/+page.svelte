<script>
  import DownloadQueueViewer from '../../../components/DownloadQueueViewer.svelte';
</script>

<section>
  <h1>Download Queue</h1>
  <p class="page-description">Manage and search for items in your download queue</p>
  
  <DownloadQueueViewer />
</section>

<style>
  :global(section) {
    max-width: 100%;
  }

  h1 {
    margin-bottom: 8px;
    font-size: 28px;
    font-weight: 600;
    color: var(--text-main, #ffffff);
  }

  .page-description {
    color: var(--text-muted, #8b9bb4);
    margin-bottom: 1.5rem;
    font-size: 14px;
  }
</style>
