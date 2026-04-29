import re

with open('webui/src/components/SystemSettings.svelte', 'r') as f:
    content = f.read()

# Let's check how the plugin card looks
match = re.search(r'(<div class="flex items-center justify-between bg-gray-900/60 border border-gray-700/40 rounded-lg px-4 py-3".*?</div>\s*</div>\s*</div>)', content, re.DOTALL)
if match:
    # Update classes
    old_card = match.group(1)

    # We want to add grayscale and opacity based on provider.disabled
    new_card = old_card.replace(
        '<div class="flex items-center justify-between bg-gray-900/60 border border-gray-700/40 rounded-lg px-4 py-3"',
        '<div class="flex items-center justify-between bg-gray-900/60 border border-gray-700/40 rounded-lg px-4 py-3 transition-all {provider.disabled ? \'opacity-50 grayscale\' : \'\'}"'
    )

    content = content.replace(old_card, new_card)

with open('webui/src/components/SystemSettings.svelte', 'w') as f:
    f.write(content)
