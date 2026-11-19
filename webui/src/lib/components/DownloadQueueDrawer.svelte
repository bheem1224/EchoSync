<script>
  import DownloadDrawer from './DownloadDrawer.svelte';
  import { isDownloadDrawerOpen } from '../../stores/ui';

  export let isOpen = false;

  $: if (isOpen !== undefined && isOpen !== $isDownloadDrawerOpen) {
    isDownloadDrawerOpen.set(Boolean(isOpen));
  }
</script>

<DownloadDrawer />
