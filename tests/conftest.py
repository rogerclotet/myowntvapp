import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.routes.proxy import sessions


@pytest.fixture
def public_host(monkeypatch: pytest.MonkeyPatch) -> str:
    """Pin the advertised host so URL assertions don't depend on the LAN."""
    host = "10.0.0.5:1919"
    monkeypatch.setattr(settings, "PUBLIC_HOST", host)
    return host


@pytest.fixture
def client(public_host: str):
    """App client with lifespan run, so app.state services exist.

    Every service constructed by the lifespan is inert until called, so this
    starts no browsers, subprocesses, or network connections.
    """
    sessions.clear()
    with TestClient(app) as test_client:
        yield test_client
    sessions.clear()
