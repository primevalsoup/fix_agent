"""
Integration tests for broker Flask API
"""
import pytest
import os
import tempfile
import csv
import json

from broker.models import (
    init_db, get_session, Order, Stock, Execution,
    OrderSide, OrderType, TimeInForce, OrderStatus
)


@pytest.fixture
def test_db_path():
    """Create a temporary test database"""
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield db_path
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def test_csv_path():
    """Create a temporary CSV file for testing"""
    fd, csv_path = tempfile.mkstemp(suffix='.csv')
    os.close(fd)

    # Write test data
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['symbol', 'last_price'])
        writer.writerow(['AAPL', '150.50'])
        writer.writerow(['MSFT', '425.30'])
        writer.writerow(['GOOGL', '142.75'])

    yield csv_path
    if os.path.exists(csv_path):
        os.unlink(csv_path)


@pytest.fixture
def client(test_db_path, test_csv_path, monkeypatch):
    """Create Flask test client"""
    # Initialize database
    init_db(test_db_path)

    # Change working directory for CSV loading
    original_dir = os.getcwd()
    test_dir = os.path.dirname(test_csv_path)
    os.chdir(test_dir)

    # Rename CSV to stock_universe.csv
    if os.path.exists(test_csv_path):
        csv_path = os.path.join(test_dir, 'stock_universe.csv')
        if not os.path.exists(csv_path):
            os.rename(test_csv_path, csv_path)
    else:
        csv_path = os.path.join(test_dir, 'stock_universe.csv')

    # Patch get_session to use test database
    original_get_session = get_session
    def mock_get_session(db_path='broker.db'):
        return original_get_session(test_db_path)

    monkeypatch.setattr('broker.models.get_session', mock_get_session)
    monkeypatch.setattr('broker.app.get_session', mock_get_session)

    # Import app after patching
    from broker.app import app as flask_app, fix_server
    flask_app.config['TESTING'] = True

    # Stop FIX server
    fix_server.running = False

    with flask_app.test_client() as test_client:
        yield test_client

    os.chdir(original_dir)
    if os.path.exists(csv_path):
        os.unlink(csv_path)


class TestStockAPI:
    """Test stock universe API endpoints"""

    def test_get_stocks_empty(self, client, test_db_path):
        """Test getting stocks when database is empty"""
        response = client.get('/api/stocks')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_reload_stocks(self, client, test_db_path):
        """Test reloading stock universe from CSV"""
        response = client.post('/api/stocks/reload')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert data['count'] == 3

        # Verify stocks are in database
        session = get_session(test_db_path)
        stocks = session.query(Stock).all()
        assert len(stocks) == 3

        symbols = [s.symbol for s in stocks]
        assert 'AAPL' in symbols
        assert 'MSFT' in symbols
        assert 'GOOGL' in symbols

        session.close()

    def test_get_stocks_after_reload(self, client, test_db_path):
        """Test getting stocks after loading"""
        # Load stocks first
        client.post('/api/stocks/reload')

        # Get stocks
        response = client.get('/api/stocks')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert len(data) == 3

        # Check structure
        stock = data[0]
        assert 'id' in stock
        assert 'symbol' in stock
        assert 'last_price' in stock
        assert 'updated_at' in stock


class TestOrderAPI:
    """Test order API endpoints"""

    def test_get_orders_empty(self, client):
        """Test getting orders when database is empty"""
        response = client.get('/api/orders')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data == []

    def test_get_orders_with_data(self, client, test_db_path):
        """Test getting orders"""
        # Create test order
        session = get_session(test_db_path)
        order = Order(
            cl_ord_id='TEST_001',
            sender_comp_id='CLIENT1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=100,
            limit_price=None,
            time_in_force=TimeInForce.DAY,
            status=OrderStatus.NEW,
            filled_quantity=0,
            remaining_quantity=100
        )
        session.add(order)
        session.commit()
        session.close()

        # Get orders
        response = client.get('/api/orders')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert len(data) == 1
        assert data[0]['cl_ord_id'] == 'TEST_001'
        assert data[0]['symbol'] == 'AAPL'
        assert data[0]['side'] == 'BUY'

    def test_get_single_order(self, client, test_db_path):
        """Test getting a specific order"""
        # Create test order
        session = get_session(test_db_path)
        order = Order(
            cl_ord_id='TEST_002',
            sender_comp_id='CLIENT1',
            symbol='MSFT',
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=50,
            limit_price=425.00,
            time_in_force=TimeInForce.GTC,
            status=OrderStatus.NEW,
            filled_quantity=0,
            remaining_quantity=50
        )
        session.add(order)
        session.commit()
        order_id = order.id
        session.close()

        # Get order
        response = client.get(f'/api/orders/{order_id}')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['cl_ord_id'] == 'TEST_002'
        assert data['limit_price'] == 425.00
        assert 'executions' in data

    def test_get_nonexistent_order(self, client):
        """Test getting an order that doesn't exist"""
        response = client.get('/api/orders/99999')
        assert response.status_code == 404


