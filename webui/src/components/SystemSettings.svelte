<script>
  const cpuUsage = 14;
  const memoryUsedGb = 2.4;
  const memoryTotalGb = 8;
  const memoryUsage = Math.round((memoryUsedGb / memoryTotalGb) * 100);

  const libraryStats = {
    totalTracks: '14,230',
    totalAlbums: '1,104',
    storageUsed: '412 GB'
  };

  let providerStates = [
    { id: 'plex', name: 'Plex', enabled: true },
    { id: 'navidrome', name: 'Navidrome', enabled: true },
    { id: 'slskd', name: 'Slskd', enabled: true },
    { id: 'yt-dlp', name: 'yt-dlp', enabled: false }
  ];

  function toggleProvider(providerId) {
    providerStates = providerStates.map((provider) =>
      provider.id === providerId
        ? { ...provider, enabled: !provider.enabled }
        : provider
    );
  }
</script>

<section class="min-h-full bg-gray-900 text-gray-100 rounded-xl p-4 md:p-6">
  <header class="mb-6">
    <h1 class="text-2xl font-semibold tracking-tight">System</h1>
    <p class="text-sm text-gray-400">System health, library metrics, and provider controls.</p>
  </header>

  <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
    <article class="bg-gray-800 border border-gray-700/60 rounded-xl p-5 shadow-sm">
      <h2 class="text-base font-semibold mb-4">System Resources</h2>

      <div class="space-y-4">
        <div>
          <div class="flex items-center justify-between text-sm mb-2">
            <span class="text-gray-300">CPU Usage</span>
            <span class="font-medium text-cyan-300">{cpuUsage}%</span>
          </div>
          <div class="w-full h-2.5 bg-gray-700 rounded-full overflow-hidden">
            <div
              class="h-full rounded-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-700 ease-out"
              style="width: {cpuUsage}%"
            ></div>
          </div>
        </div>

        <div>
          <div class="flex items-center justify-between text-sm mb-2">
            <span class="text-gray-300">Memory Usage</span>
            <span class="font-medium text-emerald-300">{memoryUsedGb} GB / {memoryTotalGb} GB</span>
          </div>
          <div class="w-full h-2.5 bg-gray-700 rounded-full overflow-hidden">
            <div
              class="h-full rounded-full bg-gradient-to-r from-emerald-500 to-teal-500 transition-all duration-700 ease-out"
              style="width: {memoryUsage}%"
            ></div>
          </div>
        </div>
      </div>
    </article>

    <article class="bg-gray-800 border border-gray-700/60 rounded-xl p-5 shadow-sm">
      <h2 class="text-base font-semibold mb-4">Library Statistics</h2>

      <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div class="bg-gray-900/60 rounded-lg border border-gray-700/40 p-3">
          <div class="flex items-center gap-2 text-gray-300 text-xs mb-2">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <path d="M9 18V5l12-2v13" />
              <circle cx="6" cy="18" r="3" />
              <circle cx="18" cy="16" r="3" />
            </svg>
            Total Tracks
          </div>
          <div class="text-xl font-semibold">{libraryStats.totalTracks}</div>
        </div>

        <div class="bg-gray-900/60 rounded-lg border border-gray-700/40 p-3">
          <div class="flex items-center gap-2 text-gray-300 text-xs mb-2">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <rect x="3" y="4" width="18" height="16" rx="2" />
              <path d="M8 4v16" />
            </svg>
            Total Albums
          </div>
          <div class="text-xl font-semibold">{libraryStats.totalAlbums}</div>
        </div>

        <div class="bg-gray-900/60 rounded-lg border border-gray-700/40 p-3">
          <div class="flex items-center gap-2 text-gray-300 text-xs mb-2">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <ellipse cx="12" cy="5" rx="8" ry="3" />
              <path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5" />
              <path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6" />
            </svg>
            Storage Used
          </div>
          <div class="text-xl font-semibold">{libraryStats.storageUsed}</div>
        </div>
      </div>
    </article>

    <article class="lg:col-span-2 bg-gray-800 border border-gray-700/60 rounded-xl p-5 shadow-sm">
      <h2 class="text-base font-semibold mb-4">Installed Providers</h2>

      <div class="space-y-3">
        {#each providerStates as provider}
          <div class="flex items-center justify-between bg-gray-900/60 border border-gray-700/40 rounded-lg px-4 py-3">
            <div>
              <p class="font-medium text-gray-100">{provider.name}</p>
              <p class="text-xs text-gray-400">{provider.enabled ? 'Enabled' : 'Disabled'}</p>
            </div>

            <label class="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                class="sr-only peer"
                checked={provider.enabled}
                on:change={() => toggleProvider(provider.id)}
              />
              <span class="w-11 h-6 bg-gray-600 rounded-full peer peer-checked:bg-emerald-500 transition-colors duration-200"></span>
              <span class="absolute left-0.5 top-0.5 w-5 h-5 bg-white rounded-full transition-transform duration-200 peer-checked:translate-x-5"></span>
            </label>
          </div>
        {/each}
      </div>

      <p class="mt-4 text-xs italic text-amber-300/90">
        Note: Disabling a provider requires a system restart to fully unload.
      </p>
    </article>
  </div>
</section>