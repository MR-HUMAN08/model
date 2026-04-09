from typing import Any, Dict

try:
    from openenv.core import EnvClient
except Exception:
    try:
        from openenv.core.client import EnvClient
    except Exception:
        class EnvClient:  # type: ignore[no-redef]
            def __class_getitem__(cls, _item):
                return cls

            def __init__(self, *args, **kwargs):
                self.base_url = kwargs.get("base_url")

try:
    from openenv.core.env_server import State
except Exception:
    from pydantic import BaseModel as State

try:
    from models import RedTeamAction, RedTeamObservation, RedTeamState
except Exception:
    from .models import RedTeamAction, RedTeamObservation, RedTeamState


class RedteampentestlabEnv(EnvClient[RedTeamAction, RedTeamObservation, State]):
    env_name = "redteampentestlab"
    action_type = RedTeamAction
    observation_type = RedTeamObservation

    def _step_payload(self, action: RedTeamAction) -> Dict[str, Any]:
        if hasattr(action, "model_dump"):
            return action.model_dump()
        return {"action": getattr(action, "action", str(action))}

    def _parse_result(self, result: Dict[str, Any]) -> RedTeamObservation:
        if hasattr(RedTeamObservation, "model_validate"):
            return RedTeamObservation.model_validate(result)
        return RedTeamObservation(**result)

    def _parse_state(self, state_payload: Dict[str, Any]) -> State:
        if hasattr(RedTeamState, "model_validate"):
            return RedTeamState.model_validate(state_payload)
        return RedTeamState(**state_payload)