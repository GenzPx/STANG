"""Conceptual node system for extended STANG routers.

This module is provided for architectural completeness. Custom nodes can be
built by subclassing :class:`Node` and registered in a routing pipeline.
"""

from __future__ import annotations

from typing import Any


class NodeError(RuntimeError):
    """Raised when a node fails to process a request or response."""


class Node:
    """Base class for processing nodes in an extended STANG pipeline."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = dict(config or {})

    def process_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Process an incoming request. Must return a dictionary."""
        return request

    def process_response(self, response: dict[str, Any]) -> dict[str, Any]:
        """Process an outgoing response. Must return a dictionary."""
        return response
