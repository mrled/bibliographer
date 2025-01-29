# Initial prompt

Implement this program.

General implementation notes:

* Some files contain JSON objects.
  When saving to these files,
  combine existing contents of the file with any new results.
  If there are conflicts,
  overwrite old values with new ones.
* Handle API pagination everywhere.
* The function signatures are only guidelines.
  Feel free to add new arguments where necessary.
* If necessary, use multiple API calls to complete a function.
* If I've missed any steps, notice what I've missed and try to solve it yourself.
  Tell me when you do this.
* Functions calling APIs should save the result of APIs based on lookup parameters.
  Future calls to the function with the same parameters
  should returned the saved values.

The command-line interface:

* Use argparse
* Provide subcommands:
    * `audible login`: Create an Audible authentication file
    * `audible retrieve`: retrieve the library, enrich it, and populate books from it
    * `audible populate`: enrich and populate, but don't retrieve the library again
    * `kindle ingest`: Ingest a new Kindle library export, enrich it, and populate books from it
    * `kindle populate` enrich and populate books based on existing Kindle library
* For all paths, provide options with default values
    * Accept `--repo-root` that defaults to the ancestor directory containing a `.git` directory
    * `--book-slug-root` defaults to repo_root / "content" / "books"
    * API cache files should all go inside book_slug_root / "apicache" / something.
      No need to accept an argument for each one of these individually.
* Accept a `--google-books-key` argument

