with open('/app/core/matching_engine/matching_engine.py', 'r') as f:
    content = f.read()

import re

new_init = """    def __init__(self, profile: ScoringProfile):
        \"\"\"
        Initialize engine with a scoring profile
        \"\"\"
        self.profile = profile
        self.weights = profile.get_weights()

        from core.hook_manager import hook_manager

        # weights should be a dict-like or have a dict we can update, let's see.
        # But wait, weights might be a dataclass. Let's convert to dict, let hook update it, then set back.
        weights_dict = self.weights.__dict__.copy() if hasattr(self.weights, '__dict__') else self.weights
        hook_result = hook_manager.apply_filters('ON_SCORING_WEIGHTS_CALCULATE', weights_dict)
        if hook_result and isinstance(hook_result, dict):
            if hasattr(self.weights, '__dict__'):
                self.weights.__dict__.update(hook_result)
            else:
                self.weights.update(hook_result)

        if not self.weights.validate():
            raise ValueError("Invalid scoring weights")"""

content = re.sub(
    r'    def __init__\(self, profile: ScoringProfile\):.*?if not self\.weights\.validate\(\):',
    new_init + '\n            if not self.weights.validate():',
    content,
    flags=re.DOTALL
)

with open('/app/core/matching_engine/matching_engine.py', 'w') as f:
    f.write(content)
