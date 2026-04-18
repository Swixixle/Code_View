"""Live monitoring session model."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class MonitoringSession(BaseModel):
    """Registered repository monitoring configuration."""

    session_id: str
    repository_url: str
    check_interval_seconds: int = 300
    enabled: bool = True
    last_commit: Optional[str] = None
    last_check_at: Optional[datetime] = None
    webhook_secret: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
