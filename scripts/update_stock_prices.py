#!/usr/bin/env python3
"""
Update stock_universe.csv with current prices from Yahoo Finance

Usage:
    uv run python scripts/update_stock_prices.py

Or directly:
    python scripts/update_stock_prices.py
"""

import csv
import os
import sys
from pathlib import Path

try:
    import yfinance as yf
except ImportError:
    print("Error: yfinance is not installed.")
    print("Please install it with: uv pip install yfinance")
    sys.exit(1)


def update_stock_prices(csv_path='broker/stock_universe.csv', dry_run=False):
    """
    Update stock prices in the CSV file using Yahoo Finance

    Args:
        csv_path: Path to the stock_universe.csv file
        dry_run: If True, don't update the file, just show what would change
    """
    # Read current CSV
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        return False

    stocks = []
    symbols = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            stocks.append(row)
            symbols.append(row['symbol'])

    print(f"Found {len(stocks)} stocks in {csv_path}")
    print("\nFetching current prices from Yahoo Finance...")
    print("-" * 80)

    # Fetch prices for all symbols at once (more reliable)
    try:
        # Download data for all symbols
        data = yf.download(
            tickers=' '.join(symbols),
            period='1d',
            progress=False
        )

        # Extract closing prices
        if len(symbols) == 1:
            # Single stock case
            prices = {symbols[0]: data['Close'].iloc[-1] if not data.empty else None}
        else:
            # Multiple stocks case
            if 'Close' in data.columns:
                prices = data['Close'].iloc[-1].to_dict()
            else:
                prices = {}

    except Exception as e:
        print(f"Error fetching data: {e}")
        return False

    # Update stocks with new prices
    updated_count = 0
    failed_count = 0

    for stock in stocks:
        symbol = stock['symbol']
        old_price = float(stock['last_price'])

        current_price = prices.get(symbol)

        if current_price is None or current_price != current_price:  # None or NaN
            print(f"  {symbol:6s} - FAILED: Could not fetch price")
            failed_count += 1
            continue

        # Round to 2 decimal places
        current_price = round(float(current_price), 2)

        # Calculate change
        change = current_price - old_price
        change_pct = (change / old_price) * 100 if old_price > 0 else 0

        # Update the stock dict
        stock['last_price'] = f"{current_price:.2f}"

        # Print status
        status = "✓" if change >= 0 else "✗"
        print(f"  {status} {symbol:6s} ${old_price:8.2f} → ${current_price:8.2f} "
              f"({change:+7.2f}, {change_pct:+6.2f}%)")

        updated_count += 1

    print("-" * 80)
    print(f"\nSummary:")
    print(f"  Updated:  {updated_count}")
    print(f"  Failed:   {failed_count}")
    print(f"  Total:    {len(stocks)}")

    # Write updated CSV
    if not dry_run and updated_count > 0:
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['symbol', 'last_price'])
            writer.writeheader()
            writer.writerows(stocks)
        print(f"\n✓ Updated {csv_path}")
    elif dry_run:
        print(f"\n(Dry run - no changes written to {csv_path})")
    else:
        print(f"\n✗ No prices were updated")

    return updated_count > 0


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Update stock prices in stock_universe.csv from Yahoo Finance'
    )
    parser.add_argument(
        '--csv',
        default='broker/stock_universe.csv',
        help='Path to stock_universe.csv (default: broker/stock_universe.csv)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would change without updating the file'
    )

    args = parser.parse_args()

    # Change to project root if running from scripts/ directory
    if os.path.basename(os.getcwd()) == 'scripts':
        os.chdir('..')

    success = update_stock_prices(args.csv, args.dry_run)

    if success:
        print("\n✓ Stock prices updated successfully!")
        return 0
    else:
        print("\n✗ Failed to update stock prices")
        return 1


if __name__ == '__main__':
    sys.exit(main())
