# Sangin Snoop

Watch availability checker for [Sangin Instruments](https://sangininstruments.com) tactical watches.

## Features

- **Automated Availability Checking** - Scrapes product pages to detect "Sold Out" or "Add to Cart" status
- **Change Detection** - Tracks previous status and alerts you when availability changes
- **Discord Notifications** - Get instant alerts when a watch becomes available
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

## Monitored Watches

The script monitors these Sangin Instruments models by default:

| Model | Handle |
|-------|--------|
| Atlas II | `atlas-ii` |
| Overlord | `overlord` |
| Professional | `professional` |
| Neptune | `neptune` |
| Merlin | `merlin` |
| Dark Merlin | `dark-merlin` |
| Kingmaker | `kingmaker` |
| Kinetic II | `kinetic-ii` |
| Kinetic II Ti | `kinetic-ii-ti` |
| Hydra | `hydra` |
| Overlord Special Edition | `overlord-special-edition` |
| Kinetic Gypsy | `kinetic-gypsy` |
| Marauder | `marauder` |

### Adding More Watches

Edit the `PRODUCT_HANDLES` list in `Sanginsnoop.py`:

```python
PRODUCT_HANDLES = [
    "atlas-ii",
    "your-new-watch-handle",
    # ...
]
```

The handle is the URL slug from the product page. For example:
- URL: `https://sangininstruments.com/products/atlas-ii`
- Handle: `atlas-ii`

## How It Works

1. Makes HTTP requests to each product page
2. Parses the HTML and searches for availability keywords:
   - "Sold out" = unavailable
   - "Add to cart" / "Add to basket" = available
3. Compares current status to previous run
4. Sends Discord notification if status changed
5. Saves current status for next comparison

## Example Output

```
Checking Sangin Instruments watch availability...

Product Handle            | Status                         | URL
------------------------------------------------------------------------------------------
atlas-ii                  | available                      | https://sangininstruments.com/products/atlas-ii
overlord                  | sold out                       | https://sangininstruments.com/products/overlord
professional              | available                      | https://sangininstruments.com/products/professional
...

==========================================================================================
CHANGES DETECTED:
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
