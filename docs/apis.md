# Book APIS

* OpenLibrary
    * Lots of data
    * Free, no key required
    * Low quality data, e.g. covers for the wrong language, incorrect publish date, etc
    * Metadata includes covers, title, list of ISBNs, sometimes Internet Archive link, sometimes ASIN or Amazon Store link,
      sometimes author web page / wikipedia links, etc.
* Google Books API requires a free key and works better.
    * Search provides a list of partial matches
    * Simple: `https://www.googleapis.com/books/v1/volumes?q=URL%20Encoded%20Title&key=FreeGoogleBooksApiKey`
    * Title and author:
        `https://www.googleapis.com/books/v1/volumes?q=intitle:Some+Keywords&inauthor:Author+Name&key=FreeGoogleBooksApiKey`
    * ISBN: `https://www.googleapis.com/books/v1/volumes?q=isbn:9781250261564&key=FreeGoogleBooksApiKey`.
      Does not know about Libro.fm ISBNs from my spot checking.
    * The search provides cover thumbnails, but not high quality covers, but the direct volume ID sometimes does.
      `https://www.googleapis.com/books/v1/volumes/VOLUMEID?fields=id,volumeInfo(title,imageLinks)&key=FreeGoogleBooksApiKey`
      Apparently this is unreliable tho.
* Amazon Product Advertising API only returns Amazon results
    * Unclear if this will work for longer than 30 days if I'm not referring actual sales
    * Product details from ASIN
      <https://webservices.amazon.com/paapi5/documentation/use-cases/localized-product-details.html>: product details from
       * Will not return ISBN, will return a title
    * ISBN to ASIN
      <https://webservices.amazon.com/paapi5/documentation/use-cases/search-with-external-identifiers.html>
* Amazon Store search/link generation (without API or scraping)
    * `https://audible.com/pd/ASIN` for Audible books
    * `https://amazon.com/pd/ASIN` for other books -- will 404 for Audible titles
    * `https://amazon.com/s?k=Anything+Here` for generic search
    * `https://amazon.com/s?k=ISBN` for ISBN search, returning a results page with a single product listed
      (but doesn't go directly to a product page)
    * `https://images-na.ssl-images-amazon.com/images/P/[ASIN].jpg` to get a product image.
      Not sure if this works for Audible books, but seems to generally work for ASINs for Amazon.com products, including books
* LibraryThing has some simple offerings
    * Free, requires account
    * <https://www.librarything.com/developer/documentation/thingapis>
    * The thingISBN endpoint does know the Libro.fm ISBN that I spot-checked.
    * It's apparently all user-determined, so there could be errors. I wonder how it compares to OpenLibrary.
    * It returns JUST a list of ISBNs. (In XML, lol.)
    * In my spot checking, the first in the list was generally pretty old / generic,
      like the first paperback or hardcover release of the book.
      Not sure how reliable that's going to be though.
* Libation desktop app for liberating Audible books
    * Includes title, author, and ASIN
    * Includes cover, but of the audiobook
* Official Kindle app for macOS
    * Covers for all books (even undownloaded ones)
      `~/Library/Containers/com.amazon.Lassen/Data/Library/Caches/covers`
    * Books are downloaded to `~/Library/Containers/com.amazon.Lassen/Data/Library/eBooks`,
      encrypted and without any info, even a title in the filesystem.
    * Could use Calibre and DeDRM to liberate them, but there is no automated way to do that.
* Kindle Web <https://read.amazon.com>
    * This awful hack: https://joeldare.com/export-your-kindle-library.html
* <libro.fm>
    * Can look up ISBNs that are in their catalog only
    * Trick found via this library <https://github.com/library-pals/isbn/blob/main/src/providers/librofm.js>
    * Retrieve `https://libro.fm/audiobooks/<ISBN>`, where the ISBN has had all dashes removed.
    * Find `<script type="application/ld+json">` tag which has JSON data for the audiobook,
      including title, authors, readers, the cover image
    * This claims to be able to download books directly <https://github.com/burntcookie90/librofm-downloader/tree/main>
    * Auth with oauth and then pull `https://libro.fm/user/library`, the list of all their books?
      That would get ISBNs that could be looked up directly on Libro.fm, including correct title/authors.
      Probably gets paginated at a certain size, but that's not the case for me.
* Scraping Amazon
    * Noah says this is painful, but not at my scale. (They do it at work lol.)
    * Curl has to pass the right headers but this works at least for a few requests in my tests:
      `curl --compressed -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: en-US,en;q=0.5' -H 'Accept-Encoding: gzip, deflate, br, zstd' -H 'DNT: 1' -H 'Sec-GPC: 1' -H 'Connection: keep-alive' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: none' -H 'Sec-Fetch-User: ?1' -H 'Priority: u=0, i'         $URL`
    * ISBN lookup: `https://www.amazon.com/s?k=ISBN`.
      In very limited testing, for valid ISBNs, that returns a page containing a single entry with
      `<div role="listitem" data-asin="0330375474"`.
      There are other instances of `data-asin`, but they are all empty.
      That ASIN might link to
    * Audible ASIN lookup: `https://audible.com/pd/ASIN` for Audible books
    * Amazon ASIN lookup: `https://amazon.com/pd/ASIN` for books sold on Amazon.com
    * Doesn't know all ISBNs, e.g. Libro.fm ISBNs return 404
* The `audible` Python package supports querying the private Audible API from Python
    * <https://audible.readthedocs.io/en/latest/intro/getting_started.html>
