"""
Sangin Instruments Watch Availability Checker
===========================================

This script is designed to check the availability status of watches listed on
the Sangin Instruments website.  It works by making HTTP requests to the
product pages and looking for keywords in the page content (specifically
"Sold Out" or "Add to cart").  If the script sees the "Sold Out" string
anywhere on the page it will assume the watch is unavailable.  Otherwise,
if it finds "Add to cart", it will conclude that the watch is available.

**Disclaimer:** At the time of writing this code we could not test it
end‑to‑end from within the environment because direct HTTP requests to
`sangininstruments.com` were blocked by a 403 (Forbidden) response.  The
approach below follows a conventional pattern for scraping Shopify‑based
stores; you may need to tweak headers, use session cookies, or run from
a residential IP address if the site uses aggressive bot protection.

Usage
-----
1. Install the dependencies if they aren’t already available:

   ```bash
   pip install requests beautifulsoup4
   ```

2. Edit the `PRODUCT_HANDLES` list to include any Sangin product handles
   you want to monitor.  A handle is the slug portion of the product URL.
   For example, the Atlas II product page is available at
   `https://sangininstruments.com/products/atlas-ii`, so its handle is
   "atlas-ii".

3. Run the script:

   ```bash
   python sangin_scraper.py
   ```

The script will print a table summarising whether each product appears to be
available or sold out based on the presence of the keywords mentioned above.

Limitations
-----------
* This script uses a simple keyword search and does not handle edge cases
  where the page layout changes.  If Sangin Instruments updates their
  website, you may need to refine the selectors.
* If the website returns an HTTP 403 or uses JavaScript to load the
  availability status, requests may not suffice.  In those cases you might
  consider using a headless browser (e.g. Selenium) or solving any
  anti‑bot challenges manually.
"""

import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import List


@dataclass
class ProductStatus:
    """Simple data structure to hold the status of each product."""

    handle: str
    url: str
    status: str


def check_product_availability(handle: str, session: requests.Session) -> ProductStatus:
    """Check the availability of a single product on Sangin Instruments.

    Parameters
    ----------
    handle : str
        The product handle (slug) used to build the URL.
    session : requests.Session
        A session object to persist headers and cookies across requests.

    Returns
    -------
    ProductStatus
        An object describing the product and its current status.
    """
    url = f"https://sangininstruments.com/products/{handle}"
    try:
        response = session.get(url, timeout=20)
        if response.status_code >= 400:
            # Could not retrieve the page; return unknown status
            return ProductStatus(handle, url, f"unreachable (HTTP {response.status_code})")
        # Parse the HTML
        soup = BeautifulSoup(response.text, "html.parser")
        page_text = soup.get_text(" ").lower()
        if "sold out" in page_text:
            return ProductStatus(handle, url, "sold out")
        if "add to cart" in page_text or "add to basket" in page_text:
            return ProductStatus(handle, url, "available")
        # Fallback if keywords aren't found
        return ProductStatus(handle, url, "unknown – check page manually")
    except Exception as exc:
        return ProductStatus(handle, url, f"error: {exc}")


def scrape_products(handles: List[str]) -> List[ProductStatus]:
    """Scrape multiple products and return their availability status.

    Parameters
    ----------
    handles : List[str]
        A list of product handles to scrape.

    Returns
    -------
    List[ProductStatus]
        A list of results for each product.
    """
    session = requests.Session()
    # Set a realistic User‑Agent header to reduce the chance of being blocked
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/116.0.0.0 Safari/537.36"
            )
        }
    )
    results: List[ProductStatus] = []
    for handle in handles:
        status = check_product_availability(handle, session)
        results.append(status)
    return results


def main() -> None:
    # List of product handles we want to check
    PRODUCT_HANDLES = [
        "atlas-ii",
        "overlord",
        "professional",
        "neptune",
        "merlin",
        "dark-merlin",
        "kingmaker",
        "kinetic-ii",
        "kinetic-ii-ti",
        "hydra",
        "overlord-special-edition",
        "kinetic-gypsy",
        "marauder",
    ]
    results = scrape_products(PRODUCT_HANDLES)
    # Print the results in a simple table
    print(f"{'Product Handle':<25} | {'Status':<30} | URL")
    print("-" * 80)
    for item in results:
        print(f"{item.handle:<25} | {item.status:<30} | {item.url}")


if __name__ == "__main__":
    main()
