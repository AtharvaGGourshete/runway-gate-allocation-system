from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class User(BaseModel):
    user_id: str
    username: str
    email: EmailStr
    role: str = "user"
    created_at: datetime
    last_active: Optional[datetime]
    preferences: Optional[dict]
