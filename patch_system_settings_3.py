import re

with open('webui/src/components/SystemSettings.svelte', 'r') as f:
    content = f.read()

# I want to add the Beta indicator next to the version tag.
# Also modify the data mapping to capture if it is beta
# The loadProviders maps `providerStates = response.data.map(provider => ({ ... }))`

map_code = """
        providerStates = response.data.map(provider => ({
          id: provider.id,
          name: provider.display_name || provider.name || provider.id,
          configured: provider.is_configured || false,
          disabled: provider.disabled || false,
          version: provider.version || '0.0.0',
          channel: provider.channel || 'stable',
          category: provider.category || 'provider'
        }));
"""

# Let's see the current mapping
match_map = re.search(r'providerStates = response\.data\.map\(provider => \(\{.*?\}\)\);', content, re.DOTALL)
if match_map:
    content = content.replace(match_map.group(0), map_code.strip())

# The version tag is inside:
# <span class="text-[10px] text-gray-500 font-mono bg-gray-800/80 px-1.5 py-0.5 rounded border border-gray-700/50">
#   v{provider.version}
# </span>

version_span = """<span class="text-[10px] text-gray-500 font-mono bg-gray-800/80 px-1.5 py-0.5 rounded border border-gray-700/50">
                      v{provider.version}
                    </span>"""

new_version_span = """<span class="text-[10px] text-gray-500 font-mono bg-gray-800/80 px-1.5 py-0.5 rounded border border-gray-700/50">
                      v{provider.version}
                      {#if provider.channel === 'beta'}
                        <span class="ml-1 text-blue-400 font-bold uppercase tracking-wider">Beta</span>
                      {/if}
                    </span>"""

content = content.replace(version_span, new_version_span)

with open('webui/src/components/SystemSettings.svelte', 'w') as f:
    f.write(content)
