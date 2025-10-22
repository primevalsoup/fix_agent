"""
Tests for stock universe CSV loading
"""
import pytest
import os
import tempfile
import csv

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../broker'))

from models import init_db, get_session, Stock


@pytest.fixture
def test_db_path():
    """Create a temporary test database"""
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    init_db(db_path)
    yield db_path
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def sample_csv():
    """Create a sample CSV file"""
    fd, csv_path = tempfile.mkstemp(suffix='.csv')
    os.close(fd)

    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['symbol', 'last_price'])
        writer.writerow(['AAPL', '150.50'])
        writer.writerow(['MSFT', '425.30'])
        writer.writerow(['GOOGL', '142.75'])
        writer.writerow(['AMZN', '168.90'])
        writer.writerow(['TSLA', '242.80'])

    yield csv_path
    if os.path.exists(csv_path):
        os.unlink(csv_path)


class TestStockUniverseLoading:
    """Test loading stock universe from CSV"""

    def test_load_stocks_from_csv(self, test_db_path, sample_csv):
        """Test loading stocks from CSV file"""
        session = get_session(test_db_path)

        # Load from CSV
        with open(sample_csv, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stock = Stock(
                    symbol=row['symbol'],
                    last_price=float(row['last_price'])
                )
                session.add(stock)

        session.commit()

        # Verify
        stocks = session.query(Stock).all()
        assert len(stocks) == 5

        # Check specific stocks
        aapl = session.query(Stock).filter_by(symbol='AAPL').first()
        assert aapl is not None
        assert aapl.last_price == 150.50

        msft = session.query(Stock).filter_by(symbol='MSFT').first()
        assert msft is not None
        assert msft.last_price == 425.30

        session.close()

    def test_reload_stocks_updates_database(self, test_db_path, sample_csv):
        """Test that reloading stocks clears old data"""
        session = get_session(test_db_path)

        # Load initial stocks
        with open(sample_csv, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stock = Stock(
                    symbol=row['symbol'],
                    last_price=float(row['last_price'])
                )
                session.add(stock)
        session.commit()

        assert session.query(Stock).count() == 5

        # Clear and reload
        session.query(Stock).delete()

        with open(sample_csv, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stock = Stock(
                    symbol=row['symbol'],
                    last_price=float(row['last_price'])
                )
                session.add(stock)
        session.commit()

        # Should still have same count
        assert session.query(Stock).count() == 5

        session.close()

    def test_update_stock_prices(self, test_db_path, sample_csv):
        """Test updating stock prices"""
        session = get_session(test_db_path)

        # Load stocks
        with open(sample_csv, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stock = Stock(
                    symbol=row['symbol'],
                    last_price=float(row['last_price'])
                )
                session.add(stock)
        session.commit()

        # Update price
        aapl = session.query(Stock).filter_by(symbol='AAPL').first()
        old_price = aapl.last_price
        aapl.last_price = 155.75
        session.commit()

        # Verify update
        aapl = session.query(Stock).filter_by(symbol='AAPL').first()
        assert aapl.last_price == 155.75
        assert aapl.last_price != old_price

        session.close()

    def test_empty_csv(self, test_db_path):
        """Test loading from empty CSV"""
        fd, csv_path = tempfile.mkstemp(suffix='.csv')
        os.close(fd)

        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['symbol', 'last_price'])
            # No data rows

        session = get_session(test_db_path)

        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stock = Stock(
                    symbol=row['symbol'],
                    last_price=float(row['last_price'])
                )
                session.add(stock)

        session.commit()

        # Should have no stocks
        assert session.query(Stock).count() == 0

        session.close()
        os.unlink(csv_path)

    def test_csv_with_invalid_price(self, test_db_path):
        """Test CSV with invalid price data"""
        fd, csv_path = tempfile.mkstemp(suffix='.csv')
        os.close(fd)

        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['symbol', 'last_price'])
            writer.writerow(['AAPL', 'invalid'])

        session = get_session(test_db_path)

        with pytest.raises(ValueError):
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    stock = Stock(
                        symbol=row['symbol'],
                        last_price=float(row['last_price'])  # Should raise ValueError
                    )
                    session.add(stock)

        session.close()
        os.unlink(csv_path)

    def test_large_stock_universe(self, test_db_path):
        """Test loading a large number of stocks"""
        fd, csv_path = tempfile.mkstemp(suffix='.csv')
        os.close(fd)

        # Create CSV with 100 stocks
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['symbol', 'last_price'])
            for i in range(100):
                writer.writerow([f'SYM{i:03d}', f'{100.0 + i}'])

        session = get_session(test_db_path)

        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stock = Stock(
                    symbol=row['symbol'],
                    last_price=float(row['last_price'])
                )
                session.add(stock)

        session.commit()

        # Verify count
        assert session.query(Stock).count() == 100

        # Verify first and last
        first = session.query(Stock).filter_by(symbol='SYM000').first()
        assert first.last_price == 100.0

        last = session.query(Stock).filter_by(symbol='SYM099').first()
        assert last.last_price == 199.0

        session.close()
        os.unlink(csv_path)


class TestStockQueries:
    """Test querying stocks from database"""

    def test_query_by_symbol(self, test_db_path, sample_csv):
        """Test querying stocks by symbol"""
        session = get_session(test_db_path)

        # Load stocks
        with open(sample_csv, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stock = Stock(
                    symbol=row['symbol'],
                    last_price=float(row['last_price'])
                )
                session.add(stock)
        session.commit()

        # Query
        stock = session.query(Stock).filter_by(symbol='TSLA').first()
        assert stock is not None
        assert stock.symbol == 'TSLA'
        assert stock.last_price == 242.80

        session.close()

    def test_query_nonexistent_symbol(self, test_db_path, sample_csv):
        """Test querying a symbol that doesn't exist"""
        session = get_session(test_db_path)

        # Load stocks
        with open(sample_csv, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stock = Stock(
                    symbol=row['symbol'],
                    last_price=float(row['last_price'])
                )
                session.add(stock)
        session.commit()

        # Query
        stock = session.query(Stock).filter_by(symbol='INVALID').first()
        assert stock is None

        session.close()

    def test_get_all_stocks(self, test_db_path, sample_csv):
        """Test getting all stocks"""
        session = get_session(test_db_path)

        # Load stocks
        with open(sample_csv, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stock = Stock(
                    symbol=row['symbol'],
                    last_price=float(row['last_price'])
                )
                session.add(stock)
        session.commit()

        # Get all
        stocks = session.query(Stock).all()
        assert len(stocks) == 5

        symbols = [s.symbol for s in stocks]
        assert 'AAPL' in symbols
        assert 'MSFT' in symbols
        assert 'GOOGL' in symbols
        assert 'AMZN' in symbols
        assert 'TSLA' in symbols

        session.close()
