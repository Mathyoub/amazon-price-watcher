import schedule
import time
import threading
from datetime import datetime
from database import PriceWatcherDB
from scraper import AmazonScraper

class PriceScheduler:
    def __init__(self):
        self.db = PriceWatcherDB()
        self.scraper = AmazonScraper()
        self.running = False
        self.thread = None

    def check_all_prices(self):
        """Check prices for all active products."""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting price check...")

        products = self.db.get_active_products()
        if not products:
            print("No products to check.")
            return

        for product_id, url, title, asin in products:
            try:
                print(f"Checking: {title or url}")
                result = self.scraper.scrape_product(url)

                if result['error']:
                    print(f"  Error: {result['error']}")
                    continue

                if not result['price']:
                    print(f"  No price found - {result['availability']}")
                    # Still record the availability status
                    self.db.add_price_record(
                        product_id,
                        0.0,  # Use 0 for unavailable items
                        result['currency'],
                        result['availability']
                    )
                else:
                    print(f"  Price: ${result['price']} - {result['availability']}")
                    self.db.add_price_record(
                        product_id,
                        result['price'],
                        result['currency'],
                        result['availability']
                    )

                    # Update title if we got one and don't have it stored
                    if result['title'] and not title:
                        # Update product title in database
                        pass  # We'd need to add this method to the database class

                # Small delay between requests to be respectful
                time.sleep(2)

            except Exception as e:
                print(f"  Failed to check {title or url}: {str(e)}")

        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Price check completed.")

    def start_scheduler(self):
        """Start the background scheduler with fixed 30-minute intervals."""
        if self.running:
            print("Scheduler is already running.")
            return

        # Clear any existing jobs
        schedule.clear()

        # Schedule price checks every 30 minutes
        schedule.every(30).minutes.do(self.check_all_prices)

        # Run an initial check immediately in a separate thread
        # (don't schedule it, just run it once)
        initial_check_thread = threading.Thread(target=self.check_all_prices, daemon=True)
        initial_check_thread.start()

        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()

        print("Price scheduler started. Will check prices every 30 minutes.")
        print("Running initial price check now...")

    def _run_scheduler(self):
        """Internal method to run the scheduler loop."""
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute for scheduled jobs

    def stop_scheduler(self):
        """Stop the background scheduler."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        schedule.clear()
        print("Price scheduler stopped.")

    def run_manual_check(self):
        """Run a manual price check immediately."""
        print("Running manual price check...")
        self.check_all_prices()

    def get_next_scheduled_time(self):
        """Get the next scheduled run time."""
        if not self.running:
            return None

        jobs = schedule.get_jobs()
        if jobs:
            # Get the job with the nearest next run time
            next_job = min(jobs, key=lambda job: job.next_run)
            return next_job.next_run
        return None