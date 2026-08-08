from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class JobSchema(BaseModel):
    id: Optional[str] = None
    type: Optional[str] = None
    state: Optional[str] = None  # queued, running, failed, completed
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    meta: Dict = Field(default_factory=dict)

    def to_dict(self) -> Dict:
        return self.model_dump(exclude_none=True)

class JobRunRequest(BaseModel):
    job_name: Optional[str] = None
    name: Optional[str] = None
    params: Optional[Dict[str, Any]] = Field(default_factory=dict)

class JobIntervalRequest(BaseModel):
    interval_seconds: float
