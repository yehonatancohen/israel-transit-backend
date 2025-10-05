import io, os, json, zipfile
from fastapi import APIRouter, UploadFile, File, HTTPException
from ..config import GTFS_ZIP, LATENESS_STORE, GTFS_DIR
from ..services.gtfs_loader import GTFSStore

router = APIRouter()

@router.post("/gtfs/upload", summary="Upload a GTFS ZIP")
async def upload_gtfs(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Expected a .zip file")
    data = await file.read()
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
