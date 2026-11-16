"""Tests for the cryptographic primitives (STG2 encryption)."""

from __future__ import annotations

import hashlib
import hmac

import pytest

from stang.crypto import (
    NONCE_SIZE,
    PBKDF2_ITERATIONS,
    decrypt_block,
    derive_keys,
    encrypt_block,
)


def test_derive_keys_matches_reference_vector():
    salt = bytes(range(16))
    enc_master, mac_key = derive_keys("secret-stang-key", salt)
    assert enc_master.hex().startswith("a70b763d772b5fb0")
    assert mac_key.hex().startswith("377d72af039121d0")


def test_derive_keys_rejects_short_salt():
    with pytest.raises(ValueError):
        derive_keys("pw", b"\x00" * 8)


def test_derive_keys_rejects_empty_passphrase():
    with pytest.raises(ValueError):
        derive_keys("", b"\x00" * NONCE_SIZE)


def test_encrypt_decrypt_roundtrip():
    salt = b"\x11" * NONCE_SIZE
    enc_master, _ = derive_keys("pw", salt)
    plaintext = b'[{"id":1,"name":"stang"}]'
    blob = encrypt_block(plaintext, enc_master, 0)
    assert blob[:NONCE_SIZE] != plaintext[:NONCE_SIZE] or len(blob) != len(plaintext)
    assert decrypt_block(blob, enc_master, 0) == plaintext


def test_decrypt_is_block_index_bound():
    salt = b"\x22" * NONCE_SIZE
    enc_master, _ = derive_keys("pw", salt)
    blob = encrypt_block(b"payload", enc_master, 0)
    # Decrypting block 0's blob as block 1 must produce garbage, not the plaintext.
    assert decrypt_block(blob, enc_master, 1) != b"payload"


def test_encrypt_uses_random_nonces():
    salt = b"\x33" * NONCE_SIZE
    enc_master, _ = derive_keys("pw", salt)
    blob1 = encrypt_block(b"same-input", enc_master, 0)
    blob2 = encrypt_block(b"same-input", enc_master, 0)
    assert blob1 != blob2
    assert decrypt_block(blob1, enc_master, 0) == decrypt_block(blob2, enc_master, 0)


def test_decrypt_rejects_short_blob():
    with pytest.raises(ValueError):
        decrypt_block(b"\x00" * 4, b"\x00" * 32, 0)


def test_hmac_keystream_reference():
    """Pin the keystream construction to a fixed test vector."""
    salt = bytes(range(16))
    enc_master, _ = derive_keys("secret-stang-key", salt)
    nonce = bytes(range(16))
    info = b"stang-blk" + (0).to_bytes(4, "big") + nonce
    block_key = hmac.new(enc_master, info, hashlib.sha256).digest()
    ks0 = hmac.new(block_key, (0).to_bytes(8, "big"), hashlib.sha256).digest()
    assert ks0.hex().startswith("18eb8ad86136e642")


def test_pbkdf2_iteration_count_is_documented_value():
    assert PBKDF2_ITERATIONS == 100_000
