from pydantic import BaseModel

class Metrics(BaseModel):
    avg_delay: float
    conflicts_resolved: int
    utilization: dict
