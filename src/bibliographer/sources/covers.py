###############################################################################
# Download a cover image
###############################################################################


from dataclasses import dataclass
import pathlib
from typing import Optional

from bibliographer import mlogger
from bibliographer.cardcatalog import CardCatalog
from bibliographer.ratelimiter import RateLimiter
import requests


@dataclass
class CoverData:
    image_data: bytes
    content_type: str
    filename: str


def download_cover_from_url(url: str) -> CoverData:
    """Download a cover image

    Return the image data, content type, and file path if successful, otherwise None.
    """

    r = requests.get(url, timeout=10, allow_redirects=True)
    r.raise_for_status()
    mlogger.debug(f"[COVER] => status {r.status_code}, content-type={r.headers.get('Content-Type','')}")
    if r.headers.get("Content-Type", "").startswith("image/"):
        image_data = r.content
        content_type = r.headers.get("Content-Type", "")
        filename = None
        if content_type.startswith("image/jpeg"):
            filename = "cover.jpg"
        elif content_type.startswith("image/png"):
            filename = "cover.png"
        elif content_type.startswith("image/gif"):
            filename = "cover.gif"
        elif content_type.startswith("image/webp"):
            filename = "cover.webp"
        if not filename:
            raise ValueError(f"Unknown image content type: {content_type} from url {url}")
        return CoverData(image_data, content_type, filename)
    else:
        raise ValueError(f"Data at URL {url} was not an image")


###############################################################################
# Amazon Cover Retrieve
###############################################################################


@RateLimiter.limit("amazon.com", interval=1)
def amazon_cover_retreive(asin: str):
    """Retrieve the cover image for an ASIN from Amazon.

    TODO: if the result is a 43-byte gif, treat as a 404.

    TODO: get a higher quality image for these. This one isn't good enough.

    TODO: use download_cover_image
    """
    url = f"https://images-na.ssl-images-amazon.com/images/P/{asin}.jpg"
    headers = {"User-Agent": "Mozilla/5.0"}
    mlogger.debug(f"[AMAZON COVER] GET {url}")
    r = requests.get(url, headers=headers, timeout=10)
    mlogger.debug(f"[AMAZON COVER] => status {r.status_code}, content-type={r.headers.get('Content-Type','')}")
    if r.status_code == 200 and r.headers.get("Content-Type", "").startswith("image/"):
        return r.content
    return None


###############################################################################
# Retrieve Cover from Google Books
###############################################################################


def google_books_cover_retreive(catalog: CardCatalog, gbooks_volid: str) -> Optional[CoverData]:
    """
    Retrieve the largest image from Google Books for a volumeID.
    """
    data = catalog.contents("apicache_gbooks_volumes").get(gbooks_volid)
    if data and "image_urls" in data and data["image_urls"]:
        img_url = data["image_urls"][0]  # only 1 stored if we followed the "largest" logic
        mlogger.debug(f"[COVER] Attempting GoogleBooks largest image {img_url}")
        return download_cover_from_url(img_url)
    mlogger.debug(f"[COVER] No image found for {gbooks_volid}")
    return None


###############################################################################
# Retrieve Cover
###############################################################################


def lookup_cover(
    catalog: CardCatalog,
    gbooks_volid: Optional[str],
    fallback_asin: Optional[str],
    book_dir: pathlib.Path,
    force=False,
):
    """Retrieve cover image for a book from APIs

    If a cover is already present, don't re-fetch unless 'force' is True.
    """
    existing_cover = cover_path(book_dir)
    if existing_cover:
        if force:
            mlogger.debug(f"[cover] already exists at {existing_cover} and force is passed, redownloading...")
        else:
            mlogger.debug(f"[cover] already exists at {existing_cover}, will not redownload")
            return
    else:
        mlogger.debug(f"[cover] downloading for {book_dir}...")

    cover_data = None
    if gbooks_volid:
        cover_data = google_books_cover_retreive(catalog, gbooks_volid)
    # Don't try Amazon for covers at all for now.
    # These covers are pretty low quality.
    # TODO: is there a way to get higher quality covers here?
    # if not cover_data and fallback_asin:
    #     cover_data = amazon_cover_retreive(fallback_asin)
    if cover_data:
        book_dir.mkdir(exist_ok=True, parents=True)

        while existing_cover := cover_path(book_dir):
            existing_cover.unlink()

        new_cover_path = book_dir / cover_data.filename
        with new_cover_path.open("wb") as f:
            f.write(cover_data.image_data)


def cover_path(book_dir: pathlib.Path) -> Optional[pathlib.Path]:
    """Return True if the cover image exists in the book directory

    slice "image" "image/jpg" "image/jpeg" "image/png" "image/gif" "image/webp")) 0) }}
    """
    if not book_dir.is_dir():
        return None
    for child in book_dir.iterdir():
        if child.is_file() and child.suffix.lower() in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
            return child
    return None
