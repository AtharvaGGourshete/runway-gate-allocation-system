from pydantic import BaseModel
from typing import Optional

class Runway(BaseModel):
    runway_id: str
    occupied_by: Optional[str]
    status: str 
