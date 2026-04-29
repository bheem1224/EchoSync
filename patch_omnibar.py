import re
with open('webui/src/lib/components/Omnibar.svelte', 'r') as f:
    content = f.read()

# Fix window is not defined error for server side rendering
content = content.replace("window.addEventListener", "if (typeof window !== 'undefined') window.addEventListener")
content = content.replace("window.removeEventListener", "if (typeof window !== 'undefined') window.removeEventListener")
content = content.replace("const platform = window.navigator", "const platform = typeof window !== 'undefined' ? window.navigator : {platform: ''}")

with open('webui/src/lib/components/Omnibar.svelte', 'w') as f:
    f.write(content)
