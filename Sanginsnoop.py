"""
Sangin Instruments Watch Availability Checker
===========================================

This script is designed to check the availability status of watches listed on
the Sangin Instruments website.  It works by making HTTP requests to the
product pages and looking for keywords in the page content (specifically
"Sold Out" or "Add to cart").  If the script sees the "Sold Out" string
anywhere on the page it will assume the watch is unavailable.  Otherwise,
if it finds "Add to cart", it will conclude that the watch is available.

The script automatically discovers all products from the Sangin Instruments
website, so new watches are detected automatically without code changes.

**Disclaimer:** At the time of writing this code we could not test it
end‑to‑end from within the environment because direct HTTP requests to
`sangininstruments.com` were blocked by a 403 (Forbidden) response.  The
approach below follows a conventional pattern for scraping Shopify‑based
stores; you may need to tweak headers, use session cookies, or run from
a residential IP address if the site uses aggressive bot protection.

Usage
-----
1. Install the dependencies if they aren't already available:

   ```bash
   pip install requests beautifulsoup4
   ```

2. Run the script:

   ```bash
   python Sanginsnoop.py
   ```

3. (Optional) Set up notifications by setting the DISCORD_WEBHOOK_URL
   environment variable:

   ```bash
   export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
   python Sanginsnoop.py
   ```

The script will automatically discover all products on the site and print a
table summarising whether each product appears to be available or sold out.

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

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup


# File to store previous status for change detection
STATUS_FILE = Path(__file__).parent / "status_cache.json"

# Base URL for Sangin Instruments
BASE_URL = "https://sangininstruments.com"

# Fallback list if automatic discovery fails
FALLBACK_HANDLES = [
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


@dataclass
class ProductStatus:
    """Simple data structure to hold the status of each product."""

    handle: str
    url: str
    status: str


def get_session() -> requests.Session:
    """Create a requests session with realistic headers."""
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/116.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
    )
    return session


def discover_products(session: requests.Session) -> List[str]:
    """Automatically discover all product handles from the Sangin website.

    Uses Shopify's products.json endpoint to get all products dynamically.
    Falls back to scraping the collections page if JSON endpoint fails.
    Returns FALLBACK_HANDLES if all discovery methods fail.

    Parameters
    ----------
    session : requests.Session
        A session object to persist headers and cookies across requests.

    Returns
    -------
    List[str]
        A list of product handles discovered from the website.
    """
    handles = []

    # Method 1: Try Shopify's products.json endpoint (most reliable)
    try:
        response = session.get(f"{BASE_URL}/products.json", timeout=20)
        if response.status_code == 200:
            data = response.json()
            products = data.get("products", [])
            handles = [p["handle"] for p in products if "handle" in p]
            if handles:
                print(f"Discovered {len(handles)} products via products.json")
                return handles
    except (requests.RequestException, json.JSONDecodeError, KeyError):
        pass

    # Method 2: Try paginated products.json (some stores paginate)
    try:
        page = 1
        while page <= 10:  # Limit to 10 pages
            response = session.get(
                f"{BASE_URL}/products.json?page={page}&limit=250",
                timeout=20
            )
            if response.status_code != 200:
                break
            data = response.json()
            products = data.get("products", [])
            if not products:
                break
            handles.extend([p["handle"] for p in products if "handle" in p])
            page += 1
            time.sleep(0.5)
        if handles:
            print(f"Discovered {len(handles)} products via paginated products.json")
            return list(dict.fromkeys(handles))  # Remove duplicates, preserve order
    except (requests.RequestException, json.JSONDecodeError, KeyError):
        pass

    # Method 3: Scrape the collections/all page
    try:
        response = session.get(f"{BASE_URL}/collections/all", timeout=20)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            # Look for product links
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if "/products/" in href:
                    # Extract handle from URL like /products/atlas-ii
                    parts = href.split("/products/")
                    if len(parts) > 1:
                        handle = parts[1].split("?")[0].split("/")[0]
                        if handle and handle not in handles:
                            handles.append(handle)
            if handles:
                print(f"Discovered {len(handles)} products via collections page")
                return handles
    except requests.RequestException:
        pass

    # Method 4: Fallback to hardcoded list
    print(f"Using fallback list of {len(FALLBACK_HANDLES)} known products")
    return FALLBACK_HANDLES


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
    url = f"{BASE_URL}/products/{handle}"
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
    except requests.RequestException as exc:
        return ProductStatus(handle, url, f"error: {exc}")


def scrape_products(handles: List[str], session: requests.Session) -> List[ProductStatus]:
    """Scrape multiple products and return their availability status.

    Parameters
    ----------
    handles : List[str]
        A list of product handles to scrape.
    session : requests.Session
        A session object to persist headers and cookies across requests.

    Returns
    -------
    List[ProductStatus]
        A list of results for each product.
    """
    results: List[ProductStatus] = []
    for handle in handles:
        status = check_product_availability(handle, session)
        results.append(status)
        # Small delay between requests to be respectful
        time.sleep(1)
    return results


def load_previous_status() -> Dict[str, str]:
    """Load the previous status from the cache file."""
    if STATUS_FILE.exists():
        try:
            with open(STATUS_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_current_status(results: List[ProductStatus]) -> None:
    """Save current status to the cache file."""
    status_dict = {item.handle: item.status for item in results}
    with open(STATUS_FILE, "w") as f:
        json.dump(status_dict, f, indent=2)


def save_public_status(results: List[ProductStatus]) -> None:
    """Save status to a public JSON file for the landing page."""
    from datetime import datetime, timezone

    public_file = Path(__file__).parent / "status.json"
    data = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "total_products": len(results),
        "products": [
            {
                "name": item.handle.replace("-", " ").title(),
                "handle": item.handle,
                "status": item.status,
                "url": item.url,
            }
            for item in results
        ]
    }
    with open(public_file, "w") as f:
        json.dump(data, f, indent=2)


def detect_changes(
    results: List[ProductStatus], previous: Dict[str, str]
) -> tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """Detect changes between current and previous status.

    Returns a tuple of:
    - changes: list of status changes with 'handle', 'old_status', 'new_status', and 'url'
    - new_products: list of new products with 'handle', 'status', and 'url'
    """
    changes = []
    new_products = []
    for item in results:
        old_status = previous.get(item.handle)
        if old_status is None and previous:
            # This is a new product (only if we have previous data)
            new_products.append({
                "handle": item.handle,
                "status": item.status,
                "url": item.url,
            })
        elif old_status is not None and old_status != item.status:
            changes.append({
                "handle": item.handle,
                "old_status": old_status,
                "new_status": item.status,
                "url": item.url,
            })
    return changes, new_products


def send_discord_notification(
    webhook_url: str,
    changes: List[Dict[str, str]],
    new_products: Optional[List[Dict[str, str]]] = None
) -> bool:
    """Send a Discord notification about status changes and new products.

    Parameters
    ----------
    webhook_url : str
        The Discord webhook URL.
    changes : List[Dict[str, str]]
        List of status changes to report.
    new_products : Optional[List[Dict[str, str]]]
        List of new products discovered.

    Returns
    -------
    bool
        True if the notification was sent successfully.
    """
    if not changes and not new_products:
        return True

    # Build the message
    embeds = []

    # Add new product notifications
    if new_products:
        for product in new_products:
            color = 0x0099FF  # Blue - new product
            title = f"🆕 NEW WATCH: {product['handle'].replace('-', ' ').title()}"
            embeds.append({
                "title": title,
                "description": f"**Status:** {product['status']}",
                "url": product["url"],
                "color": color,
            })

    # Add status change notifications
    for change in changes:
        # Determine color based on new status
        if change["new_status"] == "available":
            color = 0x00FF00  # Green - watch is now available!
            title = f"🟢 {change['handle'].replace('-', ' ').title()} is NOW AVAILABLE!"
        elif change["new_status"] == "sold out":
            color = 0xFF0000  # Red - sold out
            title = f"🔴 {change['handle'].replace('-', ' ').title()} is now Sold Out"
        else:
            color = 0xFFFF00  # Yellow - unknown status
            title = f"🟡 {change['handle'].replace('-', ' ').title()} status changed"

        embeds.append({
            "title": title,
            "description": f"**Previous:** {change['old_status']}\n**Current:** {change['new_status']}",
            "url": change["url"],
            "color": color,
        })

    # Determine content message
    content_parts = []
    if new_products:
        content_parts.append(f"{len(new_products)} new product(s) discovered")
    if changes:
        content_parts.append(f"{len(changes)} status change(s)")
    content = "**Watch Update:** " + ", ".join(content_parts)

    payload = {
        "username": "Sangin Snoop",
        "avatar_url": "https://sangininstruments.com/cdn/shop/files/SI_Logo_White.png",
        "content": content,
        "embeds": embeds[:10],  # Discord limit is 10 embeds per message
    }

    try:
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=10,
        )
        return response.status_code == 204
    except requests.RequestException as e:
        print(f"Failed to send Discord notification: {e}")
        return False


def main() -> None:
    print("Sangin Snoop - Watch Availability Checker")
    print("=" * 50)
    print()

    # Create session for all requests
    session = get_session()

    # Automatically discover all products
    print("Discovering products...")
    product_handles = discover_products(session)
    print()

    # Load previous status for change detection
    previous_status = load_previous_status()

    # Scrape current status
    print(f"Checking availability for {len(product_handles)} products...")
    print()
    results = scrape_products(product_handles, session)

    # Print the results in a simple table
    print(f"{'Product Handle':<25} | {'Status':<30} | URL")
    print("-" * 90)
    for item in results:
        print(f"{item.handle:<25} | {item.status:<30} | {item.url}")

    # Detect changes and new products
    changes, new_products = detect_changes(results, previous_status)

    # Report new products
    if new_products:
        print()
        print("=" * 90)
        print(f"NEW PRODUCTS DISCOVERED ({len(new_products)}):")
        print("=" * 90)
        for product in new_products:
            print(f"  🆕 {product['handle']}: {product['status']}")

    # Report status changes
    if changes:
        print()
        print("=" * 90)
        print(f"STATUS CHANGES ({len(changes)}):")
        print("=" * 90)
        for change in changes:
            print(f"  {change['handle']}: {change['old_status']} -> {change['new_status']}")

    # Send Discord notification if webhook is configured
    if changes or new_products:
        webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
        if webhook_url:
            print()
            print("Sending Discord notification...")
            if send_discord_notification(webhook_url, changes, new_products):
                print("Discord notification sent successfully!")
            else:
                print("Failed to send Discord notification.")
        else:
            print()
            print("Tip: Set DISCORD_WEBHOOK_URL environment variable to receive notifications.")
    else:
        if previous_status:
            print()
            print("No changes detected since last check.")
        else:
            print()
            print("First run - status saved for future comparison.")

    # Save current status for next run
    save_current_status(results)

    # Save public status for landing page
    save_public_status(results)


if __name__ == "__main__":
    main()
