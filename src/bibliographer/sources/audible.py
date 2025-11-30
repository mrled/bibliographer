"""Audible library retrieval and metadata management.
"""

from getpass import getpass
import json
import pathlib
import re
import tempfile
from typing import Any, Mapping, Optional, TYPE_CHECKING

import audible

from bibliographer import mlogger
from bibliographer.cardcatalog import CardCatalog, CatalogBook
from bibliographer.util.slugify import slugify

if TYPE_CHECKING:
    from bibliographer.cli.bibliographer import SecretValueGetter


def audible_login(
    authfile: pathlib.Path,
    password_getter: Optional["SecretValueGetter"] = None,
) -> audible.Client:
    """
    If the authfile doesn't exist, prompt for email/password+TOTP. Otherwise reuse existing.
    Return an audible.Client instance.

    SECURITY: This function REQUIRES an encryption password. Audible credentials will NOT be
    saved unencrypted to disk. If no password is provided, the function will fail.

    Args:
        authfile: Path to the authentication file
        password_getter: SecretValueGetter to retrieve encryption password for the auth file (REQUIRED)

    Raises:
        ValueError: If no encryption password is provided
    """
    # Require encryption password
    if not password_getter:
        raise ValueError("audible_auth_password_cmd must be configured")

    encryption_password = password_getter.get()
    if not encryption_password:
        raise ValueError("Failed to retrieve Audible auth encryption password")

    if authfile.exists():
        mlogger.debug(f"[AUDIBLE] Using existing authenticator from {authfile}")
        try:
            authenticator = audible.Authenticator.from_file(authfile, password=encryption_password)
            mlogger.debug("[AUDIBLE] Loaded encrypted auth file")
        except Exception as e:
            mlogger.error(f"[AUDIBLE] Failed to load encrypted auth file: {e}")
            raise
    else:
        email = input("Enter your Audible/Amazon email: ")
        password_totp = getpass("Enter your password + TOTP code (no spaces): ")
        mlogger.debug("[AUDIBLE] Logging in via from_login(...)")
        authenticator = audible.Authenticator.from_login(email, password_totp, locale="us")
        authenticator.to_file(authfile, password=encryption_password, encryption="json")
        mlogger.info(f"[AUDIBLE] Auth saved with encryption to {authfile}")

    client = audible.Client(authenticator)
    return client


def decrypt_credentials(authfile: pathlib.Path, password_getter: "SecretValueGetter") -> str:
    """
    Decrypt an encrypted Audible credentials file and return as JSON string.

    Args:
        authfile: Path to the encrypted authentication file
        password_getter: SecretValueGetter to retrieve encryption password

    Returns:
        JSON string of decrypted credentials

    Raises:
        ValueError: If no encryption password is provided
    """
    if not password_getter:
        raise ValueError("audible_auth_password_cmd must be configured")

    encryption_password = password_getter.get()
    if not encryption_password:
        raise ValueError("Failed to retrieve Audible auth encryption password")

    authenticator = audible.Authenticator.from_file(authfile, password=encryption_password)
    return json.dumps(authenticator.to_dict(), indent=2)


def encrypt_credentials(authfile: pathlib.Path, password_getter: "SecretValueGetter") -> str:
    """
    Load an unencrypted Audible credentials file and output encrypted JSON.

    Args:
        authfile: Path to the unencrypted authentication file
        password_getter: SecretValueGetter to retrieve encryption password

    Returns:
        JSON string of encrypted credentials

    Raises:
        ValueError: If no encryption password is provided

    Note:
        We have to use a temporary file because to_dict() doesn't encrypt.
        The only way to get encrypted output is to use to_file() with encryption,
        then read back the encrypted file.
    """
    if not password_getter:
        raise ValueError("audible_auth_password_cmd must be configured")

    encryption_password = password_getter.get()
    if not encryption_password:
        raise ValueError("Failed to retrieve Audible auth encryption password")

    # Load unencrypted file
    authenticator = audible.Authenticator.from_file(authfile)

    # Save to temporary file with encryption (to_dict() doesn't encrypt)
    with tempfile.NamedTemporaryFile(mode='r', delete=False, suffix='.json') as tmp:
        tmp_path = pathlib.Path(tmp.name)

    try:
        authenticator.to_file(tmp_path, password=encryption_password, encryption="json")
        encrypted_content = tmp_path.read_text()
        return encrypted_content
    finally:
        # Clean up temp file
        tmp_path.unlink(missing_ok=True)


def retrieve_audible_library(
    catalog: CardCatalog,
    client: audible.Client,
):
    """
    Retrieve the user's Audible library with pagination via the `audible` module.
    Saves results in audible_library_metadata as:
       {
         asin: {
           "title": ...,
           "authors": [ ... ],
           "cover_image_url": ...,
           "purchase_date": "YYYY-MM-DD" or None,
           "audible_asin": ...,
         }
       }
    """
    page = 1
    page_size = 1000
    while True:
        mlogger.debug(f"[AUDIBLE] GET library page={page} size={page_size}")
        params: Mapping[str, Any] = dict(
            num_results=page_size, page=page, response_groups="product_desc, media, product_attrs"
        )
        resp = client.get("1.0/library", **params)
        items = resp["items"]
        if not items:
            break

        for item in items:
            asin = item["asin"]
            catalog.audiblelib.contents[asin] = item

        page += 1
        if len(items) < page_size:
            break

    print(f"Retrieved library pages up to page {page-1}")


def process_audible_library(
    catalog: CardCatalog,
):
    """
    Retrieve the user's Audible library with pagination via the `audible` module.
    Saves results in audible_library_metadata as:
       {
         asin: {
           "title": ...,
           "authors": [ ... ],
           "cover_image_url": ...,
           "purchase_date": "YYYY-MM-DD" or None,
           "audible_asin": ...,
         }
       }
    """
    for asin, item in catalog.audiblelib.contents.items():
        mlogger.debug(f"Processing Audible library ASIN {asin}")
        book = CatalogBook()
        book.audible_asin = asin
        book.title = item["title"]
        book.authors = [author["name"] for author in item.get("authors", [])]

        product_images = item.get("product_images", {})
        if product_images:
            sorted_img_keys = sorted(product_images.keys(), key=lambda x: int(x) if x.isdigit() else 0, reverse=True)
            book.audible_cover_url = product_images[sorted_img_keys[0]]

        purchase_date = item.get("purchase_date")
        if purchase_date:
            # If it's something like "2020-01-15T05:00:00Z", extract date portion
            match = re.match(r"(\d{4}-\d{2}-\d{2})", purchase_date)
            if match:
                book.purchase_date = match.group(1)
            else:
                book.purchase_date = purchase_date[:10]
        else:
            book.purchase_date = None

        if asin not in catalog.audibleslugs.contents:
            catalog.audibleslugs.contents[asin] = slugify(item["title"])
        book.slug = catalog.audibleslugs.contents[asin]

        if book.slug in catalog.combinedlib.contents:
            catalog.combinedlib.contents[book.slug].merge(book)
        else:
            catalog.combinedlib.contents[book.slug] = book
