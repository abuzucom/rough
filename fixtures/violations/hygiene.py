"""Autofixable hygiene the baseline blocks, and maintainability signals it only warns on."""


class Base(object):  # expect: useless-object-inheritance
    """Inherit from object explicitly."""


def label(code: int):  # expect-warn: complex-structure, missing-return-type-undocumented-public-function
    """Map a status code to a label through many branches.

    Returns:
        The label.
    """
    match code:
        case 1:
            return "one"
        case 2:
            return "two"
        case 3:
            return "three"
        case 4:
            return "four"
        case 5:
            return "five"
        case 6:
            return "six"
        case 7:
            return "seven"
        case 8:
            return "eight"
        case 9:
            return "nine"
        case 10:
            return "ten"
        case _:
            return "many"
