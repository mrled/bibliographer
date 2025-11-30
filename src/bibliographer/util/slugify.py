import re


def slugify(title: str, remove_subtitle: bool = True) -> str:
    """
    Convert a title into a slug.
    - Optionally remove subtitle (default: True)
    - Lowercase
    - Remove punctuation
    - Replace spaces with hyphens
    - Remove leading 'the' if present
    """
    out = title.lower()
    if remove_subtitle:
        out = re.sub(r"\:.*", "", out)  # remove subtitle
    out = re.sub(r"[^\w\s-]", "", out)  # remove punctuation
    out = re.sub(r"^the\s+", "", out)  # remove leading 'the '
    out = re.sub(r"^a\s+", "", out)  # remove leading 'a '
    out = re.sub(r"\s+", "-", out)  # convert spaces to hyphens
    out = re.sub(r"-+", "-", out)  # collapse multiple hyphens
    return out.strip("-")