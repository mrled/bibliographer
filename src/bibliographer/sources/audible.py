"""Audible library retrieval and metadata management.
"""

from getpass import getpass
import pathlib
import re
from typing import Any, Mapping, Optional, TYPE_CHECKING

import audible

from bibliographer import mlogger
from bibliographer.cardcatalog import CardCatalog, CombinedCatalogBook
from bibliographer.hugo import slugify

if TYPE_CHECKING:
    from bibliographer.cli.bibliographer import SecretValueGetter


def audible_login(
    authfile: pathlib.Path,
    password_getter: Optional["SecretValueGetter"] = None,
) -> audible.Client:
    """
    If the authfile doesn't exist, prompt for email/password+TOTP. Otherwise reuse existing.
    Return an audible.Client instance.

    Args:
        authfile: Path to the authentication file
        password_getter: Optional SecretValueGetter to retrieve encryption password for the auth file
    """
    # Get the encryption password if available
    encryption_password = password_getter.get() if password_getter else None

    if authfile.exists():
        mlogger.debug(f"[AUDIBLE] Using existing authenticator from {authfile}")

        # Try to load with encryption password first
        if encryption_password:
            try:
                authenticator = audible.Authenticator.from_file(authfile, password=encryption_password)
                mlogger.debug("[AUDIBLE] Loaded encrypted auth file")
            except Exception as e:
                # Migration path: file might be unencrypted, try without password
                mlogger.debug(f"[AUDIBLE] Failed to load with password, trying unencrypted: {e}")
                try:
                    authenticator = audible.Authenticator.from_file(authfile)
                    mlogger.warning(
                        "[AUDIBLE] Loaded unencrypted auth file. "
                        "It will be re-saved with encryption on next login."
                    )
                    # Re-save with encryption
                    authenticator.to_file(authfile, password=encryption_password, encryption="json")
                    mlogger.info(f"[AUDIBLE] Auth file has been encrypted and saved to {authfile}")
                except Exception as e2:
                    mlogger.error(f"[AUDIBLE] Failed to load auth file: {e2}")
                    raise
        else:
            # No password provided, load without encryption
            authenticator = audible.Authenticator.from_file(authfile)
            if "INSECURE" not in str(authfile):
                mlogger.warning(
                    "[AUDIBLE] Loading auth file without encryption. "
                    "Consider setting audible_auth_password_cmd to encrypt credentials."
                )
    else:
        email = input("Enter your Audible/Amazon email: ")
        password_totp = getpass("Enter your password + TOTP code (no spaces): ")
        mlogger.debug("[AUDIBLE] Logging in via from_login(...)")
        authenticator = audible.Authenticator.from_login(email, password_totp, locale="us")

        # Save with encryption if password is available
        if encryption_password:
            authenticator.to_file(authfile, password=encryption_password, encryption="json")
            mlogger.info(f"[AUDIBLE] Auth saved with encryption to {authfile}")
        else:
            authenticator.to_file(authfile)
            mlogger.warning(
                f"[AUDIBLE] Auth saved WITHOUT encryption to {authfile}. "
                "Consider setting audible_auth_password_cmd to encrypt credentials."
            )

    client = audible.Client(authenticator)
    return client


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
        book = CombinedCatalogBook()
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
