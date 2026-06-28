<script>
  import OmniSearch from './OmniSearch.svelte';

  let { 
    forcedPrefix = "", 
    placeholder = "Search library, settings, or type ? for web search...", 
    mode = "inline",
    onselect = null
  } = $props();
</script>

<OmniSearch 
  inline={false} 
  mode={mode} 
  forcedPrefix={forcedPrefix} 
  placeholder={placeholder} 
  onselect={onselect} 
/>
