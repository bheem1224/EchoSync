<svelte:options customElement="echosync-settings-form" />

<script>
  export let schema = "{}";
  export let initialValues = "{}";

  // Reactively parse props if they are strings
  $: parsedSchema = typeof schema === 'string' ? JSON.parse(schema || "{}") : schema || {};
  $: parsedInitialValues = typeof initialValues === 'string' ? JSON.parse(initialValues || "{}") : initialValues || {};

  // Initialize formData reacting to initialValues change, applying defaults from schema
  let formData = {};

  $: {
    const newData = { ...parsedInitialValues };
    for (const key of Object.keys(parsedSchema)) {
      if (newData[key] === undefined) {
         if (parsedSchema[key].default !== undefined) {
             newData[key] = parsedSchema[key].default;
         } else {
             // Basic default types
             if (parsedSchema[key].type === 'boolean') newData[key] = false;
             else if (parsedSchema[key].type === 'number') newData[key] = 0;
             else newData[key] = '';
         }
      }
    }
    formData = newData;
  }

  let formRef;

  function handleSave(event) {
    event.preventDefault();
    if (formRef) {
      formRef.dispatchEvent(new CustomEvent('es-settings-save', {
        detail: formData,
        bubbles: true,
        composed: true
      }));
    }
  }

  function toggleBoolean(key) {
      formData[key] = !formData[key];
  }
</script>

<form bind:this={formRef} on:submit={handleSave} class="flex flex-col gap-6 p-6 bg-surface rounded-global border border-border shadow-sm">
  {#each Object.entries(parsedSchema) as [key, field]}
    <div class="flex flex-col gap-2">
      <label for={key} class="text-sm font-medium text-primary">
        {field.label || key}
        {#if field.required}
          <span class="text-red-500 ml-1">*</span>
        {/if}
      </label>

      {#if field.type === 'string'}
        <input
          id={key}
          type={field.secret ? "password" : "text"}
          bind:value={formData[key]}
          required={field.required}
          class="px-4 py-2 bg-background border border-border rounded-global text-primary focus:outline-none focus:border-accent transition-colors"
        />
      {:else if field.type === 'number'}
        <input
          id={key}
          type="number"
          bind:value={formData[key]}
          required={field.required}
          min={field.min}
          max={field.max}
          step={field.step || 1}
          class="px-4 py-2 bg-background border border-border rounded-global text-primary focus:outline-none focus:border-accent transition-colors"
        />
      {:else if field.type === 'boolean'}
        <!-- Custom Pill Toggle Switch -->
        <!-- svelte-ignore a11y-click-events-have-key-events -->
        <!-- svelte-ignore a11y-no-static-element-interactions -->
        <div
          class="w-12 h-6 flex items-center rounded-full p-1 cursor-pointer transition-colors duration-200 {formData[key] ? 'bg-accent' : 'bg-surface-hover border border-border'}"
          on:click={() => toggleBoolean(key)}
        >
          <div
            class="bg-primary w-4 h-4 rounded-full shadow-md transform transition-transform duration-200 {formData[key] ? 'translate-x-6' : 'translate-x-0'}"
          ></div>
        </div>
        <!-- Hidden checkbox for standard form submission if needed, but we bind formData directly -->
        <input type="checkbox" id={key} bind:checked={formData[key]} class="hidden" required={field.required} />
      {:else if field.type === 'select'}
        <select
          id={key}
          bind:value={formData[key]}
          required={field.required}
          class="px-4 py-2 bg-background border border-border rounded-global text-primary focus:outline-none focus:border-accent transition-colors cursor-pointer"
        >
          {#if field.options && Array.isArray(field.options)}
            {#each field.options as option}
              <!-- Support both simple arrays and arrays of objects with value/label -->
              {#if typeof option === 'object' && option !== null}
                 <option value={option.value}>{option.label}</option>
              {:else}
                 <option value={option}>{option}</option>
              {/if}
            {/each}
          {/if}
        </select>
      {:else}
         <!-- Fallback -->
         <span class="text-sm text-red-500">Unsupported field type: {field.type}</span>
      {/if}
    </div>
  {/each}

  <div class="flex justify-end pt-4 mt-2 border-t border-border">
    <button
      type="submit"
      class="px-6 py-2 bg-accent text-primary font-medium rounded-global hover:opacity-90 transition-opacity focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-accent"
    >
      Save Settings
    </button>
  </div>
</form>

<style>
  /* The memory constraint mentions using `--es-` prefixed CSS variables mapped to semantic classes,
     which are used in the template (bg-surface, text-primary, bg-accent, etc.) via tailwind config */
</style>
