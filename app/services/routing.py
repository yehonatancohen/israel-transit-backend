from __future__ import annotations
import pandas as pd
from datetime import datetime, timezone
from typing import Tuple, List
import uuid

from .gtfs_loader import GTFSStore
from .geoutil import nearest_stops
from .lateness import LatenessModel
from ..schemas import RouteOption, Leg

class Router:
    def __init__(self, lat_model: LatenessModel):
        self.lat_model = lat_model
        frames = GTFSStore.frames()
        self.stops = frames["stops"]
        self.stop_times = frames["stop_times"]
        self.trips = frames["trips"]
        self.routes = frames["routes"]

    @staticmethod
    def _sec(hms: str) -> int:
        h, m, s = [int(x) for x in hms.split(":")]
        return h*3600 + m*60 + s

    @staticmethod
    def _hms(sec: int) -> str:
        sec = max(0, sec)
        h = sec//3600; sec%=3600
        m = sec//60; s = sec%60
        return f"{h:02d}:{m:02d}:{s:02d}"

    def search(self, origin: Tuple[float,float], destination: Tuple[float,float], departure_dt: datetime, max_transfers: int=2, quick_mode: bool=False) -> List[RouteOption]:
        # Find candidate origin and destination stops
        if self.stops.empty or self.stop_times.empty or self.trips.empty:
            return []
        o_near = nearest_stops(self.stops, origin[0], origin[1], k=6)
        d_near = nearest_stops(self.stops, destination[0], destination[1], k=6)
        o_ids = [sid for sid,_ in o_near]
        d_ids = [sid for sid,_ in d_near]

        # Build fast lookup
        st = self.stop_times
        trips = self.trips
        st = st.merge(trips[["trip_id","route_id"]], on="trip_id", how="left")

        # Departure time in seconds from midnight local. Assume UTC for MVP.
        dep_sec = (departure_dt.hour*3600 + departure_dt.minute*60 + departure_dt.second)

        # Candidates: direct rides
        options: List[RouteOption] = []
        direct = []
        st_o = st[st["stop_id"].isin(o_ids)]
        for _, row in st_o.iterrows():
            trip_id = row["trip_id"]
            dep_hms = row["departure_time"]
            try:
                dep_s = self._sec(dep_hms)
            except Exception:
                continue
            if dep_s < dep_sec or dep_s > dep_sec + 45*60:
                continue
            # Does this trip reach any dest stop later?
            seq = row["stop_sequence"]
            downstream = st[(st["trip_id"]==trip_id) & (st["stop_sequence"]>seq) & (st["stop_id"].isin(d_ids))]
            if not downstream.empty:
                to = downstream.sort_values("stop_sequence").iloc[0]
                arr_s = self._sec(to["arrival_time"])
                leg = Leg(
                    mode="BUS", route_id=str(row.get("route_id","")), trip_id=str(trip_id),
                    from_stop_id=str(row["stop_id"]), to_stop_id=str(to["stop_id"]),
                    depart_time=dep_hms, arrive_time=to["arrival_time"], predicted_delay_secs=0,
                    description="Direct"
                )
                total = arr_s - dep_s
                opt = RouteOption(
                    id=str(uuid.uuid4()), summary="Direct",
                    total_duration_secs=int(total), transfer_count=0,
                    min_transfer_slack_secs=600, risk_score=0.1, legs=[leg]
                )
                direct.append(opt)

        options.extend(sorted(direct, key=lambda o:o.total_duration_secs)[:5])

        # One transfer
        if max_transfers >= 1:
            one_tx = self._search_with_transfers(st, o_ids, d_ids, dep_sec, max_transfers=1)
            options.extend(one_tx[:8])

        # Two transfers
        if max_transfers >= 2 and not quick_mode:
            two_tx = self._search_with_transfers(st, o_ids, d_ids, dep_sec, max_transfers=2)
            options.extend(two_tx[:8])

        # Score and sort
        options = self._score_and_sort(options, departure_dt)
        # Deduplicate by summary+duration
        seen = set(); uniq = []
        for o in options:
            k = (tuple((lg.mode, lg.route_id, lg.from_stop_id, lg.to_stop_id) for lg in o.legs), o.total_duration_secs)
            if k in seen: 
                continue
            seen.add(k); uniq.append(o)
        return uniq[:12]

    def _search_with_transfers(self, st, o_ids, d_ids, dep_sec, max_transfers):
        res: List[RouteOption] = []
        # First leg candidates
        firsts = st[st["stop_id"].isin(o_ids)].copy()
        firsts["dep_s"] = firsts["departure_time"].apply(lambda t: self._sec(t) if isinstance(t,str) else 10**9)
        firsts = firsts[(firsts["dep_s"] >= dep_sec) & (firsts["dep_s"] <= dep_sec + 45*60)]
        firsts = firsts.sort_values("dep_s").head(500)

        for _, f in firsts.iterrows():
            f_trip = f["trip_id"]; f_seq = f["stop_sequence"]; f_dep_s = f["dep_s"]
            downstream = st[(st["trip_id"]==f_trip) & (st["stop_sequence"]>f_seq)].copy()
            if downstream.empty: 
                continue
            # Transfer points up to next 6 stops
            for _, mid in downstream.head(6).iterrows():
                mid_stop = mid["stop_id"]
                mid_arr_s = self._sec(mid["arrival_time"])
                # Slack dynamic
                how = 0  # unknown local hour-of-week in MVP
                slack = self.lat_model.estimate_slack(trip_id=str(f_trip), stop_id=str(mid_stop), hour_of_week=how)
                # Next legs that depart at or after mid_arr_s + slack
                second = st[(st["stop_id"]==mid_stop)].copy()
                second["dep_s"] = second["departure_time"].apply(lambda t: self._sec(t) if isinstance(t,str) else 10**9)
                cand2 = second[second["dep_s"] >= mid_arr_s + slack]
                if cand2.empty:
                    continue
                # Direct to destination on second leg
                for _, s2 in cand2.head(20).iterrows():
                    s2_trip = s2["trip_id"]; s2_seq = s2["stop_sequence"]; s2_dep_s = s2["dep_s"]
                    down2 = st[(st["trip_id"]==s2_trip) & (st["stop_sequence"]>s2_seq) & (st["stop_id"].isin(d_ids))]
                    if down2.empty:
                        continue
                    drow = down2.sort_values("stop_sequence").iloc[0]
                    arr_s = self._sec(drow["arrival_time"])
                    legs = [
                        Leg(mode="BUS", route_id=str(f.get("route_id","")), trip_id=str(f_trip),
                            from_stop_id=str(f["stop_id"]), to_stop_id=str(mid_stop),
                            depart_time=str(f["departure_time"]), arrive_time=str(mid["arrival_time"]),
                            predicted_delay_secs=int(slack), description="Leg 1"),
                        Leg(mode="BUS", route_id=str(s2.get("route_id","")), trip_id=str(s2_trip),
                            from_stop_id=str(mid_stop), to_stop_id=str(drow["stop_id"]),
                            depart_time=str(s2["departure_time"]), arrive_time=str(drow["arrival_time"]),
                            predicted_delay_secs=0, description="Leg 2")
                    ]
                    total = arr_s - f_dep_s
                    res.append(RouteOption(
                        id=str(uuid.uuid4()), summary="1 transfer",
                        total_duration_secs=int(total), transfer_count=1,
                        min_transfer_slack_secs=int(slack), risk_score=0.2, legs=legs
                    ))
                    if len(res) > 40:
                        break
                if len(res) > 50:
                    break
            if len(res) > 60:
                break
        # TODO: a true two-transfer search. For MVP we reuse one-transfer or chain if needed.
        return sorted(res, key=lambda o:o.total_duration_secs)

    def _score_and_sort(self, options: List[RouteOption], departure_dt: datetime) -> List[RouteOption]:
        # Risk score includes small penalty for minimal slack and for more transfers
        for o in options:
            risk = 0.0 + 0.15*o.transfer_count
            risk += 0.0002*max(0, 600 - o.min_transfer_slack_secs)
            o.risk_score = round(risk, 3)
            # Improve summary
            modes = " → ".join([lg.mode for lg in o.legs])
            o.summary = f"{modes} · {int(o.total_duration_secs/60)} min · {o.transfer_count} tx"
        return sorted(options, key=lambda o: (o.total_duration_secs + int(1800*o.risk_score)))
