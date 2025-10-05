from fastapi.testclient import TestClient
from app.main import app
import io, zipfile, pandas as pd

def make_min_gtfs_zip():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        # stops.txt
        import pandas as pd
        stops = pd.DataFrame([
            {"stop_id":"A","stop_name":"A","stop_lat":32.08,"stop_lon":34.78},
            {"stop_id":"B","stop_name":"B","stop_lat":32.085,"stop_lon":34.79},
            {"stop_id":"C","stop_name":"C","stop_lat":32.09,"stop_lon":34.80},
        ])
        z.writestr("stops.txt", stops.to_csv(index=False))
        trips = pd.DataFrame([
            {"route_id":"R1","service_id":"WEEK","trip_id":"T1"},
            {"route_id":"R1","service_id":"WEEK","trip_id":"T2"},
        ])
        z.writestr("trips.txt", trips.to_csv(index=False))
        routes = pd.DataFrame([
            {"route_id":"R1","agency_id":"1","route_short_name":"1","route_long_name":"Line 1","route_type":3}
        ])
        z.writestr("routes.txt", routes.to_csv(index=False))
        stop_times = pd.DataFrame([
            {"trip_id":"T1","arrival_time":"08:10:00","departure_time":"08:10:00","stop_id":"A","stop_sequence":1},
            {"trip_id":"T1","arrival_time":"08:25:00","departure_time":"08:25:00","stop_id":"B","stop_sequence":2},
            {"trip_id":"T1","arrival_time":"08:40:00","departure_time":"08:40:00","stop_id":"C","stop_sequence":3},
            {"trip_id":"T2","arrival_time":"08:15:00","departure_time":"08:15:00","stop_id":"A","stop_sequence":1},
            {"trip_id":"T2","arrival_time":"08:30:00","departure_time":"08:30:00","stop_id":"B","stop_sequence":2},
            {"trip_id":"T2","arrival_time":"08:45:00","departure_time":"08:45:00","stop_id":"C","stop_sequence":3},
        ])
        z.writestr("stop_times.txt", stop_times.to_csv(index=False))
        cal = pd.DataFrame([{"service_id":"WEEK","monday":1,"tuesday":1,"wednesday":1,"thursday":1,"friday":1,"saturday":0,"sunday":1,"start_date":20240101,"end_date":20251231}])
        z.writestr("calendar.txt", cal.to_csv(index=False))
        cald = pd.DataFrame([])
        z.writestr("calendar_dates.txt", cald.to_csv(index=False))
    buf.seek(0)
    return buf.getvalue()

def test_search_minimal():
    c = TestClient(app)
    # Upload GTFS
    z = make_min_gtfs_zip()
    r = c.post('/v1/feeds/gtfs/upload', files={'file': ('gtfs.zip', z, 'application/zip')})
    assert r.status_code == 200
    # Query route
    body = {
        "origin": {"lat": 32.081, "lon": 34.781},
        "destination": {"lat": 32.089, "lon": 34.799},
        "departure_time": "2025-10-05T08:05:00+00:00"
    }
    r = c.post('/v1/routes/search', json=body)
    assert r.status_code == 200
    data = r.json()
    assert "options" in data
    assert len(data["options"]) >= 1
