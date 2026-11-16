"""Conceptual processing nodes for extended STANG routers.

This module is provided for architectural completeness. Custom nodes can be
built by subclassing :class:`Node` and registered in a :class:`Pipeline`.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from typing import Any


class NodeError(RuntimeError):
    """Raised when a node fails to process a request or response."""


class PipelineError(NodeError):
    """Raised when a pipeline stage fails.

    Carries the failing node and stage so callers can report precisely which
    step broke and why.
    """

    def __init__(self, node: str, stage: str, message: str) -> None:
        """Store the failing *node*/*stage* and format a descriptive message."""
        self.node = node
        self.stage = stage
        super().__init__(f"[{stage}] node {node!r} failed: {message}")


class Node:
    """Base class for processing nodes in an extended STANG pipeline.

    Nodes receive and return plain dictionaries. They should not mutate the
    input unless documented.
    """

    def __init__(
        self, config: dict[str, Any] | None = None, *, name: str | None = None
    ) -> None:
        """Store configuration and apply the optional timeout."""
        self.config = dict(config or {})
        self.name = name or self.__class__.__name__
        timeout = self.config.get("timeout")
        self.timeout: float | None = float(timeout) if timeout is not None else None

    def process_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Process an incoming request. Must return a dictionary."""
        return request

    def process_response(self, response: dict[str, Any]) -> dict[str, Any]:
        """Process an outgoing response. Must return a dictionary."""
        return response

    def __repr__(self) -> str:
        """Return a compact developer summary."""
        return f"{self.__class__.__name__}(name={self.name!r})"


def _run_stage(
    node: Node,
    stage: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    handler: Callable[[dict[str, Any]], dict[str, Any]]
    handler = node.process_request if stage == "request" else node.process_response
    started = time.monotonic()
    try:
        result = handler(dict(payload))
    except NodeError as exc:
        raise PipelineError(node.name, stage, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - pipeline boundary: normalize any node failure
        raise PipelineError(node.name, stage, f"{type(exc).__name__}: {exc}") from exc
    if node.timeout is not None and time.monotonic() - started > node.timeout:
        raise PipelineError(node.name, stage, f"exceeded timeout of {node.timeout}s")
    if not isinstance(result, dict):
        raise PipelineError(
            node.name, stage, f"must return dict, got {type(result).__name__}"
        )
    return result


class Pipeline:
    """Ordered execution of nodes for the request and response phases."""

    def __init__(self, nodes: Sequence[Node] = ()) -> None:
        """Create a pipeline from an ordered sequence of nodes."""
        self.nodes: list[Node] = list(nodes)

    def add(self, node: Node) -> Pipeline:
        """Append *node* to the pipeline and return ``self`` for chaining."""
        self.nodes.append(node)
        return self

    def process_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Run every node's request stage in order."""
        payload = dict(request)
        for node in self.nodes:
            payload = _run_stage(node, "request", payload)
        return payload

    def process_response(self, response: dict[str, Any]) -> dict[str, Any]:
        """Run every node's response stage in reverse order."""
        payload = dict(response)
        for node in reversed(self.nodes):
            payload = _run_stage(node, "response", payload)
        return payload
