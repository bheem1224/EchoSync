import re

with open('webui/src/components/SystemSettings.svelte', 'r') as f:
    content = f.read()

# Let's inspect the version string display
print(re.search(r'v\{provider\.version\}', content).group(0))

with open('webui/src/components/SystemSettings.svelte', 'w') as f:
    f.write(content)
