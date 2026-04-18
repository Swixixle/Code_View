"""Analysis session model."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AnalysisSession(BaseModel):
    """Server-side analysis job / session metadata."""

    session_id: str
    repository_url: str
    mode: str = "standard"
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    error: Optional[str] = None
    result_summary: Dict[str, Any] = Field(default_factory=dict)
    stages: List[str] = Field(default_factory=list)
