import io, os, json, zipfile
from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from ..config import GTFS_ZIP, LATENESS_STORE, GTFS_DIR
from ..services.gtfs_loader import GTFSStore
from multipart.multipart import parse_options_header

router = APIRouter()

@router.post("/gtfs/upload", summary="Upload a GTFS ZIP")
async def upload_gtfs(request: Request, file: UploadFile | None = File(None)):
    filename = file.filename if file else ""
    data: bytes | None = None
    if file is not None:
        data = await file.read()
    else:
        data = await _read_multipart_bytes(request)
        filename = filename or "uploaded.zip"
    if not filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Expected a .zip file")
    if data is None:
        raise HTTPException(status_code=400, detail="Missing GTFS payload")
    try:
        zipfile.ZipFile(io.BytesIO(data)).testzip()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ZIP")
    os.makedirs(GTFS_DIR, exist_ok=True)
    with open(GTFS_ZIP, "wb") as f:
        f.write(data)
    # Warm indexes
    GTFSStore.reload()
    return {"stored": True}


async def _read_multipart_bytes(request: Request) -> bytes:
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" not in content_type.lower():
        raise HTTPException(status_code=400, detail="Expected multipart/form-data upload")
    _, params = parse_options_header(content_type)
    boundary = params.get(b"boundary") if isinstance(params, dict) else None
    if not boundary:
        raise HTTPException(status_code=400, detail="Missing multipart boundary")
    body = await request.body()
    boundary_bytes = b"--" + boundary
    segments = body.split(boundary_bytes)
    for segment in segments:
        if not segment:
            continue
        segment = segment.lstrip(b"\r\n")
        if segment.startswith(b"--"):
            continue
        segment = segment.rstrip(b"\r\n")
        if segment.endswith(b"--"):
            segment = segment[:-2]
        header_bytes, sep, content = segment.partition(b"\r\n\r\n")
        if not sep:
            continue
        headers_text = header_bytes.decode("latin-1", errors="ignore")
        if "filename=" not in headers_text:
            continue
        return content
    raise HTTPException(status_code=400, detail="GTFS file missing in multipart body")

@router.post("/realtime/ingest", summary="Ingest normalized realtime events")
async def ingest_realtime(payload: dict):
    # Expect payload with items like:
    # {"events": [{"trip_id": "...", "stop_id": "...", "delay_secs": 120, "ts": "..."}, ...]}
    events = payload.get("events", [])
    if not isinstance(events, list):
        return {"accepted": 0}
    # Append to lateness store (very simple aggregation by (route_id or trip_id, stop_id, hour_of_week))
    from ..services.lateness import LatenessModel
    model = LatenessModel.load()
    for ev in events:
        model.observe(ev)
    model.save()
    return {"accepted": len(events)}
