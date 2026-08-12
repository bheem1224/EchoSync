<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import ConfirmDialog from '../../../components/ConfirmDialog.svelte';

  export let plugin: any = null;
  export let escalationData: any = null;
  export let show: boolean = false;

  const dispatch = createEventDispatcher();

  function onConfirm() {
    dispatch('confirm');
  }

  function onCancel() {
    dispatch('cancel');
  }
</script>

{#if show && plugin && escalationData}
  <ConfirmDialog 
      title="⚠️ Warning: Elevated Permissions Required"
      confirmText="Accept Risk & Update"
      cancelText="Cancel Update"
      danger={true}
      on:confirm={onConfirm}
      on:cancel={onCancel}
  >
      <div class="text-sm mt-2">
          An update for <strong>{plugin?.name}</strong> is requesting additional permissions:
          
          <ul class="mt-4 space-y-3">
            {#if escalationData.privileged_mode}
              <li class="flex items-start gap-3 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
                <span class="text-lg">⚖️</span>
                <div>
                  <p class="font-bold text-red-400">Privileged Mode</p>
                  <p class="text-xs text-gray-400 leading-tight">Allows the plugin to bypass AST security sandboxing and perform direct OS-level operations.</p>
                </div>
              </li>
            {/if}
            
            {#if escalationData.network_domains && escalationData.network_domains.length > 0}
              <li class="flex items-start gap-3 p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                <span class="text-lg">🌐</span>
                <div>
                  <p class="font-bold text-blue-400">Expanded Network Access</p>
                  <p class="text-xs text-gray-400 mb-2">The plugin is requesting access to new external domains:</p>
                  <div class="flex flex-wrap gap-2">
                    {#each escalationData.network_domains as domain}
                      <span class="px-2 py-0.5 bg-white/5 border border-white/10 rounded font-mono text-[10px]">{domain}</span>
                    {/each}
                  </div>
                </div>
              </li>
            {/if}

            {#if escalationData.wasm_fs_access && escalationData.wasm_fs_access.length > 0}
              <li class="flex items-start gap-3 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                <span class="text-lg">📁</span>
                <div>
                  <p class="font-bold text-yellow-400">File System Access</p>
                  <p class="text-xs text-gray-400 mb-2">The plugin is requesting access to additional file system paths:</p>
                  <div class="flex flex-wrap gap-2">
                    {#each escalationData.wasm_fs_access as path}
                      <span class="px-2 py-0.5 bg-white/5 border border-white/10 rounded font-mono text-[10px]">{path}</span>
                    {/each}
                  </div>
                </div>
              </li>
            {/if}
          </ul>
          
          <p class="mt-4 text-[10px] text-gray-500 italic leading-tight">
            By proceeding, you grant this plugin full access to the requested resources. Only accept if you trust the source.
          </p>
      </div>
  </ConfirmDialog>
{/if}
