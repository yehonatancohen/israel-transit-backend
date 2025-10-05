import time, uuid
from typing import Dict, Any, Tuple

class SessionManager:
    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}

    def start(self, selected_route_id: str, user_context: str) -> str:
        sid = str(uuid.uuid4())
        # For MVP we only store destination lat/lon later via progress calls
        self._store[sid] = {"route_id": selected_route_id, "user_context": user_context, "ts": time.time(), "destination": (0.0, 0.0)}
        return sid

    def exists(self, sid: str) -> bool:
        return sid in self._store

    def get(self, sid: str) -> Dict[str, Any]:
        return self._store[sid]

    def set_destination(self, sid: str, dest: Tuple[float,float]):
        if sid in self._store:
            self._store[sid]["destination"] = dest

    def touch(self, sid: str):
        if sid in self._store:
            self._store[sid]["ts"] = time.time()
