"""
Unit tests for broker database models
"""
import pytest
import os
import tempfile
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from broker.models import (
    Base, Order, Execution, Stock,
    OrderSide, OrderType, TimeInForce, OrderStatus,
    init_db, get_session
)


@pytest.fixture
def test_db():
    """Create a temporary test database"""
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    engine, Session = init_db(db_path)
    session = Session()

    yield session

    session.close()
    os.unlink(db_path)


class TestStock:
    """Test Stock model"""

    def test_create_stock(self, test_db):
        """Test creating a stock"""
        stock = Stock(symbol='AAPL', last_price=150.50)
        test_db.add(stock)
        test_db.commit()

        assert stock.id is not None
        assert stock.symbol == 'AAPL'
        assert stock.last_price == 150.50
        assert stock.updated_at is not None

    def test_stock_unique_symbol(self, test_db):
        """Test that stock symbols must be unique"""
        stock1 = Stock(symbol='AAPL', last_price=150.50)
        test_db.add(stock1)
        test_db.commit()

        stock2 = Stock(symbol='AAPL', last_price=155.00)
        test_db.add(stock2)

        with pytest.raises(Exception):
            test_db.commit()

    def test_update_stock_price(self, test_db):
        """Test updating stock price"""
        stock = Stock(symbol='AAPL', last_price=150.50)
        test_db.add(stock)
        test_db.commit()

        original_updated_at = stock.updated_at

        stock.last_price = 155.00
        test_db.commit()

        assert stock.last_price == 155.00
        # Note: updated_at auto-update depends on SQLAlchemy configuration


