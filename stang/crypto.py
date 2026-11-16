"""Standard-library authenticated stream encryption for STG blocks.

Implements PBKDF2-HMAC-SHA256 key derivation paired with domain-separated
HMAC-SHA256 counter-mode encryption and container-wide Encrypt-then-MAC
authentication. Compatible with both Python stdlib and Web Crypto APIs.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import struct

NONCE_SIZE = 16
PBKDF2_ITERATIONS = 100_000
BLOCK_DOMAIN_PREFIX = b"stang-blk"


def derive_keys(passphrase: bytes | str, salt: bytes) -> tuple[bytes, bytes]:
    """Derive a 32-byte encryption master key and 32-byte MAC key via PBKDF2.

    Args:
        passphrase: Secret passphrase as ``str`` or UTF-8 ``bytes``.
        salt: 16-byte salt (stored as block 0's nonce).

    Returns:
        Tuple of ``(enc_master_key, mac_key)``.
    """
    raw_pass = passphrase.encode("utf-8") if isinstance(passphrase, str) else passphrase
    if not raw_pass:
        raise ValueError("Encryption passphrase must not be empty.")
    if len(salt) != NONCE_SIZE:
        raise ValueError(f"Salt must be {NONCE_SIZE} bytes.")
    derived = hashlib.pbkdf2_hmac("sha256", raw_pass, salt, PBKDF2_ITERATIONS, dklen=64)
    return derived[:32], derived[32:]


def _xor_keystream(enc_master_key: bytes, block_index: int, nonce: bytes, data: bytes) -> bytes:
    """XOR ``data`` with a deterministic HMAC-SHA256 counter keystream."""
    info = BLOCK_DOMAIN_PREFIX + struct.pack("!I", block_index) + nonce
    block_key = hmac.new(enc_master_key, info, hashlib.sha256).digest()

    out = bytearray(len(data))
    counter = 0
    offset = 0
    total = len(data)
    while offset < total:
        ks = hmac.new(block_key, struct.pack("!Q", counter), hashlib.sha256).digest()
        chunk_len = min(32, total - offset)
        for i in range(chunk_len):
            out[offset + i] = data[offset + i] ^ ks[i]
        offset += chunk_len
        counter += 1
    return bytes(out)


def encrypt_block(
    plaintext: bytes,
    enc_master_key: bytes,
    block_index: int,
    nonce: bytes | None = None,
) -> bytes:
    """Encrypt a single block payload and prepend its 16-byte nonce."""
    actual_nonce = nonce if nonce is not None else secrets.token_bytes(NONCE_SIZE)
    if len(actual_nonce) != NONCE_SIZE:
        raise ValueError(f"Block nonce must be {NONCE_SIZE} bytes.")
    ciphertext = _xor_keystream(enc_master_key, block_index, actual_nonce, plaintext)
    return actual_nonce + ciphertext


def decrypt_block(blob: bytes, enc_master_key: bytes, block_index: int) -> bytes:
    """Extract the 16-byte nonce from ``blob`` and decrypt its ciphertext."""
    if len(blob) < NONCE_SIZE:
        raise ValueError("Encrypted block is shorter than nonce length.")
    nonce = blob[:NONCE_SIZE]
    ciphertext = blob[NONCE_SIZE:]
    return _xor_keystream(enc_master_key, block_index, nonce, ciphertext)
