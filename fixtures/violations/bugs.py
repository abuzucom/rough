"""Bug patterns the baseline blocks."""


def add_item(item: int, bucket: list | None = [], /) -> list:  # expect: mutable-argument-default
    """Append to a shared default list.

    Returns:
        The list.
    """
    bucket.append(item)
    return bucket


def total() -> int:
    """Refer to a name that does not exist.

    Returns:
        Nothing; the name is undefined.
    """
    return missing_total  # expect: undefined-name


class Account:
    """Return a value from __init__."""

    def __init__(self) -> None:
        """Initialize."""
        return 1  # expect: return-in-init
