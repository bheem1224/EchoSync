import re

content = open("tests/services/test_metadata_enhancer.py").read()
content = content.replace(
    "    enhancer.tag_file(fake_file, metadata)",
    '    from unittest.mock import patch\n    with patch("services.metadata_enhancer.echosync_core.write_metadata"):\n        enhancer.tag_file(fake_file, metadata)',
)
open("tests/services/test_metadata_enhancer.py", "w").write(content)
