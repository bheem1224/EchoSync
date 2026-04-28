<script>
  import { page } from '$app/stores';
  import { pluginViews } from '../../../stores/pluginViews';
  import YamlDashboardRenderer from '../../../components/YamlDashboardRenderer.svelte';

  $: viewId   = $page.params.viewId;
  $: view     = $pluginViews.find(v => v.id === viewId) ?? null;
  $: yamlUrl  = view?.yamlPath ?? '';
  $: pageTitle = view?.title ?? viewId;
</script>

<svelte:head>
  <title>{pageTitle} • EchoSync</title>
</svelte:head>

{#if view}
  <section class="plugin-view-page">
    <header class="plugin-view-page__header">
      <span class="plugin-view-page__icon" aria-hidden="true">{view.icon}</span>
      <div>
        <p class="plugin-view-page__eyebrow">Plugin View · {view.pluginId}</p>
        <h1>{view.title}</h1>
      </div>
    </header>

    <YamlDashboardRenderer {yamlUrl}>
      <svelte:fragment slot="loading">
        <div class="pv-skeleton">
          <div class="pv-skeleton__bar"></div>
          <div class="pv-skeleton__bar pv-skeleton__bar--short"></div>
          <div class="pv-skeleton__bar"></div>
        </div>
      </svelte:fragment>
    </YamlDashboardRenderer>
  </section>
{:else}
  <div class="pv-not-found" role="alert">
    <p class="pv-not-found__code">404</p>
    <p class="pv-not-found__msg">
      Plugin view <code>{viewId}</code> is not registered.
      Make sure the plugin is enabled and the backend has restarted.
    </p>
    <a href="/settings/plugin-store" class="pv-not-found__link">Go to Plugin Store →</a>
  </div>
{/if}

<style>
  .plugin-view-page { display: flex; flex-direction: column; gap: 28px; max-width: 1000px; }

  .plugin-view-page__header {
    display: flex; align-items: center; gap: 16px;
  }
  .plugin-view-page__icon {
    font-size: 32px; line-height: 1;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px; padding: 10px 14px;
    flex-shrink: 0;
  }
  .plugin-view-page__eyebrow {
    margin: 0 0 4px;
    font-size: 10px; font-weight: 900; text-transform: uppercase;
    letter-spacing: 0.25em; color: var(--color-primary, #1db954);
  }
  h1 { margin: 0; font-size: 26px; font-weight: 800; color: #fff; }

  /* Skeleton */
  .pv-skeleton { display: flex; flex-direction: column; gap: 12px; padding: 4px 0; }
  .pv-skeleton__bar {
    height: 14px; border-radius: 7px;
    background: linear-gradient(90deg,
      rgba(255,255,255,0.04) 0%,
      rgba(255,255,255,0.09) 50%,
      rgba(255,255,255,0.04) 100%);
    background-size: 200% 100%;
    animation: shim 1.4s ease-in-out infinite;
  }
  .pv-skeleton__bar--short { width: 55%; }
  @keyframes shim { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

  /* 404 */
  .pv-not-found {
    display: flex; flex-direction: column; align-items: center;
    padding: 80px 24px; text-align: center;
    border-radius: 16px; background: rgba(255,255,255,0.02);
    border: 1px dashed rgba(255,255,255,0.08);
  }
  .pv-not-found__code { font-size: 64px; font-weight: 900; color: rgba(255,255,255,0.08); margin: 0 0 8px; line-height: 1; }
  .pv-not-found__msg { font-size: 14px; color: rgba(255,255,255,0.45); max-width: 360px; line-height: 1.6; }
  .pv-not-found__msg code { color: rgba(255,255,255,0.65); background: rgba(255,255,255,0.06); border-radius: 4px; padding: 1px 6px; }
  .pv-not-found__link { margin-top: 20px; font-size: 13px; font-weight: 700; color: var(--color-primary, #1db954); text-decoration: none; }
  .pv-not-found__link:hover { text-decoration: underline; }
</style>
