"""Subset of functions required by FastAPI's upload handling tests."""

from __future__ import annotations

from typing import Dict, Tuple, Callable, Any

CallbackMap = Dict[str, Callable[..., Any]]


def parse_options_header(value: str) -> Tuple[str, Dict[bytes, bytes]]:
    """Return a tuple of (disposition, params) similar to python-multipart.

    The implementation only supports the pieces required by the test-suite: it
    splits the header on semicolons and extracts simple key=value parameters.
    """

    if not value:
        return "", {}
    parts = [part.strip() for part in value.split(";") if part.strip()]
    disposition = parts[0]
    params: Dict[bytes, bytes] = {}
    for item in parts[1:]:
        if "=" not in item:
            continue
        key, raw = item.split("=", 1)
        key_bytes = key.strip().lower().encode("latin-1")
        raw_bytes = raw.strip().strip('"').encode("latin-1")
        params[key_bytes] = raw_bytes
    return disposition, params


class MultipartParser:
    """Very small multipart parser compatible with Starlette's expectations."""

    def __init__(self, boundary: bytes | str, callbacks: CallbackMap):
        if isinstance(boundary, str):
            boundary = boundary.encode("latin-1")
        self.boundary = b"--" + boundary
        self.callbacks = callbacks
        self._buffer = bytearray()

    def write(self, data: bytes) -> None:
        self._buffer.extend(data)
        self._process_buffer()

    def finalize(self) -> None:
        # Nothing additional is required; processing happens during write.
        if "on_end" in self.callbacks:
            self.callbacks["on_end"]()

    def _process_buffer(self) -> None:
        data = bytes(self._buffer)
        if self.boundary not in data:
            return
        parts = data.split(self.boundary)
        # First element is preamble; last may be epilogue with trailing '--'
        for raw in parts[1:]:
            if raw.startswith(b"--"):
                break
            if raw.startswith(b"\r\n"):
                raw = raw[2:]
            if raw.endswith(b"\r\n"):
                raw = raw[:-2]
            if not raw:
                continue
            header_block, body = raw.split(b"\r\n\r\n", 1)
            headers = header_block.split(b"\r\n")
            self.callbacks.get("on_part_begin", lambda: None)()
            for header in headers:
                if not header:
                    continue
                if b":" not in header:
                    continue
                name, value = header.split(b":", 1)
                name = name.strip()
                value = value.lstrip()
                cb_field = self.callbacks.get("on_header_field")
                cb_value = self.callbacks.get("on_header_value")
                cb_end = self.callbacks.get("on_header_end")
                if cb_field:
                    cb_field(name, 0, len(name))
                if cb_value:
                    cb_value(value, 0, len(value))
                if cb_end:
                    cb_end()
            on_headers_finished = self.callbacks.get("on_headers_finished")
            if on_headers_finished:
                on_headers_finished()
            data_cb = self.callbacks.get("on_part_data")
            if data_cb and body:
                data_cb(body, 0, len(body))
            end_cb = self.callbacks.get("on_part_end")
            if end_cb:
                end_cb()
        # Clear buffer after processing to avoid duplicate parsing
        self._buffer.clear()
