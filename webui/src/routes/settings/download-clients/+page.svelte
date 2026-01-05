<script>
  import { onMount } from 'svelte';
  import Card from '../../components/Card.svelte';

  let downloadClients = [];

  onMount(async () => {
    try {
      const response = await fetch('/api/download-clients');
      downloadClients = await response.json();
    } catch (error) {
      console.error('Failed to fetch download clients:', error);
    }
  });
</script>

<section>
  <h1>Download Clients</h1>
  {#if downloadClients.length > 0}
    {#each downloadClients as client}
      <Card title={client.name}>
        <p>{client.description}</p>
        <button>Configure</button>
      </Card>
    {/each}
  {:else}
    <p>No download clients available.</p>
  {/if}
</section>