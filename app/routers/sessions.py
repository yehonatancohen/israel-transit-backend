from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
from ..schemas import SessionStartRequest, SessionUpdateRequest, SessionUpdateResponse, SearchResponse
from ..services.sessions import SessionManager
from ..services.routing import Router
from ..services.gtfs_loader import GTFSStore
from ..services.lateness import LatenessModel

router = APIRouter()
_sessions = SessionManager()

@router.post("/start", summary="Start a trip session")
async def start(req: SessionStartRequest):
    sid = _sessions.start(req.selected_route_id, req.user_context or "")
    return {"session_id": sid}

@router.post("/progress", response_model=SessionUpdateResponse, summary="Update session progress and maybe re-route")
async def progress(req: SessionUpdateRequest):
    if not _sessions.exists(req.session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    # For MVP, use current position to look for opportunistic better options
    lat_model = LatenessModel.load()
    router = Router(lat_model=lat_model)
    # Re-run a short search from here with limited depth
    if GTFSStore.dataframe_counts().get("stops", 0) == 0:
        raise HTTPException(status_code=400, detail="No GTFS loaded")
    # The session stores the original destination
    sess = _sessions.get(req.session_id)
    dest = sess["destination"]
    dt = datetime.fromisoformat(req.timestamp) if req.timestamp else datetime.now(timezone.utc)
    options = router.search(
        origin=(req.current_location.lat, req.current_location.lon),
        destination=(dest[0], dest[1]),
        departure_dt=dt,
        max_transfers=2,
        quick_mode=True,
    )
    _sessions.touch(req.session_id)
    advice = "Continue as planned." if not options else "Consider a route change based on traffic and delays."
    return SessionUpdateResponse(session_id=req.session_id, advice=advice, maybe_better_options=options[:3])
