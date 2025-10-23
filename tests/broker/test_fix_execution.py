"""
Integration tests for FIX order execution workflow

These tests verify the complete order lifecycle:
1. Client submits order via FIX
2. Broker accepts order (ExecutionReport with status=NEW)
3. Admin executes order via API
4. Broker sends ExecutionReport via FIX (status=FILLED/PARTIALLY_FILLED)
"""

import pytest
import time
import socket
import simplefix
import tempfile
import os
from broker.models import init_db, get_session, Order, OrderStatus, Stock, OrderSide, TimeInForce, Execution
from broker.fix_server import FIXServer


class FIXTestClient:
    """FIX client for testing"""

    def __init__(self, sender_comp_id='TEST_CLIENT', target_comp_id='BROKER', host='localhost', port=15001):
        self.sender_comp_id = sender_comp_id
        self.target_comp_id = target_comp_id
        self.host = host
        self.port = port
        self.socket = None
        self.msg_seq_num = 1
        self.connected = False

    def connect(self):
        """Connect to FIX server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.socket.settimeout(3)
            self.connected = True
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def disconnect(self):
        """Disconnect from FIX server"""
        if self.socket:
            self.socket.close()
        self.connected = False

    def send_logon(self):
        """Send Logon message"""
        msg = simplefix.FixMessage()
        msg.append_pair(simplefix.TAG_BEGINSTRING, "FIX.4.2", header=True)
        msg.append_pair(simplefix.TAG_MSGTYPE, simplefix.MSGTYPE_LOGON)
        msg.append_pair(simplefix.TAG_SENDER_COMPID, self.sender_comp_id)
        msg.append_pair(simplefix.TAG_TARGET_COMPID, self.target_comp_id)
        msg.append_pair(simplefix.TAG_MSGSEQNUM, self.msg_seq_num)
        msg.append_utc_timestamp(simplefix.TAG_SENDING_TIME)
        msg.append_pair(98, 0)  # EncryptMethod: None
        msg.append_pair(108, 30)  # HeartBtInt: 30 seconds

        self.socket.send(msg.encode())
        self.msg_seq_num += 1

        # Receive Logon response
        return self._receive_message()

    def send_new_order(self, symbol, side, quantity, order_type='MARKET', price=None,
                       time_in_force='DAY', cl_ord_id=None):
        """Send NewOrderSingle message"""
        if cl_ord_id is None:
            cl_ord_id = f"ORDER_{self.msg_seq_num}"

        msg = simplefix.FixMessage()
        msg.append_pair(simplefix.TAG_BEGINSTRING, "FIX.4.2", header=True)
        msg.append_pair(simplefix.TAG_MSGTYPE, simplefix.MSGTYPE_NEW_ORDER_SINGLE)
        msg.append_pair(simplefix.TAG_SENDER_COMPID, self.sender_comp_id)
        msg.append_pair(simplefix.TAG_TARGET_COMPID, self.target_comp_id)
        msg.append_pair(simplefix.TAG_MSGSEQNUM, self.msg_seq_num)
        msg.append_utc_timestamp(simplefix.TAG_SENDING_TIME)

        msg.append_pair(simplefix.TAG_CLORDID, cl_ord_id)
        msg.append_pair(21, 1)  # HandlInst: Automated execution
        msg.append_pair(simplefix.TAG_SYMBOL, symbol)
        msg.append_pair(simplefix.TAG_SIDE, '1' if side == 'BUY' else '2')
        msg.append_utc_timestamp(60)  # TransactTime

        # Order type
        if order_type == 'MARKET':
            msg.append_pair(simplefix.TAG_ORDTYPE, '1')
        else:
            msg.append_pair(simplefix.TAG_ORDTYPE, '2')
            if price:
                msg.append_pair(44, str(price))  # Price

        msg.append_pair(simplefix.TAG_ORDERQTY, quantity)

        # Time in force
        tif_map = {'DAY': '0', 'GTC': '1', 'IOC': '3', 'FOK': '4'}
        msg.append_pair(simplefix.TAG_TIMEINFORCE, tif_map.get(time_in_force, '0'))

        self.socket.send(msg.encode())
        self.msg_seq_num += 1

        # Receive ExecutionReport
        return self._receive_message()

    def _receive_message(self, timeout=2):
        """Receive and parse FIX message"""
        buffer = b''
        self.socket.settimeout(timeout)

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

    def receive_execution_report(self, timeout=3):
        """Wait for and receive an execution report"""
        return self._receive_message(timeout=timeout)


@pytest.fixture
def test_db_path():
    """Create temporary test database"""
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    # Initialize database
    init_db(db_path)

    # Add test stocks
    session = get_session(db_path)
    session.add(Stock(symbol='AAPL', last_price=230.10))
    session.add(Stock(symbol='MSFT', last_price=416.50))
    session.add(Stock(symbol='GOOGL', last_price=167.25))
    session.commit()
    session.close()

    yield db_path

    # Cleanup
    try:
        os.unlink(db_path)
    except:
        pass


@pytest.fixture(scope='module')
def fix_server(tmp_path_factory):
    """Start FIX server for testing"""
    # Create temp db for module scope
    test_db = tmp_path_factory.mktemp("data") / "test.db"
    init_db(str(test_db))

    # Add stocks
    session = get_session(str(test_db))
    session.add(Stock(symbol='AAPL', last_price=230.10))
    session.add(Stock(symbol='MSFT', last_price=416.50))
    session.add(Stock(symbol='GOOGL', last_price=167.25))
    session.commit()
    session.close()

    # Monkey patch get_session
    import broker.fix_server
    original_get_session = broker.fix_server.get_session
    broker.fix_server.get_session = lambda: get_session(str(test_db))

    # Create server
    tmp_path = tmp_path_factory.mktemp('fix_logs')
    server = FIXServer(host='localhost', port=15002, log_dir=str(tmp_path))
    server.start()

    time.sleep(0.5)

    yield server, str(test_db)

    # Cleanup
    server.stop()
    time.sleep(0.2)
    broker.fix_server.get_session = original_get_session


@pytest.fixture
def fix_client(fix_server):
    """Create FIX test client"""
    server, _ = fix_server
    client = FIXTestClient(port=15002)
    client.connect()

    yield client

    client.disconnect()


class TestOrderExecution:
    """Test order execution workflow via FIX"""

    def test_full_execution(self, fix_client, fix_server):
        """Test complete order execution flow"""
        server, db_path = fix_server

        # 1. Logon
        fix_client.send_logon()
        time.sleep(0.1)

        # 2. Submit market order via FIX
        cl_ord_id = "EXEC_TEST_001"
        response = fix_client.send_new_order(
            symbol='AAPL',
            side='BUY',
            quantity=100,
            order_type='MARKET',
            cl_ord_id=cl_ord_id
        )

        # Verify NEW execution report received
        assert response is not None
        assert response.get(39) == b'0'  # OrdStatus: New

        time.sleep(0.2)

        # 3. Get order from database
        session = get_session(db_path)
        order = session.query(Order).filter_by(cl_ord_id=cl_ord_id).first()
        assert order is not None
        assert order.status == OrderStatus.NEW
        order_id = order.id

        # 4. Execute order via broker (simulating admin action)
        stock = session.query(Stock).filter_by(symbol='AAPL').first()
        execution = Execution(
            order_id=order_id,
            exec_id=f"EXEC_{cl_ord_id}_1",
            exec_quantity=100,
            exec_price=stock.last_price
        )
        session.add(execution)

        # Update order status
        order.filled_quantity = 100
        order.remaining_quantity = 0
        order.status = OrderStatus.FILLED

        session.commit()

        # 5. Send ExecutionReport to client
        server.send_execution_to_client(
            cl_ord_id=cl_ord_id,
            sender_comp_id=order.sender_comp_id,
            exec_type='2',  # Fill
            ord_status='2',  # Filled
            last_qty=100,
            last_px=stock.last_price,
            cum_qty=100,
            avg_px=stock.last_price,
            symbol='AAPL',
            side='1',
            order_qty=100,
            ord_type='1'
        )

        session.close()

        # 6. Receive ExecutionReport via FIX
        exec_report = fix_client.receive_execution_report(timeout=3)

        assert exec_report is not None
        assert exec_report.get(simplefix.TAG_MSGTYPE) == simplefix.MSGTYPE_EXECUTION_REPORT
        assert exec_report.get(simplefix.TAG_CLORDID) == cl_ord_id.encode('utf-8')
        assert exec_report.get(150) == b'2'  # ExecType: Fill
        assert exec_report.get(39) == b'2'  # OrdStatus: Filled
        assert exec_report.get(14) == b'100'  # CumQty
        assert exec_report.get(151) == b'0'  # LeavesQty

    def test_partial_fill(self, fix_client, fix_server):
        """Test partial order execution"""
        server, db_path = fix_server

        # Logon
        fix_client.send_logon()
        time.sleep(0.1)

        # Submit order for 100 shares
        cl_ord_id = "PARTIAL_TEST_001"
        fix_client.send_new_order(
            symbol='MSFT',
            side='SELL',
            quantity=100,
            order_type='LIMIT',
            price=420.00,
            cl_ord_id=cl_ord_id
        )

        time.sleep(0.2)

        # Execute partial fill (50 shares)
        session = get_session(db_path)
        order = session.query(Order).filter_by(cl_ord_id=cl_ord_id).first()
        stock = session.query(Stock).filter_by(symbol='MSFT').first()

        execution = Execution(
            order_id=order.id,
            exec_id=f"EXEC_{cl_ord_id}_1",
            exec_quantity=50,
            exec_price=420.00
        )
        session.add(execution)

        order.filled_quantity = 50
        order.remaining_quantity = 50
        order.status = OrderStatus.PARTIALLY_FILLED
        session.commit()

        # Send partial fill ExecutionReport
        server.send_execution_to_client(
            cl_ord_id=cl_ord_id,
            sender_comp_id=order.sender_comp_id,
            exec_type='1',  # PartialFill
            ord_status='1',  # PartiallyFilled
            last_qty=50,
            last_px=420.00,
            cum_qty=50,
            avg_px=420.00,
            symbol='MSFT',
            side='2',
            order_qty=100,
            ord_type='2'
        )

        session.close()

        # Receive partial fill ExecutionReport
        exec_report = fix_client.receive_execution_report(timeout=3)

        assert exec_report is not None
        assert exec_report.get(150) == b'1'  # ExecType: PartialFill
        assert exec_report.get(39) == b'1'  # OrdStatus: PartiallyFilled
        assert exec_report.get(14) == b'50'  # CumQty
        assert exec_report.get(151) == b'50'  # LeavesQty
        assert exec_report.get(32) == b'50'  # LastQty
        assert exec_report.get(31) == b'420.0'  # LastPx

    def test_multiple_partial_fills(self, fix_client, fix_server):
        """Test order with multiple partial fills"""
        server, db_path = fix_server

        fix_client.send_logon()
        time.sleep(0.1)

        # Submit order for 100 shares
        cl_ord_id = "MULTI_PARTIAL_001"
        fix_client.send_new_order(
            symbol='GOOGL',
            side='BUY',
            quantity=100,
            order_type='MARKET',
            cl_ord_id=cl_ord_id
        )

        time.sleep(0.2)

        session = get_session(db_path)
        order = session.query(Order).filter_by(cl_ord_id=cl_ord_id).first()
        stock = session.query(Stock).filter_by(symbol='GOOGL').first()

        # First partial fill: 30 shares
        exec1 = Execution(order_id=order.id, exec_id=f"EXEC_{cl_ord_id}_1", exec_quantity=30, exec_price=stock.last_price)
        session.add(exec1)
        order.filled_quantity = 30
        order.remaining_quantity = 70
        order.status = OrderStatus.PARTIALLY_FILLED
        session.commit()

        server.send_execution_to_client(
            cl_ord_id=cl_ord_id,
            sender_comp_id=order.sender_comp_id,
            exec_type='1',  # PartialFill
            ord_status='1',  # PartiallyFilled
            last_qty=30,
            last_px=stock.last_price,
            cum_qty=30,
            avg_px=stock.last_price,
            symbol='GOOGL',
            side='1',
            order_qty=100,
            ord_type='1'
        )

        # Receive first partial fill
        exec_report1 = fix_client.receive_execution_report(timeout=3)
        assert exec_report1 is not None
        assert exec_report1.get(14) == b'30'  # CumQty
        assert exec_report1.get(151) == b'70'  # LeavesQty

        time.sleep(0.1)

        # Second partial fill: 40 shares (total: 70)
        exec2 = Execution(order_id=order.id, exec_id=f"EXEC_{cl_ord_id}_2", exec_quantity=40, exec_price=stock.last_price)
        session.add(exec2)
        order.filled_quantity = 70
        order.remaining_quantity = 30
        session.commit()

        server.send_execution_to_client(
            cl_ord_id=cl_ord_id,
            sender_comp_id=order.sender_comp_id,
            exec_type='1',  # PartialFill
            ord_status='1',  # PartiallyFilled
            last_qty=40,
            last_px=stock.last_price,
            cum_qty=70,
            avg_px=stock.last_price,
            symbol='GOOGL',
            side='1',
            order_qty=100,
            ord_type='1'
        )

        # Receive second partial fill
        exec_report2 = fix_client.receive_execution_report(timeout=3)
        assert exec_report2 is not None
        assert exec_report2.get(14) == b'70'  # CumQty
        assert exec_report2.get(151) == b'30'  # LeavesQty

        time.sleep(0.1)

        # Final fill: 30 shares (total: 100)
        exec3 = Execution(order_id=order.id, exec_id=f"EXEC_{cl_ord_id}_3", exec_quantity=30, exec_price=stock.last_price)
        session.add(exec3)
        order.filled_quantity = 100
        order.remaining_quantity = 0
        order.status = OrderStatus.FILLED
        session.commit()

        server.send_execution_to_client(
            cl_ord_id=cl_ord_id,
            sender_comp_id=order.sender_comp_id,
            exec_type='2',  # Fill
            ord_status='2',  # Filled
            last_qty=30,
            last_px=stock.last_price,
            cum_qty=100,
            avg_px=stock.last_price,
            symbol='GOOGL',
            side='1',
            order_qty=100,
            ord_type='1'
        )

        # Receive final fill
        exec_report3 = fix_client.receive_execution_report(timeout=3)
        assert exec_report3 is not None
        assert exec_report3.get(150) == b'2'  # ExecType: Fill
        assert exec_report3.get(39) == b'2'  # OrdStatus: Filled
        assert exec_report3.get(14) == b'100'  # CumQty
        assert exec_report3.get(151) == b'0'  # LeavesQty

        session.close()


class TestOrderCancellation:
    """Test order cancellation via FIX"""

    def test_cancel_order(self, fix_client, fix_server):
        """Test canceling an order"""
        server, db_path = fix_server

        fix_client.send_logon()
        time.sleep(0.1)

        # Submit order
        cl_ord_id = "CANCEL_TEST_001"
        fix_client.send_new_order(
            symbol='AAPL',
            side='BUY',
            quantity=100,
            order_type='LIMIT',
            price=225.00,
            cl_ord_id=cl_ord_id
        )

        time.sleep(0.2)

        # Cancel order
        session = get_session(db_path)
        order = session.query(Order).filter_by(cl_ord_id=cl_ord_id).first()
        order.status = OrderStatus.CANCELED
        session.commit()

        # Send cancel ExecutionReport
        server.send_execution_to_client(
            cl_ord_id=cl_ord_id,
            sender_comp_id=order.sender_comp_id,
            exec_type='4',  # Canceled
            ord_status='4',  # Canceled
            cum_qty=0,
            avg_px=0,
            symbol='AAPL',
            side='1',
            order_qty=100,
            ord_type='2'
        )

        session.close()

        # Receive cancel ExecutionReport
        exec_report = fix_client.receive_execution_report(timeout=3)

        assert exec_report is not None
        assert exec_report.get(150) == b'4'  # ExecType: Canceled
        assert exec_report.get(39) == b'4'  # OrdStatus: Canceled
        assert exec_report.get(14) == b'0'  # CumQty
        assert exec_report.get(151) == b'100'  # LeavesQty


class TestOrderRejection:
    """Test order rejection via FIX"""

    def test_reject_order(self, fix_client, fix_server):
        """Test rejecting an order"""
        server, db_path = fix_server

        fix_client.send_logon()
        time.sleep(0.1)

        # Submit order
        cl_ord_id = "REJECT_TEST_001"
        fix_client.send_new_order(
            symbol='MSFT',
            side='SELL',
            quantity=50,
            order_type='LIMIT',
            price=410.00,
            cl_ord_id=cl_ord_id
        )

        time.sleep(0.2)

        # Reject order
        session = get_session(db_path)
        order = session.query(Order).filter_by(cl_ord_id=cl_ord_id).first()
        order.status = OrderStatus.REJECTED
        order.reject_reason = "Insufficient inventory"
        session.commit()

        # Send reject ExecutionReport
        server.send_execution_to_client(
            cl_ord_id=cl_ord_id,
            sender_comp_id=order.sender_comp_id,
            exec_type='8',  # Rejected
            ord_status='8',  # Rejected
            cum_qty=0,
            avg_px=0,
            symbol='MSFT',
            side='2',
            order_qty=50,
            ord_type='2'
        )

        session.close()

        # Receive reject ExecutionReport
        exec_report = fix_client.receive_execution_report(timeout=3)

        assert exec_report is not None
        assert exec_report.get(150) == b'8'  # ExecType: Rejected
        assert exec_report.get(39) == b'8'  # OrdStatus: Rejected
