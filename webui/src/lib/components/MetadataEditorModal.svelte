<script>
  import MetadataReviewModal from "./MetadataReviewModal.svelte";
  export let task = null;
  export let mediaId = null;
  export let media_id = null;
</script>

<MetadataReviewModal
  {task}
  mediaId={mediaId || media_id}
  media_id={mediaId || media_id}
  on:close
  on:saved
  on:approved
  on:rejected
  on:approvestart
  on:approveend
/>
