from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class UserProfile(BaseModel):
    user_id: str
    display_name: Optional[str] = None
    created_at: datetime
    local_only: bool = True
    consent_confirmed: bool = False
    notes: Optional[str] = None
