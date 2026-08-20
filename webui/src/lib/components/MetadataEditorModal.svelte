<script>
  import MetadataReviewModal from './MetadataReviewModal.svelte';
  export let task = null;
</script>

<MetadataReviewModal {task} on:close on:saved on:approved on:rejected on:approvestart on:approveend />
