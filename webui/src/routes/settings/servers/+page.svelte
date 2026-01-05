<script>
  import PlexServiceCard from '../../../components/PlexServiceCard.svelte';
  import NavidromeServiceCard from '../../../components/NavidromeServiceCard.svelte';
  import JellyfinServiceCard from '../../../components/JellyfinServiceCard.svelte';
</script>

<svelte:head>
  <title>Servers • SoulSync</title>
</svelte:head>

<section class="page">
  <header class="page__header">
    <h1>Servers</h1>
    <p class="subtitle">Configure your media servers</p>
  </header>

  <div class="servers-container">
    <PlexServiceCard />
    <NavidromeServiceCard />
    <JellyfinServiceCard />
  </div>
</section>

<style>
  .page {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .page__header {
    margin-bottom: 8px;
  }

  .page__header h1 {
    margin: 0 0 8px 0;
    font-size: 28px;
    font-weight: 600;
  }

  .subtitle {
    margin: 0;
    color: var(--muted);
    font-size: 14px;
  }

  .servers-container {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .muted {
    color: var(--muted);
  }
</style>