class TestOrderExecution:
    """Test order execution endpoints"""

    def test_execute_market_order(self, client, test_db_path):
        """Test executing a market order"""
        # Load stocks
        client.post('/api/stocks/reload')

        # Create order
        session = get_session(test_db_path)
        order = Order(
            cl_ord_id='EXEC_001',
            sender_comp_id='CLIENT1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=100,
            limit_price=None,
            time_in_force=TimeInForce.DAY,
            status=OrderStatus.NEW,
            filled_quantity=0,
            remaining_quantity=100
        )
        session.add(order)
        session.commit()
        order_id = order.id
        session.close()

        # Execute order
        response = client.post(
            f'/api/orders/{order_id}/execute',
            data=json.dumps({}),
            content_type='application/json'
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True

        # Verify order is filled
        session = get_session(test_db_path)
        order = session.query(Order).filter_by(id=order_id).first()
        assert order.status == OrderStatus.FILLED
        assert order.filled_quantity == 100
        assert order.remaining_quantity == 0
        assert len(order.executions) == 1
        session.close()

    def test_execute_limit_order_valid_price(self, client, test_db_path):
        """Test executing limit order with valid price"""
        # Load stocks
        client.post('/api/stocks/reload')

        # Create buy limit order with acceptable price
        session = get_session(test_db_path)
        order = Order(
            cl_ord_id='EXEC_002',
            sender_comp_id='CLIENT1',
            symbol='AAPL',  # Price is 150.50
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=100,
            limit_price=151.00,  # Higher than last price, should execute
            time_in_force=TimeInForce.DAY,
            status=OrderStatus.NEW,
            filled_quantity=0,
            remaining_quantity=100
        )
        session.add(order)
        session.commit()
        order_id = order.id
        session.close()

        # Execute order
        response = client.post(
            f'/api/orders/{order_id}/execute',
            data=json.dumps({}),
            content_type='application/json'
        )
        assert response.status_code == 200

    def test_execute_limit_order_invalid_price(self, client, test_db_path):
        """Test executing limit order with invalid price"""
        # Load stocks
        client.post('/api/stocks/reload')

        # Create buy limit order with too low price
        session = get_session(test_db_path)
        order = Order(
            cl_ord_id='EXEC_003',
            sender_comp_id='CLIENT1',
            symbol='AAPL',  # Price is 150.50
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=100,
            limit_price=140.00,  # Lower than last price, should reject
            time_in_force=TimeInForce.DAY,
            status=OrderStatus.NEW,
            filled_quantity=0,
            remaining_quantity=100
        )
        session.add(order)
        session.commit()
        order_id = order.id
        session.close()

        # Try to execute order
        response = client.post(
            f'/api/orders/{order_id}/execute',
            data=json.dumps({}),
            content_type='application/json'
        )
        assert response.status_code == 400

        data = json.loads(response.data)
        assert 'error' in data
        assert 'limit price' in data['error'].lower()

    def test_partial_execution(self, client, test_db_path):
        """Test partial order execution"""
        # Load stocks
        client.post('/api/stocks/reload')

        # Create order
        session = get_session(test_db_path)
        order = Order(
            cl_ord_id='EXEC_004',
            sender_comp_id='CLIENT1',
            symbol='MSFT',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=100,
            limit_price=None,
            time_in_force=TimeInForce.DAY,
            status=OrderStatus.NEW,
            filled_quantity=0,
            remaining_quantity=100
        )
        session.add(order)
        session.commit()
        order_id = order.id
        session.close()

        # Partially execute
        response = client.post(
            f'/api/orders/{order_id}/execute',
            data=json.dumps({'quantity': 50}),
            content_type='application/json'
        )
        assert response.status_code == 200

        # Verify partial fill
        session = get_session(test_db_path)
        order = session.query(Order).filter_by(id=order_id).first()
        assert order.status == OrderStatus.PARTIALLY_FILLED
        assert order.filled_quantity == 50
        assert order.remaining_quantity == 50
        session.close()


class TestOrderCancel:
    """Test order cancellation"""

    def test_cancel_order(self, client, test_db_path):
        """Test canceling an order"""
        # Create order
        session = get_session(test_db_path)
        order = Order(
            cl_ord_id='CANCEL_001',
            sender_comp_id='CLIENT1',
            symbol='GOOGL',
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=100,
            limit_price=145.00,
            time_in_force=TimeInForce.DAY,
            status=OrderStatus.NEW,
            filled_quantity=0,
            remaining_quantity=100
        )
        session.add(order)
        session.commit()
        order_id = order.id
        session.close()

        # Cancel order
        response = client.post(f'/api/orders/{order_id}/cancel')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True

        # Verify cancellation
        session = get_session(test_db_path)
        order = session.query(Order).filter_by(id=order_id).first()
        assert order.status == OrderStatus.CANCELED
        session.close()


class TestOrderReject:
    """Test order rejection"""

    def test_reject_order(self, client, test_db_path):
        """Test rejecting an order"""
        # Create order
        session = get_session(test_db_path)
        order = Order(
            cl_ord_id='REJECT_001',
            sender_comp_id='CLIENT1',
            symbol='INVALID',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=100,
            limit_price=None,
            time_in_force=TimeInForce.DAY,
            status=OrderStatus.NEW,
            filled_quantity=0,
            remaining_quantity=100
        )
        session.add(order)
        session.commit()
        order_id = order.id
        session.close()

        # Reject order
        response = client.post(
            f'/api/orders/{order_id}/reject',
            data=json.dumps({'reason': 'Invalid symbol'}),
            content_type='application/json'
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True

        # Verify rejection
        session = get_session(test_db_path)
        order = session.query(Order).filter_by(id=order_id).first()
        assert order.status == OrderStatus.REJECTED
        assert order.reject_reason == 'Invalid symbol'
        session.close()
