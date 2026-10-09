"""Run: uv run --group dev python -m pytest tests"""

import pytest
from _client import _keypair

import didkey


def test_abbreviate_renders_the_canonical_shape():
    """abbreviate is the text-view identity (design 5.4) and nothing pinned its shape.

    It slices without validating, so a refactor that moves a bound -- mb[:4] to
    mb[:3], or swapping the ellipsis for ... -- would silently rewrite every room
    line and every 403 body that prints an abbreviated signer, with no test to catch it.
    """
    did, _ = _keypair()
    mb = did[len(didkey.PREFIX):]
    out = didkey.abbreviate(did)
    assert out == f"{mb[:4]}\u2026{mb[-4:]}"
    assert out.startswith("z6Mk\u2026")  # the ed25519-pub multicodec prefix is fixed
    assert len(out) == 9  # 4 + ellipsis + 4
    assert didkey.PREFIX not in out  # stripped once, not repeated inside the abbreviation


def test_is_did_refuses_none_and_non_strings():
    """is_did catches TypeError so a non-string never reaches public_key's slicing.

    who() guards with is_did first, so this is the line that keeps a stray None
    (a missing JSON field, a header the proxy dropped) from becoming a 500 instead of
    the unsigned ~ lane.
    """
    assert not didkey.is_did(None)
    assert not didkey.is_did(12345)
    assert not didkey.is_did(b"did:key:z6Mk")  # bytes are not str


def test_verify_refuses_a_missing_signature_before_decoding():
    """verify checks the encoding before it base64-decodes, so an absent signature is
    a 400 (DidError), never a libsodium call on garbage bytes.

    The signed-lane tests cover aliased strings; this pins the absent-signature branch
    that _signer reaches when a POST body omits sig entirely.
    """
    did, _ = _keypair()
    for blank in (None, "", "short"):
        with pytest.raises(didkey.DidError):
            didkey.verify(did, blank, "hello")
def test_nonce_pattern_bounds_the_replay_counter():
    """NONCE_RE is the gate _signer runs before _burn_nonce's monotonic compare.

    The 19-digit ceiling is the int64 bound: a 20-digit nonce would survive fullmatch
    and then feed int() a value past the counter's intent, quietly weakening the
    single-use guarantee the nonce exists to provide. Nothing in the suite pinned the
    pattern's edges, so a {1,19} -> {1,20} typo would pass every existing test.
    """
    # Valid: 1..19 digits, including a bare zero (a counter may start at 0).
    for ok in ("0", "1", "9", "10", "9999999999999999999"):  # 19 nines
        assert didkey.NONCE_RE.fullmatch(ok), ok

    # Invalid: empty, whitespace, sign, decimal, hex, letters, and the 20-digit
    # overflow the ceiling exists to stop.
    for bad in ("", " ", "-1", "+1", "1.5", "0x1", "abc", "1a",
                "99999999999999999999"):  # 20 nines
        assert not didkey.NONCE_RE.fullmatch(bad), bad