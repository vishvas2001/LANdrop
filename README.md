# LANDrop

A zero-cloud, local Wi-Fi file transfer and real-time shared clipboard engine built with Python and FastAPI. Share multi-gigabyte videos, photos, text snippets, and screenshots across devices on the same local network—without internet usage, account sign-ups, or file size limits.

---

## Key Features

* **Memory-Safe Chunked Streaming:** Streams uploads and downloads in 64 KB chunks (`UploadFile` + `FileResponse`), keeping RAM usage flat under 5 MB even during 5–10 GB transfers.
* **35+ MB/s Local Throughput:** Transfers travel strictly over local Wi-Fi/hotspot links (achieving ~35 MB/s over 5 GHz Wi-Fi).
* **Real-Time Shared Clipboard (`WS /ws`):** Persistent WebSocket connection manager broadcasts text, links, and `Ctrl+V` pasted screenshots across all connected devices in milliseconds.
* **Multi-File Queue & Live Speed Metrics:** Sequential `XMLHttpRequest` upload queue with per-file percentage bars, real-time `MB/s` speed readouts, drag-and-drop support, and instant UI updates.
* **Self-Cleaning TTL Reaper & Download Locks:** An asynchronous background worker (`asyncio.create_task`) automatically purges expired files after 15 minutes using SQLite metadata tracking, while active-download reference locks prevent files from being deleted mid-transfer.
* **ZIP-on-the-Fly (`GET /download-all`):** Bundles all active room files into a single `landrop_bundle.zip` using `ZIP_STORED` (zero CPU overhead on already-compressed media) with automated temp-file cleanup.
* **Zero-Config QR Discovery:** Detects the active local network IPv4 interface via an offline UDP socket lookup and renders an ASCII QR code directly in the terminal on startup.

---

## Architecture & Project Structure

```text
landrop/
├── src/
│   └── landrop/
│       ├── main.py          # FastAPI routes, chunked streaming, TTL reaper & active download locks
│       ├── database.py      # SQLite persistence layer & expired metadata queries
│       ├── ws_manager.py    # WebSocket connection manager & clipboard state sync
│       ├── network.py       # Offline LAN IP detection & terminal ASCII QR generator
│       └── static/
│           └── index.html   # Single-page dark-mode UI (WebSockets, XHR progress, live countdowns)
├── Dockerfile               # Slim Python 3.12 container image built with uv
├── pyproject.toml           # Project metadata and dependencies
└── uv.lock                  # Deterministic dependency lockfile
```

---

## Quick Start (Local with `uv`)

### Prerequisites
* Python 3.12+
* [`uv`](https://docs.astral.sh/uv/) package manager

### Run Locally
```bash
git clone [https://github.com/vishvas2001/LANDrop.git](https://github.com/vishvas2001/LANDrop.git)
cd LANDrop

# Install dependencies and start the server on all network interfaces
uv sync
uv run fastapi run src/landrop/main.py --host 0.0.0.0 --port 8000
```

Scan the ASCII QR code printed in your terminal using your phone's camera (ensure both devices are on the same Wi-Fi or 5 GHz mobile hotspot).

---

## Running with Docker

### 1. Build the Image
```bash
docker build -t landrop:latest .
```

### 2. Run the Container

**On Windows / macOS** (pass your host machine's LAN IP via `HOST_IP` so the terminal QR code points to your Wi-Fi interface instead of Docker's internal bridge IP):
```powershell
docker run --rm -it -p 8000:8000 -e HOST_IP=<YOUR_LAN_IP> -v landrop_uploads:/app/uploads landrop:latest
```

**On Linux** (uses `--network host` for automatic LAN IP detection):
```bash
docker run --rm -it --network host -v landrop_uploads:/app/uploads landrop:latest
```

---

## API Reference

| Method & Endpoint | Description |
| :--- | :--- |
| `GET /` | Serves the single-page web interface (`index.html`). |
| `GET /health` | Health check returning server status. |
| `POST /upload` | Streams an uploaded file to disk in 64 KB chunks and records metadata in SQLite. |
| `GET /files` | Lists all active files with size and UTC expiration timestamps. |
| `GET /files/{file_id}` | Streams a file back to the client while holding an active-download lock. |
| `GET /download-all` | Packages all active files into `landrop_bundle.zip` and cleans up the archive post-transfer. |
| `WS /ws` | Bidirectional WebSocket channel for real-time shared clipboard sync. |