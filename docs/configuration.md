# Configuration

STANG's core CLI does not require a configuration file. The following describes a conceptual configuration schema used by extended STANG routers and examples.

## Example

```yaml
stang:
  name: main-router

rotation:
  mode: circular
  initial_position: 0

nodes:
  - id: A
    type: validation
  - id: B
    type: transform
  - id: C
    type: backend
```

## Properties

### `stang.name`

- **Type**: string
- **Default**: `"stang"`
- **Description**: Human-readable name for the router instance.

### `rotation.mode`

- **Type**: string
- **Allowed values**: `"circular"`
- **Default**: `"circular"`
- **Description**: Rotation mode. Only circular is implemented.

### `rotation.initial_position`

- **Type**: integer
- **Default**: `0`
- **Description**: Starting rotation index. Must be non-negative.

### `nodes[].id`

- **Type**: string
- **Required**: yes
- **Description**: Unique identifier for a node.

### `nodes[].type`

- **Type**: string
- **Allowed values**: `"validation"`, `"transform"`, `"backend"`, `"custom"`
- **Description**: Node behavior type.

## Validation Errors

- Missing `nodes[].id` raises a configuration error.
- Duplicate node IDs raise a configuration error.
- Unsupported `rotation.mode` raises a configuration error.
