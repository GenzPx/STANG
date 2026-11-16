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
stang encode demo.json demo.stg --blocks 4 --rotation 1 --compress
```

## 3. Inspect

```bash
stang inspect demo.stg
```

Output:

```text
File       : demo.stg
Magic      : STG2
Format     : STG2
Blocks     : 4
Rotation   : 1
Records    : 3
Flags      : compressed
Schema     : {'id': 'integer', 'meta.score': 'float', ...}
Checksum   : VALID
```

## 4. Dump

```bash
stang dump demo.stg
stang dump demo.stg --format markdown
stang dump demo.stg --format csv
stang dump demo.stg --format stats
```

## 5. Decode

```bash
stang decode demo.stg demo-out.json
```

The output JSON is semantically identical to the input.

## 6. Encrypt

```bash
export STANG_PASSPHRASE="$(stang keygen)"
stang encode demo.json secret.stg --encrypt --passphrase-env STANG_PASSPHRASE
stang verify secret.stg --passphrase-env STANG_PASSPHRASE
stang decode secret.stg secret.json --passphrase-env STANG_PASSPHRASE
```

## Lifecycle

```text
demo.json
   ↓ encode (+compress, +encrypt)
demo.stg
   ↓ rotate / dump / inspect / verify / convert
decoded view
   ↓ decode
demo-out.json
```
