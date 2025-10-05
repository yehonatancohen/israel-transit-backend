import os, zipfile, io
import pandas as pd
from typing import Dict
from ..config import GTFS_ZIP

class GTFSStore:
    _frames: Dict[str, pd.DataFrame] = {}
    _loaded_hash: str = ""

    @classmethod
    def reload(cls):
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
            except KeyError:
                return pd.DataFrame()
        cls._frames = {
            "stops": read_csv("stops.txt"),
            "stop_times": read_csv("stop_times.txt"),
            "trips": read_csv("trips.txt"),
            "routes": read_csv("routes.txt"),
            "calendar": read_csv("calendar.txt"),
            "calendar_dates": read_csv("calendar_dates.txt"),
        }
        cls._frames["stops"]["lat"] = cls._frames["stops"]["stop_lat"]
        cls._frames["stops"]["lon"] = cls._frames["stops"]["stop_lon"]
        cls._loaded_hash = str(len(data))

    @classmethod
    def frames(cls) -> Dict[str, pd.DataFrame]:
        if not cls._frames:
            cls.reload()
        return cls._frames

    @classmethod
    def dataframe_counts(cls):
        f = cls.frames()
        return {k: len(v) for k, v in f.items()}
