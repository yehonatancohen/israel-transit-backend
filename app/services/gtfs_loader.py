import os, zipfile, io, hashlib, logging
import pandas as pd
from typing import Dict
from ..config import GTFS_ZIP, CURLBUS_API_BASE, CURLBUS_TIMEOUT
from .curlbus import CurlbusClient

logger = logging.getLogger(__name__)

class GTFSStore:
    _frames: Dict[str, pd.DataFrame] = {}
    _loaded_hash: str = ""

    @classmethod
    def reload(cls):
        # Prefer Curlbus API when configured.  Fall back to local ZIP uploads
        # if the API is unreachable.
        if CURLBUS_API_BASE:
            try:
                client = CurlbusClient(CURLBUS_API_BASE, timeout=CURLBUS_TIMEOUT)
                frames = client.fetch_gtfs_frames()
                cls._set_frames(frames, source="curlbus")
                return
            except Exception as exc:
                logger.info("Curlbus fetch failed, falling back to local GTFS: %s", exc)

        if not os.path.exists(GTFS_ZIP):
            cls._frames = {}
            cls._loaded_hash = ""
            return
        with open(GTFS_ZIP, "rb") as f:
            data = f.read()
        z = zipfile.ZipFile(io.BytesIO(data))
        def read_csv(name):
            try:
                with z.open(name) as fh:
                    return pd.read_csv(fh)
            except (KeyError, pd.errors.EmptyDataError):
                return pd.DataFrame()
        frames = {
            "stops": read_csv("stops.txt"),
            "stop_times": read_csv("stop_times.txt"),
            "trips": read_csv("trips.txt"),
            "routes": read_csv("routes.txt"),
            "calendar": read_csv("calendar.txt"),
            "calendar_dates": read_csv("calendar_dates.txt"),
        }
        cls._set_frames(frames, source=str(len(data)))

    @classmethod
    def frames(cls) -> Dict[str, pd.DataFrame]:
        if not cls._frames:
            cls.reload()
        return cls._frames

    @classmethod
    def dataframe_counts(cls):
        f = cls.frames()
        return {k: len(v) for k, v in f.items()}

    @classmethod
    def _set_frames(cls, frames: Dict[str, pd.DataFrame], source: str = ""):
        processed: Dict[str, pd.DataFrame] = {}
        for name in ("stops", "stop_times", "trips", "routes", "calendar", "calendar_dates"):
            df = frames.get(name)
            processed[name] = df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()

        stops = processed["stops"]
        if not stops.empty:
            if "lat" not in stops.columns:
                if "stop_lat" in stops.columns:
                    stops["lat"] = stops["stop_lat"]
                elif "latitude" in stops.columns:
                    stops["lat"] = stops["latitude"]
            if "lon" not in stops.columns:
                if "stop_lon" in stops.columns:
                    stops["lon"] = stops["stop_lon"]
                elif "longitude" in stops.columns:
                    stops["lon"] = stops["longitude"]

        cls._frames = processed
        digest_input = "|".join(f"{k}:{len(v)}" for k, v in processed.items()).encode("utf-8")
        cls._loaded_hash = f"{source}:{hashlib.md5(digest_input).hexdigest()}"
