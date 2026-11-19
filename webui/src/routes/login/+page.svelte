<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { auth } from '../../stores/auth';
  import FirstBootSetup from '$lib/components/FirstBootSetup.svelte';
  import LoginView from '$lib/components/LoginView.svelte';

  onMount(async () => {
    const status = await auth.refresh();
    if (status && !status.setup_required && status.authenticated) {
      goto('/dashboard');
    }
  });
</script>

<svelte:head>
  <title>Sign In • EchoSync</title>
</svelte:head>

{#if $auth.setupRequired}
  <FirstBootSetup onSetupComplete={() => goto('/dashboard')} />
{:else}
  <LoginView
    oidcEnabled={$auth.oidcEnabled}
    onLoginSuccess={() => goto('/dashboard')}
  />
{/if}
