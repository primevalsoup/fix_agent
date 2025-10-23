"""
Integration tests for FIX protocol communication
Tests actual FIX client-server communication over sockets
"""
import pytest
import socket
import time
import os
import tempfile
import simplefix
from datetime import datetime

from broker.models import init_db, get_session, Order, Stock, OrderStatus, OrderSide
from broker.fix_server import FIXServer


class FIXTestClient:
    """Test FIX client for integration testing"""

    def __init__(self, sender_comp_id='TEST_CLIENT', target_comp_id='BROKER',
                 host='localhost', port=5001):
        self.sender_comp_id = sender_comp_id
        self.target_comp_id = target_comp_id
        self.host = host
        self.port = port
        self.socket = None
        self.msg_seq_num = 1
        self.connected = False

    def connect(self, timeout=5):
        """Connect to FIX server"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(timeout)

        # Try to connect with retries
        max_retries = 10
        for i in range(max_retries):
            try:
                self.socket.connect((self.host, self.port))
                self.connected = True
                return True
            except ConnectionRefusedError:
                if i < max_retries - 1:
                    time.sleep(0.1)
                else:
                    raise
        return False

    def disconnect(self):
        """Disconnect from FIX server"""
        if self.socket:
            self.socket.close()
            self.connected = False

    def send_logon(self):
        """Send Logon message"""
        msg = simplefix.FixMessage()
        msg.append_pair(simplefix.TAG_BEGINSTRING, "FIX.4.2")
        msg.append_pair(simplefix.TAG_MSGTYPE, simplefix.MSGTYPE_LOGON)
        msg.append_pair(simplefix.TAG_SENDER_COMPID, self.sender_comp_id)
        msg.append_pair(simplefix.TAG_TARGET_COMPID, self.target_comp_id)
        msg.append_pair(simplefix.TAG_MSGSEQNUM, self.msg_seq_num)
        msg.append_pair(98, 0)  # EncryptMethod: None
        msg.append_pair(108, 30)  # HeartBtInt: 30 seconds
        msg.append_utc_timestamp(simplefix.TAG_SENDING_TIME)

        self._send_message(msg)
        return self._receive_message()

    def send_new_order(self, symbol, side, quantity, order_type='MARKET',
                       price=None, time_in_force='DAY', cl_ord_id=None):
        """Send NewOrderSingle message"""
        if cl_ord_id is None:
            cl_ord_id = f"ORD_{int(time.time() * 1000)}"

        msg = simplefix.FixMessage()
        msg.append_pair(simplefix.TAG_BEGINSTRING, "FIX.4.2")
        msg.append_pair(simplefix.TAG_MSGTYPE, simplefix.MSGTYPE_NEW_ORDER_SINGLE)
        msg.append_pair(simplefix.TAG_SENDER_COMPID, self.sender_comp_id)
        msg.append_pair(simplefix.TAG_TARGET_COMPID, self.target_comp_id)
        msg.append_pair(simplefix.TAG_MSGSEQNUM, self.msg_seq_num)

        # Order details
        msg.append_pair(simplefix.TAG_CLORDID, cl_ord_id)
        msg.append_pair(simplefix.TAG_SYMBOL, symbol)
        msg.append_pair(simplefix.TAG_SIDE, '1' if side == 'BUY' else '2')
        msg.append_pair(simplefix.TAG_ORDERQTY, quantity)
        msg.append_pair(simplefix.TAG_ORDTYPE, '1' if order_type == 'MARKET' else '2')

        if price:
            msg.append_pair(simplefix.TAG_PRICE, price)

        # Time in force
        tif_map = {'DAY': '0', 'GTC': '1', 'IOC': '3', 'FOK': '4'}
        msg.append_pair(simplefix.TAG_TIMEINFORCE, tif_map.get(time_in_force, '0'))

        msg.append_utc_timestamp(simplefix.TAG_SENDING_TIME)

        self._send_message(msg)
        return self._receive_message()

    def send_heartbeat(self, test_req_id=None):
        """Send Heartbeat message"""
        msg = simplefix.FixMessage()
        msg.append_pair(simplefix.TAG_BEGINSTRING, "FIX.4.2")
        msg.append_pair(simplefix.TAG_MSGTYPE, simplefix.MSGTYPE_HEARTBEAT)
        msg.append_pair(simplefix.TAG_SENDER_COMPID, self.sender_comp_id)
        msg.append_pair(simplefix.TAG_TARGET_COMPID, self.target_comp_id)
        msg.append_pair(simplefix.TAG_MSGSEQNUM, self.msg_seq_num)

        if test_req_id:
            msg.append_pair(112, test_req_id)  # TestReqID

        msg.append_utc_timestamp(simplefix.TAG_SENDING_TIME)

        self._send_message(msg)

    def _send_message(self, msg):
        """Send FIX message"""
        encoded = msg.encode()
        self.socket.send(encoded)
        self.msg_seq_num += 1

    def _receive_message(self, timeout=2):
        """Receive FIX message"""
        self.socket.settimeout(timeout)
        buffer = b''

        try:
            # Receive data
            data = self.socket.recv(4096)
            if data:
                buffer += data

            # Use FixParser to parse the buffer
            parser = simplefix.FixParser()
            parser.append_buffer(buffer)
            msg = parser.get_message()

            return msg

        except socket.timeout:
            return None
        except Exception as e:
            print(f"Error receiving message: {e}")
            return None


@pytest.fixture(scope='session')
def test_db_path():
    """Create temporary test database"""
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    # Initialize database
    init_db(db_path)

    # Add test stocks
    session = get_session(db_path)
    stocks = [
        Stock(symbol='AAPL', last_price=150.50),
        Stock(symbol='MSFT', last_price=425.30),
        Stock(symbol='GOOGL', last_price=142.75),
    ]
    for stock in stocks:
        session.add(stock)
    session.commit()
    session.close()

    yield db_path

    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture(scope='session')
def fix_server(test_db_path, tmp_path_factory):
    """Start FIX server for testing"""
    # Monkey patch get_session to use test database
    import broker.fix_server
    original_get_session = broker.fix_server.get_session
    broker.fix_server.get_session = lambda: get_session(test_db_path)

    # Create server with unique port for testing
    tmp_path = tmp_path_factory.mktemp('fix_logs')
    server = FIXServer(host='localhost', port=15001, log_dir=str(tmp_path))
    server.start()

    # Wait for server to start
    time.sleep(0.5)

    yield server

    # Cleanup
    server.stop()
    time.sleep(0.2)
    broker.fix_server.get_session = original_get_session


@pytest.fixture
def fix_client(fix_server):
    """Create FIX test client"""
    client = FIXTestClient(port=15001)
    client.connect()

    yield client

    client.disconnect()


class TestFIXConnection:
    """Test FIX connection and session management"""

    def test_connect_to_server(self, fix_server):
        """Test basic connection to FIX server"""
        client = FIXTestClient(port=15001)
        assert client.connect()
        client.disconnect()

    def test_logon(self, fix_client):
        """Test FIX Logon message"""
        response = fix_client.send_logon()

        assert response is not None
        assert response.get(simplefix.TAG_MSGTYPE) == simplefix.MSGTYPE_LOGON
        assert response.get(simplefix.TAG_SENDER_COMPID) == b'BROKER'
        assert response.get(simplefix.TAG_TARGET_COMPID) == b'TEST_CLIENT'

    def test_heartbeat(self, fix_client):
        """Test heartbeat message"""
        # First logon
        fix_client.send_logon()

        # Send heartbeat
        fix_client.send_heartbeat()

        # Should not crash
        assert fix_client.connected


class TestFIXOrderSubmission:
    """Test order submission via FIX"""

    def test_submit_market_order(self, fix_client, test_db_path):
        """Test submitting a market order via FIX"""
        # Logon first
        fix_client.send_logon()
        time.sleep(0.1)

        # Send market order
        cl_ord_id = "TEST_MARKET_001"
        response = fix_client.send_new_order(
            symbol='AAPL',
            side='BUY',
            quantity=100,
            order_type='MARKET',
            time_in_force='DAY',
            cl_ord_id=cl_ord_id
        )

        # Verify execution report received
        assert response is not None
        assert response.get(simplefix.TAG_MSGTYPE) == simplefix.MSGTYPE_EXECUTION_REPORT
        assert response.get(simplefix.TAG_CLORDID) == cl_ord_id.encode('utf-8')
        assert response.get(simplefix.TAG_SYMBOL) == b'AAPL'
        assert response.get(39) == b'0'  # OrdStatus: New

        # Verify order in database
        time.sleep(0.1)
        session = get_session(test_db_path)
        order = session.query(Order).filter_by(cl_ord_id=cl_ord_id).first()

        assert order is not None
        assert order.symbol == 'AAPL'
        assert order.side == OrderSide.BUY
        assert order.quantity == 100
        assert order.status == OrderStatus.NEW

        session.close()

    def test_submit_limit_order(self, fix_client, test_db_path):
        """Test submitting a limit order via FIX"""
        # Logon
        fix_client.send_logon()
        time.sleep(0.1)

        # Send limit order
        cl_ord_id = "TEST_LIMIT_001"
        response = fix_client.send_new_order(
            symbol='MSFT',
            side='SELL',
            quantity=50,
            order_type='LIMIT',
            price=430.00,
            time_in_force='GTC',
            cl_ord_id=cl_ord_id
        )

        # Verify execution report
        assert response is not None
        assert response.get(simplefix.TAG_MSGTYPE) == simplefix.MSGTYPE_EXECUTION_REPORT
        assert response.get(simplefix.TAG_CLORDID) == cl_ord_id.encode('utf-8')

        # Verify in database
        time.sleep(0.1)
        session = get_session(test_db_path)
        order = session.query(Order).filter_by(cl_ord_id=cl_ord_id).first()

        assert order is not None
        assert order.symbol == 'MSFT'
        assert order.limit_price == 430.00
        assert order.status == OrderStatus.NEW

        session.close()

    def test_multiple_orders(self, fix_client, test_db_path):
        """Test submitting multiple orders"""
        # Logon
        fix_client.send_logon()
        time.sleep(0.1)

        # Send multiple orders
        orders = [
            ('AAPL', 'BUY', 100),
            ('MSFT', 'SELL', 50),
            ('GOOGL', 'BUY', 75),
        ]

        for i, (symbol, side, qty) in enumerate(orders):
            response = fix_client.send_new_order(
                symbol=symbol,
                side=side,
                quantity=qty,
                order_type='MARKET',
                cl_ord_id=f'MULTI_{i}'
            )
            assert response is not None
            time.sleep(0.05)

        # Verify all orders in database
        time.sleep(0.1)
        session = get_session(test_db_path)
        db_orders = session.query(Order).all()

        assert len(db_orders) >= 3
        session.close()


class TestFIXOrderTypes:
    """Test different order types via FIX"""

    def test_day_order(self, fix_client, test_db_path):
        """Test Day time in force"""
        fix_client.send_logon()
        time.sleep(0.1)

        cl_ord_id = "TEST_DAY"
        fix_client.send_new_order(
            symbol='AAPL',
            side='BUY',
            quantity=100,
            order_type='MARKET',
            time_in_force='DAY',
            cl_ord_id=cl_ord_id
        )

        time.sleep(0.1)
        session = get_session(test_db_path)
        order = session.query(Order).filter_by(cl_ord_id=cl_ord_id).first()
        assert order is not None
        assert order.time_in_force.value == 'DAY'
        session.close()

    def test_gtc_order(self, fix_client, test_db_path):
        """Test GTC time in force"""
        fix_client.send_logon()
        time.sleep(0.1)

        cl_ord_id = "TEST_GTC"
        fix_client.send_new_order(
            symbol='MSFT',
            side='SELL',
            quantity=50,
            order_type='LIMIT',
            price=420.00,
            time_in_force='GTC',
            cl_ord_id=cl_ord_id
        )

        time.sleep(0.1)
        session = get_session(test_db_path)
        order = session.query(Order).filter_by(cl_ord_id=cl_ord_id).first()
        assert order is not None
        assert order.time_in_force.value == 'GTC'
        session.close()

    def test_ioc_order(self, fix_client, test_db_path):
        """Test IOC time in force"""
        fix_client.send_logon()
        time.sleep(0.1)

        cl_ord_id = "TEST_IOC"
        fix_client.send_new_order(
            symbol='GOOGL',
            side='BUY',
            quantity=25,
            order_type='LIMIT',
            price=145.00,
            time_in_force='IOC',
            cl_ord_id=cl_ord_id
        )

        time.sleep(0.1)
        session = get_session(test_db_path)
        order = session.query(Order).filter_by(cl_ord_id=cl_ord_id).first()
        assert order is not None
        assert order.time_in_force.value == 'IOC'
        session.close()

    def test_fok_order(self, fix_client, test_db_path):
        """Test FOK time in force"""
        fix_client.send_logon()
        time.sleep(0.1)

        cl_ord_id = "TEST_FOK"
        fix_client.send_new_order(
            symbol='AAPL',
            side='SELL',
            quantity=200,
            order_type='LIMIT',
            price=148.00,
            time_in_force='FOK',
            cl_ord_id=cl_ord_id
        )

        time.sleep(0.1)
        session = get_session(test_db_path)
        order = session.query(Order).filter_by(cl_ord_id=cl_ord_id).first()
        assert order is not None
        assert order.time_in_force.value == 'FOK'
        session.close()


class TestFIXMessageFlow:
    """Test complete FIX message flows"""

    def test_order_lifecycle(self, fix_client, test_db_path):
        """Test complete order lifecycle via FIX"""
        # Logon
        logon_resp = fix_client.send_logon()
        assert logon_resp is not None

        time.sleep(0.1)

        # Submit order
        cl_ord_id = "LIFECYCLE_001"
        order_resp = fix_client.send_new_order(
            symbol='AAPL',
            side='BUY',
            quantity=100,
            order_type='MARKET',
            cl_ord_id=cl_ord_id
        )

        # Should receive ExecutionReport with status NEW
        assert order_resp is not None
        assert order_resp.get(simplefix.TAG_MSGTYPE) == simplefix.MSGTYPE_EXECUTION_REPORT
        assert order_resp.get(150) == b'0'  # ExecType: New
        assert order_resp.get(39) == b'0'   # OrdStatus: New

        # Verify in database
        time.sleep(0.1)
        session = get_session(test_db_path)
        order = session.query(Order).filter_by(cl_ord_id=cl_ord_id).first()

        assert order is not None
        assert order.status == OrderStatus.NEW
        assert order.filled_quantity == 0
        assert order.remaining_quantity == 100

        session.close()

    def test_sender_target_fields(self, fix_client):
        """Test SenderCompID and TargetCompID are correct"""
        response = fix_client.send_logon()

        # Check fields are swapped correctly in response
        assert response.get(simplefix.TAG_SENDER_COMPID) == b'BROKER'
        assert response.get(simplefix.TAG_TARGET_COMPID) == b'TEST_CLIENT'
