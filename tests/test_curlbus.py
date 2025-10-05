import pandas as pd

from app.services.gtfs_loader import GTFSStore
from app.services import gtfs_loader


def test_gtfs_reload_prefers_curlbus(monkeypatch, tmp_path):
    monkeypatch.setattr(gtfs_loader, "GTFS_ZIP", tmp_path / "missing.zip")
    monkeypatch.setattr(gtfs_loader, "CURLBUS_API_BASE", "https://curlbus.test/api")
    monkeypatch.setattr(gtfs_loader, "CURLBUS_TIMEOUT", 1.0)

    frames = {
        "stops": pd.DataFrame([{"stop_id": "A", "stop_lat": 32.1, "stop_lon": 34.8}]),
        "stop_times": pd.DataFrame(),
        "trips": pd.DataFrame(),
        "routes": pd.DataFrame(),
        "calendar": pd.DataFrame(),
        "calendar_dates": pd.DataFrame(),
    }

    class DummyClient:
        def __init__(self, base_url, timeout):
            self.base_url = base_url
            self.timeout = timeout

        def fetch_gtfs_frames(self):
            return frames

    monkeypatch.setattr(gtfs_loader, "CurlbusClient", lambda base_url, timeout: DummyClient(base_url, timeout))

    GTFSStore._frames = {}
    GTFSStore._loaded_hash = ""
    GTFSStore.reload()

    data = GTFSStore.frames()
    assert "stops" in data and not data["stops"].empty
    assert list(data["stops"]["lat"]) == [32.1]
    assert list(data["stops"]["lon"]) == [34.8]
    assert GTFSStore._loaded_hash.startswith("curlbus:")
