"""Code that passes both the block and the warn config."""

import hashlib

GREETING = "hello"


def fingerprint(data: bytes) -> str:
    """Hash data for an integrity check.

    Args:
        data: The bytes to hash.

    Returns:
        The SHA-256 hex digest.
    """
    return hashlib.sha256(data).hexdigest()


def greet(name: str) -> str:
    """Build a greeting.

    Args:
        name: Who to greet.

    Returns:
        The greeting text.
    """
    return f"{GREETING}, {name}"

