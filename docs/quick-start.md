# Quick Start

This guide gets you running STANG in a few minutes.

## 1. Create Sample Data

```bash
cat > demo.json <<'EOF'
[
  {"id": 1, "name": "Genz", "tags": ["alpha"], "meta": {"score": 9.5}},
  {"id": 2, "name": "Ana", "tags": ["beta"], "meta": {"score": 8.0}},
  {"id": 3, "name": "Bob", "tags": ["gamma"], "meta": {"score": 7.5}}
]
EOF
```

## 2. Encode to STG

```bash
stang encode demo.json demo.stg --blocks 4 --rotation 1
```

## 3. Inspect

```bash
stang inspect demo.stg
```

Output:

```text
File       : demo.stg
Magic      : STG1
Version    : 1
Flags      : 0
Blocks     : 4
Rotation   : 1
Records    : 3
Schema     : {...}
Checksum   : VALID
```

## 4. Dump

```bash
stang dump demo.stg
stang dump demo.stg --format json
stang dump demo.stg --format csv
```

## 5. Decode

```bash
stang decode demo.stg demo-out.json
```

The output JSON is semantically identical to the input.

## Lifecycle

```text
demo.json
   ↓ encode
demo.stg
   ↓ rotate / dump / inspect / verify / status
decoded view
   ↓ decode
demo-out.json
```
