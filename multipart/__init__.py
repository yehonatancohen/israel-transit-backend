"""Minimal stub of python-multipart for offline test environments."""

from .multipart import parse_options_header, MultipartParser  # noqa: F401

__version__ = "0.0"

__all__ = ["parse_options_header", "MultipartParser"]
