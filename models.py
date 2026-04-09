from typing import Literal

from pydantic import Field

try:
    from openenv.core.env_server import Action, Observation, State
except Exception:
    from pydantic import BaseModel

    class Action(BaseModel):
        pass

    class Observation(BaseModel):
        reward: float = 0.1
        done: bool = False

    class State(BaseModel):
        pass


class RedTeamAction(Action):
    action: Literal["scan", "enumerate", "exploit", "escalate", "c2", "cleanup"]


class RedTeamObservation(Observation):
    target_ip: str = Field(description="Target host or network currently under assessment.")
    current_state: str = Field(description="Current simulator state label, such as BRIEFING or SUCCESS.")
    output: str = Field(description="Detailed command output and analysis text from the simulation step.")
    difficulty: str = Field(description="Task difficulty level: easy, medium, or hard.")


class RedTeamState(State):
    episode: int = Field(description="Current episode counter.")
    task: str = Field(description="Current task name.")
    progress: float = Field(description="Normalized completion progress from 0.0 to 1.0.")

    def __call__(self) -> "RedTeamState":
        return self