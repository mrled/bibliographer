 /* exportKindleLibrary.js
 *
 * Adapted from <https://joeldare.com/export-your-kindle-library.html>
 *
 * Log in to read.amazon.com and run this script in the browser console.
 */

/* Fetch the Kindle library and return a list of books
 *
 * Returns a list of book objects in this format:
 * [
 *   {
 *     "asin": "B0030CVQ0S",
 *     "webReaderUrl": "https://read.amazon.com/?asin=B0030CVQ0S",
 *     "productUrl": "https://m.media-amazon.com/images/I/51Mnt7MOhgL._SY400_.jpg",
 *     "title": "Angelology: A Novel (Angelology Series Book 1)",
 *     "percentageRead": 0,
 *     "authors": [
 *       "Trussoni, Danielle:"
 *     ],
 *     "resourceType": "EBOOK",
 *     "originType": "PURCHASE",
 *     "mangaOrComicAsin": false
 *   }
 * ]
 *
 * Note that the authors field as an array,
 * but it appears to always contain a single element,
 * where each author's name is followed by a colon
 * (even when only one author is listed).
 * Here's an example of two authors from my library:
 *
 *   "authors": ["Turner, Brandon:Turner, Heather:"]
 */
function fetchKindleLibrary() {
  const items = [];

  function makeRequest(paginationToken = null) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();

      const urlComponents = [
        window.location.origin,
        '/kindle-library/search?query=&libraryType=BOOKS',
        paginationToken ? `&paginationToken=${paginationToken}` : '',
        "&sortType=acquisition_desc&querySize=50"
      ];
      const url = urlComponents.join('');

      xhr.open('GET', url, true);

      xhr.onreadystatechange = function() {
        if (xhr.readyState === 4) {
          if (xhr.status === 200) {
            try {
              const data = JSON.parse(xhr.responseText);
              if (data.itemsList) {
                items.push(...data.itemsList);
              }
              if (data.paginationToken) {
                makeRequest(data.paginationToken)
                  .then(() => resolve(items))
                  .catch(reject);
              } else {
                resolve(items);
              }
            } catch (error) {
              reject(new Error('Failed to parse response: ' + error.message));
            }
          } else {
            reject(new Error('Request failed with status: ' + xhr.status));
          }
        }
      };

      xhr.onerror = () => reject(new Error('Network request failed'));

      try {
        xhr.send();
      } catch (error) {
        reject(new Error('Failed to send request: ' + error.message));
      }
    });
  }

  return makeRequest();
}

/* Convert the Kindle library items to CSV (with pipe-separated authors column)
 */
function itemsToCsv(items) {
  return items.map(item => {
    return [
      item.asin,
      item.title,
      item.authors[0],
      item.percentageRead
    ].map(value => `"${value}"`).join(',');
  }).join('\n');
}

/* Convert the Kindle library items to a Markdown table
 */
function itemsToMarkdown(items) {
  return items.map(item => {
    return [
      item.asin,
      item.title,
      item.authors[0],
      item.percentageRead
    ].map(value => `| ${value}`).join(' | ') + ' |';
  }).join('\n');
}

/* Download data as a file
 */
function downloadData(data, filename, type) {
  const blob = new Blob([data], { type: type });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

/* Fetch the Kindle library and download it
 */
fetchKindleLibrary().then(
  items => {
    // downloadData(itemsToCsv(items), 'kindle-library.csv', 'text/csv');
    // downloadData(itemsToMarkdown(items), 'kindle-library.md', 'text/markdown');
    downloadData(JSON.stringify(items, null, 2), 'kindle-library.json', 'application/json');
  }
).catch(error => {
  console.error('Error:', error);
})
