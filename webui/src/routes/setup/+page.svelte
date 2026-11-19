<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { auth } from '../../stores/auth';
  import FirstBootSetup from '$lib/components/FirstBootSetup.svelte';

  onMount(async () => {
    const status = await auth.refresh();
    if (status && !status.setup_required) {
      goto(status.authenticated ? '/dashboard' : '/login');
    }
  });
</script>

<svelte:head>
  <title>First-Boot Setup • EchoSync</title>
</svelte:head>

<FirstBootSetup onSetupComplete={() => goto('/dashboard')} />
