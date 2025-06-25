# Amazon Price Watcher

A simple command-line tool that tracks Amazon product prices in the background and builds a historical record to help you identify sales and price drops.

## Features

- 🔍 **Track Any Amazon Product**: Add products by URL
- 📊 **Price History**: Build historical price records over time
- 🔄 **Background Monitoring**: Automatically checks prices every 30 minutes
- 💾 **Local Database**: All data stored locally in SQLite
- 🎯 **Deal Detection**: Compare current prices with historical data
- 🖥️ **Simple CLI**: Easy-to-use command line interface

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Add your first product:**
   ```bash
   python price_watcher.py add "https://www.amazon.com/dp/PRODUCT_ID"
   ```

3. **Start background monitoring:**
   ```bash
   python price_watcher.py start
   ```

## Commands

### Add Products
```bash
python price_watcher.py add "https://www.amazon.com/dp/B08N5WRWNW"
```

### List All Tracked Products
```bash
python price_watcher.py list
```

### View Price History
```bash
python price_watcher.py history 1 --days 30
```

### Manual Price Check
```bash
python price_watcher.py check
```

### Start Background Monitoring
```bash
python price_watcher.py start
```

**Note**: The background monitoring automatically checks prices every 30 minutes. This interval is fixed to provide consistent monitoring while being respectful to Amazon's servers.

### Remove a Product
```bash
python price_watcher.py remove 1
```

### Test Scraping
```bash
python price_watcher.py test "https://www.amazon.com/dp/PRODUCT_ID"
```

## How It Works

1. **Product Addition**: When you add a product URL, the tool extracts the ASIN (Amazon product ID) and fetches initial product information
2. **Price Monitoring**: The background scheduler runs every 30 minutes to check current prices
3. **Data Storage**: All price data is stored in a local SQLite database (`price_watcher.db`)
4. **Historical Analysis**: You can view price trends and identify when items go on sale

## Tips for Use

- **Be Respectful**: The tool includes delays between requests to avoid overwhelming Amazon's servers
- **Monitor Regularly**: Run the background service daily for best results
- **Clean URLs**: The tool automatically cleans Amazon URLs to remove tracking parameters
- **Check History**: Use the history command to spot patterns and identify good deals

## Database Schema

The tool creates two main tables:
- `products`: Stores product URLs, titles, and ASINs
- `price_history`: Records price points over time with timestamps

## Troubleshooting

- **No Price Found**: Some products may have dynamic pricing or be temporarily unavailable
- **Scraping Errors**: Amazon occasionally blocks requests; the tool will retry on the next scheduled run
- **Missing Titles**: Initial product scraping might not always capture titles; they'll be updated on subsequent checks

## Note

This tool is for personal use only. Please respect Amazon's terms of service and don't abuse their servers with excessive requests.