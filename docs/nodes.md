# Node Development

This document explains how to create custom nodes for extended STANG routers.

## Example Node

```python
from stang.nodes import Node

class ExampleNode(Node):
    def process_request(self, request):
        return request

    def process_response(self, response):
        return response
```

## Lifecycle

1. `__init__` — configure the node.
2. `process_request` — transform or validate a request.
3. `process_response` — transform a response.

## Input/Output Contract

Nodes receive and return plain Python dictionaries. They should not mutate the input unless documented.

## Error Handling

Raise `NodeError` or `ValueError` for invalid input. The pipeline will stop and report the error.

## Timeout

Long-running nodes should accept a `timeout` parameter and enforce it.

## Registration

Register custom nodes in the router configuration:

```yaml
nodes:
  - id: example
    type: custom
    class: mypackage.nodes.ExampleNode
```

## Testing

Unit test nodes in isolation:

```python
def test_example_node():
    node = ExampleNode()
    assert node.process_request({"x": 1}) == {"x": 1}
```
