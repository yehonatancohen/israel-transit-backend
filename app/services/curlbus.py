from __future__ import annotations

import httpx
import pandas as pd
from typing import Dict, Any, Iterable


class CurlbusError(RuntimeError):
    """Raised when the Curlbus API cannot be queried or parsed."""


class CurlbusClient:
    """Lightweight client for retrieving GTFS-like tables from the Curlbus API.

    The Curlbus service exposes normalized GTFS tables over HTTP.  This client
    fetches those tables and converts them into ``pandas.DataFrame`` instances
    that can be consumed by the rest of the routing stack.
    """

    def __init__(self, base_url: str, timeout: float = 5.0):
        if not base_url:
            raise ValueError("base_url must be provided")
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout

    def fetch_gtfs_frames(self) -> Dict[str, pd.DataFrame]:
        """Fetch the core GTFS tables from Curlbus.

        Returns a dictionary containing DataFrames for the tables we need in the
        router.  Raises :class:`CurlbusError` if any of the required tables could
        not be retrieved or parsed.
        """

        tables = {}
        with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
            for name in ("stops", "stop_times", "trips", "routes", "calendar", "calendar_dates"):
                tables[name] = self._fetch_table(client, name)
        return tables

    def _fetch_table(self, client: httpx.Client, table: str) -> pd.DataFrame:
        last_exc: Exception | None = None
        for path in (f"gtfs/{table}", table):
            try:
                resp = client.get(path)
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:  # pragma: no cover - handled by next candidate
                last_exc = exc
                continue
            except httpx.RequestError as exc:
                raise CurlbusError(f"Failed to call Curlbus at {path}: {exc}") from exc

            try:
                payload = resp.json()
            except ValueError as exc:
                raise CurlbusError(f"Curlbus response for {path} was not JSON") from exc

            rows = self._extract_rows(payload)
            return pd.DataFrame(rows)

        raise CurlbusError(f"Curlbus endpoint for table '{table}' returned an error") from last_exc

    @staticmethod
    def _extract_rows(payload: Any) -> Iterable[Dict[str, Any]]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("data", "items", "rows", "results"):
                value = payload.get(key)
                if isinstance(value, list):
                    return value
        raise CurlbusError("Unexpected Curlbus payload structure")

