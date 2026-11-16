# Routing

STANG uses a simple routing concept to describe how data flows through the system.

## Concepts

### Route

A path from input to output. Example: JSON → STG → JSON.

### Node

A processing stage such as validation, transformation, or backend storage.

### Pipeline

An ordered sequence of nodes.

## Example Routing

```text
Request
   ↓
STANG
   ↓
Validation
   ↓
Transform
   ↓
Cache
   ↓
Backend
   ↓
Response
```

## Request Lifecycle

1. Parse input.
2. Resolve route.
3. Run pipeline nodes in order.
4. Apply rotation if needed.
5. Return output.

## Response Lifecycle

1. Collect backend response.
2. Run reverse pipeline nodes.
3. Format output.

## Failure Handling

- Invalid input is rejected with a clear error.
- Corrupted containers fail trailer verification (SHA-256 / HMAC / AEAD).
- Timeouts are enforced per node (`config["timeout"]`); node failures are wrapped in `PipelineError` (node + stage) and bubble up to the caller.

## Fallback

Extended routers may define fallback nodes for when a primary node fails.

## Timeout

Node-level timeouts can be configured in extended deployments.

## Concurrent Requests

Each request should carry its own `RequestContext` and `RotationEngine` instance to avoid shared mutable state.
