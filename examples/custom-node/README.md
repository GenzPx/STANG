# Custom Node Example

Conceptual example of a custom processing node.

```python
from stang.nodes import Node

class UppercaseNode(Node):
    def process_request(self, request):
        if "name" in request:
            request["name"] = request["name"].upper()
        return request
```
