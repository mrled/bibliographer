"""Hugo-related functions
"""

import re


def slugify(title: str) -> str:
    """
    Convert a title into a slug.
    - Lowercase
    - Remove punctuation
    - Replace spaces with hyphens
    - Remove leading 'the' if present
    """
    out = re.sub(r"[^\w\s-]", "", title.lower())  # remove punctuation
    out = re.sub(r"^the\s+", "", out)  # remove leading 'the '
    out = re.sub(r"^a\s+", "", out)  # remove leading 'a '
    out = re.sub(r"\s+", "-", out)  # convert spaces to hyphens
    out = re.sub(r"-+", "-", out)  # collapse multiple hyphens
    return out.strip("-")