class TestOrder:
    """Test Order model"""

    def test_create_market_order(self, test_db):
        """Test creating a market order"""
        order = Order(
            cl_ord_id='ORD123',
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
        test_db.add(order)
        test_db.commit()

        assert order.id is not None
        assert order.cl_ord_id == 'ORD123'
        assert order.symbol == 'AAPL'
        assert order.side == OrderSide.BUY
        assert order.order_type == OrderType.MARKET
        assert order.quantity == 100
        assert order.limit_price is None
        assert order.status == OrderStatus.NEW
        assert order.created_at is not None

    def test_create_limit_order(self, test_db):
        """Test creating a limit order"""
        order = Order(
            cl_ord_id='ORD124',
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
        test_db.add(order)
        test_db.commit()

        assert order.limit_price == 425.00
        assert order.time_in_force == TimeInForce.GTC

    def test_order_status_transitions(self, test_db):
        """Test order status transitions"""
        order = Order(
            cl_ord_id='ORD125',
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
        test_db.add(order)
        test_db.commit()

        # Partially fill
        order.status = OrderStatus.PARTIALLY_FILLED
        order.filled_quantity = 50
        order.remaining_quantity = 50
        test_db.commit()

        assert order.status == OrderStatus.PARTIALLY_FILLED
        assert order.filled_quantity == 50
        assert order.remaining_quantity == 50

        # Fully fill
        order.status = OrderStatus.FILLED
        order.filled_quantity = 100
        order.remaining_quantity = 0
        test_db.commit()

        assert order.status == OrderStatus.FILLED
        assert order.filled_quantity == 100
        assert order.remaining_quantity == 0

    def test_order_unique_cl_ord_id(self, test_db):
        """Test that client order IDs must be unique"""
        order1 = Order(
            cl_ord_id='ORD123',
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
        test_db.add(order1)
        test_db.commit()

        order2 = Order(
            cl_ord_id='ORD123',  # Duplicate
            sender_comp_id='CLIENT2',
            symbol='MSFT',
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=50,
            limit_price=None,
            time_in_force=TimeInForce.DAY,
            status=OrderStatus.NEW,
            filled_quantity=0,
            remaining_quantity=50
        )
        test_db.add(order2)

        with pytest.raises(Exception):
            test_db.commit()


class TestExecution:
    """Test Execution model"""

    def test_create_execution(self, test_db):
        """Test creating an execution"""
        # First create an order
        order = Order(
            cl_ord_id='ORD126',
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
        test_db.add(order)
        test_db.commit()

        # Create execution
        execution = Execution(
            order_id=order.id,
            exec_id='EXEC001',
            exec_quantity=50,
            exec_price=150.50
        )
        test_db.add(execution)
        test_db.commit()

        assert execution.id is not None
        assert execution.order_id == order.id
        assert execution.exec_id == 'EXEC001'
        assert execution.exec_quantity == 50
        assert execution.exec_price == 150.50
        assert execution.executed_at is not None

    def test_order_execution_relationship(self, test_db):
        """Test relationship between order and executions"""
        # Create order
        order = Order(
            cl_ord_id='ORD127',
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
        test_db.add(order)
        test_db.commit()

        # Create multiple executions
        exec1 = Execution(
            order_id=order.id,
            exec_id='EXEC001',
            exec_quantity=30,
            exec_price=150.50
        )
        exec2 = Execution(
            order_id=order.id,
            exec_id='EXEC002',
            exec_quantity=70,
            exec_price=151.00
        )
        test_db.add(exec1)
        test_db.add(exec2)
        test_db.commit()

        # Test relationship
        assert len(order.executions) == 2
        assert exec1 in order.executions
        assert exec2 in order.executions

        # Test back reference
        assert exec1.order == order
        assert exec2.order == order

    def test_execution_unique_exec_id(self, test_db):
        """Test that execution IDs must be unique"""
        order = Order(
            cl_ord_id='ORD128',
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
        test_db.add(order)
        test_db.commit()

        exec1 = Execution(
            order_id=order.id,
            exec_id='EXEC001',
            exec_quantity=50,
            exec_price=150.50
        )
        test_db.add(exec1)
        test_db.commit()

        exec2 = Execution(
            order_id=order.id,
            exec_id='EXEC001',  # Duplicate
            exec_quantity=50,
            exec_price=151.00
        )
        test_db.add(exec2)

        with pytest.raises(Exception):
            test_db.commit()


class TestOrderTimeInForce:
    """Test different Time in Force scenarios"""

    def test_day_order(self, test_db):
        """Test Day order"""
        order = Order(
            cl_ord_id='ORD_DAY',
            sender_comp_id='CLIENT1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=100,
            limit_price=150.00,
            time_in_force=TimeInForce.DAY,
            status=OrderStatus.NEW,
            filled_quantity=0,
            remaining_quantity=100
        )
        test_db.add(order)
        test_db.commit()

        assert order.time_in_force == TimeInForce.DAY

    def test_gtc_order(self, test_db):
        """Test GTC (Good Till Cancel) order"""
        order = Order(
            cl_ord_id='ORD_GTC',
            sender_comp_id='CLIENT1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=100,
            limit_price=150.00,
            time_in_force=TimeInForce.GTC,
            status=OrderStatus.NEW,
            filled_quantity=0,
            remaining_quantity=100
        )
        test_db.add(order)
        test_db.commit()

        assert order.time_in_force == TimeInForce.GTC

    def test_ioc_order(self, test_db):
        """Test IOC (Immediate or Cancel) order"""
        order = Order(
            cl_ord_id='ORD_IOC',
            sender_comp_id='CLIENT1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=100,
            limit_price=150.00,
            time_in_force=TimeInForce.IOC,
            status=OrderStatus.NEW,
            filled_quantity=0,
            remaining_quantity=100
        )
        test_db.add(order)
        test_db.commit()

        assert order.time_in_force == TimeInForce.IOC

    def test_fok_order(self, test_db):
        """Test FOK (Fill or Kill) order"""
        order = Order(
            cl_ord_id='ORD_FOK',
            sender_comp_id='CLIENT1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=100,
            limit_price=150.00,
            time_in_force=TimeInForce.FOK,
            status=OrderStatus.NEW,
            filled_quantity=0,
            remaining_quantity=100
        )
        test_db.add(order)
        test_db.commit()

        assert order.time_in_force == TimeInForce.FOK
