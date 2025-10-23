# Scripts Directory

Utility scripts for managing the FIX trading system.

## update_stock_prices.py

Updates the stock prices in `broker/stock_universe.csv` with current market data from Yahoo Finance.

### Usage

```bash
# Update prices (from project root)
uv run python scripts/update_stock_prices.py

# Dry run to see what would change
uv run python scripts/update_stock_prices.py --dry-run

# Update a different CSV file
uv run python scripts/update_stock_prices.py --csv path/to/custom.csv
```

### Requirements

- `yfinance` package (automatically installed with project dependencies)
- Internet connection
- Yahoo Finance access (not blocked by firewall/network)

### Known Issues

**Yahoo Finance 403 Errors**: Yahoo Finance may block automated requests from certain environments or IP addresses. If you encounter HTTP 403 errors:

1. **Try from a different network**: Corporate/cloud networks may be blocked
2. **Use a VPN**: Route traffic through a different IP
3. **Manual update**: Edit `broker/stock_universe.csv` directly with current prices
4. **Wait and retry**: Temporary rate limiting may clear after some time

### Manual Price Updates

If the script doesn't work due to network restrictions, you can manually update prices:

1. Look up current prices on financial websites:
   - [Yahoo Finance](https://finance.yahoo.com/)
   - [Google Finance](https://www.google.com/finance/)
   - [MarketWatch](https://www.marketwatch.com/)

2. Edit `broker/stock_universe.csv` directly:
   ```csv
   symbol,last_price
   AAPL,230.10
   MSFT,416.50
   ...
   ```

### Last Updated

The stock_universe.csv was last updated on: **October 23, 2025**

Prices are approximate and based on recent market data. For production use, implement real-time price feeds or use a proper market data provider API.

### How It Works

The script:
1. Reads all symbols from the CSV file
2. Uses `yfinance.download()` to fetch the latest closing prices in batch
3. Compares new prices with old prices
4. Updates the CSV file (unless `--dry-run` is specified)
5. Shows a summary of changes with percentage movements

### Example Output

```
Found 20 stocks in broker/stock_universe.csv

Fetching current prices from Yahoo Finance...
--------------------------------------------------------------------------------
  ✓ AAPL    $  178.50 → $  230.10 (+ 51.60, +28.91%)
  ✗ MSFT    $  425.30 → $  416.50 (-  8.80, - 2.07%)
  ✓ GOOGL   $  142.75 → $  167.25 (+ 24.50, +17.16%)
  ...
--------------------------------------------------------------------------------

Summary:
  Updated:  20
  Failed:   0
  Total:    20

✓ Updated broker/stock_universe.csv
```

## Future Scripts

Additional scripts that could be added:

- `backup_database.py` - Backup the broker/client databases
- `generate_test_orders.py` - Create sample orders for testing
- `market_simulator.py` - Simulate price movements
- `performance_metrics.py` - Analyze order execution statistics
