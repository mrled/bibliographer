"""ISBN utilities
"""


def normalize_isbn(isbn: str) -> str:
    """Normalize an ISBN by removing dashes and spaces.

    Args:
        isbn: The ISBN string to normalize

    Returns:
        The normalized ISBN with dashes and spaces removed

    Examples:
        >>> normalize_isbn("978-0-596-52068-7")
        '9780596520687'
        >>> normalize_isbn("978 0 596 52068 7")
        '9780596520687'
        >>> normalize_isbn("978-0-596-52068-7 ")
        '9780596520687'
    """
    return isbn.replace("-", "").replace(" ", "")
