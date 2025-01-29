"""Audible library retrieval and metadata management.
"""

from getpass import getpass
import pathlib
import re
from typing import Any, Mapping

import audible

from bibliographer import mlogger
from bibliographer.util.jsonutil import load_json, save_json


def audible_login(authfile: pathlib.Path) -> audible.Client:
    """
    If the authfile doesn't exist, prompt for email/password+TOTP. Otherwise reuse existing.
    Return an audible.Client instance.
    """
    if authfile.exists():
        mlogger.debug(f"[AUDIBLE] Using existing authenticator from {authfile}")
        authenticator = audible.Authenticator.from_file(authfile)
    else:
        email = input("Enter your Audible/Amazon email: ")
        password_totp = getpass("Enter your password + TOTP code (no spaces): ")
        mlogger.debug("[AUDIBLE] Logging in via from_login(...)")
        authenticator = audible.Authenticator.from_login(email, password_totp, locale="us")
        authenticator.to_file(authfile)
        mlogger.debug(f"[AUDIBLE] Auth saved to {authfile}")
    client = audible.Client(authenticator)
    return client


###############################################################################
# Retrieve Audible Library
###############################################################################


def retrieve_audible_library(
    client: audible.Client,
    audible_library_metadata: pathlib.Path,
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
    merged_data = load_json(audible_library_metadata)

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
            title = item["title"]
            authors = [author["name"] for author in item.get("authors", [])]

            product_images = item.get("product_images", {})
            cover_url = None
            if product_images:
                sorted_img_keys = sorted(
                    product_images.keys(), key=lambda x: int(x) if x.isdigit() else 0, reverse=True
                )
                cover_url = product_images[sorted_img_keys[0]]

            purchase_date = item.get("purchase_date")
            if purchase_date:
                # If it's something like "2020-01-15T05:00:00Z", extract date portion
                match = re.match(r"(\d{4}-\d{2}-\d{2})", purchase_date)
                if match:
                    purchase_date = match.group(1)
                else:
                    purchase_date = purchase_date[:10]
            else:
                purchase_date = None

            merged_data[asin] = {
                "title": title,
                "authors": authors,
                "cover_image_url": cover_url,
                "purchase_date": purchase_date,
                "audible_asin": asin,
            }

        page += 1
        if len(items) < page_size:
            break

    save_json(audible_library_metadata, merged_data)
    mlogger.debug(f"[AUDIBLE] Library data saved to {audible_library_metadata}")
    print(f"Retrieved library pages up to page {page-1} and saved to {audible_library_metadata}")
