with open('/app/core/matching_engine/matching_engine.py', 'r') as f:
    content = f.read()

import re

# Hook ON_ENGINE_EVALUATE in calculate_match
new_calculate_match = """    def calculate_match(
        self,
        source: EchosyncTrack,
        candidate: EchosyncTrack,
        target_source: Optional[str] = None,
        target_identifier: Optional[str] = None,
    ) -> MatchResult:
        \"\"\"
        Calculate match confidence between source and candidate tracks
        \"\"\"
        from core.hook_manager import hook_manager
        hook_result = hook_manager.apply_filters('ON_ENGINE_EVALUATE', {'skip': False, 'result': None}, source=source, candidate=candidate, target_source=target_source, target_identifier=target_identifier)
        if hook_result and isinstance(hook_result, dict) and hook_result.get('skip'):
            return hook_result.get('result')

        # Initialize scoring components"""

content = re.sub(
    r'    def calculate_match\(\n        self,\n        source: EchosyncTrack,\n        candidate: EchosyncTrack,\n        target_source: Optional\[str\] = None,\n        target_identifier: Optional\[str\] = None,\n    \) -> MatchResult:.*?        # Initialize scoring components',
    new_calculate_match,
    content,
    flags=re.DOTALL
)

with open('/app/core/matching_engine/matching_engine.py', 'w') as f:
    f.write(content)
