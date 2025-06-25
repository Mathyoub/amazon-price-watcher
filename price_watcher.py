#!/usr/bin/env python3
import click
import sys
from datetime import datetime
from database import PriceWatcherDB
from scraper import AmazonScraper
from scheduler import PriceScheduler

@click.group()
def cli():
    """Amazon Price Watcher - Track prices and get notified of deals!"""
    pass

@cli.command()
@click.argument('url')
def add(url):
    """Add a new Amazon product to track."""
    if 'amazon.com' not in url.lower():
        click.echo("Error: Please provide a valid Amazon URL")
        return

    db = PriceWatcherDB()
    scraper = AmazonScraper()

    click.echo(f"Adding product: {url}")
    click.echo("Fetching product information...")

    # Get initial product info
    result = scraper.scrape_product(url)

    if result['error']:
        click.echo(f"Error: {result['error']}")
        return

    # Add to database
    product_id = db.add_product(
        url=scraper.clean_url(url),
        title=result['title'],
        asin=result['asin']
    )

    # Add initial price record if available
    if result['price']:
        db.add_price_record(
            product_id,
            result['price'],
            result['currency'],
            result['availability']
        )
        click.echo(f"✓ Added: {result['title']}")
        click.echo(f"  Current price: ${result['price']}")
        click.echo(f"  Availability: {result['availability']}")
    else:
        click.echo(f"✓ Added: {result['title'] or 'Product'}")
        click.echo(f"  Price: Not available")
        click.echo(f"  Status: {result['availability']}")

@cli.command()
def list():
    """List all tracked products with their latest prices."""
    db = PriceWatcherDB()
    products = db.list_products_with_prices()

    if not products:
        click.echo("No products being tracked.")
        return

    click.echo("\n📦 Tracked Products:")
    click.echo("=" * 80)

    for product_id, url, title, asin, price, checked_date, availability in products:
        click.echo(f"\n[{product_id}] {title or 'Unknown Title'}")
        click.echo(f"    URL: {url}")
        click.echo(f"    ASIN: {asin or 'Unknown'}")

        if price and price > 0:
            click.echo(f"    Latest Price: ${price:.2f}")
            if checked_date:
                click.echo(f"    Last Checked: {checked_date}")
            click.echo(f"    Status: {availability or 'Unknown'}")
        else:
            click.echo(f"    Price: Not available")
            click.echo(f"    Status: {availability or 'Not checked yet'}")

@cli.command()
@click.argument('product_id', type=int)
@click.option('--days', default=30, help='Number of days of history to show')
def history(product_id, days):
    """Show price history for a specific product."""
    db = PriceWatcherDB()

    # Get product info
    products = db.list_products_with_prices()
    product = next((p for p in products if p[0] == product_id), None)

    if not product:
        click.echo(f"Product with ID {product_id} not found.")
        return

    _, url, title, asin, _, _, _ = product

    click.echo(f"\n📈 Price History for: {title or 'Unknown Title'}")
    click.echo(f"URL: {url}")
    click.echo("=" * 60)

    history_records = db.get_product_history(product_id, days)

    if not history_records:
        click.echo("No price history available.")
        return

    for price, checked_date, availability in history_records:
        if price > 0:
            click.echo(f"{checked_date}: ${price:.2f} ({availability})")
        else:
            click.echo(f"{checked_date}: Not available ({availability})")

@cli.command()
def check():
    """Run a manual price check for all products."""
    scheduler = PriceScheduler()
    scheduler.run_manual_check()

@cli.command()
def start():
    """Start the background price monitoring service."""
    scheduler = PriceScheduler()

    try:
        scheduler.start_scheduler()
        click.echo("🚀 Price monitoring started! Checking every 30 minutes.")
        click.echo("Press Ctrl+C to stop...")

        # Keep the main thread alive
        while True:
            next_run = scheduler.get_next_scheduled_time()
            if next_run:
                click.echo(f"\rNext check: {next_run.strftime('%Y-%m-%d %H:%M:%S')}", nl=False)
            import time
            time.sleep(30)

    except KeyboardInterrupt:
        click.echo("\n\n🛑 Stopping price monitoring...")
        scheduler.stop_scheduler()
        click.echo("Price monitoring stopped.")

@cli.command()
@click.argument('product_id', type=int)
def remove(product_id):
    """Remove a product from tracking."""
    db = PriceWatcherDB()

    # Check if product exists
    products = db.list_products_with_prices()
    product = next((p for p in products if p[0] == product_id), None)

    if not product:
        click.echo(f"Product with ID {product_id} not found.")
        return

    _, url, title, _, _, _, _ = product

    if click.confirm(f"Remove '{title or url}' from tracking?"):
        db.deactivate_product(product_id)
        click.echo("✓ Product removed from tracking.")

@cli.command()
@click.argument('url')
def test(url):
    """Test scraping on a specific Amazon URL."""
    if 'amazon.com' not in url.lower():
        click.echo("Error: Please provide a valid Amazon URL")
        return

    scraper = AmazonScraper()
    scraper.test_scraping(url)

if __name__ == '__main__':
    cli()