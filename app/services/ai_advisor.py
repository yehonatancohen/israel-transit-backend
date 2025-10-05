import os
import httpx
from typing import List
from ..config import OPENROUTER_API_KEY, OPENROUTER_MODEL
from ..schemas import RouteOption

SYS_PROMPT = (
    "You are an Israeli transit assistant. Rerank route options by real usefulness: "
    "prefer reliable transfers with adequate slack given historical lateness, avoid risky corridors, "
    "minimize total time, and reduce cognitive load. Penalize 1-minute transfers."
)

class AIAdvisor:
    def __init__(self):
        self.enabled = bool(OPENROUTER_API_KEY)

    def rerank(self, options: List[RouteOption], user_notes: str | None = None) -> List[RouteOption]:
        if not self.enabled or not options:
            return options
        try:
            content = "User notes: " + (user_notes or "None") + "\n\n"
            for i, o in enumerate(options):
                content += f"[{i}] id={o.id} time={o.total_duration_secs}s transfers={o.transfer_count} min_slack={o.min_transfer_slack_secs}s risk={o.risk_score}\n"
                for lg in o.legs:
                    content += f"  - {lg.mode} {lg.route_id or ''} {lg.from_stop_id}->{lg.to_stop_id} dep={lg.depart_time} arr={lg.arrive_time} delay={lg.predicted_delay_secs}s\n"
            payload = {
                "model": OPENROUTER_MODEL or "openrouter/auto",
                "messages": [
                    {"role": "system", "content": SYS_PROMPT},
                    {"role": "user", "content": content + "\nReturn a JSON list of route indexes best-to-worst and a one-line reason."}
                ],
                "response_format": {"type": "json_object"}
            }
            headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
            with httpx.Client(timeout=30) as client:
                resp = client.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
            # Parse
            txt = data["choices"][0]["message"]["content"]
            import json as _json
            obj = _json.loads(txt)
            order = obj.get("order") or obj.get("indexes") or []
            reason = obj.get("reason") or ""
            # Reorder
            new = []
            for idx in order:
                if isinstance(idx, int) and 0 <= idx < len(options):
                    o = options[idx]
                    o.ai_reason = reason
                    new.append(o)
            if not new:
                return options
            return new
        except Exception:
            return options
