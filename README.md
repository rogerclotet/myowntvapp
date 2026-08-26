# MyOwnTVApp

A self-hosted web app for watching live sports and TV streams. Built with FastAPI, it scrapes live event listings, proxies HLS streams, and supports AirPlay casting to Apple TV.

**This is an experimental/personal project.** It was built for learning and personal use. No guarantees of reliability, legality in your jurisdiction, or continued maintenance.

## Features

- Live sports: NBA, MLB, NHL, NFL, NCAAF, NCAAB, Soccer, PPV
- Live TV channels
- HLS stream proxying with playlist rewriting
- Team logos fetched from TheSportsDB
- AirPlay casting to Apple TV (via pyatv)
- Mobile-responsive UI with native iOS AirPlay support
- ffmpeg-based stream remuxing for Apple TV compatibility
- Status log showing real-time progress during stream loading

## Screenshots

The app displays a dark, card-based UI with team logos and game times. On mobile, categories scroll horizontally and the video player fills the screen with native AirPlay controls.

---

## Quick Start (Docker)

### Option 1: Docker Compose (Recommended)

1. Clone the repo:
   ```bash
   git clone https://github.com/Tom-Enns/myowntvapp.git
   cd myowntvapp
   ```

2. Start the app:
   ```bash
   docker compose up -d
   ```

3. Open `http://<your-server-ip>:1919` in your browser.

### Option 2: Docker Run

```bash
docker run -d \
  --name myowntvapp \
  --network host \
  -v ./data:/app/data \
  ghcr.io/tom-enns/myowntvapp:latest
```

> **Note:** `--network host` is required for Apple TV discovery (mDNS) and so the Apple TV can reach the proxy server. If you don't need AirPlay casting, you can use `-p 1919:1919` instead.

### Option 3: Pull from GitHub Container Registry

```bash
docker pull ghcr.io/tom-enns/myowntvapp:latest
```

### Supported Architectures

Published images are multi-arch manifests; `docker pull` picks the right one automatically.

| Architecture | Platform | Typical hosts |
|---|---|---|
| `linux/amd64` | x86-64 | Unraid, most NAS boxes, generic servers |
| `linux/arm64` | ARM 64-bit (aarch64) | Apple Silicon Macs, Raspberry Pi 4/5 (64-bit OS), ARM cloud VMs |

32-bit ARM (`armv7`/`armhf`) is not built — several dependencies have no 32-bit wheels.

---

## Unraid Installation

### Using Community Applications (Docker)

1. Go to the **Docker** tab in Unraid
2. Click **Add Container**
3. Fill in the following:

| Field | Value |
|-------|-------|
| **Name** | `myowntvapp` |
| **Repository** | `ghcr.io/tom-enns/myowntvapp:latest` |
| **Network Type** | `host` |
| **WebUI** | `http://[IP]:[PORT:1919]` |

4. Add a **Path** mapping:

| Container Path | Host Path | Description |
|---------------|-----------|-------------|
| `/app/data` | `/mnt/user/appdata/myowntvapp` | App data (credentials) |

5. Click **Apply**
6. Access the app at `http://<unraid-ip>:1919`

### Using Docker Compose on Unraid

If you have the **Compose Manager** plugin installed:

1. Create a new stack called `myowntvapp`
2. Paste this compose file:

```yaml
services:
  myowntvapp:
    image: ghcr.io/tom-enns/myowntvapp:latest
    container_name: myowntvapp
    network_mode: host
    volumes:
      - /mnt/user/appdata/myowntvapp:/app/data
    restart: unless-stopped
```

3. Click **Compose Up**

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `1919` | Server port |
| `PUBLIC_HOST` | auto-detect | Public host:port for stream URLs (e.g. `192.168.1.50:1919`) |
| `CREDENTIAL_FILE` | `data/credentials.json` | Path to AirPlay credentials file |
| `EXTRACT_TIMEOUT_S` | `45` | Stream extraction timeout in seconds |
| `FFMPEG_BIN` | auto-detect | Path to ffmpeg binary |

---

## Development

### Local Setup

Dependencies are managed with [uv](https://docs.astral.sh/uv/). Install it once
(`brew install uv`, or `curl -LsSf https://astral.sh/uv/install.sh | sh`), then:

```bash
uv sync                 # creates .venv from uv.lock, exact pinned versions
uv run uvicorn app.main:app --host 0.0.0.0 --port 1919
```

`uv sync` provisions Python 3.12 itself if you don't have it, so there's no
`python3 -m venv` / `pip install` step. Requires `ffmpeg` installed locally
(`brew install ffmpeg` on macOS).

### Managing Dependencies

```bash
uv add <package>            # add a runtime dependency (updates uv.lock)
uv add --dev <package>      # add a dev/test-only dependency
uv remove <package>
uv lock --upgrade           # re-resolve everything to the newest allowed versions
uv sync --all-groups        # install runtime + dev dependencies
```

`uv.lock` is committed and is the source of truth. Both the Docker build and CI
install with `--frozen`, so they fail loudly if the lockfile drifts from
`pyproject.toml` rather than silently resolving something different.

### Tests

```bash
uv run pytest
```

The suite is offline and hermetic — no live server, no network, no Apple TV
required. It covers HLS playlist rewriting, event/date parsing, host resolution,
and the HTTP routes (with the scraper and extractor stubbed out).

### Build Docker Image Locally

```bash
docker build -t myowntvapp .
docker run --network host -v ./data:/app/data myowntvapp
```

Build for a specific architecture, or both at once:

```bash
# Single architecture (loadable into the local Docker daemon)
docker build --platform linux/arm64 -t myowntvapp:arm64 .

# Both architectures in one manifest — requires a registry to push to,
# plus QEMU (`docker run --privileged --rm tonistiigi/binfmt --install all`)
# when building for an architecture other than your own.
docker buildx build --platform linux/amd64,linux/arm64 \
  -t ghcr.io/<you>/myowntvapp:dev --push .
```

> **Note:** `pyatv` depends on `miniaudio`, which ships no prebuilt aarch64 wheel. The Dockerfile
> compiles it from source in a separate builder stage (via `uv sync --frozen --no-dev`), so the
> final ARM64 image carries neither a compiler nor uv itself. Expect the first ARM64 build to
> take a couple of minutes longer than AMD64.

---

## Tech Stack

- **Backend:** Python, FastAPI, aiohttp, BeautifulSoup
- **Frontend:** Vanilla JS, HLS.js (Chrome/Firefox), native HLS (Safari/iOS)
- **Streaming:** ffmpeg for HLS remuxing, m3u8 playlist rewriting
- **Casting:** pyatv for AirPlay protocol
- **Container:** Python 3.12 slim + ffmpeg, multi-arch (`linux/amd64`, `linux/arm64`)
- **Dependencies:** uv (`pyproject.toml` + committed `uv.lock`)

---

## Disclaimer

This project is for educational and personal use only. It does not host or distribute any content. Users are responsible for ensuring their use complies with applicable laws and terms of service. The authors assume no liability for misuse.
