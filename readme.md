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
> You must configure `audible_auth_password_cmd` to set an encryption password
> for the Audible credentials file.

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
  - Automatically pull your library from Libro.fm,
    which requires your username and password
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
uvx bibliographer --help

# With pip
pip install bibliographer
bibliographer --help
```

### Installing for development

In theory there's nothing uv-specific about the code,
but only uv is tested.
Clone the repo, and then:

```sh
uv add --dev .[dev]
. .venv/bin/activate
```

`bibliographer` supports the `--debug`/`-D` flag
which will drop you into the debugger on any unhandled exception.

```sh
bibliographer -D ...
```

## `bibliograhper` versioning

We follow [Pride Versioning](https://pridever.org/).

You can't expect [real stability](https://semver.org/)
because the most important APIs we use are ~~user-hostile~~undocumented,
so we might as well have fun.

## Usage examples

### Simple usage with Audible

Without any other configuration, this will:

* Prompt you to log in to your Audible account
* Retrieve your Audible library
* Retrieve metadata from various APIs like OpenLibrary
* Save your Audible library to `bibliographer/data/apicache/audible_library_metadata.json`
* Populate some mapping files in `bibliographer/data/usermaps`:
  * `audible_library_metadata_enriched.json`: to save enriched data about your books
  * `isbn2olid_map.json`: to map your books to OpenLibrary IDs
  * `search2asin.json`: to find an ASIN on Amazon.com for your books
  * `wikipedia_relevant.json`: to contain a list of relevant Wikipedia pages
* Create a slug directory inside `bibliographer/books` for each book based on its title,
  like `bibliographer/books/getting-things-done`.
  The slug can be configured inside `audible_library_metadata_enriched.json`.
* Create a `cover.jpg` (or `.png` etc) inside each slug directory
* Create a `bibliographer.json` file containing enriched metadata inside each slug directory

```sh
# Retrieve library from Audible
bibliographer audible

# Populate bibliographer.json metadata files
bibliograhper populate
```

### Simple usage with libro.fm

```sh
# Retrieve library from Libro.fm
bibliographer --librofm-username you@example.com --librofm-password p@ssw0rd librofm retrieve

# Populate bibliographer.json metadata files
bibliographer populate
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

### Logging

Passing the `--verbose`/`-v` flag provides detailed log messages.
If you're ingesting more than a handful of books at a time,
it's nice to do this to know that the process hasn't gotten stuck.

```sh
bibliographer -v ...
```

### Changing settings in usermaps

The usermaps directory is populated based on some heuristic queries,
but you may want to override these.
After enriching book metadata,
you should always check that these heuristics found the correct data for your books.

