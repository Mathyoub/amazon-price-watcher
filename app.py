#!/usr/bin/env python3
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import threading
import time
import traceback
from datetime import datetime, timedelta
from database import PriceWatcherDB
from scraper import AmazonScraper
from scheduler import PriceScheduler

app = Flask(__name__)
app.secret_key = 'amazon-price-watcher-secret-key'

# Global scheduler instance
scheduler = None
scheduler_thread = None

@app.route('/')
def index():
    """Main dashboard showing all tracked products."""
    global scheduler

    db = PriceWatcherDB()
    products = db.list_products_with_prices()

    # Calculate some stats
    total_products = len(products)
    products_with_prices = len([p for p in products if p[4] and p[4] > 0])

    # Get monitoring status
    monitoring_active = scheduler and scheduler.running
    next_check = None
    if monitoring_active:
        next_run = scheduler.get_next_scheduled_time()
        if next_run:
            next_check = next_run.isoformat()

    return render_template('index.html',
                         products=products,
                         total_products=total_products,
                         products_with_prices=products_with_prices,
                         monitoring_active=monitoring_active,
                         next_check=next_check)

@app.route('/test')
def test():
    """Simple test endpoint."""
    return "Flask is working! Test successful."

@app.route('/add', methods=['GET', 'POST'])
def add_product():
    """Add a new product to track."""
    print(f"[DEBUG] add_product called with method: {request.method}")

    if request.method == 'POST':
        try:
            print(f"[DEBUG] POST request received")
            print(f"[DEBUG] Form data: {request.form}")
            print(f"[DEBUG] Request headers: {request.headers}")

            url = request.form.get('url', '').strip()
            print(f"[DEBUG] Received URL: {url}")

            if not url:
                print(f"[DEBUG] No URL provided")
                flash('Please enter a URL', 'error')
                return render_template('add.html')

            # Initialize scraper to use validation
            scraper = AmazonScraper()

            # Validate and normalize URL
            if not scraper.is_valid_amazon_url(url):
                print(f"[DEBUG] Invalid URL - not a valid Amazon product URL")
                flash('Please enter a valid Amazon product URL. We support Amazon URLs from various countries and formats.', 'error')
                return render_template('add.html')

            # Clean/normalize the URL
            clean_url = scraper.clean_url(url)
            print(f"[DEBUG] Cleaned URL: {clean_url}")

            print(f"[DEBUG] URL validation passed")

            db = PriceWatcherDB()

            print(f"[DEBUG] Starting to scrape product...")
            # Scrape product information
            result = scraper.scrape_product(clean_url)
            print(f"[DEBUG] Scraping result: {result}")

            if result['error']:
                print(f"[DEBUG] Scraping error: {result['error']}")
                flash(f'Error fetching product: {result["error"]}', 'error')
                return render_template('add.html')

            print(f"[DEBUG] Adding product to database...")
            # Add to database
            product_id = db.add_product(
                url=clean_url,
                title=result['title'],
                asin=result['asin']
            )
            print(f"[DEBUG] Product added with ID: {product_id}")

            # Add initial price record if available
            if result['price']:
                print(f"[DEBUG] Adding price record: {result['price']}")
                db.add_price_record(
                    product_id,
                    result['price'],
                    result['currency'],
                    result['availability']
                )
                flash(f'✓ Added: {result["title"]} (${result["price"]})', 'success')
            else:
                flash(f'✓ Added: {result["title"] or "Product"} (Price not available)', 'success')

            print(f"[DEBUG] Redirecting to index...")
            return redirect(url_for('index'))

        except Exception as e:
            print(f"[ERROR] Exception in add_product: {str(e)}")
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            flash(f'Unexpected error: {str(e)}', 'error')
            return render_template('add.html')

    print(f"[DEBUG] Returning add.html template for GET request")
    return render_template('add.html')

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    """Show detailed view of a specific product with price history."""
    db = PriceWatcherDB()

    # Get product info
    products = db.list_products_with_prices()
    product = next((p for p in products if p[0] == product_id), None)

    if not product:
        flash('Product not found', 'error')
        return redirect(url_for('index'))

    # Get price history (last 60 days)
    history = db.get_product_history(product_id, 60)
    print(f"[DEBUG] Raw history data: {history}")

    # Prepare data for chart
    chart_data = []
    for price, checked_date, availability in reversed(history):
        print(f"[DEBUG] Processing: price={price}, date={checked_date}, availability={availability}")
        if price and price > 0:  # Only include valid prices
            chart_data.append({
                'date': checked_date,
                'price': float(price),
                'availability': availability
            })

    print(f"[DEBUG] Final chart_data: {chart_data}")
    print(f"[DEBUG] Chart data length: {len(chart_data)}")

    return render_template('product_detail.html',
                         product=product,
                         history=history,
                         chart_data=chart_data)

