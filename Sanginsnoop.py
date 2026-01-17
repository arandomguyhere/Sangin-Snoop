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
1. Install the dependencies if they aren't already available:

   ```bash
   pip install requests beautifulsoup4
   ```

2. Edit the `PRODUCT_HANDLES` list to include any Sangin product handles
   you want to monitor.  A handle is the slug portion of the product URL.
   For example, the Atlas II product page is available at
   `https://sangininstruments.com/products/atlas-ii`, so its handle is
   "atlas-ii".

3. Run the script:

   ```bash
   python Sanginsnoop.py
   ```

4. (Optional) Set up notifications by setting the DISCORD_WEBHOOK_URL
   environment variable:

   ```bash
   export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
   python Sanginsnoop.py
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

import json
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup


# File to store previous status for change detection
STATUS_FILE = Path(__file__).parent / "status_cache.json"


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
    except requests.RequestException as exc:
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


def detect_changes(
    results: List[ProductStatus], previous: Dict[str, str]
) -> List[Dict[str, str]]:
    """Detect changes between current and previous status.

    Returns a list of changes with 'handle', 'old_status', 'new_status', and 'url'.
    """
    changes = []
    for item in results:
        old_status = previous.get(item.handle)
        if old_status is not None and old_status != item.status:
            changes.append({
                "handle": item.handle,
                "old_status": old_status,
                "new_status": item.status,
                "url": item.url,
            })
    return changes


def send_discord_notification(
    webhook_url: str, changes: List[Dict[str, str]]
) -> bool:
    """Send a Discord notification about status changes.

    Parameters
    ----------
    webhook_url : str
        The Discord webhook URL.
    changes : List[Dict[str, str]]
        List of changes to report.

    Returns
    -------
    bool
        True if the notification was sent successfully.
    """
    if not changes:
        return True

    # Build the message
    embeds = []
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

    payload = {
        "username": "Sangin Snoop",
        "avatar_url": "https://sangininstruments.com/cdn/shop/files/SI_Logo_White.png",
        "content": "**Watch Availability Update**",
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

    # Load previous status for change detection
    previous_status = load_previous_status()

    # Scrape current status
    print("Checking Sangin Instruments watch availability...")
    print()
    results = scrape_products(PRODUCT_HANDLES)

    # Print the results in a simple table
    print(f"{'Product Handle':<25} | {'Status':<30} | URL")
    print("-" * 90)
    for item in results:
        print(f"{item.handle:<25} | {item.status:<30} | {item.url}")

    # Detect changes
    changes = detect_changes(results, previous_status)

    if changes:
        print()
        print("=" * 90)
        print("CHANGES DETECTED:")
        print("=" * 90)
        for change in changes:
            print(f"  {change['handle']}: {change['old_status']} -> {change['new_status']}")

        # Send Discord notification if webhook is configured
        webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
        if webhook_url:
            print()
            print("Sending Discord notification...")
            if send_discord_notification(webhook_url, changes):
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


if __name__ == "__main__":
    main()