For instance, the book
[Blackletter: Type and National Identity](https://me.micahrl.com/books/blackletter-type-and-national-identity)
is by design historian [Paul Shaw](https://en.wikipedia.org/wiki/Paul_Shaw_%28design_historian%29),
but Wikipedia knows [several people](https://en.wikipedia.org/wiki/Paul_Shaw)
by that name and may have returned the disambiguation page or one of the other individuals.
To fix that, you can edit the `bibliographer/data/apicache/wikipedia_relevant.json` file
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
  assets/
    bibliographer/
      apicache/
        audible_library_metadata.json
        ...
      usermaps/
        audible_library_metadata_enriched.json
        ...
  content/
    books/
      getting-things-done/
        index.md
        bibliographer.json
        cover.jpg
      ...
  bibliographer.toml
  hugo.toml
```

You might set the `bibliographer.toml` config file like:

```toml
google_books_key = "your-google-books-key"
bibliographer_data_root = "assets/bibliographer"
default_slug_root = "content/books"
individual_bibliographer_json = true
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
with `content/books/` as your `default_slug_root`,
you can make a Hugo layout file in e.g. `layouts/books/single.html`
that will generate book pages.
Here's a simple example:

Your Hugo templates can get the JSON data and cover files like this:

```go-html-template
{{- define "main" }}

<section class="book-metadata">

  {{ $coverImg := (index (where (.Resources.Match "cover.*") "ResourceType" "in" (slice "image" "image/jpg" "image/jpeg" "image/png" "image/gif" "image/webp")) 0) }}
  <img src="{{ $coverImg.RelPermalink }}">

  {{ $book := .Resources.Get "bibliographer.json" | transform.Unmarshal }}
  <dl class="public-book-metadata">
    <dt>Author</dt>
    <dd>{{ delimit $book.authors ", " }}</dd5>

    {{ with $book.isbn }}
    <dt>ISBN</dt>
    <dd>{{ . }}</dd>
    {{ end }}

    <dt>Book Data</dt>
    <dd>
      <ul>
        {{ with $book.openlibrary_id }}<li><a href="https://openlibrary.org/books/{{ . }}">Open Library</a></li>{{ end }}
        {{ with $book.gbooks_volid }}<li><a href="https://books.google.com/books?id={{ . }}">Google Books</a></li>{{ end }}
      </ul>
    </dd>

    {{- if and $book.urls_wikipedia (gt (len $book.urls_wikipedia) 0) }}
    <dt>Elsewhere</dt>
    <dd>
      <ul>
        {{ range $title, $url := $book.urls_wikipedia }}
        <li><a href="{{ $url }}">{{ $title }} - Wikipedia</a></li>
        {{- end }}
      </ul>
    </dd>
    {{ end }}
  </dl>

</section>

<section>
  {{ .Content }}
</section>

{{- end }}
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
from bibliographer.config import get_example_config
cog.out(f"```toml\n{get_example_config()}```\n")
]]]-->
```toml
version = "2.3"

debug = false
verbose = false
google_books_key = ""
google_books_key_cmd = ""
audible_auth_password = ""
audible_auth_password_cmd = ""
librofm_username = ""
librofm_password = ""
librofm_password_cmd = ""
raindrop_token = ""
raindrop_token_cmd = ""
individual_bibliographer_json = false
default_slug_root = "bibliographer/books"
audible_login_file = ".bibliographer-audible-auth.json"
bibliographer_data_root = "bibliographer/data"
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
are stored in `{bibliographer_data}/usermaps/*.json` files.
These **are** intended to be edited by hand.
Currently these files include:

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

### Generating and saving a Google Books API Key

See the [Google Books API documentation](https://developers.google.com/books/docs/v1/using)
for information on obtaining and using an API key.

You can pass it in or save it directly with `--google-books-key`,
and you can also use the `google_books_key_cmd` config file option (or command line argument)
to provide a command to retrieve the key from a password manager.
For instance, if you have a 1Password entry called `GoogleBooksApi`
that has a field called `bibliographer-google-books-api-key`,
you might set this in `bibliographer.toml`:

```toml
google_books_key_cmd = "op item get GoogleBooksApi --field label=bibliographer-google-books-api-key"
```

This way you can safely store your config file in git without committing any secrets in plain text.

You can also set the key directly in `bibliographer.toml` if you prefer:

```toml
google_books_key = "your key goes here"
```

## Future

* Goodreads support mrled/bibliographer#11
* Support other site generators besides Hugo generically mrled/bibliographer#4

Please comment on the above issues to register your interest,
or open a new one if there are other services that would be helpful.

## Program help

<!--[[[cog
import cog
from bibliographer.cli.bibliographer import get_help_string
cog.out(f"```text\n{get_help_string()}```\n")
]]]-->
```text
> bibliographer --help
usage: bibliographer [-h] [-D] [-c CONFIG] [-v] [-i]
                     {populate,audible,kindle,googlebook,amazon,librofm,raindrop,add,slug,cover,version,help-file-paths,help-services} ...

Manage Audible/Kindle libraries, enrich them, and populate local book repos.

positional arguments:
  {populate,audible,kindle,googlebook,amazon,librofm,raindrop,add,slug,cover,version,help-file-paths,help-services}
    populate            Populate bibliographer.json files
    audible             Audible operations
    kindle              Kindle operations
    googlebook          Operate on Google Books data
    amazon              Amazon forced re-scrape
    librofm             Libro.fm operations
    raindrop            Raindrop.io operations
    add                 Add works to the library
    slug                Manage slugs
    cover               Cover operations
    version             Show version information
    help-file-paths     Show data file path options
    help-services       Show service authentication options

options:
  -h, --help            show this help message and exit
  -D, --debug           Drop into an interactive debugger on unhandled
                        exceptions.
  -c, --config CONFIG   Path to TOML config file, defaulting to a file in any
                        parent directory called one of ['bibliographer.conf',
                        '.bibliographer.conf'].
  -v, --verbose         Enable verbose logging of API calls.
  -i, --individual-bibliographer-json
                        Write out each work to its own JSON file (in addition to
                        the combined bibliographer.json), under the appropriate
                        slug root/SLUG/bibliographer.json

________________________________________________________________________

> bibliographer populate --help
usage: bibliographer populate [-h] [--slug [SLUG ...]]

Populate bibliographer.json files

options:
  -h, --help         show this help message and exit
  --slug [SLUG ...]  Populate only specific books by slug (can specify multiple)

________________________________________________________________________

> bibliographer audible --help
usage: bibliographer audible [-h] {retrieve,credentials} ...

Audible operations

positional arguments:
  {retrieve,credentials}
    retrieve            Retrieve the Audible library
    credentials         Manage Audible credentials

options:
  -h, --help            show this help message and exit

________________________________________________________________________

> bibliographer audible retrieve --help
usage: bibliographer audible retrieve [-h]

Retrieve the Audible library

options:
  -h, --help  show this help message and exit

________________________________________________________________________

> bibliographer audible credentials --help
usage: bibliographer audible credentials [-h] {encrypt,decrypt} ...

Manage Audible credentials

positional arguments:
  {encrypt,decrypt}
    encrypt          Load unencrypted credentials and output to terminal
    decrypt          Load encrypted credentials and output to terminal

options:
  -h, --help         show this help message and exit

________________________________________________________________________

> bibliographer audible credentials encrypt --help
usage: bibliographer audible credentials encrypt [-h] source

Load unencrypted credentials and output to terminal

positional arguments:
  source      Path to unencrypted credentials file

options:
  -h, --help  show this help message and exit

________________________________________________________________________

> bibliographer audible credentials decrypt --help
usage: bibliographer audible credentials decrypt [-h] source

Load encrypted credentials and output to terminal

positional arguments:
  source      Path to encrypted credentials file

options:
  -h, --help  show this help message and exit

________________________________________________________________________

> bibliographer kindle --help
usage: bibliographer kindle [-h] {ingest} ...

Kindle operations

positional arguments:
  {ingest}
    ingest    Ingest a new Kindle library export JSON

options:
  -h, --help  show this help message and exit

________________________________________________________________________

> bibliographer kindle ingest --help
usage: bibliographer kindle ingest [-h] export_json

Ingest a new Kindle library export JSON

positional arguments:
  export_json  Path to the Kindle library export JSON

options:
  -h, --help   show this help message and exit

________________________________________________________________________

> bibliographer googlebook --help
usage: bibliographer googlebook [-h] {requery} ...

Operate on Google Books data

positional arguments:
  {requery}
    requery   Overwrite the local Google Books cache for a volume ID

options:
  -h, --help  show this help message and exit

________________________________________________________________________

> bibliographer googlebook requery --help
usage: bibliographer googlebook requery [-h] volume_ids [volume_ids ...]

Overwrite the local Google Books cache for a volume ID

positional arguments:
  volume_ids  One or more volume IDs to re-download

options:
  -h, --help  show this help message and exit

________________________________________________________________________

> bibliographer amazon --help
usage: bibliographer amazon [-h] {requery} ...

Amazon forced re-scrape

positional arguments:
  {requery}
    requery   Force re-scrape for one or more search terms.

options:
  -h, --help  show this help message and exit

________________________________________________________________________

> bibliographer amazon requery --help
usage: bibliographer amazon requery [-h] searchterms [searchterms ...]

Force re-scrape for one or more search terms.

positional arguments:
  searchterms  Search terms to re-scrape from Amazon

options:
  -h, --help   show this help message and exit

________________________________________________________________________

> bibliographer librofm --help
usage: bibliographer librofm [-h] {retrieve} ...

Libro.fm operations

positional arguments:
  {retrieve}
    retrieve  Retrieve the Libro.fm library

options:
  -h, --help  show this help message and exit

________________________________________________________________________

> bibliographer librofm retrieve --help
usage: bibliographer librofm retrieve [-h]

Retrieve the Libro.fm library

options:
  -h, --help  show this help message and exit

________________________________________________________________________

> bibliographer raindrop --help
usage: bibliographer raindrop [-h] {highlights} ...

Raindrop.io operations

positional arguments:
  {highlights}
    highlights  Raindrop.io highlights operations

options:
  -h, --help    show this help message and exit

________________________________________________________________________

> bibliographer raindrop highlights --help
usage: bibliographer raindrop highlights [-h] {retrieve} ...

Raindrop.io highlights operations

positional arguments:
  {retrieve}
    retrieve  Retrieve all highlights from Raindrop.io

options:
  -h, --help  show this help message and exit

________________________________________________________________________

> bibliographer raindrop highlights retrieve --help
usage: bibliographer raindrop highlights retrieve [-h]

Retrieve all highlights from Raindrop.io

options:
  -h, --help  show this help message and exit

________________________________________________________________________

> bibliographer add --help
usage: bibliographer add [-h] {book,article,podcast,video} ...

Add works to the library

positional arguments:
  {book,article,podcast,video}
    book                Add a book
    article             Add an article
    podcast             Add a podcast episode
    video               Add a video

options:
  -h, --help            show this help message and exit

________________________________________________________________________

> bibliographer add book --help
usage: bibliographer add book [-h] [--title TITLE]
                              [--authors AUTHORS [AUTHORS ...]] [--isbn ISBN]
                              [--purchase-date PURCHASE_DATE]
                              [--read-date READ_DATE] [--slug SLUG]

Add a book

options:
  -h, --help            show this help message and exit
  --title TITLE         Book title
  --authors AUTHORS [AUTHORS ...]
                        Authors (allows multiple)
  --isbn ISBN           ISBN if known
  --purchase-date PURCHASE_DATE
                        Purchase date if any (YYYY-MM-DD)
  --read-date READ_DATE
                        Read/consumed date if any (YYYY-MM-DD)
  --slug SLUG           Slug for URL (set to a slugified title by default)

________________________________________________________________________

> bibliographer add article --help
usage: bibliographer add article [-h] [--title TITLE]
                                 [--authors AUTHORS [AUTHORS ...]] [--url URL]
                                 [--publication PUBLICATION]
                                 [--purchase-date PURCHASE_DATE]
                                 [--read-date READ_DATE] [--slug SLUG]

Add an article

options:
  -h, --help            show this help message and exit
  --title TITLE         Article title
  --authors AUTHORS [AUTHORS ...]
                        Authors (allows multiple)
  --url URL             Article URL
  --publication PUBLICATION
                        Publication name (journal, blog, magazine)
  --purchase-date PURCHASE_DATE
                        Purchase/acquired date if any (YYYY-MM-DD)
  --read-date READ_DATE
                        Read date if any (YYYY-MM-DD)
  --slug SLUG           Slug for URL (set to a slugified title by default)

________________________________________________________________________

> bibliographer add podcast --help
usage: bibliographer add podcast [-h] [--title TITLE]
                                 [--authors AUTHORS [AUTHORS ...]] [--url URL]
                                 [--podcast-name PODCAST_NAME]
                                 [--episode-number EPISODE_NUMBER]
                                 [--purchase-date PURCHASE_DATE]
                                 [--listened-date LISTENED_DATE] [--slug SLUG]

Add a podcast episode

options:
  -h, --help            show this help message and exit
  --title TITLE         Episode title
  --authors AUTHORS [AUTHORS ...]
                        Hosts/authors (allows multiple)
  --url URL             Episode URL
  --podcast-name PODCAST_NAME
                        Name of the podcast
  --episode-number EPISODE_NUMBER
                        Episode number
  --purchase-date PURCHASE_DATE
                        Purchase/acquired date if any (YYYY-MM-DD)
  --listened-date LISTENED_DATE
                        Listened date if any (YYYY-MM-DD)
  --slug SLUG           Slug for URL (set to a slugified title by default)

________________________________________________________________________

> bibliographer add video --help
usage: bibliographer add video [-h] [--title TITLE]
                               [--authors AUTHORS [AUTHORS ...]] [--url URL]
                               [--purchase-date PURCHASE_DATE]
                               [--watched-date WATCHED_DATE] [--slug SLUG]

Add a video

options:
  -h, --help            show this help message and exit
  --title TITLE         Video title
  --authors AUTHORS [AUTHORS ...]
                        Creators (allows multiple)
  --url URL             Video URL
  --purchase-date PURCHASE_DATE
                        Purchase/acquired date if any (YYYY-MM-DD)
  --watched-date WATCHED_DATE
                        Watched date if any (YYYY-MM-DD)
  --slug SLUG           Slug for URL (set to a slugified title by default)

________________________________________________________________________

> bibliographer slug --help
usage: bibliographer slug [-h] {show,rename,regenerate} ...

Manage slugs

positional arguments:
  {show,rename,regenerate}
    show                Show what slug would be generated for a given title
    rename              Renamed a slug
    regenerate          Regenerate a slug

options:
  -h, --help            show this help message and exit

________________________________________________________________________

> bibliographer slug show --help
usage: bibliographer slug show [-h] title

Show what slug would be generated for a given title

positional arguments:
  title       Title to slugify

options:
  -h, --help  show this help message and exit

________________________________________________________________________

> bibliographer slug rename --help
usage: bibliographer slug rename [-h] old_slug new_slug

Renamed a slug

positional arguments:
  old_slug    Old slug
  new_slug    New slug

options:
  -h, --help  show this help message and exit

________________________________________________________________________

> bibliographer slug regenerate --help
usage: bibliographer slug regenerate [-h] [--interactive] slug

Regenerate a slug

positional arguments:
  slug               Slug to regenerate

options:
  -h, --help         show this help message and exit
  --interactive, -i  Prompt before taking any action

________________________________________________________________________

> bibliographer cover --help
usage: bibliographer cover [-h] {set,retrieve,list-missing} ...

Cover operations

positional arguments:
  {set,retrieve,list-missing}
    set                 Set a cover image
    retrieve            Retrieve cover images for all books that don't have them
    list-missing        List books missing cover images

options:
  -h, --help            show this help message and exit

________________________________________________________________________

> bibliographer cover set --help
usage: bibliographer cover set [-h] slug url

Set a cover image

positional arguments:
  slug        Book slug
  url         URL for a cover image

options:
  -h, --help  show this help message and exit

________________________________________________________________________

> bibliographer cover retrieve --help
usage: bibliographer cover retrieve [-h]

Retrieve cover images for all books that don't have them

options:
  -h, --help  show this help message and exit

________________________________________________________________________

> bibliographer cover list-missing --help
usage: bibliographer cover list-missing [-h]

List books missing cover images

options:
  -h, --help  show this help message and exit

________________________________________________________________________

> bibliographer version --help
usage: bibliographer version [-h]

Show version information

options:
  -h, --help  show this help message and exit

________________________________________________________________________

> bibliographer help-file-paths --help
usage: bibliographer help-file-paths [-h]

Data File Path Options
======================

These options allow you to override the default paths for data files.

Root Directories:
  -b, --bibliographer-data-root  Root directory for bibliographer data
                                 (default: ./bibliographer/data)
  -s, --default-slug-root        Default root directory for slug folders
                                 (default: ./bibliographer/books)
  --book-slug-root               Override slug root for books only
                                 (defaults to --default-slug-root)
  --article-slug-root            Override slug root for articles only
                                 (defaults to --default-slug-root)
  --podcast-slug-root            Override slug root for podcasts only
                                 (defaults to --default-slug-root)
  --video-slug-root              Override slug root for videos only
                                 (defaults to --default-slug-root)

API Cache Files:
  --audible-library-file       Path to Audible library metadata file
  --kindle-library-file        Path to Kindle library metadata file
  --gbooks-volumes-file        Path to Google Books volumes cache file
  --librofm-library-file       Path to Libro.fm library metadata file
  --raindrop-highlights-file   Path to Raindrop.io highlights cache file

User Map Files:
  --combined-library-file   Path to combined library file
  --audible-slugs-file      Path to Audible slugs mapping file
  --kindle-slugs-file       Path to Kindle slugs mapping file
  --librofm-slugs-file      Path to Libro.fm slugs mapping file
  --raindrop-slugs-file     Path to Raindrop.io URL to slug mapping file
  --isbn2olid-map-file      Path to ISBN to OpenLibrary ID mapping file
  --search2asin-file        Path to search term to ASIN mapping file
  --wikipedia-relevant-file Path to Wikipedia relevant pages file

These options can also be set in the config file.

options:
  -h, --help  show this help message and exit

________________________________________________________________________

> bibliographer help-services --help
usage: bibliographer help-services [-h]

Service Authentication Options
==============================

These options configure authentication for external services.

Audible:
  -a, --audible-login-file       Path to Audible credentials file
                                 (default: ./.bibliographer-audible-auth.json)
  --audible-auth-password        Password to encrypt/decrypt the Audible
                                 authentication file
  --audible-auth-password-cmd    Command to retrieve the Audible auth password
                                 (e.g. from a password manager)

Google Books:
  -g, --google-books-key         Google Books API key
  -G, --google-books-key-cmd     Command to retrieve the Google Books API key
                                 (e.g. from a password manager)

Libro.fm:
  --librofm-username             Libro.fm username (email address)
  --librofm-password             Libro.fm password
  --librofm-password-cmd         Command to retrieve the Libro.fm password
                                 (e.g. from a password manager)

Raindrop.io:
  --raindrop-token               Raindrop.io API access token
  --raindrop-token-cmd           Command to retrieve the Raindrop.io token
                                 (e.g. from a password manager)

These options can also be set in the config file.

options:
  -h, --help  show this help message and exit
```
<!--[[[end]]]-->
