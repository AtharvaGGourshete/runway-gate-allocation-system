from pydantic import BaseModel
from typing import Optional

class Gate(BaseModel):
    gate_id: str
    occupied_by: Optional[str]
    status: str