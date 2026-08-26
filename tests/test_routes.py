import pytest
from fastapi.testclient import TestClient

from app.services.extractor import StreamInfo
from app.routes.proxy import sessions
from app.services.scraper import StreamEvent


def test_index_renders(client: TestClient) -> None:
    """Regression: a Starlette upgrade broke the TemplateResponse call signature
    and turned every index request into a 500."""
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_watch_page_points_at_the_proxied_playlist(
    client: TestClient, public_host: str
) -> None:
    response = client.get("/watch/session-123")

    assert response.status_code == 200
    assert f"http://{public_host}/proxy/playlist/session-123" in response.text


def test_static_assets_are_served(client: TestClient) -> None:
    assert client.get("/static/app.js").status_code == 200


def test_unknown_playlist_session_is_404(client: TestClient) -> None:
    response = client.get("/proxy/playlist/does-not-exist")

    assert response.status_code == 404


def test_unknown_remux_session_is_404(client: TestClient) -> None:
    response = client.get("/proxy/remux/does-not-exist/stream.m3u8")

    assert response.status_code == 404


def test_remux_404s_for_a_missing_file_in_a_known_session(
    client: TestClient, tmp_path
) -> None:
    client.app.state.transcoder.get_output_dir = lambda session_id: str(tmp_path)

    response = client.get("/proxy/remux/known/absent.m3u8")

    assert response.status_code == 404


def test_remux_serves_hls_playlists_with_the_hls_content_type(
    client: TestClient, tmp_path
) -> None:
    (tmp_path / "stream.m3u8").write_text("#EXTM3U\n")
    client.app.state.transcoder.get_output_dir = lambda session_id: str(tmp_path)

    response = client.get("/proxy/remux/known/stream.m3u8")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.apple.mpegurl"
    assert response.headers["access-control-allow-origin"] == "*"


def test_remux_serves_segments_as_mpeg_ts(client: TestClient, tmp_path) -> None:
    (tmp_path / "stream0.ts").write_bytes(b"\x47\x40\x00\x10")
    client.app.state.transcoder.get_output_dir = lambda session_id: str(tmp_path)

    response = client.get("/proxy/remux/known/stream0.ts")

    assert response.status_code == 200
    assert response.headers["content-type"] == "video/mp2t"


def test_cast_rejects_an_unknown_session(client: TestClient) -> None:
    response = client.post(
        "/api/cast", json={"session_id": "nope", "device_id": "device-1"}
    )

    assert response.json() == {"error": "Session not found"}


def test_prepare_remux_rejects_an_unknown_session(client: TestClient) -> None:
    response = client.post("/api/prepare-remux", json={"session_id": "nope"})

    assert response.json() == {"error": "Session not found"}


def test_extract_registers_a_session_and_returns_a_proxy_url(
    client: TestClient, public_host: str
) -> None:
    async def fake_extract(url: str, timeout_s: int = 45) -> StreamInfo:
        return StreamInfo(m3u8_url="https://cdn.example.com/live.m3u8", headers={})

    client.app.state.extractor.extract = fake_extract

    body = client.post("/api/extract", json={"url": "https://example.com/event"}).json()

    assert body["original_m3u8"] == "https://cdn.example.com/live.m3u8"
    assert body["proxy_url"] == f"http://{public_host}/proxy/playlist/{body['session_id']}"
    assert body["session_id"] in sessions


def test_extract_reports_extractor_failures_instead_of_raising(
    client: TestClient,
) -> None:
    async def failing_extract(url: str, timeout_s: int = 45) -> StreamInfo:
        raise RuntimeError("Page returned 403")

    client.app.state.extractor.extract = failing_extract

    body = client.post("/api/extract", json={"url": "https://example.com/event"}).json()

    assert body["error"] == "Stream extraction failed: Page returned 403"
    assert sessions == {}


def test_extract_requires_a_url(client: TestClient) -> None:
    assert client.post("/api/extract", json={}).status_code == 422


def test_sports_category_returns_serialised_events(client: TestClient) -> None:
    async def fake_scrape(category: str) -> list[StreamEvent]:
        return [
            StreamEvent(
                id="e1",
                title="Boston Bruins @ New York Rangers",
                home_team="New York Rangers",
                away_team="Boston Bruins",
                url="https://thetvapp.to/event/e1/x",
                category=category,
            )
        ]

    client.app.state.scraper.scrape_category = fake_scrape

    body = client.get("/api/sports/nhl").json()

    assert [event["id"] for event in body["events"]] == ["e1"]
    assert body["events"][0]["category"] == "nhl"


def test_sports_category_reports_scraper_failures(client: TestClient) -> None:
    async def failing_scrape(category: str) -> list[StreamEvent]:
        raise RuntimeError("upstream down")

    client.app.state.scraper.scrape_category = failing_scrape

    body = client.get("/api/sports/nhl").json()

    assert body["error"] == "Failed to fetch category nhl: upstream down"
