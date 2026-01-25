from pydantic import BaseModel
from typing import Optional, Tuple

class Flight(BaseModel):
    flight_id: str
    status: str
    arrival_time: float
    assigned_gate: Optional[str]
    assigned_runway: Optional[str]
    delay: float
    position: Tuple[int,int]