import sqlite3
import datetime
from typing import List, Tuple, Optional

class PriceWatcherDB:
    def __init__(self, db_path: str = "price_watcher.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize the database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Products table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    title TEXT,
                    asin TEXT,
                    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    active BOOLEAN DEFAULT 1
                )
            ''')

            # Price history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER,
                    price REAL,
                    currency TEXT DEFAULT 'USD',
                    checked_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    availability TEXT,
                    FOREIGN KEY (product_id) REFERENCES products (id)
                )
            ''')

            conn.commit()

    def add_product(self, url: str, title: str = None, asin: str = None) -> int:
        """Add a new product to track."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO products (url, title, asin) VALUES (?, ?, ?)",
                    (url, title, asin)
                )
                conn.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                # Product already exists - reactivate it and update info
                cursor.execute("SELECT id FROM products WHERE url = ?", (url,))
                product_id = cursor.fetchone()[0]

                # Reactivate the product and update title/asin if provided
                if title and asin:
                    cursor.execute(
                        "UPDATE products SET active = 1, title = ?, asin = ? WHERE id = ?",
                        (title, asin, product_id)
                    )
                else:
                    cursor.execute(
                        "UPDATE products SET active = 1 WHERE id = ?",
                        (product_id,)
                    )
                conn.commit()
                return product_id

    def get_active_products(self) -> List[Tuple]:
        """Get all active products to monitor."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, url, title, asin FROM products WHERE active = 1"
            )
            return cursor.fetchall()

    def add_price_record(self, product_id: int, price: float, currency: str = "USD",
                        availability: str = "In Stock"):
        """Add a price record for a product."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO price_history
                   (product_id, price, currency, availability)
                   VALUES (?, ?, ?, ?)""",
                (product_id, price, currency, availability)
            )
            conn.commit()

    def get_product_history(self, product_id: int, days: int = 30) -> List[Tuple]:
        """Get price history for a product."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT price, checked_date, availability
                   FROM price_history
                   WHERE product_id = ?
                   AND checked_date >= datetime('now', '-{} days')
                   ORDER BY checked_date DESC""".format(days),
                (product_id,)
            )
            return cursor.fetchall()

    def get_latest_price(self, product_id: int) -> Optional[Tuple]:
        """Get the most recent price for a product."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT price, checked_date, availability
                   FROM price_history
                   WHERE product_id = ?
                   ORDER BY checked_date DESC
                   LIMIT 1""",
                (product_id,)
            )
            return cursor.fetchone()

    def list_products_with_prices(self) -> List[Tuple]:
        """Get all products with their latest prices."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT p.id, p.url, p.title, p.asin,
                          COALESCE(latest_price.price, 0) as price,
                          latest_price.checked_date,
                          latest_price.availability
                   FROM products p
                   LEFT JOIN (
                       SELECT product_id, price, checked_date, availability,
                              ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY checked_date DESC) as rn
                       FROM price_history
                   ) latest_price ON p.id = latest_price.product_id AND latest_price.rn = 1
                   WHERE p.active = 1
                   ORDER BY p.added_date DESC"""
            )
            return cursor.fetchall()

    def deactivate_product(self, product_id: int):
        """Mark a product as inactive (stop tracking)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE products SET active = 0 WHERE id = ?",
                (product_id,)
            )
            conn.commit()