# Sangin Snoop

Watch availability checker for [Sangin Instruments](https://sangininstruments.com) tactical watches.

**[View the Project Page](https://arandomguyhere.github.io/Sangin-Snoop/)**

## Features

- **Automatic Product Discovery** - Discovers all watches automatically, no manual updates needed
- **New Product Alerts** - Get notified when Sangin releases new watches
- **Availability Checking** - Detects "Sold Out" or "Add to Cart" status
- **Change Detection** - Tracks status and alerts you when availability changes
- **Discord Notifications** - Get instant alerts for new products and restocks
- **GitHub Actions** - Automated checks every 30 minutes (free!)
- **Rate Limiting** - Respectful 1-second delay between requests

## Quick Start

### Local Usage

```bash
# Install dependencies
pip install requests beautifulsoup4

# Run the checker
python Sanginsnoop.py
```

### With Discord Notifications

```bash
# Set your Discord webhook URL
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/YOUR_WEBHOOK_URL"

# Run the checker
python Sanginsnoop.py
```

## Automated Monitoring with GitHub Actions

The included workflow automatically checks watch availability every 30 minutes and sends Discord notifications when status changes.

### Setup

1. **Fork this repository**

2. **Create a Discord Webhook**
   - Go to your Discord server
   - Server Settings > Integrations > Webhooks
   - Create a new webhook and copy the URL

3. **Add the webhook to GitHub Secrets**
   - Go to your forked repo's Settings > Secrets and variables > Actions
   - Create a new secret named `DISCORD_WEBHOOK_URL`
   - Paste your Discord webhook URL

4. **Enable GitHub Actions**
   - Go to the Actions tab in your repository
   - Enable workflows if prompted

The workflow will now run automatically every 30 minutes. You can also trigger it manually from the Actions tab.

## Automatic Product Discovery

The script **automatically discovers all watches** from the Sangin Instruments website. When new watches are added to the store, they'll be detected and monitored automatically - no code changes needed!

### How Discovery Works

The script tries multiple methods to find all products:

1. **Shopify products.json API** (primary method)
2. **Paginated products endpoint** (for large catalogs)
3. **Collections page scraping** (fallback)
4. **Hardcoded fallback list** (if all else fails)

### New Product Notifications

When a new watch is discovered, you'll receive a Discord notification:

> **Watch Update:** 1 new product(s) discovered
>
> **NEW WATCH: Example Watch Name**
> Status: available
> [Link to product page]

## How It Works

1. **Discovers products** from the Sangin website automatically
2. **Checks each product page** for availability keywords:
   - "Sold out" = unavailable
   - "Add to cart" / "Add to basket" = available
3. **Detects new products** that weren't seen before
4. **Compares status** to previous run for changes
5. **Sends Discord notifications** for new products and status changes
6. **Saves state** for the next comparison

## Example Output

```
Sangin Snoop - Watch Availability Checker
==================================================

Discovering products...
Discovered 15 products via products.json

Checking availability for 15 products...

Product Handle            | Status                         | URL
------------------------------------------------------------------------------------------
atlas-ii                  | available                      | https://sangininstruments.com/products/atlas-ii
overlord                  | sold out                       | https://sangininstruments.com/products/overlord
professional              | available                      | https://sangininstruments.com/products/professional
...

==========================================================================================
NEW PRODUCTS DISCOVERED (1):
==========================================================================================
  🆕 new-watch-model: available

==========================================================================================
STATUS CHANGES (1):
==========================================================================================
  atlas-ii: sold out -> available

Sending Discord notification...
Discord notification sent successfully!
```

## Discord Notification Preview

When a watch becomes available, you'll receive a notification like this:

> **Watch Availability Update**
>
> **Atlas Ii is NOW AVAILABLE!**
> Previous: sold out
> Current: available
> [Link to product page]

## Limitations

- Uses simple keyword matching (may not work if site layout changes significantly)
- May be blocked by aggressive bot protection (403 errors)
- Does not handle JavaScript-rendered content

If you encounter issues, you may need to:
- Run from a residential IP
- Use a headless browser like Selenium
- Adjust the User-Agent header

## License

MIT License - feel free to use and modify.

## Disclaimer

This project is not affiliated with Sangin Instruments. Use responsibly and respect the website's terms of service.
