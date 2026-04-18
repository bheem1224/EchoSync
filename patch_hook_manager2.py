with open('core/hook_manager.py', 'r') as f:
    content = f.read()

# Fix indentation of prev_value and try block
bad_block = """                    import logging
                prev_value = value
                try:"""
good_block = """                    import logging
                    prev_value = value
                    try:"""
content = content.replace(bad_block, good_block)

with open('core/hook_manager.py', 'w') as f:
    f.write(content)
