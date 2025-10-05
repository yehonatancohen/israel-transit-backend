import json, os, math
from datetime import datetime
from typing import Dict, Any
from ..config import LATENESS_STORE, MIN_TRANSFER_SLACK_SECONDS

class LatenessModel:
    def __init__(self, table: Dict[str, Dict[str, float]] | None = None):
        self.table = table or {}

    @staticmethod
    def key(ev: Dict[str, Any]) -> str:
        # Bucket by route_or_trip + stop_id + hour-of-week
        trip = ev.get("trip_id", "unknown")
        stop = ev.get("stop_id", "unknown")
        ts = ev.get("ts") or datetime.utcnow().isoformat()
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            dt = datetime.utcnow()
        how = dt.weekday()*24 + dt.hour
        return f"{trip}|{stop}|{how}"

    def observe(self, ev: Dict[str, Any]):
        k = self.key(ev)
        delay = float(ev.get("delay_secs", 0.0))
        bucket = self.table.get(k) or {"n": 0.0, "mean": 0.0, "m2": 0.0}
        # Welford
        n = bucket["n"] + 1.0
        delta = delay - bucket["mean"]
        mean = bucket["mean"] + delta / n
        m2 = bucket["m2"] + delta * (delay - mean)
        self.table[k] = {"n": n, "mean": mean, "m2": m2}

    def estimate_slack(self, trip_id: str, stop_id: str, hour_of_week: int) -> int:
        k = f"{trip_id}|{stop_id}|{hour_of_week}"
        b = self.table.get(k)
        base = MIN_TRANSFER_SLACK_SECONDS
        if not b or b["n"] < 10:
            return base
        var = b["m2"] / max(b["n"] - 1.0, 1.0)
        std = math.sqrt(max(var, 0.0))
        # Mean + one std, capped
        return int(min(1800, base + b["mean"] + 0.5*std))

    @classmethod
    def load(cls):
        if os.path.exists(LATENESS_STORE):
            with open(LATENESS_STORE, "r") as f:
                return cls(json.load(f))
        return cls({})

    def save(self):
        os.makedirs(os.path.dirname(LATENESS_STORE), exist_ok=True)
        with open(LATENESS_STORE, "w") as f:
            json.dump(self.table, f)
