try:
    from openenv.core.env_server.http_server import create_app
except Exception as exc:
    raise RuntimeError(f"Failed to import OpenEnv HTTP server integration: {exc}")

try:
    from models import RedTeamAction, RedTeamObservation
except Exception:
    from ..models import RedTeamAction, RedTeamObservation

try:
    from server.environment import RedTeamPentestEnvironment
except Exception:
    from .environment import RedTeamPentestEnvironment


app = create_app(
    RedTeamPentestEnvironment,
    RedTeamAction,
    RedTeamObservation,
    env_name="redteampentestlab",
    max_concurrent_envs=4,
)


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "redteampentestlab",
        "routes": ["/reset", "/step", "/state", "/health"],
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


def main(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()