@app.route('/remove/<int:product_id>', methods=['POST'])
def remove_product(product_id):
    """Remove a product from tracking."""
    db = PriceWatcherDB()
    db.deactivate_product(product_id)
    flash('Product removed from tracking', 'success')
    return redirect(url_for('index'))

@app.route('/check', methods=['POST'])
def manual_check():
    """Run a manual price check for all products."""
    def run_check():
        scheduler = PriceScheduler()
        scheduler.run_manual_check()

    # Run in background thread to avoid blocking the web request
    thread = threading.Thread(target=run_check)
    thread.daemon = True
    thread.start()

    flash('Manual price check started! Refresh the page in a few moments.', 'info')
    return redirect(url_for('index'))

@app.route('/monitor', methods=['POST'])
def toggle_monitoring():
    """Start or stop background monitoring."""
    global scheduler, scheduler_thread

    action = request.form.get('action')

    if action == 'start':
        if scheduler and scheduler.running:
            flash('Monitoring is already running', 'info')
        else:
            scheduler = PriceScheduler()
            scheduler_thread = threading.Thread(
                target=lambda: scheduler.start_scheduler(),
                daemon=True
            )
            scheduler_thread.start()
            flash('Background monitoring started! Checking every 30 minutes.', 'success')

    elif action == 'stop':
        if scheduler and scheduler.running:
            scheduler.stop_scheduler()
            scheduler = None
            flash('Background monitoring stopped', 'success')
        else:
            flash('Monitoring is not running', 'info')

    return redirect(url_for('index'))

@app.route('/api/status')
def api_status():
    """API endpoint to get monitoring status."""
    global scheduler

    status = {
        'monitoring': scheduler and scheduler.running,
        'next_check': None
    }

    if scheduler and scheduler.running:
        next_run = scheduler.get_next_scheduled_time()
        if next_run:
            status['next_check'] = next_run.isoformat()

    return jsonify(status)

@app.route('/api/products')
def api_products():
    """API endpoint to get all products (for AJAX updates)."""
    db = PriceWatcherDB()
    products = db.list_products_with_prices()

    products_data = []
    for product_id, url, title, asin, price, checked_date, availability in products:
        products_data.append({
            'id': product_id,
            'title': title,
            'url': url,
            'asin': asin,
            'price': float(price) if price and price > 0 else None,
            'last_checked': checked_date,
            'availability': availability
        })

    return jsonify(products_data)

@app.route('/api/add', methods=['POST'])
def api_add_product():
    """API endpoint to add a new product by URL."""
    data = request.get_json()
    url = data.get('url', '').strip() if data else ''
    if not url:
        return jsonify({'success': False, 'error': 'No URL provided'}), 400
    scraper = AmazonScraper()
    if not scraper.is_valid_amazon_url(url):
        return jsonify({'success': False, 'error': 'Invalid Amazon URL'}), 400
    clean_url = scraper.clean_url(url)
    result = scraper.scrape_product(clean_url)
    if result['error']:
        return jsonify({'success': False, 'error': result['error']}), 500
    db = PriceWatcherDB()
    product_id = db.add_product(
        url=clean_url,
        title=result['title'],
        asin=result['asin']
    )
    if result['price']:
        db.add_price_record(
            product_id,
            result['price'],
            result['currency'],
            result['availability']
        )
    return jsonify({'success': True, 'product_id': product_id, 'title': result['title'], 'asin': result['asin']}), 201

@app.route('/api/remove/<int:product_id>', methods=['POST'])
def api_remove_product(product_id):
    """API endpoint to remove a product by product_id."""
    db = PriceWatcherDB()
    db.deactivate_product(product_id)
    return jsonify({'success': True, 'product_id': product_id})

@app.route('/api/history/<int:product_id>')
def api_product_history(product_id):
    """API endpoint to get price history for a product."""
    db = PriceWatcherDB()
    history = db.get_product_history(product_id, 365)  # up to 1 year
    # Format: list of dicts
    history_data = [
        {'price': float(price), 'checked_date': checked_date, 'availability': availability}
        for price, checked_date, availability in history
    ]
    return jsonify(history_data)

@app.route('/api/changes')
def api_recent_changes():
    """API endpoint to get recent price changes (last 24h)."""
    db = PriceWatcherDB()
    # Get all products
    products = db.list_products_with_prices()
    changes = []
    for product_id, url, title, asin, price, checked_date, availability in products:
        # Get last two price records
        history = db.get_product_history(product_id, 2)
        if len(history) >= 2:
            latest, previous = history[0], history[1]
            if latest[0] != previous[0]:
                changes.append({
                    'product_id': product_id,
                    'title': title,
                    'asin': asin,
                    'old_price': float(previous[0]),
                    'new_price': float(latest[0]),
                    'change': float(latest[0]) - float(previous[0]),
                    'checked_date': latest[1],
                })
    return jsonify(changes)

if __name__ == '__main__':
    print("🚀 Starting Amazon Price Watcher Web Interface...")
    print("📱 Open your browser to: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)