from pydantic import BaseModel
from typing import Optional

class Event(BaseModel):
    timestamp: float
    type: str
    flight_id: Optional[str]
    resource: Optional[str]
    action: str
