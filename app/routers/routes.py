from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
from ..schemas import SearchRequest, SearchResponse
from ..services.gtfs_loader import GTFSStore
from ..services.routing import Router
from ..services.ai_advisor import AIAdvisor
from ..services.lateness import LatenessModel
from ..config import ROUTER_MAX_TRANSFERS

router = APIRouter()

@router.post("/search", response_model=SearchResponse, summary="Search route options")
async def search(req: SearchRequest):
    if GTFSStore.dataframe_counts().get("stops", 0) == 0:
        raise HTTPException(status_code=400, detail="No GTFS loaded. Upload via /v1/feeds/gtfs/upload.")
    dt = datetime.fromisoformat(req.departure_time) if req.departure_time else datetime.now(timezone.utc)
    lat_model = LatenessModel.load()
    r = Router(lat_model=lat_model)
    options = r.search(
        origin=(req.origin.lat, req.origin.lon),
        destination=(req.destination.lat, req.destination.lon),
        departure_dt=dt,
        max_transfers=req.max_transfers or ROUTER_MAX_TRANSFERS,
    )
    # Optional AI rerank
    ai = AIAdvisor()
    options = ai.rerank(options, user_notes=req.notes)
    return SearchResponse(options=options)
