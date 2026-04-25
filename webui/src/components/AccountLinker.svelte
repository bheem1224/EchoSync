<script>
  import { onMount } from 'svelte';
  
  let mediaServers = [
    { id: 'plex-1', name: 'Plex Home Server', provider: 'plex' }
  ];
  
  let musicServices = [
    { id: 'spotify-1', name: 'Spotify Premium', provider: 'spotify' },
    { id: 'tidal-1', name: 'Tidal HiFi', provider: 'tidal' },
    { id: 'deezer-1', name: 'Deezer Family', provider: 'deezer' }
  ];

  let links = [
    { mediaServerId: 'plex-1', musicServiceId: 'spotify-1' }
  ];

  function toggleLink(mediaServerId, musicServiceId) {
    const existingIndex = links.findIndex(l => l.mediaServerId === mediaServerId && l.musicServiceId === musicServiceId);
    if (existingIndex >= 0) {
      links = links.filter((_, i) => i !== existingIndex);
    } else {
      links = [...links, { mediaServerId, musicServiceId }];
    }
  }

  function isLinked(mediaServerId, musicServiceId) {
    return links.some(l => l.mediaServerId === mediaServerId && l.musicServiceId === musicServiceId);
  }
</script>

<div class="flex flex-col h-full text-white">
    <div class="mb-6 border-b border-glass-border pb-4">
        <h3 class="text-lg font-bold">Account Linker</h3>
        <p class="text-xs text-muted mt-1">Bind music service accounts to media servers to enable sync pathways.</p>
    </div>

    <div class="flex flex-col gap-6 overflow-y-auto custom-scrollbar">
        {#each mediaServers as mediaServer}
            <div class="flex flex-col gap-3 p-4 bg-black/20 rounded-xl border border-glass-border shadow-inner">
                <div class="flex items-center gap-2 mb-2">
                    <span class="text-sm font-bold">{mediaServer.name}</span>
                    <span class="text-[10px] bg-primary/20 text-primary px-2 py-0.5 rounded-full uppercase tracking-wider">{mediaServer.provider}</span>
                </div>

                <div class="flex flex-col gap-2">
                    <span class="text-xs text-muted uppercase tracking-wider font-semibold">Available Music Services</span>
                    {#each musicServices as musicService}
                        <div class="flex items-center justify-between p-3 bg-card border border-glass-border rounded-lg hover:border-[rgba(255,255,255,0.1)] transition-colors">
                            <div class="flex flex-col">
                                <span class="text-sm font-bold flex items-center gap-2">
                                    {musicService.name}
                                    {#if isLinked(mediaServer.id, musicService.id)}
                                        <span class="text-[10px] bg-primary text-black px-1.5 py-0.5 rounded-sm uppercase tracking-tight">Active</span>
                                    {/if}
                                </span>
                                <span class="text-xs text-muted">{musicService.provider}</span>
                            </div>
                            <button 
                                class="px-4 py-1.5 text-xs font-bold rounded-lg transition-all {isLinked(mediaServer.id, musicService.id) ? 'bg-[#b04242]/20 text-[#ef4444] border border-[#b04242]/30 hover:bg-[#b04242]/30' : 'bg-primary/10 text-primary border border-primary/20 hover:bg-primary/20'}"
                                on:click={() => toggleLink(mediaServer.id, musicService.id)}
                            >
                                {isLinked(mediaServer.id, musicService.id) ? 'Unlink' : 'Link'}
                            </button>
                        </div>
                    {/each}
                </div>
            </div>
        {/each}

        {#if mediaServers.length === 0}
            <div class="text-center text-muted text-sm italic py-8">
                No media servers configured.
            </div>
        {/if}
    </div>
</div>
