<script>
  import { jobs } from '../stores/jobs';

  let activeJobs = [];
  let completedJobs = [];

  $: {
    activeJobs = $jobs.active;
    completedJobs = $jobs.history;
  }
</script>

<div class="job-status">
  <h2>Job Status</h2>

  <div class="job-section">
    <h3>Active Jobs</h3>
    {#if activeJobs && activeJobs.length > 0}
      <ul>
        {#each activeJobs as job}
          <li>
            {job?.name || job?.id || 'Unknown Job'} 
            {#if job?.progress !== undefined}
              - {job.progress}%
            {:else if job?.status}
              - {job.status}
            {/if}
          </li>
        {/each}
      </ul>
    {:else}
      <p>No active jobs.</p>
    {/if}
  </div>

  <div class="job-section">
    <h3>Completed Jobs</h3>
    {#if completedJobs && completedJobs.length > 0}
      <ul>
        {#each completedJobs as job}
          <li>
            {job?.name || job?.id || 'Unknown Job'}
            {#if job?.completed_at}
              - Completed {new Date(job.completed_at).toLocaleString()}
            {:else}
              - Completed
            {/if}
          </li>
        {/each}
      </ul>
    {:else}
      <p>No completed jobs.</p>
    {/if}
  </div>
</div>

<style>
  .job-status {
    padding: 20px;
    border: 1px solid #ccc;
    border-radius: 5px;
    margin-bottom: 20px;
  }

  .job-section {
    margin-bottom: 15px;
  }

  .job-section h3 {
    margin-bottom: 10px;
  }

  ul {
    list-style: none;
    padding: 0;
  }

  li {
    margin-bottom: 5px;
  }
</style>