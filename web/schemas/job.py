from dataclasses import dataclass, field
from typing import Optional, Dict

@dataclass
class JobSchema:
    id: Optional[str] = None
    type: Optional[str] = None
    state: Optional[str] = None  # queued, running, failed, completed
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    meta: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type,
            "state": self.state,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "meta": self.meta,
        }
