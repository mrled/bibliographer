# Book sources

How to ingest books of different types

## Audible books

* Script to pull directly from Audible
    * Use Python `audible` package to retrieve my Audible library
    * Google Books API title/author/cover
    *

## Kindle books

* Get CSV of titles, authors, and ASINs from the awful `read.amazon.com` hack
* Script to ingest CSV
    * Get cover from ASIN
    * Google Books API title/author, get first candidate

## Libro.fm books

* Script to ingest from Libro.fm directly
    * Reimplement enough of the Java libro.fm downloader to get the metadata for purchased books
    * Google Books API title/author, get first candidate
    * OpenLibrary for ASIN and Cover

## Physical books (batch)

* Scan with BookBuddy?
    <https://www.kimicoapps.com/bookbuddy>
    Exports to CSV supposedly
* Script to ingest BookBuddy CSV
    * Google Books API title/author from ISBN
    * OpenLibrary for ASIN and Cover

## New physical books (one at a time)

* Manually get ASIN from amazon.com
* Pass in title and author manually
* Get cover from ASIN
* Google Books API title/author
