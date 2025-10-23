"""
FIX Server (Acceptor) for Broker Service
Accepts FIX connections from clients and processes orders
"""
import socket
import threading
import simplefix
from datetime import datetime
import uuid
import logging
import os
from broker.models import Order, OrderSide, OrderType, TimeInForce, OrderStatus, get_session


# Configure logging
def setup_fix_logging(log_dir='logs'):
    """Setup FIX message logging"""
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Create logger
    logger = logging.getLogger('FIXServer')
    logger.setLevel(logging.DEBUG)

    # Create file handler for all messages
    fh_all = logging.FileHandler(os.path.join(log_dir, 'fix_server.log'))
    fh_all.setLevel(logging.DEBUG)

    # Create file handler for FIX messages only
    fh_messages = logging.FileHandler(os.path.join(log_dir, 'fix_messages.log'))
    fh_messages.setLevel(logging.INFO)

    # Create console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh_all.setFormatter(formatter)
    fh_messages.setFormatter(formatter)
    ch.setFormatter(formatter)

    # Add handlers
    logger.addHandler(fh_all)
    logger.addHandler(fh_messages)
    logger.addHandler(ch)

    return logger


class FIXServer:
    def __init__(self, host='0.0.0.0', port=5001, sender_comp_id='BROKER', log_dir='logs'):
        self.host = host
        self.port = port
        self.sender_comp_id = sender_comp_id
        self.running = False
        self.clients = {}  # {socket: {'target_comp_id': str, 'msg_seq_num': int}}
        self.server_socket = None
        self.msg_seq_num = 1
        self.order_callback = None  # Callback when order is received
        self.logger = setup_fix_logging(log_dir)
        self.logger.info(f"FIX Server initialized: {sender_comp_id} on {host}:{port}")

    def set_order_callback(self, callback):
        """Set callback function to be called when order is received"""
        self.order_callback = callback

    def start(self):
        """Start the FIX server"""
        self.running = True
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.logger.info(f"FIX Server listening on {self.host}:{self.port}")

        # Accept connections in a separate thread
        accept_thread = threading.Thread(target=self._accept_connections)
        accept_thread.daemon = True
        accept_thread.start()

    def _accept_connections(self):
        """Accept incoming client connections"""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                self.logger.info(f"Client connected from {address}")

                # Handle client in separate thread
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address)
                )
                client_thread.daemon = True
                client_thread.start()
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error accepting connection: {e}")

    def _handle_client(self, client_socket, address):
        """Handle messages from a connected client"""
        buffer = b''

        while self.running:
            try:
                data = client_socket.recv(4096)
                if not data:
                    self.logger.info(f"Client {address} disconnected")
                    break

                buffer += data

                # Process complete FIX messages using FixParser
                parser = simplefix.FixParser()
                parser.append_buffer(buffer)

                while True:
                    try:
                        msg = parser.get_message()
                        if not msg:
                            break

                        # Get the remaining buffer
                        buffer = parser.get_buffer()

                        # Process the message
                        self._process_message_obj(msg, client_socket)

                    except Exception as e:
                        self.logger.error(f"Error processing message: {e}", exc_info=True)
                        break

            except Exception as e:
                self.logger.error(f"Error handling client {address}: {e}")
                break

        client_socket.close()
        if client_socket in self.clients:
            del self.clients[client_socket]

    def _process_message_obj(self, msg, client_socket):
        """Process a parsed FIX message object"""
        try:
            msg_type = msg.get(simplefix.TAG_MSGTYPE)
            sender = msg.get(simplefix.TAG_SENDER_COMPID)

            # Log parsed message type
            if sender:
                self.logger.info(f"Received {self._get_msg_type_name(msg_type)} from {sender.decode('utf-8')}")

            if msg_type == simplefix.MSGTYPE_LOGON:
                self._handle_logon(msg, client_socket)
            elif msg_type == simplefix.MSGTYPE_HEARTBEAT:
                self._handle_heartbeat(msg, client_socket)
            elif msg_type == simplefix.MSGTYPE_TEST_REQUEST:
                self._handle_test_request(msg, client_socket)
            elif msg_type == simplefix.MSGTYPE_NEW_ORDER_SINGLE:
                self._handle_new_order(msg, client_socket)
            elif msg_type == simplefix.MSGTYPE_ORDER_CANCEL_REQUEST:
                self._handle_cancel_request(msg, client_socket)
            else:
                self.logger.warning(f"Unknown message type: {msg_type}")

        except Exception as e:
            self.logger.error(f"Error processing message: {e}", exc_info=True)

    def _handle_logon(self, msg, client_socket):
        """Handle Logon message"""
        try:
            target_comp_id = msg.get(simplefix.TAG_SENDER_COMPID).decode('utf-8')
            self.logger.info(f"Logon from {target_comp_id}")

            # Store client info
            self.clients[client_socket] = {
                'target_comp_id': target_comp_id,
                'msg_seq_num': 1
            }

            # Send Logon response
            self.logger.debug("Creating Logon response...")
            response = simplefix.FixMessage()
            response.append_pair(simplefix.TAG_BEGINSTRING, "FIX.4.2", header=True)
            response.append_pair(simplefix.TAG_MSGTYPE, simplefix.MSGTYPE_LOGON)
            response.append_pair(simplefix.TAG_SENDER_COMPID, self.sender_comp_id)
            response.append_pair(simplefix.TAG_TARGET_COMPID, target_comp_id)
            response.append_pair(simplefix.TAG_MSGSEQNUM, self.msg_seq_num)
            response.append_pair(98, 0)  # EncryptMethod: None
            response.append_pair(108, 30)  # HeartBtInt: 30 seconds

            self.logger.debug("Sending Logon response...")
            self._send_message(response, client_socket)
            self.logger.debug("Logon response sent")
        except Exception as e:
            self.logger.error(f"Error in _handle_logon: {e}", exc_info=True)

    def _handle_heartbeat(self, msg, client_socket):
        """Handle Heartbeat message"""
        # Just acknowledge, no response needed unless TestReqID is present
        pass

    def _handle_test_request(self, msg, client_socket):
        """Handle Test Request - send Heartbeat with TestReqID"""
        test_req_id = msg.get(112)  # TestReqID
        target_comp_id = self.clients[client_socket]['target_comp_id']

        response = simplefix.FixMessage()
        response.append_pair(simplefix.TAG_BEGINSTRING, "FIX.4.2", header=True)
        response.append_pair(simplefix.TAG_MSGTYPE, simplefix.MSGTYPE_HEARTBEAT)
        response.append_pair(simplefix.TAG_SENDER_COMPID, self.sender_comp_id)
        response.append_pair(simplefix.TAG_TARGET_COMPID, target_comp_id)
        response.append_pair(simplefix.TAG_MSGSEQNUM, self.msg_seq_num)
        if test_req_id:
            response.append_pair(112, test_req_id)  # Echo back TestReqID

        self._send_message(response, client_socket)

    def _handle_new_order(self, msg, client_socket):
        """Handle New Order Single message"""
        try:
            # Extract order details
            cl_ord_id = msg.get(simplefix.TAG_CLORDID).decode('utf-8')
            symbol = msg.get(simplefix.TAG_SYMBOL).decode('utf-8')
            side = msg.get(simplefix.TAG_SIDE).decode('utf-8')
            order_qty = int(msg.get(simplefix.TAG_ORDERQTY).decode('utf-8'))
            ord_type = msg.get(simplefix.TAG_ORDTYPE).decode('utf-8')

            # Optional fields
            price = msg.get(simplefix.TAG_PRICE)
            if price:
                price = float(price.decode('utf-8'))

            time_in_force = msg.get(simplefix.TAG_TIMEINFORCE)
            if time_in_force:
                time_in_force = time_in_force.decode('utf-8')
            else:
                time_in_force = '0'  # Day order default

            sender_comp_id = msg.get(simplefix.TAG_SENDER_COMPID).decode('utf-8')

            self.logger.info(f"New Order: {cl_ord_id} {symbol} {side} {order_qty} @ {price if price else 'MKT'}")

            # Map FIX values to our enums
            side_enum = OrderSide.BUY if side == '1' else OrderSide.SELL

            # Order type: 1=Market, 2=Limit
            order_type_enum = OrderType.MARKET if ord_type == '1' else OrderType.LIMIT

            # Time in force: 0=Day, 1=GTC, 3=IOC, 4=FOK
            tif_map = {'0': TimeInForce.DAY, '1': TimeInForce.GTC, '3': TimeInForce.IOC, '4': TimeInForce.FOK}
            tif_enum = tif_map.get(time_in_force, TimeInForce.DAY)

            # Create order in database
            session = get_session()
            order = Order(
                cl_ord_id=cl_ord_id,
                sender_comp_id=sender_comp_id,
                symbol=symbol,
                side=side_enum,
                order_type=order_type_enum,
                quantity=order_qty,
                limit_price=price,
                time_in_force=tif_enum,
                status=OrderStatus.NEW,
                filled_quantity=0,
                remaining_quantity=order_qty
            )
            session.add(order)
            session.commit()
            order_id = order.id
            session.close()

            # Send Execution Report (New)
            self._send_execution_report(
                client_socket,
                cl_ord_id,
                symbol,
                side,
                order_qty,
                ord_type,
                exec_type='0',  # New
                ord_status='0'  # New
            )

            # Notify callback
            if self.order_callback:
                self.order_callback(order_id)

        except Exception as e:
            self.logger.error(f"Error handling new order: {e}", exc_info=True)

    def _handle_cancel_request(self, msg, client_socket):
        """Handle Order Cancel Request"""
        # TODO: Implement cancel logic
        self.logger.info("Cancel request received")

    def _send_execution_report(self, client_socket, cl_ord_id, symbol, side,
                               order_qty, ord_type, exec_type='0', ord_status='0',
                               last_qty=None, last_px=None, cum_qty=0, avg_px=0):
        """Send Execution Report to client"""
        target_comp_id = self.clients[client_socket]['target_comp_id']

        msg = simplefix.FixMessage()
        msg.append_pair(simplefix.TAG_BEGINSTRING, "FIX.4.2", header=True)
        msg.append_pair(simplefix.TAG_MSGTYPE, simplefix.MSGTYPE_EXECUTION_REPORT)
        msg.append_pair(simplefix.TAG_SENDER_COMPID, self.sender_comp_id)
        msg.append_pair(simplefix.TAG_TARGET_COMPID, target_comp_id)
        msg.append_pair(simplefix.TAG_MSGSEQNUM, self.msg_seq_num)

        # Order identification
        msg.append_pair(simplefix.TAG_CLORDID, cl_ord_id)
        msg.append_pair(17, str(uuid.uuid4())[:8])  # ExecID
        msg.append_pair(150, exec_type)  # ExecType: 0=New, 1=PartialFill, 2=Fill, 4=Canceled, 8=Rejected
        msg.append_pair(39, ord_status)  # OrdStatus: 0=New, 1=PartiallyFilled, 2=Filled, 4=Canceled, 8=Rejected

        # Order details
        msg.append_pair(simplefix.TAG_SYMBOL, symbol)
        msg.append_pair(simplefix.TAG_SIDE, side)
        msg.append_pair(simplefix.TAG_ORDERQTY, order_qty)
        msg.append_pair(simplefix.TAG_ORDTYPE, ord_type)

        # Execution details
        if last_qty is not None:
            msg.append_pair(32, last_qty)  # LastQty
        if last_px is not None:
            msg.append_pair(31, last_px)  # LastPx
        msg.append_pair(14, cum_qty)  # CumQty
        msg.append_pair(6, avg_px)  # AvgPx

        # Leaves qty
        leaves_qty = order_qty - cum_qty
        msg.append_pair(151, leaves_qty)  # LeavesQty

        self._send_message(msg, client_socket)

    def _send_message(self, msg, client_socket):
        """Send FIX message to client"""
        try:
            msg.append_utc_timestamp(simplefix.TAG_SENDING_TIME)
            encoded = msg.encode()

            # Log outgoing message
            msg_type = msg.get(simplefix.TAG_MSGTYPE)
            self.logger.debug(f"SEND: {encoded}")
            self.logger.info(f"Sent {self._get_msg_type_name(msg_type)}")

            client_socket.send(encoded)
            self.msg_seq_num += 1
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")

    def send_execution_to_client(self, cl_ord_id, sender_comp_id, exec_type,
                                  ord_status, last_qty=None, last_px=None,
                                  cum_qty=0, avg_px=0, symbol='', side='',
                                  order_qty=0, ord_type=''):
        """Send execution report to specific client (called from external code)"""
        # Find client socket by sender_comp_id
        for client_socket, client_info in self.clients.items():
            if client_info['target_comp_id'] == sender_comp_id:
                self._send_execution_report(
                    client_socket, cl_ord_id, symbol, side, order_qty, ord_type,
                    exec_type, ord_status, last_qty, last_px, cum_qty, avg_px
                )
                break

    def _get_msg_type_name(self, msg_type):
        """Get human-readable message type name"""
        msg_types = {
            simplefix.MSGTYPE_LOGON: 'Logon',
            simplefix.MSGTYPE_LOGOUT: 'Logout',
            simplefix.MSGTYPE_HEARTBEAT: 'Heartbeat',
            simplefix.MSGTYPE_TEST_REQUEST: 'TestRequest',
            simplefix.MSGTYPE_NEW_ORDER_SINGLE: 'NewOrderSingle',
            simplefix.MSGTYPE_ORDER_CANCEL_REQUEST: 'OrderCancelRequest',
            simplefix.MSGTYPE_EXECUTION_REPORT: 'ExecutionReport',
        }
        if msg_type:
            return msg_types.get(msg_type, msg_type.decode('utf-8') if isinstance(msg_type, bytes) else msg_type)
        return 'Unknown'

    def stop(self):
        """Stop the FIX server"""
        self.logger.info("Stopping FIX server")
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        for client_socket in list(self.clients.keys()):
            client_socket.close()
        self.logger.info("FIX server stopped")


# For testing
if __name__ == '__main__':
    from broker.models import init_db

    # Initialize database
    init_db('broker.db')

    # Start FIX server
    server = FIXServer()
    server.start()

    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
