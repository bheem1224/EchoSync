<script>
  import YamlDashboardRenderer from '../../components/YamlDashboardRenderer.svelte';

  const YAML_URL = '/dashboards/discover-dashboard.yaml';

  function onRendererReady(e) {
    console.log("Discover dashboard ready");
  }

  function onRendererError(e) {
    console.warn("Discover dashboard YAML missing or failed to load");
  }
</script>

<svelte:head>
  <title>Discover • EchoSync</title>
</svelte:head>

<section class="page px-6 py-10">
  <div class="mb-10 text-center">
    <h1 class="text-4xl font-bold text-white mb-4">Discover</h1>
    <p class="text-xl text-accent/80 font-semibold tracking-wide">Coming Soon!</p>
    <p class="text-sm text-muted mt-3 max-w-lg mx-auto">This configurable dashboard is powered by a Lovelace-style <code class="bg-black/30 px-1 rounded text-accent">dashboard.yaml</code>. You'll soon be able to drop custom UI cards right into this view to discover new music!</p>
  </div>

  <div class="dashboard-container max-w-6xl mx-auto">
    <YamlDashboardRenderer 
      yamlUrl={YAML_URL} 
      on:ready={onRendererReady} 
      on:error={onRendererError} 
    />
  </div>
</section>

<style>
  .page {
    min-height: 100vh;
  }
</style>