```python

def audible_login(authfile: pathlib.Path):
    """Log in to Audible.

    Handle TOTP and captchas properly.
    Save the authentication data to the authfile.
    Return the path to the authfile.
    """
    raise NotImplementedError

def retrieve_audible_library(
    authfile: pathlib.Path,
    audible_library_metadata: pathlib.Path,
):
    """Retrieve the user's Audible library using the `audible` Python package

    If authentication fails, throw a unique error.

    Save the results as JSON to the audible_library_metadata.
    File should be a JSON document with keys of the ASIN and values containing:
    - title
    - authors (list)
    - cover image URL for largest image available
    """
    raise NotImplementedError

def google_books_retrieve(
    key: str,
    gbooks_volumes: pathlib.Path,
    bookid: str
) -> str:
    """Retrieve information about specific title from Google Books

    First, query the gbooks_volumes.

    If not present, query the live API and save the results to the gbooks_volumes.
    The key is the Google Books Volume ID, and the value is:
    - ISBN-13
    - title
    - authors (list)
    - publish date
    - image URLs

    Return a dict with the Google Books Volume ID returned from the API, and the values above.
    """
    # TODO: fix this URL to also retrieve ISBN-13
    url = f"https://www.googleapis.com/books/v1/volumes/{bookid}?fields=id,volumeInfo(title,authors,publishedDate,imageLinks)&key=${key}"
    raise NotImplementedError

def google_books_search(
    key: str,
    gbooks_volumes: pathlib.Path,
    title: str,
    author: str
):
    """Search Google Books for a title/author

    params:
    - key: Google API key
    - gbooks_volumes: A file containing JSON object where keys are the volume ID
    - title: Book title
    - author: Book author

    Use the volume search API to search for the author and title.
    Ignore all but the first result.
    Call google_books_retrieve() and return its result.
    """
    # Note: author and title have to be URL-encoded, like %20 etc, for use with the API URL
    url_author = author
    url_title = title
    url = f"https://www.googleapis.com/books/v1/volumes?q=intitle:{url_title}&inauthor:{url_author}&key=${key}"
    raise NotImplementedError

def wikipedia_relevant_pages(
    title: str,
    authors: list[str],
):
    """Find related pages on Wikipediate

    Look for the book title as "Book Title (book)" first,
    and if that doesn't exist then simply "Book Title".

    Look for the authors as their names.

    Query the Wikipedia API to determine if those pages exist.
    Return a list of all that do as a dict where keys are titles and values are URLs.
    """
    raise NotImplementedError

def isbn2olid(
    isbn2olid_map: pathlib.Path,
    isbn: str
):
    """Find the OpenLibrary ID from an ISBN
    """
    url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json"
    raise NotImplementedError

def asin2gbv(
    asin2gbv_map: pathlib.Path,
    asin: str,
    title: str,
    author: str,
):
    """Look up a Google Books Volume given an ASIN

    params:
    - asin2gbv_map: A file containing a JSON object where the keys are an ASIN and the values are a Google Books Volume ID
    - asin: An ASIN, the Amazon product ID
    - title: Book title
    - author: Book author

    First, check in the local asin2gbv_map.

    If not present, use google_books_search() to query for the title and author.
    Save the result in asin2gbv_map.

    Return the Google Books Volume ID.
    """
    raise NotImplementedError

def amazon_browser_search(
    search2asin_map: pathlib.Path,
    searchterm: str,
):
    """Search Amazon.com for the search terms.

    params:
    - search2asin_map: A file containing a JSON object where the keys are search terms and the values are ASINs
    - searchterm: A search term for Amazon, which might be book title and author, or ISBN

    Convert the searchterm to plus-separated string+like+this.
    If the converted value is found in the search2asin_map,
    return that.

    Otherwise, retrieve the result from Amazon.
    Use curl impersonating a desktop web browser.

    Find the first instance of `<div role="listitem" data-asin="0330375474"` in the response,
    parse the ASIN out of that string,
    save that value to the search2asin_map,
    and return it.
    """
    # TODO: properly encode the search term
    url = "https://amazon.com/s?k={searchterm}"
    raise NotImplementedError

def amazon_cover_retreive(
    asin: str,
):
    """Retrieve a cover image from Amazon

    Return the data of the image.

    Note that this only works with products sold on amazon.com, not Audible.
    Some products may not have an image available this way.

    Impersonate a browser when downloading.
    """
    url = "https://images-na.ssl-images-amazon.com/images/P/[ASIN].jpg"
    raise NotImplementedError

def audible2slug(
    audible2slug_map: pathlib.Path,
    asin: str,
    title: str,
):
    """Given an Audible title, return its slug.

    params:
    - audible2slug_map: A file containing a JSON object where keys are Audible ASINs and values are the URL slugs for an internal website
    - asin: The Audible ASIN
    - title: The Audible book title

    If the ASIN is in the map already,
    return the map value.

    If not, convert the title to a slug.
    Strip punctuation and leading "the", put dashes between words, etc.
    Save the result to the map and return it.
    """
    raise NotImplementedError

def retrieve_cover(
    gbooks_volumes: pathlib.Path,
    gbooks_volid: str,
    asin: str,
    output: pathlib.Path
):
    """Retrieve a cover

    Download a cover image.
    """
    raise NotImplementedError

def enrich_audible_library(
    audible_library_metadata: pathlib.Path,
    audible_library_metadata_enriched: pathlib.Path,
):
    """Get information from all books in the Audible library

    params:
    - audible_library_metadata: A file populated by retrieve_audible_library()
    - audible_library_enriched: A file containing a JSON object where keys are Audible ASINs and values are objects containing
        - slug
        - gbooks_volid
        - openlibrary_id
        - isbn
        - book_asin: not an Audible ASIN, but the ASIN for a physical book from Amazon
        - skip: if true, ignore this book; set to false by default

    For each entry in the Audible library,
    ensure it has a value for each enriched property
    (unless it is marked as 'skip').
    If a value is present, leave it as is.
    If a value is not present or null,
    attempt to populate it with the other functions in this project.
    If any of the functions raise exceptions or return empty,
    set the value to null.
    """
    raise NotImplementedError

def populate_books_from_audible(
    audible_library_metadata: pathlib.Path,
    audible_library_metadata_enriched: pathlib.Path,
    gbooks_volumes: pathlib.Path,
    isbn2olid_map: pathlib.Path,
    book_slug_root: pathlib.Path,
):
    """Retrieve metadata and cover image for all books in Audible library

    Iterate over the enriched metadata.
    For each property that is not marked as skipped,
    ensure it has a directory created as book_slug_root / slug.

    Ensure a cover exists in that directory as "cover.jpg" (or whatever file extension is appropriate).

    Ensure a JSON file called "book.json" is created in the directory,
    and that each of these properties is populated in that file:
    - title: str
    - authors: list[str]
    - published: year like YYYY or date like YYYY-MM-DD
    - isbn: number
    - links:
        - metadata:
            - openlibrary: url
            - googlebooks: url
        - affiliate:
            - amazon: url for the physical book from amazon_browser_search
            - audible: url
        - other: a list of dict like {title: str, url: str} containing wikipedia URLs etc

    Make sure to update surgically.
    E.g. if the links google books link is not yet populated,
    but the affiliate links are populated,
    do nto overwrite (or re-check) the affiliate links,
    just try to get the google books link.
    """

def ingest_kindle_library(
    kindle_library_metadata: pathlib.Path,
    export_json: pathlib.Path,
):
    """Ingest a Kindle library export.

    Use terrible hack based on <https://joeldare.com/export-your-kindle-library.html>.

    Merge the new JSON into the old.
    Overwrite any existing keys,
    but don't delete any old keys that aren't in the new export.

    The format is a JSON object where the keys are the Kindle ASIN
    and the values are:
    - title: str
    - authors: list[str]
    """
    raise NotImplementedError

def enrich_kindle_library(
    kindle_library_metadata: pathlib.Path,
    kindle_library_enriched: pathlib.Path,
):
    """Enrich Kindle library

    params:
    - kindle_library_metadata: A file populated by ingest_kindle_library()
    - kindle_library_enriched: A file containing a JSON object where keys are Kindle ASINs and values are objects containing
        - slug
        - gbooks_volid
        - openlibrary_id
        - isbn
        - book_asin: not the Kindle ASIN, but the ASIN for a physical book from Amazon
        - skip: if true, ignore this book; set to false by default

    For each entry in the Kindle library,
    ensure it has a value for each enriched property
    (unless it is marked as 'skip').
    If a value is present, leave it as is.
    If a value is not present or null,
    attempt to populate it with the other functions in this project.
    If any of the functions raise exceptions or return empty,
    set the value to null.
    """
    raise NotImplementedError

def parseargs(
    arguments: list[str]
):
    """Parse arguments for this program
    """

def main():
    """A main function for this program
    """
```