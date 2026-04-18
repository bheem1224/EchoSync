with open('core/hook_manager.py', 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if "value = callback(value, *args, **kwargs)" in line:
        new_lines.append("                        value = callback(value, *args, **kwargs)\n")
    elif "if asyncio.iscoroutine(value):" in line:
        new_lines.append("                        if asyncio.iscoroutine(value):\n")
    elif "# H1: close the coroutine" in line:
        new_lines.append("                            # H1: close the coroutine to silence ResourceWarning, restore\n")
    elif "# the last known-good value" in line:
        new_lines.append("                            # the last known-good value, and log so the plugin author is\n")
    elif "# immediately informed." in line:
        new_lines.append("                            # immediately informed.  The chain continues uninterrupted.\n")
    elif "value.close()" in line:
        new_lines.append("                            value.close()\n")
    elif "value = prev_value" in line and "except" not in ''.join(lines) and lines.index(line) > 30: # ugly heuristic
        # we know it's there twice
        pass
    else:
        new_lines.append(line)

with open('core/hook_manager.py', 'w') as f:
    f.writelines(new_lines)
