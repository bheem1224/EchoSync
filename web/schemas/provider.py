from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class ProviderSchema:
    name: str
    capabilities: List[str] = field(default_factory=list)
    scopes: List[str] = field(default_factory=list)  # library, sync, search, download, utility
    priority: int = 0

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "capabilities": self.capabilities,
            "scopes": self.scopes,
            "priority": self.priority,
        }
