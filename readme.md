# bibliographer

`bibliographer` is a Python program to compile a list of books you've read.

It's designed to pull your reading library from Audible and Kindle,
enrich those libraries with metadata like ISBN, book covers, and Wikipedia links,
and save the results to individual JSON files for use by other programs.
For instance, it retrieves the data for the
[`/books` section of my website](https://me.micahrl.com/books).

Right now, there are some mild assumptions that the consumer is a Hugo static site,
but it can be used generically too,
and work is ongoing to improve this.

## Features

> [!CAUTION]
> Retrieving your Audible library via this program relies on the
> [audible](https://github.com/mkb79/Audible) Python package
> and may violate Amazon's terms of service.
> It also saves your Audible credentials in plain text to your filesystem,
> by default in a file called `./.bibliographer-audible-auth-INSECURE.json`.

> [!CAUTION]
> Retrieving ASINs (Amazon product IDs) via this program scrapes `https://amazon.com`
> which may violate Amazon's terms of service.

> [!NOTE]
> Retrieving your Kindle library requires logging in to <https://read.amazon.com>
> and running some JavaScript in the web console,
> which cannot be done for you automatically and is a bit user-unfriendly
> but probably(?) doesn't violate Amazon's terms of service.

- Library ingestion
  - Automatically pull your library from Audible,
    which requires your username, password, and 2 factor OTP
  - Parse your library from Kindle,
    which requires you to generate it by logging in to <https://read.amazon.com>
    and running some code in the web dev tools
  - Add books one by one
- Retrieve metadata on books
  - Pull cover images from Google Books
  - Look up ISBN from title/authors
  - Find Wikipedia pages for title/authors
  - Find Amazon product pages from ISBN or title/author
- Cache API results;
  once a result is retrieved, its cached in a JSON file designed to be retained
  (committed to git, etc)
- Allow manual changes
  - Metadata retrieval isn't perfect;
    you can edit JSON files to change the mapping of books in your library
    to metadata from external APIs,
    and this will be retained on subsequent runs of the program
- Save metadata to a JSON file for use by other programs like static site generators etc

## Installing

I recommend [uv](https://github.com/astral-sh/uv) for this,
but it should work with regular pip as well.

```sh
# With uv
uv pip install git+https://github.com/username/repository.git

# With pip
pip install git+https://github.com/mrled/bibliographer.git
```

### Installing for development

In theory there's nothing uv-specific about the code,
but only uv is tested.
Clone the repo, and then:

```python
uv add --dev .
. .venv/bin/activate
```


## Usage examples

### Simple usage with Audible

Without any other configuration, this will:

* Prompt you to log in to your Audible account
* Retrieve your Audible library
* Retrieve metadata from various APIs like OpenLibrary
* Save your Audible library to `bibliographer_data/apicache/audible_library_metadata.json`
* Populate some mapping files in `bibliographer_data/apicache`:
  * `audible_library_metadata_enriched.json`: to save enriched data about your books
  * `isbn2olid_map.json`: to map your books to OpenLibrary IDs
  * `search2asin.json`: to find an ASIN on Amazon.com for your books
  * `wikipedia_relevant.json`: to contain a list of relevant Wikipedia pages
* Create a slug directory inside `./books` for each book based on its title,
  like `./books/getting-things-done`.
  The slug can be configured inside `audible_library_metadata_enriched.json`.
* Create a `cover.jpg` (or `.png` etc) inside each slug directory
* Create a `bibliographer.json` file containing enriched metadata inside each slug directory

```sh
# Retrieve library from Audible
bibliographer audible

# Populate bibliographer.json metadata files
bibliograhper populate
```

### Simple usage with Kindle

`bibliographer` doesn't currently support retrieving the Kindle library automatically.
Instead, you must log in to your Kindle account in a web browser,
run some JavaScript in the browser's developer tools,
copy the output,
and provide it to `bibliographer` yourself.

1.  Log into <https://read.amazon.com> in a web browser where you have access to the developer tools.
    This has been tested most extensively in Firefox.
2.  Open the JavaScript console in Developer Tools.
    In FireFox on macOS, this means
    Tools -> Browser Tools -> Web Developer Tools,
    then select the Console tab.
3.  Copy and paste the contents of [`exportKindleLibrary.js`](./docs/exportKindleLibrary.js).
    Run it by pressing <kbd>`Return`</kbd>
4.  That will download a file called `kindle-library.json`.

Now ingest the data and populate the `bibliographer.json` metadata files with:

```sh
bibliographer kindle ingest /path/to/kindle-library.json
bibliographer populate
```

### Changing settings in usermappings

The usermappings directory is populated based on some heuristic queries,
but you may want to override these.
After enriching book metadata,
you should always check that these heuristics found the correct data for your books.

For instance, the book
[Blackletter: Type and National Identity](https://me.micahrl.com/books/blackletter-type-and-national-identity)
is by design historian [Paul Shaw](https://en.wikipedia.org/wiki/Paul_Shaw_%28design_historian%29),
but Wikipedia knows [several people](https://en.wikipedia.org/wiki/Paul_Shaw)
by that name and may have returned the disambiguation page or one of the other individuals.
To fix that, you can edit the `bibliographer_data/apicache/wikipedia_relevant.json` file
to point to the correct Paul Shaw.

```json
{
  // ...
  "title=Blackletter: Type and National Identity;authors=Peter Bain|Paul Shaw": {
    "Paul Shaw": "https://en.wikipedia.org/wiki/Paul_Shaw_(design_historian)"
  },
  // ...
}
```

### Using with Hugo

When using with Hugo,
it's useful to set a config file in the Hugo repository root.

```text
hugosite/
  content/
    books/
      getting-things-done/
        index.md
        bibliographer.json
        cover.jpg
      ...
  hugo.toml
  bibliographer.toml
  bibliographer_data/
    apicache/
      audible_library_metadata.json
      ...
    usermappings/
      audible_library_metadata_enriched.json
      ...
```

You might set the `bibliographer.toml` config file like:

```toml
book_slug_root = "content/books"
```

And run the program like:

```sh
# Inside the hugosite directory, bibliographer will find the bibliographer.toml automatically
cd hugosite/
# Now run it as normal
bibliographer audible
bibliograhper populate
```

It'll create book slug directories inside of `content/books`,
ready to be picked up by your Hugo site.

### Example Hugo templates

If you have a Hugo site as described above,
with `content/books/` as your `book_slug_root`,
you can make a Hugo layout file in e.g. `layouts/books/single.html`
that will generate book pages.
Here's a simple example:

Your Hugo templates can get the JSON data and cover files like this:

```go-html-template
{{- define "main" }}

<section class="book-metadata">

  {{ $coverImg := (index (where (.Resources.Match "cover.*") "ResourceType" "in" (slice "image" "image/jpg" "image/jpeg" "image/png" "image/gif" "image/webp")) 0) }}
  <img src="{{ $coverImg.RelPermalink }}">

  <dl class="public-book-metadata">
    <dt>Author</dt>
    <dd>{{ delimit $book.authors ", " }}</dd5>

    {{ with $book.isbn }}
    <dt>ISBN</dt>
    <dd>{{ . }}</dd>
    {{ end }}

    {{- with $book.links }}
    <dt>Book Data</dt>
    <dd>
      <ul>
        {{ with .metadata.openlibrary }}<li><a href="{{ . }}">Open Library</a></li>{{ end }}
        {{ with .metadata.googlebooks }}<li><a href="{{ . }}">Google Books</a></li>{{ end }}
      </ul>
    </dd>

    {{- if gt (len .other) 0 }}
    <dt>Elsewhere</dt>
    <dd>
      <ul>
        {{- range .other }}
        <li><a href="{{ .url }}">{{ .title }}</a></li>
        {{- end }}
      </ul>
    </dd>
    {{ end }}

    {{ end }}
  </dl>

</section>

<section>
  {{ .Content }}
</section>

{{- end }
```

### Example output `bibliographer.json` file

Running `bibliographer populate` will create a file called `bibliographer.json` for each book in your library.
That file looks like this:

```json
{
  "title": "Getting Things Done",
  "authors": [
    "David Allen"
  ],
  "isbn": "9780143126560",
  "purchase_date": null,
  "read_date": "2024-11-01",
  "published": null,
  "links": {
    "metadata": {
      "openlibrary": "https://openlibrary.org/books/OL26211544M"
    },
    "affiliate": {
      "amazon": "https://www.amazon.com/dp/0143126563"
    },
    "other": [
      {
        "title": "Getting Things Done - Wikipedia",
        "url": "https://en.wikipedia.org/wiki/Getting_Things_Done"
      },
      {
        "title": "David Allen - Wikipedia",
        "url": "https://en.wikipedia.org/wiki/David_Allen"
      }
    ]
  }
}
```

### The `bibliographer.toml` config file

Some command-line arguments can be set in a configuration file so you don't need to pass them at runtime.
`bibliographer` looks for a file called `bibliographer.toml` or `.bibliographer.toml`
in the runtime `$PWD` and all of its parents,
or you can pass it explicitly with `--config`.

The options in the config file correspond to command-line options,
and are shown below in the program help output.

File paths specified in the config file can be absolute,
or relative _to the directory containing the config file_.

<!--[[[cog
import cog
from bibliographer.cli.bibliographer import get_example_config
cog.out(f"```toml\n{get_example_config()}```\n")
]]]-->
```
debug = false
verbose = false
google_books_key = ""
book_slug_root = "books"
audible_login_file = ".bibliographer-audible-auth-INSECURE.json"
bibliographer_data = "bibliographer_data"
```
<!--[[[end]]]-->

### API cache files

Results from external APIs are stored in `{bibliographer_data}/apicache/*.json` files.
These files are not inteded to be edited by hand.
Currently these files include:

* `audible_library_metadata.json`
* `kindle_library_metadata.json`
* `gbooks_volumes.json`

### User mapping files

Mapping of IDs and search queries from various sources to specific API results
are stored in `{bibliographer_data}/usermappings/*.json` files.
These **are** intended to be edited by hand.
Currently these files include:

* `asin2gbv_map.json`:
  Mapping ASINs (Amazon product IDs used by Kindle and Audible) to Google Books volume IDs
* `isbn2olid_map.json`:
  Mapping ISBNs to OpenLibrary IDs
* `search2asin.json`:
  Mapping a search term, which might be an ISBN or a title + author, to ASIN
* `wikipedia_relevant.json`:
  Mapping a search time, like a title or an author, to a Wikipedia page
* `audible_library_metadata_enriched.json`:
  "Enriched" data for the Audible library, including the Audible ASIN as a key,
  and an object with ISBN, links, etc as a value.
* `kindle_library_metadata_enriched.json`:
  "Enriched" data for the Kindle library,
  including the Kindle ASIN as a key,
  and an object with ISBN, links, etc as a value.
* `manual.json`:
  A manual library with books added directly on the command line from
  `bibliographer manual add ...`

## Program help

<!--[[[cog
import cog
from bibliographer.cli.bibliographer import get_help_string
cog.out(f"```\n{get_help_string()}```\n")
]]]-->
```
> bibliographer --help
usage: cog [-h] [-D] [-c CONFIG] [-v] [-b BIBLIOGRAPHER_DATA]
           [-s BOOK_SLUG_ROOT] [-a AUDIBLE_LOGIN_FILE] [-g GOOGLE_BOOKS_KEY]
           {populate,audible,kindle,googlebook,amazon,manual,cover} ...

Manage Audible/Kindle libraries, enrich them, and populate local book repos.

positional arguments:
  {populate,audible,kindle,googlebook,amazon,manual,cover}
    populate            Populate bibliographer.json files
    audible             Audible operations
    kindle              Kindle operations
    googlebook          Operate on Google Books data
    amazon              Amazon forced re-scrape
    manual              Manage manually-entered books
    cover               Cover operations

options:
  -h, --help            show this help message and exit
  -D, --debug           Drop into an interactive debugger on unhandled
                        exceptions.
  -c CONFIG, --config CONFIG
                        Path to TOML config file, defaulting to a file called
                        .bibliographer.toml in the repo root
  -v, --verbose         Enable verbose logging of API calls.
  -b BIBLIOGRAPHER_DATA, --bibliographer-data BIBLIOGRAPHER_DATA
                        Defaults to ./bibliographer_data
  -s BOOK_SLUG_ROOT, --book-slug-root BOOK_SLUG_ROOT
                        Defaults to ./books
  -a AUDIBLE_LOGIN_FILE, --audible-login-file AUDIBLE_LOGIN_FILE
                        Defaults to ./.bibliographer-audible-auth-INSECURE.json
  -g GOOGLE_BOOKS_KEY, --google-books-key GOOGLE_BOOKS_KEY
                        Google Books API key

________________________________________________________________________

> bibliographer populate --help
usage: cog populate [-h]

Populate bibliographer.json files

options:
  -h, --help  show this help message and exit

________________________________________________________________________

> bibliographer audible --help
usage: cog audible [-h] {retrieve} ...

Audible operations

positional arguments:
  {retrieve}
    retrieve  Retrieve the Audible library

options:
  -h, --help  show this help message and exit

________________________________________________________________________

> bibliographer audible retrieve --help
usage: cog audible retrieve [-h]

Retrieve the Audible library

options:
  -h, --help  show this help message and exit

________________________________________________________________________

> bibliographer kindle --help
usage: cog kindle [-h] {ingest} ...

Kindle operations

positional arguments:
  {ingest}
    ingest    Ingest a new Kindle library export JSON

options:
  -h, --help  show this help message and exit

________________________________________________________________________

> bibliographer kindle ingest --help
usage: cog kindle ingest [-h] export_json

Ingest a new Kindle library export JSON

positional arguments:
  export_json  Path to the Kindle library export JSON

options:
  -h, --help   show this help message and exit

________________________________________________________________________

> bibliographer googlebook --help
usage: cog googlebook [-h] {requery} ...

Operate on Google Books data

positional arguments:
  {requery}
    requery   Overwrite the local Google Books cache for a volume ID

options:
  -h, --help  show this help message and exit

________________________________________________________________________

> bibliographer googlebook requery --help
usage: cog googlebook requery [-h] volume_ids [volume_ids ...]

Overwrite the local Google Books cache for a volume ID

positional arguments:
  volume_ids  One or more volume IDs to re-download

options:
  -h, --help  show this help message and exit

________________________________________________________________________

> bibliographer amazon --help
usage: cog amazon [-h] {requery} ...

Amazon forced re-scrape

positional arguments:
  {requery}
    requery   Force re-scrape for one or more search terms.

options:
  -h, --help  show this help message and exit

________________________________________________________________________

> bibliographer amazon requery --help
usage: cog amazon requery [-h] searchterms [searchterms ...]

Force re-scrape for one or more search terms.

positional arguments:
  searchterms  Search terms to re-scrape from Amazon

options:
  -h, --help   show this help message and exit

________________________________________________________________________

> bibliographer manual --help
usage: cog manual [-h] {add} ...

Manage manually-entered books

positional arguments:
  {add}
    add       Add a manually-entered book

options:
  -h, --help  show this help message and exit

________________________________________________________________________

> bibliographer manual add --help
usage: cog manual add [-h] [--title TITLE] [--authors AUTHORS [AUTHORS ...]]
                      [--isbn ISBN] [--purchase-date PURCHASE_DATE]
                      [--read-date READ_DATE] [--slug SLUG]

Add a manually-entered book

options:
  -h, --help            show this help message and exit
  --title TITLE         Book title
  --authors AUTHORS [AUTHORS ...]
                        Authors (allows multiple)
  --isbn ISBN           ISBN if known
  --purchase-date PURCHASE_DATE
                        Purchase date if any (YYYY-MM-DD)
  --read-date READ_DATE
                        Read date if any (YYYY-MM-DD)
  --slug SLUG           Slug for URL (set to a slugified title by default)

________________________________________________________________________

> bibliographer cover --help
usage: cog cover [-h] {set} ...

Cover operations

positional arguments:
  {set}
    set       Set a cover image

options:
  -h, --help  show this help message and exit

________________________________________________________________________

> bibliographer cover set --help
usage: cog cover set [-h] slug url

Set a cover image

positional arguments:
  slug        Book slug
  url         URL for a cover image

options:
  -h, --help  show this help message and exit
```
<!--[[[end]]]-->
