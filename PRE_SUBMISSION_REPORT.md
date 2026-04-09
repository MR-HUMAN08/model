# Pre-Submission Validation Report

Generated: 2026-04-09 05:39:41 UTC

## Phase1 Checklist
- hf_space_deploys: BLOCKED - Requires deployed HF Space URL; local environment cannot validate remote deployment ping.
- openenv_spec_compliance: PASS - openenv.yaml fields validated locally
- reset_step_state_endpoints: PASS - root=200,health=200,paths_ok=True
- dockerfile_builds: BLOCKED - =repository%3Aopenenv%2Fopenenv-base%3Apull&service=ghcr.io: 403 Forbidden
------
 > [internal] load metadata for ghcr.io/openenv/openenv-base:latest:
------
Dockerfile:12
--------------------
  10 |     RUN . /app/.venv/bin/activate && uv sync --no-dev
  11 |     
  12 | >>> FROM ghcr.io/openenv/openenv-base:latest AS runtime
  13 |     
  14 |     WORKDIR /app
--------------------
ERROR: failed to build: failed to solve: failed to fetch anonymous token: unexpected status from GET request to https://ghcr.io/token?scope=repository%3Aopenenv%2Fopenenv-base%3Apull&service=ghcr.io: 403 Forbidden

- baseline_reproduces: PASS - exit_code=0
- strict_log_blocks: PASS - start_blocks=3, end_blocks=3
- task_scores_strict_range: PASS - task_scores=[0.53, 0.5562, 0.6125], overall=0.5662

## Phase2 Readiness
- rl_signal_progression: PASS - [0.13, 0.14, 0.21]
- ctf_challenges_solvable: PASS - [True, True, True]
- pentest_report_artifact: PASS - tasks=3, ctf_solved=3

## Runtime Notes
- inference_runtime_under_20min: PASS - 1.81s
- resource_profile_note: INFO - Designed lightweight Python logic with deterministic actions; suitable for low-resource CPU execution.
- youtube_walkthrough_alignment: BLOCKED - Direct playback/transcript extraction from provided YouTube URL is blocked by Google sign-in in this environment.

## Blockers
- Docker build blocked in this environment due ghcr.io base image pull authorization (403).