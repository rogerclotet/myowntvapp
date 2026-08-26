import pytest

from app.config import Settings


def test_public_host_override_wins_over_detection() -> None:
    settings = Settings()
    settings.PUBLIC_HOST = "192.168.1.50:1919"

    assert settings.get_public_host(9999) == "192.168.1.50:1919"


def test_public_host_falls_back_to_detected_ip_and_request_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings()
    settings.PUBLIC_HOST = ""
    monkeypatch.setattr(Settings, "_detect_lan_ip", lambda self, port: f"172.16.0.9:{port}")

    assert settings.get_public_host(8080) == "172.16.0.9:8080"


def test_public_host_uses_configured_port_when_request_port_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings()
    settings.PUBLIC_HOST = ""
    settings.PORT = 1919
    monkeypatch.setattr(Settings, "_detect_lan_ip", lambda self, port: f"172.16.0.9:{port}")

    assert settings.get_public_host(None) == "172.16.0.9:1919"


def test_detect_lan_ip_falls_back_to_loopback_when_socket_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _explode(*args: object, **kwargs: object) -> None:
        raise OSError("network unreachable")

    monkeypatch.setattr("socket.socket", _explode)

    assert Settings()._detect_lan_ip(1919) == "127.0.0.1:1919"
