from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class Coordinate(BaseModel):
    lat: float
    lon: float

class SearchRequest(BaseModel):
    origin: Coordinate = Field(..., description="Origin lat/lon")
    destination: Coordinate = Field(..., description="Destination lat/lon")
    departure_time: Optional[str] = Field(None, description="ISO8601, defaults to now if missing")
    max_transfers: Optional[int] = Field(None, description="Override global max transfers")
    notes: Optional[str] = Field(None, description="Optional free text for AI reranker")

class Leg(BaseModel):
    mode: Literal["WALK", "BUS", "TRAIN"]
    route_id: Optional[str] = None
    trip_id: Optional[str] = None
    from_stop_id: Optional[str] = None
    to_stop_id: Optional[str] = None
    depart_time: str
    arrive_time: str
    predicted_delay_secs: int = 0
    description: Optional[str] = None

class RouteOption(BaseModel):
    id: str
    summary: str
    total_duration_secs: int
    transfer_count: int
    min_transfer_slack_secs: int
    risk_score: float = 0.0
    legs: List[Leg]
    ai_reason: Optional[str] = None

class SearchResponse(BaseModel):
    options: List[RouteOption]

class SessionStartRequest(BaseModel):
    selected_route_id: str
    user_context: Optional[str] = None

class SessionUpdateRequest(BaseModel):
    session_id: str
    current_location: Coordinate
    timestamp: Optional[str] = None

class SessionUpdateResponse(BaseModel):
    session_id: str
    advice: str
    maybe_better_options: List[RouteOption] = []
