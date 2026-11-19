<script>
  import OmniSearch from './OmniSearch.svelte';

  let {
    inline = false,
    forcedPrefix = "",
    placeholder = "Search library, settings, or type ? for web search...",
    mode = "inline",
    onselect = null
  } = $props();
</script>

<OmniSearch
  {inline}
  {mode}
  {forcedPrefix}
  {placeholder}
  {onselect}
/>
