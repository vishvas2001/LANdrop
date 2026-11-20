import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
from typing import Any
import uuid
import zipfile

from fastapi import FastAPI, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from landrop.database import delete_expired_files, get_file, init_db, insert_file, list_files
from landrop.network import print_qr_banner
from landrop.ws_manager import ConnectionManager

UPLOAD_DIR = Path("uploads")
CHUNK_SIZE = 65536  # 64 KB per chunk
TTL_MINUTES = 15
REAPER_INTERVAL_SECONDS = 30

manager = ConnectionManager()

# Tracks active download count per file_id so the TTL reaper never deletes mid-transfer
active_downloads: dict[str, int] = {}


def release_download(file_id: str) -> None:
    """Decrement active download count once FileResponse finishes streaming."""
    current = active_downloads.get(file_id, 0)
    if current <= 1:
        active_downloads.pop(file_id, None)
    else:
        active_downloads[file_id] = current - 1


async def ttl_reaper_loop() -> None:
    """Background worker that deletes expired files unless actively downloading."""
    try:
        while True:
            await asyncio.sleep(REAPER_INTERVAL_SECONDS)
            now_iso = datetime.now(timezone.utc).isoformat()
            expired_files = delete_expired_files(now_iso)

            for record in expired_files:
                file_id = record["file_id"]
                if active_downloads.get(file_id, 0) > 0:
                    insert_file(record)
                    continue

                Path(record["stored_path"]).unlink(missing_ok=True)
                print(f"[TTL Reaper] Deleted expired file: {record['original_name']}")
    except asyncio.CancelledError:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize storage, start the TTL cleaner, and print the QR banner."""
    UPLOAD_DIR.mkdir(exist_ok=True)
    init_db()
    reaper_task = asyncio.create_task(ttl_reaper_loop())
    print_qr_banner()
    yield
    reaper_task.cancel()
    await reaper_task


app = FastAPI(title="LANDrop", lifespan=lifespan)


@app.get("/")
async def serve_ui():
    """Serve the single-page frontend."""
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/health")
async def health():
    return {"status": "Active", "message": "LANDrop is running."}


@app.post("/upload", status_code=201)
async def upload_file(file: UploadFile) -> dict[str, Any]:
    """Stream an incoming file to disk in 64 KB chunks and save its metadata."""
    file_id = uuid.uuid4().hex
    stored_path = UPLOAD_DIR / file_id
    size_bytes = 0

    with open(stored_path, "wb") as buffer:
        while chunk := await file.read(CHUNK_SIZE):
            buffer.write(chunk)
            size_bytes += len(chunk)

    now = datetime.now(timezone.utc)
    file_record: dict[str, Any] = {
        "file_id": file_id,
        "original_name": file.filename or "unnamed_file",
        "stored_path": str(stored_path),
        "size_bytes": size_bytes,
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=TTL_MINUTES)).isoformat(),
    }

    insert_file(file_record)
    return file_record


@app.get("/files")
async def get_all_files() -> list[dict[str, Any]]:
    """Return metadata for all currently stored files."""
    return list_files()


@app.get("/files/{file_id}")
async def download_file(file_id: str):
    """Stream a stored file with an active-download lock protecting it from TTL deletion."""
    record = get_file(file_id)
    if record is None or not Path(record["stored_path"]).exists():
        raise HTTPException(status_code=404, detail="File not found")

    active_downloads[file_id] = active_downloads.get(file_id, 0) + 1

    return FileResponse(
        path=record["stored_path"],
        filename=record["original_name"],
        background=BackgroundTask(release_download, file_id),
    )


@app.get("/download-all")
async def download_all_files():
    """Bundle all currently stored files into a temporary ZIP archive and stream it."""
    files = list_files()
    if not files:
        raise HTTPException(status_code=404, detail="No files available to zip")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp_path = Path(tmp.name)
    tmp.close()

    used_names: dict[str, int] = {}

    with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_STORED) as zf:
        for record in files:
            disk_path = Path(record["stored_path"])
            if not disk_path.exists():
                continue

            orig = record["original_name"]
            if orig in used_names:
                used_names[orig] += 1
                arcname = f"{Path(orig).stem} ({used_names[orig]}){Path(orig).suffix}"
            else:
                used_names[orig] = 0
                arcname = orig

            zf.write(disk_path, arcname=arcname)

    return FileResponse(
        path=tmp_path,
        filename="landrop_bundle.zip",
        media_type="application/zip",
        background=BackgroundTask(tmp_path.unlink, missing_ok=True),
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Sync real-time clipboard updates across all connected devices."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)