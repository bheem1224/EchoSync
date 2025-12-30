<script>
  import { writable } from 'svelte/store';

  const downloadSettings = writable({
    slskdDir: '/app/downloads',
    libraryDir: '/app/Transfer',
    logLevel: 'INFO'
  });

  const qualityProfiles = writable([
    { name: 'Audiophile', formats: ['FLAC', 'MP3 320 kbps', 'MP3 256 kbps', 'MP3 192 kbps'] },
    { name: 'Balanced', formats: ['FLAC', 'MP3 320 kbps', 'MP3 256 kbps', 'MP3 192 kbps'] },
    { name: 'Space Saver', formats: ['MP3 320 kbps', 'MP3 256 kbps', 'MP3 192 kbps'] }
  ]);

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
    <h2>Quality Profiles</h2>
    <div class="profiles">
      {#each $qualityProfiles as profile, index}
        <div class="profile">
          <h3>{profile.name}</h3>
          <button on:click={() => removeProfile(index)}>Delete</button>
          <ul>
            {#each profile.formats as format}
              <li>{format}</li>
            {/each}
          </ul>
        </div>
      {/each}
      <button on:click={addProfile}>Add Profile</button>
    </div>
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