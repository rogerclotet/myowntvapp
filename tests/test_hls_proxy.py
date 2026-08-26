import json
from urllib.parse import parse_qs, urlparse

from app.services.hls_proxy import HLSProxyService

PROXY_BASE = "http://10.0.0.5:1919/proxy"
ORIGIN = "https://cdn.example.com/live/abc/index.m3u8"

MEDIA_PLAYLIST = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:6
#EXTINF:6.0,
segment0.ts
#EXTINF:6.0,
https://other-cdn.example.net/segment1.ts
"""

MASTER_PLAYLIST = """#EXTM3U
#EXT-X-STREAM-INF:BANDWIDTH=1200000,RESOLUTION=1280x720
720p/index.m3u8
"""

ENCRYPTED_PLAYLIST = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:6
#EXT-X-KEY:METHOD=AES-128,URI="key.bin"
#EXTINF:6.0,
segment0.ts
"""


def _proxied_targets(playlist: str) -> list[str]:
    """Pull the ?url= value out of every proxied line in a rewritten playlist."""
    targets = []
    for line in playlist.splitlines():
        for candidate in (line, *_quoted_uris(line)):
            if candidate.startswith(PROXY_BASE):
                targets.append(parse_qs(urlparse(candidate).query)["url"][0])
    return targets


def _quoted_uris(line: str) -> list[str]:
    if 'URI="' not in line:
        return []
    return [part.split('"', 1)[0] for part in line.split('URI="')[1:]]


def test_relative_segment_is_resolved_against_the_playlist_url() -> None:
    rewritten = HLSProxyService(PROXY_BASE).rewrite_playlist(MEDIA_PLAYLIST, ORIGIN, {})

    assert "https://cdn.example.com/live/abc/segment0.ts" in _proxied_targets(rewritten)


def test_absolute_segment_url_is_preserved_verbatim() -> None:
    rewritten = HLSProxyService(PROXY_BASE).rewrite_playlist(MEDIA_PLAYLIST, ORIGIN, {})

    assert "https://other-cdn.example.net/segment1.ts" in _proxied_targets(rewritten)


def test_every_segment_is_routed_through_the_proxy() -> None:
    rewritten = HLSProxyService(PROXY_BASE).rewrite_playlist(MEDIA_PLAYLIST, ORIGIN, {})

    assert len(_proxied_targets(rewritten)) == 2
    # No bare URI line survives; every non-tag line points at the proxy.
    uri_lines = [ln for ln in rewritten.splitlines() if ln and not ln.startswith("#")]
    assert all(ln.startswith(PROXY_BASE) for ln in uri_lines)


def test_variant_playlists_in_a_master_are_rewritten() -> None:
    rewritten = HLSProxyService(PROXY_BASE).rewrite_playlist(MASTER_PLAYLIST, ORIGIN, {})

    assert _proxied_targets(rewritten) == ["https://cdn.example.com/live/abc/720p/index.m3u8"]


def test_encryption_key_uri_is_rewritten() -> None:
    rewritten = HLSProxyService(PROXY_BASE).rewrite_playlist(ENCRYPTED_PLAYLIST, ORIGIN, {})

    assert "https://cdn.example.com/live/abc/key.bin" in _proxied_targets(rewritten)


def test_upstream_headers_travel_with_the_proxied_url() -> None:
    headers = {"Referer": "https://example.com/", "User-Agent": "test-agent"}

    rewritten = HLSProxyService(PROXY_BASE).rewrite_playlist(MEDIA_PLAYLIST, ORIGIN, headers)

    first_line = next(line for line in rewritten.splitlines() if line.startswith(PROXY_BASE))
    assert json.loads(parse_qs(urlparse(first_line).query)["h"][0]) == headers


def test_no_header_param_is_emitted_when_there_are_no_headers() -> None:
    rewritten = HLSProxyService(PROXY_BASE).rewrite_playlist(MEDIA_PLAYLIST, ORIGIN, {})

    first_line = next(line for line in rewritten.splitlines() if line.startswith(PROXY_BASE))
    assert "h" not in parse_qs(urlparse(first_line).query)


def test_playlist_tags_survive_the_rewrite() -> None:
    rewritten = HLSProxyService(PROXY_BASE).rewrite_playlist(MEDIA_PLAYLIST, ORIGIN, {})

    assert rewritten.startswith("#EXTM3U")
    assert "#EXT-X-TARGETDURATION:6" in rewritten
