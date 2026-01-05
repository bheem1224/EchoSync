<script>
  import { writable } from 'svelte/store';

  const downloadSettings = writable({
    slskdDir: '/app/downloads',
    libraryDir: '/app/Transfer',
    logLevel: 'INFO'
  });

  const appearanceSettings = writable({
    theme: 'dark'
  });

  // Start with an empty list so the user config is authoritative
  const qualityProfiles = writable([]);

  function addProfile() {
    qualityProfiles.update((profiles) => {
      profiles.push({ name: 'New Profile', formats: [] });
      return profiles;
    });
  }

  function removeProfile(index) {
    qualityProfiles.update((profiles) => {
      profiles.splice(index, 1);
      return profiles;
    });
  }
</script>

<div class="preferences">
  <h1>Preferences</h1>

  <section class="card">
    <h2>Download Settings</h2>
    <label>
      Slskd Download Dir:
      <input type="text" bind:value={$downloadSettings.slskdDir} />
      <button>Browse</button>
    </label>
    <label>
      Library Dir:
      <input type="text" bind:value={$downloadSettings.libraryDir} />
      <button>Browse</button>
    </label>
    <label>
      Log Level:
      <select bind:value={$downloadSettings.logLevel}>
        <option value="DEBUG">DEBUG</option>
        <option value="INFO">INFO</option>
        <option value="WARNING">WARNING</option>
        <option value="ERROR">ERROR</option>
      </select>
    </label>
  </section>

  <section class="card">
    <h2>Appearance</h2>
    <label>
      Theme:
      <select bind:value={$appearanceSettings.theme}>
        <option value="dark">Dark</option>
        <option value="light">Light</option>
      </select>
    </label>
  </section>

  <section class="card">
    <h2>Quality Profiles</h2>
    <button on:click={addProfile}>Add</button>
    {#each $qualityProfiles as profile, index}
      <div>
        <input type="text" bind:value={profile.name} />
        <button on:click={() => removeProfile(index)}>Remove</button>
      </div>
    {/each}
  </section>
</div>

<style>
  .preferences {
    padding: 16px;
  }

  .card {
    margin-bottom: 24px;
    padding: 16px;
    border: 1px solid #ccc;
    border-radius: 8px;
  }

  .profiles {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .profile {
    border: 1px solid #ccc;
    padding: 8px;
    border-radius: 8px;
  }
</style>