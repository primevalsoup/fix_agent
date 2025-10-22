"""
Unit tests for client database models
"""
import pytest
import os
import tempfile
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from client.models import (
    Base, Order, Execution,
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


class TestClientOrder:
    """Test Client Order model"""

    def test_create_pending_order(self, test_db):
        """Test creating an order in PENDING_NEW status"""
        order = Order(
            cl_ord_id='CLIENT_ORD_001',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=100,
            limit_price=None,
            time_in_force=TimeInForce.DAY,
            status=OrderStatus.PENDING_NEW,
            filled_quantity=0,
            remaining_quantity=100
        )
        test_db.add(order)
        test_db.commit()

        assert order.id is not None
        assert order.status == OrderStatus.PENDING_NEW
        assert order.cl_ord_id == 'CLIENT_ORD_001'

    def test_order_status_progression(self, test_db):
        """Test order status progression from PENDING_NEW to FILLED"""
        order = Order(
            cl_ord_id='CLIENT_ORD_002',
            symbol='MSFT',
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=100,
            limit_price=425.00,
            time_in_force=TimeInForce.GTC,
            status=OrderStatus.PENDING_NEW,
            filled_quantity=0,
            remaining_quantity=100
        )
        test_db.add(order)
        test_db.commit()

        # Broker acknowledges
        order.status = OrderStatus.NEW
        test_db.commit()
        assert order.status == OrderStatus.NEW

        # Partial fill
        order.status = OrderStatus.PARTIALLY_FILLED
        order.filled_quantity = 50
        order.remaining_quantity = 50
        test_db.commit()
        assert order.status == OrderStatus.PARTIALLY_FILLED

        # Full fill
        order.status = OrderStatus.FILLED
        order.filled_quantity = 100
        order.remaining_quantity = 0
        test_db.commit()
        assert order.status == OrderStatus.FILLED

    def test_rejected_order(self, test_db):
        """Test rejected order with reason"""
        order = Order(
            cl_ord_id='CLIENT_ORD_003',
            symbol='INVALID',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=100,
            limit_price=None,
            time_in_force=TimeInForce.DAY,
            status=OrderStatus.PENDING_NEW,
            filled_quantity=0,
            remaining_quantity=100
        )
        test_db.add(order)
        test_db.commit()

        # Broker rejects
        order.status = OrderStatus.REJECTED
        order.reject_reason = "Unknown symbol"
        test_db.commit()

        assert order.status == OrderStatus.REJECTED
        assert order.reject_reason == "Unknown symbol"

    def test_canceled_order(self, test_db):
        """Test canceled order"""
        order = Order(
            cl_ord_id='CLIENT_ORD_004',
            symbol='AAPL',
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=50,
            limit_price=180.00,
            time_in_force=TimeInForce.DAY,
            status=OrderStatus.NEW,
            filled_quantity=0,
            remaining_quantity=50
        )
        test_db.add(order)
        test_db.commit()

        # Cancel order
        order.status = OrderStatus.CANCELED
        test_db.commit()

        assert order.status == OrderStatus.CANCELED


class TestClientExecution:
    """Test Client Execution model"""

    def test_create_execution_from_broker(self, test_db):
        """Test creating execution report received from broker"""
        # Create order
        order = Order(
            cl_ord_id='CLIENT_ORD_005',
            symbol='GOOGL',
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

        # Receive execution from broker
        execution = Execution(
            order_id=order.id,
            exec_id='BROKER_EXEC_001',
            exec_quantity=100,
            exec_price=142.75
        )
        test_db.add(execution)
        test_db.commit()

        assert execution.id is not None
        assert execution.exec_id == 'BROKER_EXEC_001'
        assert execution.exec_quantity == 100
        assert execution.exec_price == 142.75

    def test_multiple_executions(self, test_db):
        """Test order with multiple partial executions"""
        order = Order(
            cl_ord_id='CLIENT_ORD_006',
            symbol='TSLA',
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=100,
            limit_price=240.00,
            time_in_force=TimeInForce.GTC,
            status=OrderStatus.NEW,
            filled_quantity=0,
            remaining_quantity=100
        )
        test_db.add(order)
        test_db.commit()

        # First partial execution
        exec1 = Execution(
            order_id=order.id,
            exec_id='BROKER_EXEC_002',
            exec_quantity=30,
            exec_price=242.50
        )
        test_db.add(exec1)
        order.filled_quantity = 30
        order.remaining_quantity = 70
        order.status = OrderStatus.PARTIALLY_FILLED
        test_db.commit()

        # Second partial execution
        exec2 = Execution(
            order_id=order.id,
            exec_id='BROKER_EXEC_003',
            exec_quantity=70,
            exec_price=243.00
        )
        test_db.add(exec2)
        order.filled_quantity = 100
        order.remaining_quantity = 0
        order.status = OrderStatus.FILLED
        test_db.commit()

        # Verify
        assert len(order.executions) == 2
        assert order.filled_quantity == 100
        assert order.status == OrderStatus.FILLED

        # Calculate average price
        total_value = sum(e.exec_quantity * e.exec_price for e in order.executions)
        avg_price = total_value / order.filled_quantity
        assert avg_price == pytest.approx(242.85, 0.01)


class TestClientOrderTypes:
    """Test different order types on client side"""

    def test_market_order(self, test_db):
        """Test market order creation"""
        order = Order(
            cl_ord_id='MKT_001',
            symbol='NVDA',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=25,
            limit_price=None,
            time_in_force=TimeInForce.DAY,
            status=OrderStatus.PENDING_NEW,
            filled_quantity=0,
            remaining_quantity=25
        )
        test_db.add(order)
        test_db.commit()

        assert order.order_type == OrderType.MARKET
        assert order.limit_price is None

    def test_limit_order(self, test_db):
        """Test limit order creation"""
        order = Order(
            cl_ord_id='LMT_001',
            symbol='NVDA',
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=25,
            limit_price=880.00,
            time_in_force=TimeInForce.GTC,
            status=OrderStatus.PENDING_NEW,
            filled_quantity=0,
            remaining_quantity=25
        )
        test_db.add(order)
        test_db.commit()

        assert order.order_type == OrderType.LIMIT
        assert order.limit_price == 880.00


class TestClientTimeInForce:
    """Test Time in Force options for client orders"""

    def test_day_order_client(self, test_db):
        """Test DAY time in force"""
        order = Order(
            cl_ord_id='DAY_001',
            symbol='JPM',
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=100,
            limit_price=195.00,
            time_in_force=TimeInForce.DAY,
            status=OrderStatus.PENDING_NEW,
            filled_quantity=0,
            remaining_quantity=100
        )
        test_db.add(order)
        test_db.commit()

        assert order.time_in_force == TimeInForce.DAY

    def test_gtc_order_client(self, test_db):
        """Test GTC time in force"""
        order = Order(
            cl_ord_id='GTC_001',
            symbol='JPM',
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=100,
            limit_price=195.00,
            time_in_force=TimeInForce.GTC,
            status=OrderStatus.PENDING_NEW,
            filled_quantity=0,
            remaining_quantity=100
        )
        test_db.add(order)
        test_db.commit()

        assert order.time_in_force == TimeInForce.GTC

    def test_ioc_order_client(self, test_db):
        """Test IOC time in force"""
        order = Order(
            cl_ord_id='IOC_001',
            symbol='V',
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=50,
            limit_price=270.00,
            time_in_force=TimeInForce.IOC,
            status=OrderStatus.PENDING_NEW,
            filled_quantity=0,
            remaining_quantity=50
        )
        test_db.add(order)
        test_db.commit()

        assert order.time_in_force == TimeInForce.IOC

    def test_fok_order_client(self, test_db):
        """Test FOK time in force"""
        order = Order(
            cl_ord_id='FOK_001',
            symbol='V',
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=50,
            limit_price=275.00,
            time_in_force=TimeInForce.FOK,
            status=OrderStatus.PENDING_NEW,
            filled_quantity=0,
            remaining_quantity=50
        )
        test_db.add(order)
        test_db.commit()

        assert order.time_in_force == TimeInForce.FOK
