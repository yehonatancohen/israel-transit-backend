import math
from typing import List, Tuple

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2*R*math.atan2(math.sqrt(a), math.sqrt(1-a))

def nearest_stops(stops, lat, lon, k=5):
    # stops: DataFrame with columns stop_id, lat, lon
    dists = []
    for idx, row in stops.iterrows():
        d = haversine(lat, lon, row["lat"], row["lon"])
        dists.append((row["stop_id"], d))
    dists.sort(key=lambda x: x[1])
    return dists[:k]
