---
title: redteampentestlab
emoji: "🛡️"
colorFrom: red
colorTo: yellow
sdk: docker
app_port: 8000
pinned: false
---

# redteampentestlab

redteampentestlab is an OpenEnv-compatible reinforcement learning environment for automated penetration testing simulation. The agent must solve realistic pentest chains by executing actions in the correct order and collecting CTF-style flags.

## Environment Description

The environment exposes a FastAPI server through OpenEnv and simulates three pentesting missions:

1. Easy: Web Application Recon
2. Medium: SQLi to RCE
3. Hard: APT Multi-Stage Compromise

Each mission has:

- A target host or network
- A required ordered action chain
- Step-level rewards for partial progress
- A completion reward and a hidden flag

The reward design is shaped for RL training signals and remains strictly between 0 and 1.

## Action Space

The action model accepts one of the following values:

- scan
- enumerate
- exploit
- escalate
- c2
- cleanup

## Observation Space

Each step returns an observation with:

- target_ip: current host or subnet under assessment
- current_state: BRIEFING, IN_PROGRESS, SUCCESS, INVALID, ORDER_VIOLATION, or REPEAT
- output: realistic pentest tool-style output for the executed action
- difficulty: easy, medium, or hard
- reward: scalar reward signal (strictly 0 < reward < 1)
- done: episode termination flag

## State Space

Environment state includes:

- episode: episode counter
- task: active task name
- progress: normalized task completion value between 0.0 and 1.0

## Setup Instructions

### Option A: pip

```bash
pip install -r requirements.txt
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

### Option B: uv

```bash
uv sync
uv run uvicorn server.app:app --host 0.0.0.0 --port 8000
```

### Validate OpenEnv

```bash
openenv validate
openenv validate --url http://localhost:8000 --json --verbose
```

## Inference and Grading

Run baseline inference:

```bash
python inference.py
```

Run grader:

```bash
python inference.py > out.txt && python grader.py out.txt
```

Inference also writes a structured pentest report to pentest_report.json.

## Environment Variables

- API_BASE_URL (default: http://localhost:11434/v1)
- MODEL_NAME (default: gpt-4o-mini)
- API_KEY (fallback: HF_TOKEN, then ollama)

## Docker

```bash
docker build -t redteampentestlab .
docker run -p 8000:8000 redteampentestlab
```