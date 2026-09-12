<script lang="ts">
  import { createEventDispatcher } from "svelte";
  import ConfirmDialog from "../../../components/ConfirmDialog.svelte";

  export let plugin: any = null;
  export let escalationData: any = null;
  export let show: boolean = false;

  const dispatch = createEventDispatcher();

  function onConfirm() {
    dispatch("confirm");
  }

  function onCancel() {
    dispatch("cancel");
  }

  interface EscalationItem {
    scope: string;
    title: string;
    description: string;
    icon: string;
    color: string;
    items?: string[];
  }

  $: normalizedEscalations = parseEscalations(escalationData);

  function parseEscalations(data: any): EscalationItem[] {
    if (!data) return [];
    const list: EscalationItem[] = [];

    if (Array.isArray(data)) {
      for (const item of data) {
        const scope = item.scope || "";
        if (scope === "privileged_mode") {
          list.push({
            scope,
            title: "Privileged Mode",
            description:
              item.description ||
              "Allows the plugin to bypass AST security sandboxing and perform direct OS-level operations.",
            icon: "⚖️",
            color: "red",
          });
        } else if (scope === "network_domains") {
          list.push({
            scope,
            title: "Expanded Network Access",
            description:
              item.description ||
              "The plugin is requesting access to new external domains:",
            icon: "🌐",
            color: "blue",
            items: item.added || [],
          });
        } else if (scope === "database.read_library") {
          list.push({
            scope,
            title: "Library Read Access",
            description:
              item.description ||
              "Requests permission to read canonical library data.",
            icon: "📖",
            color: "emerald",
          });
        } else if (scope === "database.mutate_aliases") {
          list.push({
            scope,
            title: "Entity Alias Mutation",
            description:
              item.description ||
              "Requests permission to write entity aliases to library.",
            icon: "🏷️",
            color: "amber",
          });
        } else if (scope === "database.mutate_attributes") {
          list.push({
            scope,
            title: "Entity Attribute Mutation",
            description:
              item.description ||
              "Requests permission to write entity attributes to library.",
            icon: "⚡",
            color: "purple",
          });
        } else if (scope === "wasm_fs_access") {
          list.push({
            scope,
            title: "File System Access",
            description:
              item.description ||
              "The plugin is requesting access to additional file system paths:",
            icon: "📁",
            color: "yellow",
            items: item.added || [],
          });
        } else {
          list.push({
            scope,
            title: `Permission: ${scope}`,
            description: item.description || `Requests scope '${scope}'.`,
            icon: "🛡️",
            color: "cyan",
          });
        }
      }
      return list;
    }

    // Legacy object shape fallback
    if (data.privileged_mode) {
      list.push({
        scope: "privileged_mode",
        title: "Privileged Mode",
        description:
          "Allows the plugin to bypass AST security sandboxing and perform direct OS-level operations.",
        icon: "⚖️",
        color: "red",
      });
    }
    if (data.network_domains && data.network_domains.length > 0) {
      list.push({
        scope: "network_domains",
        title: "Expanded Network Access",
        description: "The plugin is requesting access to new external domains:",
        icon: "🌐",
        color: "blue",
        items: data.network_domains,
      });
    }
    if (data.wasm_fs_access && data.wasm_fs_access.length > 0) {
      list.push({
        scope: "wasm_fs_access",
        title: "File System Access",
        description:
          "The plugin is requesting access to additional file system paths:",
        icon: "📁",
        color: "yellow",
        items: data.wasm_fs_access,
      });
    }

    return list;
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
      An update for <strong>{plugin?.name}</strong> is requesting additional
      permissions:

      <ul class="mt-4 space-y-3">
        {#each normalizedEscalations as esc}
          <li
            class="flex items-start gap-3 p-3 rounded-lg border {esc.color ===
            'red'
              ? 'bg-red-500/10 border-red-500/30'
              : ''} {esc.color === 'blue'
              ? 'bg-blue-500/10 border-blue-500/30'
              : ''} {esc.color === 'emerald'
              ? 'bg-emerald-500/10 border-emerald-500/30'
              : ''} {esc.color === 'amber'
              ? 'bg-amber-500/10 border-amber-500/30'
              : ''} {esc.color === 'purple'
              ? 'bg-purple-500/10 border-purple-500/30'
              : ''} {esc.color === 'yellow'
              ? 'bg-yellow-500/10 border-yellow-500/30'
              : ''} {esc.color === 'cyan'
              ? 'bg-cyan-500/10 border-cyan-500/30'
              : ''}"
          >
            <span class="text-lg">{esc.icon}</span>
            <div class="flex-1">
              <p
                class="font-bold text-xs {esc.color === 'red'
                  ? 'text-red-400'
                  : ''} {esc.color === 'blue'
                  ? 'text-blue-400'
                  : ''} {esc.color === 'emerald'
                  ? 'text-emerald-400'
                  : ''} {esc.color === 'amber'
                  ? 'text-amber-400'
                  : ''} {esc.color === 'purple'
                  ? 'text-purple-400'
                  : ''} {esc.color === 'yellow'
                  ? 'text-yellow-400'
                  : ''} {esc.color === 'cyan' ? 'text-cyan-400' : ''}"
              >
                {esc.title}
              </p>
              <p class="text-xs text-gray-400 leading-tight mt-0.5">
                {esc.description}
              </p>
              {#if esc.items && esc.items.length > 0}
                <div class="flex flex-wrap gap-2 mt-2">
                  {#each esc.items as chip}
                    <span
                      class="px-2 py-0.5 bg-white/5 border border-white/10 rounded font-mono text-[10px]"
                      >{chip}</span
                    >
                  {/each}
                </div>
              {/if}
            </div>
          </li>
        {/each}
      </ul>

      <p class="mt-4 text-[10px] text-gray-500 italic leading-tight">
        By proceeding, you grant this plugin full access to the requested
        resources. Only accept if you trust the source.
      </p>
    </div>
  </ConfirmDialog>
{/if}
