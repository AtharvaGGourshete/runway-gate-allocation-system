from __future__ import annotations

from typing import Any, Dict, Optional

from app.agents.resource_dispatch_agent import ResourceDispatchAgent
from app.agents.surface_movement_agent import SurfaceMovementAgent
from app.simulation.airport_graph import AirportGraph


class MultiAgentCoordinator:
    """
    Coordinator that runs multiple operational agents each simulation step.

    This is a pragmatic, step-based multi-agent system (no SimPy):
    - SurfaceMovementAgent: taxi planning & deconfliction
    - ResourceDispatchAgent: ground service equipment (GSE) dispatching
    """

    def __init__(self, graph: Optional[AirportGraph] = None):
        self.graph = graph or AirportGraph()
        self.surface_agent = SurfaceMovementAgent(graph=self.graph)
        self.resource_agent = ResourceDispatchAgent(graph=self.graph)

    def step(self, current_time: int) -> Dict[str, Any]:
        surface = self.surface_agent.step(current_time=current_time)
        resources = self.resource_agent.step(current_time=current_time)

        return {
            "status": "success",
            "current_time": current_time,
            "surface": surface,
            "resources": resources,
        }


coordinator = MultiAgentCoordinator()

