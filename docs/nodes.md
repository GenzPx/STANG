# Node Development

This document explains how to create custom nodes for extended STANG routers.

## Example Node

```python
from stang.nodes import Node

class UppercaseNode(Node):
    def process_request(self, request):
        if "name" in request:
            request["name"] = str(request["name"]).upper()
        return request

    def process_response(self, response):
        return response
```

## Lifecycle

1. `__init__(config, *, name=None)` — configure the node. A `timeout` (seconds) may be set via `config["timeout"]`.
2. `process_request` — transform or validate a request. Must return a `dict`.
3. `process_response` — transform a response. Must return a `dict`.

## Running a Pipeline

```python
from stang.nodes import Node, Pipeline, PipelineError

pipeline = Pipeline([UppercaseNode()])
pipeline.add(AnotherNode())

try:
    out = pipeline.process_request({"name": "genz"})
except PipelineError as exc:
    print(exc.node, exc.stage, exc)
```

- Requests run through nodes **in order**; responses run through them **in reverse order**.
- Node exceptions are wrapped in `PipelineError` with the failing node name and stage.
- A node returning a non-`dict` raises `PipelineError` as well.

## Input/Output Contract

Nodes receive and return plain Python dictionaries. They should not mutate the input unless documented.

## Registration

Register custom nodes in the router configuration:

```yaml
nodes:
  - id: example
    type: custom
    class: mypackage.nodes.UppercaseNode
```

## Testing

```python
def test_uppercase_node():
    node = UppercaseNode()
    assert node.process_request({"name": "genz"}) == {"name": "GENZ"}
```
