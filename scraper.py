import requests
from bs4 import BeautifulSoup
import re
import time
import random
from typing import Dict, Optional

class AmazonScraper:
    def __init__(self):
        self.session = requests.Session()
        # Use a simple static user agent instead of the problematic user_agent package
        user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        self.headers = {
            'User-Agent': user_agent,
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        self.session.headers.update(self.headers)

    def extract_asin_from_url(self, url: str) -> Optional[str]:
        """Extract ASIN from Amazon URL - enhanced to handle various formats."""
        # More comprehensive ASIN patterns
        patterns = [
            r'/dp/([A-Z0-9]{10})',           # Standard /dp/ format
            r'/gp/product/([A-Z0-9]{10})',   # /gp/product/ format
            r'asin=([A-Z0-9]{10})',          # Query parameter
            r'/product/([A-Z0-9]{10})',      # Alternative product format
            r'\/([A-Z0-9]{10})(?:\/|$|\?)',  # ASIN at the end of path
            r'/([A-Z0-9]{10})/ref=',         # ASIN followed by ref parameter
            r'/([A-Z0-9]{10})\?',            # ASIN followed by query params
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def normalize_amazon_url(self, url: str) -> str:
        """Normalize and clean various Amazon URL formats."""
        # Remove whitespace
        url = url.strip()

        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        # Handle various Amazon domains
        amazon_domains = [
            'amazon.com', 'amazon.co.uk', 'amazon.ca', 'amazon.de',
            'amazon.fr', 'amazon.it', 'amazon.es', 'amazon.co.jp',
            'amazon.in', 'amazon.com.br', 'amazon.com.mx'
        ]

        # Check if it's an Amazon URL (be flexible about format)
        is_amazon = False
        for domain in amazon_domains:
            if domain in url.lower():
                is_amazon = True
                break

        if not is_amazon:
            return url  # Return as-is, let validation handle it

        # Extract ASIN and create clean URL
        asin = self.extract_asin_from_url(url)
        if asin:
            return f"https://www.amazon.com/dp/{asin}"

        return url

    def clean_url(self, url: str) -> str:
        """Clean Amazon URL to remove tracking parameters."""
        return self.normalize_amazon_url(url)

    def is_valid_amazon_url(self, url: str) -> bool:
        """Check if URL is a valid Amazon product URL."""
        # Normalize first
        normalized_url = self.normalize_amazon_url(url)

        # Check for Amazon domain
        if 'amazon.' not in normalized_url.lower():
            return False

        # Check if we can extract an ASIN
        asin = self.extract_asin_from_url(normalized_url)
        return asin is not None

    def scrape_product(self, url: str) -> Dict:
        """Scrape product information from Amazon."""
        result = {
            'title': None,
            'price': None,
            'availability': 'Unknown',
            'currency': 'USD',
            'asin': None,
            'error': None
        }

        try:
            # Add random delay to avoid being blocked
            time.sleep(random.uniform(1, 3))

            # Clean the URL
            clean_url = self.clean_url(url)
            result['asin'] = self.extract_asin_from_url(clean_url)

            # Make the request
            response = self.session.get(clean_url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract title
            title_selectors = [
                '#productTitle',
                '.product-title',
                'h1.a-size-large',
                'span#productTitle'
            ]

            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem:
                    result['title'] = title_elem.get_text().strip()
                    break

            # Extract price
            price = self._extract_price(soup)
            if price:
                result['price'] = price

            # Check availability
            availability = self._check_availability(soup)
            result['availability'] = availability

            # If no price found, might be out of stock
            if not result['price'] and 'unavailable' in availability.lower():
                result['availability'] = 'Out of Stock'

        except requests.RequestException as e:
            result['error'] = f"Request failed: {str(e)}"
        except Exception as e:
            result['error'] = f"Scraping failed: {str(e)}"

        return result

    def _extract_price(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract price from the page with improved precision."""
        print("[DEBUG] Starting price extraction...")

        # Try to extract Amazon's split price format (dollars + cents) from the main buybox
        # Look specifically in the main price containers to avoid picking up random prices
        main_price_containers = [
            '#apex_desktop .a-price.a-text-price',
            '.a-price.a-text-price.a-size-medium.a-color-base',
            '#corePrice_feature_div .a-price',
            '#apex_desktop .a-price',
            '.a-price.a-text-price'
        ]

        for container_selector in main_price_containers:
            container = soup.select_one(container_selector)
            if container:
                dollar_elem = container.select_one('.a-price-whole')
                cent_elem = container.select_one('.a-price-fraction')

                if dollar_elem and cent_elem:
                    dollar_text = dollar_elem.get_text().strip().replace(',', '').rstrip('.')
                    cent_text = cent_elem.get_text().strip()
                    print(f"[DEBUG] Found split price in container '{container_selector}': '{dollar_text}' dollars, '{cent_text}' cents")

                    try:
                        dollars = float(dollar_text)
                        cents = float(cent_text) / 100
                        total_price = dollars + cents
                        print(f"[DEBUG] Combined split price: ${total_price}")
                        if 0.01 <= total_price <= 50000:
                            return total_price
                    except (ValueError, TypeError):
                        print(f"[DEBUG] Could not parse split price format")
                        continue

        # Primary price selectors (most reliable) - target the screen reader prices
        primary_selectors = [
            # Main price with screen reader text (most reliable)
            '#apex_desktop .a-price.a-text-price .a-offscreen',
            '.a-price.a-text-price.a-size-medium.a-color-base .a-offscreen',
            '#corePrice_feature_div .a-price .a-offscreen',

            # Alternative main price formats
            '#priceblock_dealprice',
            '#priceblock_ourprice',
            '#price_inside_buybox',
        ]

        # Try primary selectors first
        for selector in primary_selectors:
            elements = soup.select(selector)
            for elem in elements:
                if elem:
                    price_text = elem.get_text().strip()
                    print(f"[DEBUG] Found primary selector '{selector}': '{price_text}'")

                    # Extract numeric price (handle both $12.34 and 12.34 formats)
                    price_match = re.search(r'\$?([\d,]+\.?\d*)', price_text.replace(',', ''))
                    if price_match:
                        try:
                            price = float(price_match.group(1))
                            print(f"[DEBUG] Extracted price from primary: ${price}")
                            # Validate price is reasonable (between $0.01 and $50,000)
                            if 0.01 <= price <= 50000:
                                return price
                            else:
                                print(f"[DEBUG] Price ${price} outside reasonable range, skipping")
                        except ValueError:
                            print(f"[DEBUG] Could not convert '{price_match.group(1)}' to float")
                            continue

        # Secondary selectors (fallback) - but be more selective
        secondary_selectors = [
            '#apex_desktop .a-price .a-offscreen',
            '.a-size-medium.a-color-price',
        ]

        print("[DEBUG] Primary selectors failed, trying secondary...")
        for selector in secondary_selectors:
            elements = soup.select(selector)
            for elem in elements:
                if elem:
                    price_text = elem.get_text().strip()
                    print(f"[DEBUG] Found secondary selector '{selector}': '{price_text}'")

                    # Skip obviously wrong prices (shipping, etc.)
                    if any(word in price_text.lower() for word in ['shipping', 'delivery', 'tax', 'fee', 'save', 'off']):
                        print(f"[DEBUG] Skipping price that looks like shipping/fee: '{price_text}'")
                        continue

                    price_match = re.search(r'\$?([\d,]+\.?\d*)', price_text.replace(',', ''))
                    if price_match:
                        try:
                            price = float(price_match.group(1))
                            print(f"[DEBUG] Extracted price from secondary: ${price}")
                            if 0.01 <= price <= 50000:
                                return price
                            else:
                                print(f"[DEBUG] Price ${price} outside reasonable range, skipping")
                        except ValueError:
                            continue

        print("[DEBUG] No valid price found using targeted selectors")
        return None

    def _check_availability(self, soup: BeautifulSoup) -> str:
        """Check product availability."""
        # Common availability indicators
        availability_selectors = [
            '#availability span',
            '.a-size-medium.a-color-success',
            '.a-size-medium.a-color-price',
            '[data-feature-name="availability"] span',
            '#merchant-info'
        ]

        for selector in availability_selectors:
            elem = soup.select_one(selector)
            if elem:
                text = elem.get_text().strip().lower()
                if any(word in text for word in ['in stock', 'available', 'ships']):
                    return 'In Stock'
                elif any(word in text for word in ['out of stock', 'unavailable', 'temporarily']):
                    return 'Out of Stock'

        # Check for "Add to Cart" button as availability indicator
        add_to_cart = soup.select_one('#add-to-cart-button')
        if add_to_cart and not add_to_cart.get('disabled'):
            return 'In Stock'

        return 'Unknown'

    def test_scraping(self, url: str) -> None:
        """Test scraping on a URL and print results."""
        print(f"Testing scraping for: {url}")
        result = self.scrape_product(url)

        print(f"Title: {result['title']}")
        print(f"Price: ${result['price']} {result['currency']}" if result['price'] else "Price: Not found")
        print(f"Availability: {result['availability']}")
        print(f"ASIN: {result['asin']}")
        if result['error']:
            print(f"Error: {result['error']}")
        print("-" * 50)