"""Tests for the processing node pipeline."""

from __future__ import annotations

import pytest

from stang.nodes import Node, NodeError, Pipeline, PipelineError


class UppercaseNameNode(Node):
    def process_request(self, request):
        if "name" in request:
            request["name"] = str(request["name"]).upper()
        return request


class AppendTagNode(Node):
    def __init__(self) -> None:
        super().__init__({"tag": "seen"})

    def process_request(self, request):
        request["tags"] = [*request.get("tags", []), self.config["tag"]]
        return request


class FailingNode(Node):
    def process_request(self, request):
        raise ValueError("boom")


class BadReturnNode(Node):
    def process_request(self, request):
        return "not-a-dict"  # type: ignore[return-value]


def test_pipeline_request_order():
    pipeline = Pipeline([UppercaseNameNode(), AppendTagNode()])
    result = pipeline.process_request({"name": "genz"})
    assert result == {"name": "GENZ", "tags": ["seen"]}


def test_pipeline_response_reverse_order():
    order: list[str] = []

    class Recorder(Node):
        def __init__(self, label: str) -> None:
            super().__init__(name=label)

        def process_response(self, response):
            order.append(self.name)
            return response

    pipeline = Pipeline([Recorder("a"), Recorder("b"), Recorder("c")])
    pipeline.process_response({})
    assert order == ["c", "b", "a"]


def test_pipeline_wraps_node_failures():
    pipeline = Pipeline([FailingNode()])
    with pytest.raises(PipelineError) as excinfo:
        pipeline.process_request({})
    assert excinfo.value.stage == "request"
    assert "boom" in str(excinfo.value)


def test_pipeline_rejects_non_dict_return():
    pipeline = Pipeline([BadReturnNode()])
    with pytest.raises(PipelineError, match="dict"):
        pipeline.process_request({})


def test_node_error_passthrough():
    class StrictNode(Node):
        def process_request(self, request):
            raise NodeError("explicit failure")

    pipeline = Pipeline([StrictNode()])
    with pytest.raises(PipelineError, match="explicit failure"):
        pipeline.process_request({})


def test_default_node_is_identity():
    node = Node()
    assert node.process_request({"x": 1}) == {"x": 1}
    assert node.process_response({"y": 2}) == {"y": 2}


def test_pipeline_chaining():
    pipeline = Pipeline()
    pipeline.add(UppercaseNameNode()).add(AppendTagNode())
    assert len(pipeline.nodes) == 2
    assert pipeline.process_request({"name": "abc"})["tags"] == ["seen"]
