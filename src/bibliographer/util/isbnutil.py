"""ISBN utilities
"""


def normalize_isbn(isbn: str) -> str:
    """Normalize an ISBN by removing dashes and spaces."""
    return isbn.replace("-", "").replace(" ", "")
