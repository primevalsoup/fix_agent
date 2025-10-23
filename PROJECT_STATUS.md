# FIX Trading System - Project Status and Roadmap

**Last Updated**: October 23, 2025
**Project**: Stock Order Management System using FIX Protocol 4.2
**Technology Stack**: Python (Flask, simplefix, SQLAlchemy), React, SQLite, UV package manager

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [What We've Built So Far](#what-weve-built-so-far)
3. [Current Test Coverage](#current-test-coverage)
4. [What's Left To Build](#whats-left-to-build)
5. [Detailed Plan: Client FIX Initiator](#detailed-plan-client-fix-initiator)
6. [Getting Started](#getting-started)

---

## Project Overview

A complete stock trading system implementing the FIX Protocol 4.2 for order management. The system consists of:

- **Broker FIX Server**: Accepts and processes orders via FIX protocol
- **Backend API**: REST API for order management and stock data
- **Client Applications**: CLI and web interfaces for order submission
- **Trading Engine**: Simulates order execution with realistic fills

### Key Features

- Full FIX protocol 4.2 compliance
- Complete order lifecycle: Submit → Execute → Cancel/Amend
- Partial fill support with multiple executions
- Client-initiated order cancellation and amendment
- Real-time execution reports
- 20-stock trading universe with current market prices

---

## What We've Built So Far

### 1. FIX Protocol Server (Broker Acceptor) ✅

**Location**: `broker/fix_server.py`

A fully functional FIX protocol server that acts as the broker acceptor:

**Features:**
- FIX 4.2 protocol implementation using `simplefix` library
- Multi-client connection support with threading
- Session management with sequence numbers and heartbeats
- Bidirectional message logging (RECV/SEND)

**Supported Message Types:**
- **MsgType=A (Logon)**: Client authentication and session establishment
- **MsgType=D (NewOrderSingle)**: Order submission from clients
- **MsgType=8 (ExecutionReport)**: Order status updates to clients
  - ExecType=0 (New): Order accepted
  - ExecType=1 (PartialFill): Partial execution
  - ExecType=2 (Fill): Complete execution
  - ExecType=4 (Canceled): Order canceled
  - ExecType=5 (Replaced): Order amended
  - ExecType=8 (Rejected): Order rejected
- **MsgType=F (OrderCancelRequest)**: Client-initiated cancellation
- **MsgType=G (OrderCancelReplaceRequest)**: Client-initiated amendment
- **MsgType=9 (OrderCancelReject)**: Rejection of cancel/amend requests

**Implementation Highlights:**
- Order socket tracking for routing messages to correct clients
- Validation of cancel/amend requests (prevents canceling filled orders)
- Proper sequence number management
- Comprehensive error handling

**Code Stats:**
- 351 statements
- 83% test coverage
- 60 lines uncovered

---

### 2. Backend REST API ✅

**Location**: `broker/app.py`

Flask-based REST API for order and stock management:

**Endpoints:**

**Order Management:**
- `POST /api/orders` - Submit new order
- `GET /api/orders` - List all orders
- `GET /api/orders/<order_id>` - Get specific order
- `DELETE /api/orders/<order_id>` - Cancel order
- `PUT /api/orders/<order_id>` - Update order

**Stock Management:**
- `GET /api/stocks` - List all stocks
- `GET /api/stocks/<symbol>` - Get stock details
- `PUT /api/stocks/<symbol>` - Update stock price

**Execution Management:**
- `POST /api/executions` - Create execution (admin)
- `GET /api/executions` - List all executions
- `GET /api/executions/<execution_id>` - Get execution details

**Integration:**
- Works seamlessly with FIX server
- When admin creates execution via API, FIX server sends ExecutionReport to client
- Shares same database with FIX server

---

### 3. Database Models ✅

**Location**: `broker/models.py`

SQLAlchemy ORM models with complete relationships:

**Models:**

**Stock Model:**
```python
class Stock:
    id: int
    symbol: str (unique)
    last_price: float
    created_at: datetime
    updated_at: datetime
```

**Order Model:**
```python
class Order:
    id: int
    cl_ord_id: str (unique, Client Order ID)
    symbol: str
    side: OrderSide (BUY/SELL)
    order_type: OrderType (MARKET/LIMIT)
    quantity: int
    limit_price: float (optional)
    time_in_force: TimeInForce (DAY/GTC/IOC/FOK)
    status: OrderStatus (NEW/PARTIALLY_FILLED/FILLED/CANCELED/REJECTED)
    filled_quantity: int (default 0)
    remaining_quantity: int
    sender_comp_id: str (FIX client identifier)
    created_at: datetime
    updated_at: datetime

    # Relationships
    executions: List[Execution]
    stock: Stock
```

**Execution Model:**
```python
class Execution:
    id: int
    exec_id: str (unique)
    order_id: int
    exec_quantity: int
    exec_price: float
    created_at: datetime

    # Relationships
    order: Order
```

**Enums:**
- `OrderSide`: BUY, SELL
- `OrderType`: MARKET, LIMIT, STOP, STOP_LIMIT
- `TimeInForce`: DAY, GTC, IOC, FOK
- `OrderStatus`: NEW, PARTIALLY_FILLED, FILLED, CANCELED, REJECTED

**Code Stats:**
- 69 statements
- 97% test coverage

---

### 4. Stock Universe ✅

**Location**: `broker/stock_universe.csv`

20 stocks with current market prices (updated October 2025):

| Symbol | Last Price | Market Cap Tier |
|--------|-----------|-----------------|
| AAPL   | $230.10   | Mega Cap        |
| MSFT   | $416.50   | Mega Cap        |
| GOOGL  | $167.25   | Mega Cap        |
| AMZN   | $178.40   | Mega Cap        |
| NVDA   | $495.30   | Mega Cap        |
| META   | $512.75   | Mega Cap        |
| TSLA   | $242.80   | Large Cap       |
| JPM    | $195.60   | Large Cap       |
| V      | $273.90   | Large Cap       |
| WMT    | $167.85   | Large Cap       |
| MA     | $445.20   | Large Cap       |
| JNJ    | $156.30   | Large Cap       |
| UNH    | $518.40   | Large Cap       |
| PG     | $162.50   | Large Cap       |
| HD     | $378.90   | Large Cap       |
| BAC    | $39.25    | Large Cap       |
| DIS    | $96.85    | Large Cap       |
| NFLX   | $625.30   | Large Cap       |
| CSCO   | $54.80    | Large Cap       |
| INTC   | $23.15    | Large Cap       |

---

### 5. Stock Price Update Script ✅

**Location**: `scripts/update_stock_prices.py`

Automated script to fetch and update stock prices using Yahoo Finance API:

**Features:**
- Batch fetch prices for all symbols
- Dry-run mode for testing
- Backup of existing prices before update
- Error handling for failed fetches

**Usage:**
```bash
# Update all stock prices
uv run python scripts/update_stock_prices.py

# Dry run to preview changes
uv run python scripts/update_stock_prices.py --dry-run
```

**Known Issues:**
- Yahoo Finance may return 403 errors due to network blocking
- Documented fallback procedures in `scripts/README.md`
- Manual update instructions provided

**Dependencies:**
- `yfinance>=0.2.0`

---

### 6. Comprehensive Testing ✅

**Total Tests**: 67 passing (100%)

#### 6.1 Unit Tests

**Location**: `tests/broker/test_models.py`

Tests for database models:
- Model creation and validation
- Relationships between models
- Enum constraints
- Field validation

**Code Coverage**: Models at 97%

#### 6.2 API Tests

**Location**: `tests/broker/test_api.py`

Tests for REST API endpoints:
- Order CRUD operations
- Stock management
- Execution creation
- Error handling
- Input validation

#### 6.3 FIX Integration Tests

**Location**: `tests/broker/test_fix_integration.py`

Basic FIX protocol tests (12 tests):
- Connection and logon
- Order submission
- Execution report reception
- Multiple client connections
- Session management

#### 6.4 FIX Execution Tests

**Location**: `tests/broker/test_fix_execution.py`

Comprehensive order lifecycle tests (14 tests):

**Order Execution Tests (3 tests):**
- `test_full_execution` - Complete order fill
- `test_partial_fill` - Single partial fill
- `test_multiple_partial_fills` - Three partial fills (30+40+30)

**Admin Actions Tests (2 tests):**
- `test_cancel_order` - Admin cancels order
- `test_reject_order` - Admin rejects order

**Client-Initiated Cancel Tests (4 tests):**
- `test_cancel_unfilled_order` - Cancel order with no fills
- `test_cancel_partially_filled_order` - Cancel order with partial fills
- `test_cancel_nonexistent_order` - Reject cancel for unknown order
- `test_cancel_already_filled_order` - Reject cancel for filled order

**Order Amendment Tests (5 tests):**
- `test_amend_quantity` - Change order quantity
- `test_amend_price` - Change limit price
- `test_amend_both_quantity_and_price` - Change both
- `test_amend_nonexistent_order` - Reject amend for unknown order
- `test_amend_filled_order` - Reject amend for filled order

**Test Infrastructure:**
- Custom FIXTestClient for simulating client connections
- Temporary test databases
- Isolated test environments
- Comprehensive message validation

---

### 7. Documentation ✅

#### 7.1 FIX Message Examples

**Location**: `test_logs/fix_message_examples.md`

Comprehensive guide with 10 sections covering:
- All FIX message types with tag-by-tag breakdowns
- Complete workflows with examples
- Multiple execution scenarios
- Cancel and amend flows with rejections
- 310 lines of detailed documentation

#### 7.2 FIX Server Logs

**Location**: `test_logs/latest_fix_server.txt`

Complete DEBUG-level logs from test runs:
- 272 lines of raw FIX protocol messages
- Shows both RECV (client → broker) and SEND (broker → client)
- All 14 execution integration tests
- Raw tags visible: `8=FIX.4.2\x019=72\x0135=A...`

#### 7.3 Additional Documentation

- `test_logs/bidirectional_fix_messages.txt` - RECV/SEND flow examples
- `test_logs/latest_fix_messages.txt` - INFO-level filtered logs
- `scripts/README.md` - Stock price update documentation

---

### 8. Development Tools ✅

#### 8.1 Package Management

Using **UV package manager** as requested:
- Fast dependency resolution
- Virtual environment management
- Lock file for reproducibility

**Usage:**
```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Run Flask app
uv run flask --app broker.app run

# Run FIX server
uv run python -m broker.fix_server
```

#### 8.2 Project Configuration

**Location**: `pyproject.toml`

Complete project metadata and dependencies:

**Key Dependencies:**
- `simplefix>=1.0.17` - FIX protocol implementation
- `flask>=3.0.0` - Web framework
- `sqlalchemy>=2.0.0` - ORM
- `yfinance>=0.2.0` - Stock price data
- `pytest>=8.0.0` - Testing framework
- `pytest-cov>=4.0.0` - Coverage reporting

---

## Current Test Coverage

**Overall Coverage**: 54%

**Module Breakdown:**

| Module | Statements | Miss | Cover | Missing Lines |
|--------|-----------|------|-------|---------------|
| broker/fix_server.py | 351 | 60 | **83%** | Various error paths |
| broker/models.py | 69 | 2 | **97%** | Minor utility functions |
| broker/app.py | 181 | 181 | **0%** | Not yet tested |
| client/models.py | 63 | 63 | **0%** | Not yet implemented |

**Test Execution Time**: ~6.7 seconds for all 67 tests

**What's Tested:**
- ✅ FIX protocol message handling
- ✅ Order lifecycle (submit → execute → cancel/amend)
- ✅ Multi-client connections
- ✅ Partial fills and multiple executions
- ✅ Error handling and rejections
- ✅ Database models and relationships

**What's Not Yet Tested:**
- ❌ REST API endpoints (broker/app.py)
- ❌ Client applications (not yet built)
- ❌ Some error edge cases in FIX server

---

## What's Left To Build

### 1. Client FIX Initiator ⏳ (PRIORITY)

**Status**: Not started
**Estimated Time**: 8-12 hours
**Details**: See [Detailed Plan](#detailed-plan-client-fix-initiator) below

A production-ready FIX client application that:
- Connects to the broker's FIX server as an initiator
- Submits orders via FIX protocol
- Receives and processes execution reports
- Supports cancel and amend operations
- Provides CLI interface for users
- Can run as background service

---

### 2. Broker React Dashboard ⏳

**Status**: Not started
**Estimated Time**: 6-8 hours

Web interface for broker operations:

**Features:**
- **Order Book View**
  - Real-time list of all orders
  - Filter by status, symbol, client
  - Sort by time, size, price

- **Order Management**
  - View order details
  - Execute orders manually
  - Cancel orders (admin)
  - Reject orders (admin)

- **Stock Management**
  - View stock universe
  - Update stock prices
  - Monitor trading activity per symbol

- **Execution History**
  - List all executions
  - Group by order
  - Export to CSV

- **System Monitoring**
  - Connected clients
  - FIX message statistics
  - System health metrics

**Technology:**
- React 18 with TypeScript
- Material-UI or Tailwind CSS
- WebSocket for real-time updates
- Chart.js for visualizations

**API Integration:**
- Connects to existing Flask REST API
- WebSocket subscription for live updates

---

### 3. Client React Dashboard ⏳

**Status**: Not started
**Estimated Time**: 6-8 hours

Web interface for end-users to trade:

**Features:**
- **Order Entry**
  - Quick order form (symbol, side, quantity, type, price)
  - Real-time stock price display
  - Order validation
  - Market vs. Limit order support

- **My Orders View**
  - List of user's orders
  - Real-time status updates
  - Filter by status/symbol

- **Order Actions**
  - Cancel pending orders
  - Amend quantity/price
  - View execution details

- **Portfolio View**
  - Current positions (if tracking)
  - Order history
  - Execution summary

- **Stock Watchlist**
  - Browse available stocks
  - Current prices
  - Quick trade buttons

**Technology:**
- React 18 with TypeScript
- Material-UI or Tailwind CSS
- React Query for data fetching
- WebSocket for real-time order updates

**Backend Options:**
1. Connect directly to REST API (Flask)
2. Connect to Client FIX Initiator REST wrapper
3. Hybrid: REST API for reads, FIX client for writes

---

### 4. Comprehensive README ⏳

**Status**: Partially complete
**Estimated Time**: 2-3 hours

Complete setup and usage documentation:

**Sections Needed:**
- **Project Overview**: High-level description
- **Architecture Diagram**: System components and flow
- **Installation**:
  - Prerequisites (Python 3.11+, Node.js)
  - UV installation
  - Dependency installation
  - Database setup
- **Configuration**:
  - FIX server settings
  - API configuration
  - Client configuration
- **Usage**:
  - Starting the FIX server
  - Starting the API server
  - Using the CLI client
  - Accessing web dashboards
- **Testing**:
  - Running tests
  - Coverage reports
- **Development**:
  - Project structure
  - Adding new features
  - Debugging FIX messages
- **Deployment**:
  - Production considerations
  - Security settings
  - Performance tuning
- **Troubleshooting**:
  - Common issues
  - FIX protocol debugging
  - Log locations
- **API Documentation**:
  - REST endpoints
  - FIX message reference
- **Contributing**: Guidelines for contributors
- **License**: Project license

---

### 5. Optional Enhancements 💡

These are not in the original plan but could be valuable:

**5.1 Position Tracking**
- Track client positions after fills
- Calculate P&L
- Margin requirements

**5.2 Risk Management**
- Order size limits
- Price collar validation
- Daily trading limits per client
- Symbol restrictions

**5.3 Market Data Feed**
- Real-time price updates
- Integrate with actual market data provider
- Level 1 quotes

**5.4 Admin Dashboard Enhancements**
- User management
- Trading hours configuration
- System configuration UI
- Audit log viewer

**5.5 Advanced Order Types**
- Stop orders
- Stop-limit orders
- Iceberg orders
- Time-based orders (MOO, MOC)

**5.6 Multi-Venue Support**
- Route orders to multiple brokers
- Smart order routing
- Venue selection

**5.7 Historical Data**
- Historical price data
- Backtesting capability
- Analytics and reporting

---

## Detailed Plan: Client FIX Initiator

### Overview

The Client FIX Initiator is a production-ready application that allows users to connect to the broker's FIX server and trade stocks. It acts as the client side (initiator) in the FIX protocol conversation.

### Architecture

We'll implement this in three layers:

1. **Core Library** (`client/fix_client.py`) - Reusable FIX client
2. **CLI Application** (`client/cli.py`) - Command-line interface
3. **Service Mode** (`client/service.py`) - Background service with API

This layered approach provides maximum flexibility - the core library can be used by the CLI, by the React dashboard, or by other Python applications.

---

### Phase 1: Core FIX Client Library

**Goal**: Build a robust, reusable FIX client that handles all FIX protocol operations.

#### 1.1 Connection Management

**File**: `client/fix_client.py`

**Class**: `FIXClient`

**Responsibilities:**
- Connect to broker FIX server (localhost:15001 by default)
- Initiate FIX logon sequence
- Handle logon response
- Maintain heartbeat
- Handle disconnections
- Support reconnection with sequence number recovery

**Key Methods:**
```python
class FIXClient:
    def __init__(self, host='localhost', port=15001,
                 sender_comp_id='CLIENT_001',
                 target_comp_id='BROKER',
                 heartbeat_interval=30):
        """Initialize FIX client with connection parameters"""

    def connect(self):
        """Connect to broker and send logon"""
        # 1. Create TCP socket connection
        # 2. Build Logon message (MsgType=A)
        # 3. Send logon with sequence number
        # 4. Wait for Logon response
        # 5. Start heartbeat thread
        # 6. Start message receiving thread

    def disconnect(self):
        """Send logout and close connection"""
        # 1. Send Logout message (MsgType=5)
        # 2. Wait for Logout response
        # 3. Close socket
        # 4. Stop all threads

    def is_connected(self):
        """Check if connected and logged in"""
        return self._connected and self._logged_in

    def _send_heartbeat(self):
        """Send heartbeat message (MsgType=0)"""
        # Runs in background thread
        # Send every heartbeat_interval seconds

    def _receive_messages(self):
        """Receive and process incoming FIX messages"""
        # Runs in background thread
        # Parse incoming messages
        # Route to appropriate handlers
```

**Implementation Details:**

**Logon Message (MsgType=A):**
```python
def _send_logon(self):
    msg = simplefix.FixMessage()
    msg.append_pair(8, b'FIX.4.2')  # BeginString
    msg.append_pair(35, b'A')  # MsgType: Logon
    msg.append_pair(49, self.sender_comp_id)  # SenderCompID
    msg.append_pair(56, self.target_comp_id)  # TargetCompID
    msg.append_pair(34, str(self.msg_seq_num))  # MsgSeqNum
    msg.append_pair(52, self._get_timestamp())  # SendingTime
    msg.append_pair(98, '0')  # EncryptMethod: None
    msg.append_pair(108, str(self.heartbeat_interval))  # HeartBtInt
    self._send_message(msg)
    self.msg_seq_num += 1
```

**Sequence Number Management:**
- Track outgoing sequence numbers (`msg_seq_num`)
- Track incoming sequence numbers (`expected_seq_num`)
- Detect gaps and request resend if needed
- Persist sequence numbers for reconnection

**Heartbeat Thread:**
```python
def _heartbeat_loop(self):
    while self._connected:
        time.sleep(self.heartbeat_interval)
        if self._logged_in:
            self._send_heartbeat()
```

**Message Receiving Thread:**
```python
def _receive_loop(self):
    parser = simplefix.FixParser()
    while self._connected:
        data = self.socket.recv(4096)
        if not data:
            self._handle_disconnection()
            break
        parser.append_buffer(data)
        msg = parser.get_message()
        while msg:
            self._handle_message(msg)
            msg = parser.get_message()
```

---

#### 1.2 Order Operations

**Responsibilities:**
- Generate unique ClOrdID for each order
- Build and send FIX order messages
- Return order identifier to caller

**Key Methods:**

```python
def submit_order(self, symbol, side, quantity, order_type='MARKET',
                 price=None, time_in_force='DAY'):
    """
    Submit a new order

    Args:
        symbol: Stock symbol (e.g., 'AAPL')
        side: 'BUY' or 'SELL'
        quantity: Number of shares
        order_type: 'MARKET' or 'LIMIT'
        price: Limit price (required for LIMIT orders)
        time_in_force: 'DAY', 'GTC', 'IOC', 'FOK'

    Returns:
        cl_ord_id: Client Order ID

    Raises:
        NotConnectedError: If not connected to broker
        ValidationError: If invalid parameters
    """
    # 1. Validate parameters
    if order_type == 'LIMIT' and price is None:
        raise ValidationError("Price required for LIMIT orders")

    # 2. Generate unique ClOrdID
    cl_ord_id = self._generate_cl_ord_id()

    # 3. Build NewOrderSingle message (MsgType=D)
    msg = simplefix.FixMessage()
    msg.append_pair(35, b'D')  # MsgType: NewOrderSingle
    msg.append_pair(11, cl_ord_id)  # ClOrdID
    msg.append_pair(21, '1')  # HandlInst: Automated
    msg.append_pair(55, symbol)  # Symbol
    msg.append_pair(54, '1' if side == 'BUY' else '2')  # Side
    msg.append_pair(60, self._get_timestamp())  # TransactTime
    msg.append_pair(40, '1' if order_type == 'MARKET' else '2')  # OrdType
    if price:
        msg.append_pair(44, str(price))  # Price
    msg.append_pair(38, str(quantity))  # OrderQty
    msg.append_pair(59, self._map_tif(time_in_force))  # TimeInForce

    # 4. Send message
    self._send_message(msg)

    # 5. Store order in local cache
    self.order_manager.add_order({
        'cl_ord_id': cl_ord_id,
        'symbol': symbol,
        'side': side,
        'quantity': quantity,
        'order_type': order_type,
        'price': price,
        'status': 'PENDING_NEW',
        'submitted_at': datetime.now()
    })

    return cl_ord_id

def cancel_order(self, cl_ord_id, symbol, side):
    """
    Cancel an existing order

    Args:
        cl_ord_id: Original Client Order ID
        symbol: Stock symbol
        side: 'BUY' or 'SELL'

    Returns:
        cancel_cl_ord_id: ClOrdID of cancel request

    Raises:
        NotConnectedError: If not connected
        OrderNotFoundError: If order not in cache
    """
    # 1. Verify order exists locally
    order = self.order_manager.get_order(cl_ord_id)
    if not order:
        raise OrderNotFoundError(f"Order {cl_ord_id} not found")

    # 2. Check if order can be canceled
    if order['status'] in ['FILLED', 'CANCELED', 'REJECTED']:
        raise InvalidStateError(f"Cannot cancel order with status {order['status']}")

    # 3. Generate new ClOrdID for cancel request
    cancel_cl_ord_id = self._generate_cl_ord_id()

    # 4. Build OrderCancelRequest (MsgType=F)
    msg = simplefix.FixMessage()
    msg.append_pair(35, b'F')  # MsgType: OrderCancelRequest
    msg.append_pair(41, cl_ord_id)  # OrigClOrdID
    msg.append_pair(11, cancel_cl_ord_id)  # ClOrdID
    msg.append_pair(55, symbol)  # Symbol
    msg.append_pair(54, '1' if side == 'BUY' else '2')  # Side
    msg.append_pair(60, self._get_timestamp())  # TransactTime

    # 5. Send message
    self._send_message(msg)

    # 6. Update local cache
    self.order_manager.update_order(cl_ord_id,
                                    status='PENDING_CANCEL',
                                    cancel_cl_ord_id=cancel_cl_ord_id)

    return cancel_cl_ord_id

def amend_order(self, orig_cl_ord_id, symbol, side,
                new_quantity=None, new_price=None, order_type='LIMIT'):
    """
    Amend an existing order (cancel/replace)

    Args:
        orig_cl_ord_id: Original Client Order ID
        symbol: Stock symbol
        side: 'BUY' or 'SELL'
        new_quantity: New quantity (optional)
        new_price: New price (optional)
        order_type: Order type

    Returns:
        new_cl_ord_id: New ClOrdID for amended order

    Raises:
        NotConnectedError: If not connected
        OrderNotFoundError: If order not found
        ValidationError: If neither quantity nor price specified
    """
    # 1. Validate
    if new_quantity is None and new_price is None:
        raise ValidationError("Must specify new_quantity or new_price")

    # 2. Get existing order
    order = self.order_manager.get_order(orig_cl_ord_id)
    if not order:
        raise OrderNotFoundError(f"Order {orig_cl_ord_id} not found")

    # Use current values if not specified
    if new_quantity is None:
        new_quantity = order['quantity']
    if new_price is None:
        new_price = order['price']

    # 3. Generate new ClOrdID
    new_cl_ord_id = self._generate_cl_ord_id()

    # 4. Build OrderCancelReplaceRequest (MsgType=G)
    msg = simplefix.FixMessage()
    msg.append_pair(35, b'G')  # MsgType: OrderCancelReplaceRequest
    msg.append_pair(41, orig_cl_ord_id)  # OrigClOrdID
    msg.append_pair(11, new_cl_ord_id)  # ClOrdID (new)
    msg.append_pair(21, '1')  # HandlInst
    msg.append_pair(55, symbol)  # Symbol
    msg.append_pair(54, '1' if side == 'BUY' else '2')  # Side
    msg.append_pair(60, self._get_timestamp())  # TransactTime
    msg.append_pair(40, '1' if order_type == 'MARKET' else '2')  # OrdType
    if new_price:
        msg.append_pair(44, str(new_price))  # Price
    msg.append_pair(38, str(new_quantity))  # OrderQty

    # 5. Send message
    self._send_message(msg)

    # 6. Update local cache
    self.order_manager.add_order({
        'cl_ord_id': new_cl_ord_id,
        'orig_cl_ord_id': orig_cl_ord_id,
        'symbol': symbol,
        'side': side,
        'quantity': new_quantity,
        'price': new_price,
        'order_type': order_type,
        'status': 'PENDING_REPLACE',
        'submitted_at': datetime.now()
    })

    return new_cl_ord_id
```

**ClOrdID Generation:**
```python
def _generate_cl_ord_id(self):
    """Generate unique Client Order ID"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
    return f"{self.sender_comp_id}_{timestamp}"
```

---

#### 1.3 Response Handling

**Responsibilities:**
- Parse incoming ExecutionReport messages
- Parse OrderCancelReject messages
- Update local order state
- Trigger callbacks for application logic

**Key Methods:**

```python
def _handle_message(self, msg):
    """Route incoming message to appropriate handler"""
    msg_type = msg.get(35)  # MsgType

    if msg_type == b'A':  # Logon
        self._handle_logon(msg)
    elif msg_type == b'8':  # ExecutionReport
        self._handle_execution_report(msg)
    elif msg_type == b'9':  # OrderCancelReject
        self._handle_cancel_reject(msg)
    elif msg_type == b'0':  # Heartbeat
        self._handle_heartbeat(msg)
    elif msg_type == b'1':  # TestRequest
        self._handle_test_request(msg)
    else:
        self.logger.warning(f"Unhandled message type: {msg_type}")

def _handle_execution_report(self, msg):
    """Process ExecutionReport (MsgType=8)"""
    # Extract fields
    cl_ord_id = msg.get(11).decode('utf-8')  # ClOrdID
    exec_id = msg.get(17).decode('utf-8')  # ExecID
    exec_type = msg.get(150).decode('utf-8')  # ExecType
    ord_status = msg.get(39).decode('utf-8')  # OrdStatus
    symbol = msg.get(55).decode('utf-8')  # Symbol
    side = msg.get(54).decode('utf-8')  # Side
    order_qty = int(msg.get(38).decode('utf-8'))  # OrderQty
    cum_qty = int(msg.get(14).decode('utf-8'))  # CumQty
    leaves_qty = int(msg.get(151).decode('utf-8'))  # LeavesQty
    avg_px = float(msg.get(6).decode('utf-8'))  # AvgPx

    # Optional fields for fills
    last_qty = None
    last_px = None
    if msg.get(32):  # LastQty
        last_qty = int(msg.get(32).decode('utf-8'))
    if msg.get(31):  # LastPx
        last_px = float(msg.get(31).decode('utf-8'))

    # Map ExecType
    exec_type_map = {
        '0': 'NEW',
        '1': 'PARTIAL_FILL',
        '2': 'FILL',
        '4': 'CANCELED',
        '5': 'REPLACED',
        '8': 'REJECTED'
    }
    exec_type_str = exec_type_map.get(exec_type, exec_type)

    # Map OrdStatus
    status_map = {
        '0': 'NEW',
        '1': 'PARTIALLY_FILLED',
        '2': 'FILLED',
        '4': 'CANCELED',
        '8': 'REJECTED'
    }
    status_str = status_map.get(ord_status, ord_status)

    # Update order in cache
    self.order_manager.update_order(cl_ord_id, {
        'status': status_str,
        'filled_quantity': cum_qty,
        'remaining_quantity': leaves_qty,
        'avg_price': avg_px
    })

    # Add execution to history
    if last_qty:
        self.order_manager.add_execution(cl_ord_id, {
            'exec_id': exec_id,
            'exec_quantity': last_qty,
            'exec_price': last_px,
            'timestamp': datetime.now()
        })

    # Log
    self.logger.info(f"Execution Report: {cl_ord_id} - {exec_type_str} - {status_str}")

    # Trigger callback
    if self._on_execution_report:
        self._on_execution_report({
            'cl_ord_id': cl_ord_id,
            'exec_id': exec_id,
            'exec_type': exec_type_str,
            'status': status_str,
            'symbol': symbol,
            'side': 'BUY' if side == '1' else 'SELL',
            'order_qty': order_qty,
            'cum_qty': cum_qty,
            'leaves_qty': leaves_qty,
            'avg_px': avg_px,
            'last_qty': last_qty,
            'last_px': last_px
        })

def _handle_cancel_reject(self, msg):
    """Process OrderCancelReject (MsgType=9)"""
    # Extract fields
    cl_ord_id = msg.get(11).decode('utf-8')  # ClOrdID (cancel request)
    orig_cl_ord_id = msg.get(41).decode('utf-8')  # OrigClOrdID
    cxl_rej_reason = msg.get(434).decode('utf-8')  # CxlRejReason
    text = ""
    if msg.get(58):
        text = msg.get(58).decode('utf-8')  # Text

    # Map reason
    reason_map = {
        '0': 'TOO_LATE_TO_CANCEL',
        '1': 'UNKNOWN_ORDER'
    }
    reason_str = reason_map.get(cxl_rej_reason, cxl_rej_reason)

    # Revert order status
    self.order_manager.update_order(orig_cl_ord_id, {
        'status': 'NEW',  # Revert to previous state
        'cancel_reject_reason': reason_str,
        'cancel_reject_text': text
    })

    # Log
    self.logger.warning(f"Cancel Rejected: {orig_cl_ord_id} - {reason_str} - {text}")

    # Trigger callback
    if self._on_cancel_reject:
        self._on_cancel_reject({
            'cl_ord_id': cl_ord_id,
            'orig_cl_ord_id': orig_cl_ord_id,
            'reason': reason_str,
            'text': text
        })
```

---

#### 1.4 Order State Tracking

**File**: `client/order_manager.py`

**Class**: `OrderManager`

**Responsibilities:**
- Maintain local cache of all orders
- Store order history in SQLite database
- Provide query interface
- Track execution history

```python
class OrderManager:
    def __init__(self, db_path='client_orders.db'):
        """Initialize order manager with database"""
        self.db_path = db_path
        self._init_database()
        self.orders = {}  # In-memory cache: {cl_ord_id: order_dict}
        self.executions = {}  # {cl_ord_id: [execution_list]}
        self._load_from_database()

    def _init_database(self):
        """Create database tables if not exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Orders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                cl_ord_id TEXT PRIMARY KEY,
                orig_cl_ord_id TEXT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                order_type TEXT NOT NULL,
                price REAL,
                time_in_force TEXT,
                status TEXT NOT NULL,
                filled_quantity INTEGER DEFAULT 0,
                remaining_quantity INTEGER,
                avg_price REAL DEFAULT 0,
                submitted_at TEXT NOT NULL,
                updated_at TEXT
            )
        ''')

        # Executions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cl_ord_id TEXT NOT NULL,
                exec_id TEXT NOT NULL,
                exec_quantity INTEGER NOT NULL,
                exec_price REAL NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (cl_ord_id) REFERENCES orders(cl_ord_id)
            )
        ''')

        conn.commit()
        conn.close()

    def add_order(self, order_dict):
        """Add new order to cache and database"""
        cl_ord_id = order_dict['cl_ord_id']

        # Add to cache
        self.orders[cl_ord_id] = order_dict

        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO orders (cl_ord_id, orig_cl_ord_id, symbol, side,
                               quantity, order_type, price, time_in_force,
                               status, submitted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            cl_ord_id,
            order_dict.get('orig_cl_ord_id'),
            order_dict['symbol'],
            order_dict['side'],
            order_dict['quantity'],
            order_dict['order_type'],
            order_dict.get('price'),
            order_dict.get('time_in_force', 'DAY'),
            order_dict['status'],
            order_dict['submitted_at'].isoformat()
        ))
        conn.commit()
        conn.close()

    def update_order(self, cl_ord_id, updates):
        """Update order in cache and database"""
        if cl_ord_id not in self.orders:
            raise KeyError(f"Order {cl_ord_id} not found")

        # Update cache
        self.orders[cl_ord_id].update(updates)
        self.orders[cl_ord_id]['updated_at'] = datetime.now()

        # Update database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [datetime.now().isoformat(), cl_ord_id]

        cursor.execute(f'''
            UPDATE orders SET {set_clause}, updated_at = ?
            WHERE cl_ord_id = ?
        ''', values)
        conn.commit()
        conn.close()

    def get_order(self, cl_ord_id):
        """Get order by ClOrdID"""
        return self.orders.get(cl_ord_id)

    def list_orders(self, status=None, symbol=None, side=None):
        """List orders with optional filters"""
        result = list(self.orders.values())

        if status:
            result = [o for o in result if o['status'] == status]
        if symbol:
            result = [o for o in result if o['symbol'] == symbol]
        if side:
            result = [o for o in result if o['side'] == side]

        # Sort by submission time (newest first)
        result.sort(key=lambda o: o['submitted_at'], reverse=True)

        return result

    def add_execution(self, cl_ord_id, execution_dict):
        """Add execution to order history"""
        if cl_ord_id not in self.executions:
            self.executions[cl_ord_id] = []

        self.executions[cl_ord_id].append(execution_dict)

        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO executions (cl_ord_id, exec_id, exec_quantity,
                                    exec_price, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            cl_ord_id,
            execution_dict['exec_id'],
            execution_dict['exec_quantity'],
            execution_dict['exec_price'],
            execution_dict['timestamp'].isoformat()
        ))
        conn.commit()
        conn.close()

    def get_executions(self, cl_ord_id):
        """Get all executions for an order"""
        return self.executions.get(cl_ord_id, [])
```

---

#### 1.5 Configuration

**File**: `client/config.py`

**Purpose**: Manage client configuration from YAML file

**Configuration File**: `config/client_config.yaml`

```yaml
# FIX Connection Settings
connection:
  host: localhost
  port: 15001
  sender_comp_id: CLIENT_001
  target_comp_id: BROKER
  heartbeat_interval: 30
  reconnect_interval: 5
  max_reconnect_attempts: 10

# Order Settings
orders:
  cl_ord_id_prefix: CLIENT_001_
  default_time_in_force: DAY

# Database Settings
database:
  path: client_orders.db

# Logging Settings
logging:
  level: INFO
  file: logs/fix_client.log
  console: true
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

**Configuration Loader:**

```python
import yaml

class ClientConfig:
    def __init__(self, config_path='config/client_config.yaml'):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

    def get(self, key_path, default=None):
        """Get config value by dot notation (e.g., 'connection.host')"""
        keys = key_path.split('.')
        value = self.config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
        return value if value is not None else default

    @property
    def connection_host(self):
        return self.get('connection.host', 'localhost')

    @property
    def connection_port(self):
        return self.get('connection.port', 15001)

    @property
    def sender_comp_id(self):
        return self.get('connection.sender_comp_id', 'CLIENT_001')

    @property
    def target_comp_id(self):
        return self.get('connection.target_comp_id', 'BROKER')
```

---

### Phase 2: CLI Application

**Goal**: Provide user-friendly command-line interface for trading

#### 2.1 CLI Structure

**File**: `client/cli.py`

**Framework**: Click (Python CLI framework)

**Commands:**

```python
import click
from rich.console import Console
from rich.table import Table
from client.fix_client import FIXClient
from client.config import ClientConfig

console = Console()

@click.group()
@click.pass_context
def cli(ctx):
    """FIX Trading Client CLI"""
    ctx.ensure_object(dict)
    config = ClientConfig()
    ctx.obj['config'] = config

@cli.command()
@click.pass_context
def connect(ctx):
    """Connect to broker FIX server"""
    config = ctx.obj['config']
    client = FIXClient(
        host=config.connection_host,
        port=config.connection_port,
        sender_comp_id=config.sender_comp_id,
        target_comp_id=config.target_comp_id
    )

    try:
        client.connect()
        console.print("[green]✓ Connected to broker[/green]")
        ctx.obj['client'] = client
    except Exception as e:
        console.print(f"[red]✗ Connection failed: {e}[/red]")
        raise click.Abort()

@cli.command()
@click.option('--symbol', required=True, help='Stock symbol (e.g., AAPL)')
@click.option('--side', type=click.Choice(['BUY', 'SELL']), required=True)
@click.option('--qty', type=int, required=True, help='Quantity')
@click.option('--type', 'order_type', type=click.Choice(['MARKET', 'LIMIT']),
              default='MARKET')
@click.option('--price', type=float, help='Limit price (required for LIMIT orders)')
@click.option('--tif', default='DAY', help='Time in force')
@click.option('--json', 'json_output', is_flag=True, help='Output as JSON')
@click.pass_context
def submit(ctx, symbol, side, qty, order_type, price, tif, json_output):
    """Submit a new order"""
    if order_type == 'LIMIT' and price is None:
        console.print("[red]Error: --price required for LIMIT orders[/red]")
        raise click.Abort()

    client = ctx.obj.get('client')
    if not client:
        console.print("[red]Not connected. Run 'connect' first.[/red]")
        raise click.Abort()

    try:
        cl_ord_id = client.submit_order(
            symbol=symbol,
            side=side,
            quantity=qty,
            order_type=order_type,
            price=price,
            time_in_force=tif
        )

        if json_output:
            import json
            click.echo(json.dumps({
                'cl_ord_id': cl_ord_id,
                'symbol': symbol,
                'side': side,
                'quantity': qty,
                'status': 'SUBMITTED'
            }))
        else:
            console.print(f"[green]✓ Order submitted: {cl_ord_id}[/green]")
            console.print(f"  Symbol: {symbol}")
            console.print(f"  Side: {side}")
            console.print(f"  Quantity: {qty}")
            console.print(f"  Type: {order_type}")
            if price:
                console.print(f"  Price: ${price:.2f}")

    except Exception as e:
        console.print(f"[red]✗ Order failed: {e}[/red]")
        raise click.Abort()

@cli.command()
@click.option('--order-id', required=True, help='Client Order ID')
@click.pass_context
def cancel(ctx, order_id):
    """Cancel an order"""
    client = ctx.obj.get('client')
    if not client:
        console.print("[red]Not connected[/red]")
        raise click.Abort()

    # Get order details
    order = client.order_manager.get_order(order_id)
    if not order:
        console.print(f"[red]Order {order_id} not found[/red]")
        raise click.Abort()

    try:
        cancel_id = client.cancel_order(
            cl_ord_id=order_id,
            symbol=order['symbol'],
            side=order['side']
        )
        console.print(f"[green]✓ Cancel request sent: {cancel_id}[/green]")
    except Exception as e:
        console.print(f"[red]✗ Cancel failed: {e}[/red]")
        raise click.Abort()

@cli.command()
@click.option('--order-id', required=True, help='Original Client Order ID')
@click.option('--qty', type=int, help='New quantity')
@click.option('--price', type=float, help='New price')
@click.pass_context
def amend(ctx, order_id, qty, price):
    """Amend an order"""
    if qty is None and price is None:
        console.print("[red]Error: Specify --qty or --price (or both)[/red]")
        raise click.Abort()

    client = ctx.obj.get('client')
    if not client:
        console.print("[red]Not connected[/red]")
        raise click.Abort()

    order = client.order_manager.get_order(order_id)
    if not order:
        console.print(f"[red]Order {order_id} not found[/red]")
        raise click.Abort()

    try:
        new_id = client.amend_order(
            orig_cl_ord_id=order_id,
            symbol=order['symbol'],
            side=order['side'],
            new_quantity=qty,
            new_price=price
        )
        console.print(f"[green]✓ Amend request sent: {new_id}[/green]")
    except Exception as e:
        console.print(f"[red]✗ Amend failed: {e}[/red]")
        raise click.Abort()

@cli.command()
@click.option('--status', help='Filter by status')
@click.option('--symbol', help='Filter by symbol')
@click.option('--json', 'json_output', is_flag=True, help='Output as JSON')
@click.pass_context
def list(ctx, status, symbol, json_output):
    """List orders"""
    client = ctx.obj.get('client')
    if not client:
        console.print("[red]Not connected[/red]")
        raise click.Abort()

    orders = client.order_manager.list_orders(status=status, symbol=symbol)

    if json_output:
        import json
        click.echo(json.dumps(orders, default=str))
    else:
        if not orders:
            console.print("[yellow]No orders found[/yellow]")
            return

        table = Table(title="Orders")
        table.add_column("ClOrdID", style="cyan")
        table.add_column("Symbol", style="magenta")
        table.add_column("Side", style="green")
        table.add_column("Qty", justify="right")
        table.add_column("Type")
        table.add_column("Price", justify="right")
        table.add_column("Status", style="yellow")
        table.add_column("Filled", justify="right")
        table.add_column("Remaining", justify="right")

        for order in orders:
            table.add_row(
                order['cl_ord_id'][:20],
                order['symbol'],
                order['side'],
                str(order['quantity']),
                order['order_type'],
                f"${order.get('price', 0):.2f}" if order.get('price') else '-',
                order['status'],
                str(order.get('filled_quantity', 0)),
                str(order.get('remaining_quantity', order['quantity']))
            )

        console.print(table)

@cli.command()
@click.option('--order-id', required=True, help='Client Order ID')
@click.pass_context
def status(ctx, order_id):
    """Get order status"""
    client = ctx.obj.get('client')
    if not client:
        console.print("[red]Not connected[/red]")
        raise click.Abort()

    order = client.order_manager.get_order(order_id)
    if not order:
        console.print(f"[red]Order {order_id} not found[/red]")
        return

    console.print(f"\n[bold]Order Details[/bold]")
    console.print(f"  ClOrdID: {order['cl_ord_id']}")
    console.print(f"  Symbol: {order['symbol']}")
    console.print(f"  Side: {order['side']}")
    console.print(f"  Quantity: {order['quantity']}")
    console.print(f"  Type: {order['order_type']}")
    if order.get('price'):
        console.print(f"  Price: ${order['price']:.2f}")
    console.print(f"  Status: [yellow]{order['status']}[/yellow]")
    console.print(f"  Filled: {order.get('filled_quantity', 0)}")
    console.print(f"  Remaining: {order.get('remaining_quantity', order['quantity'])}")
    if order.get('avg_price'):
        console.print(f"  Avg Price: ${order['avg_price']:.2f}")

    # Show executions
    executions = client.order_manager.get_executions(order_id)
    if executions:
        console.print(f"\n[bold]Executions ({len(executions)})[/bold]")
        for i, exec in enumerate(executions, 1):
            console.print(f"  {i}. {exec['exec_quantity']} @ ${exec['exec_price']:.2f} - {exec['exec_id']}")

@cli.command()
@click.pass_context
def interactive(ctx):
    """Interactive mode"""
    console.print("[bold cyan]FIX Client Interactive Mode[/bold cyan]")
    console.print("Type 'help' for commands, 'quit' to exit\n")

    config = ctx.obj['config']
    client = None

    while True:
        try:
            cmd = console.input("[bold green]>[/bold green] ").strip()

            if not cmd:
                continue

            if cmd == 'quit' or cmd == 'exit':
                if client:
                    client.disconnect()
                console.print("Goodbye!")
                break

            elif cmd == 'help':
                console.print("""
Available commands:
  connect                    - Connect to broker
  submit SYMBOL SIDE QTY     - Submit order (e.g., submit AAPL BUY 100)
  cancel ORDER_ID            - Cancel order
  amend ORDER_ID [qty=N] [price=N] - Amend order
  list                       - List all orders
  status ORDER_ID            - Get order status
  quit                       - Exit
                """)

            elif cmd == 'connect':
                client = FIXClient(
                    host=config.connection_host,
                    port=config.connection_port,
                    sender_comp_id=config.sender_comp_id,
                    target_comp_id=config.target_comp_id
                )
                client.connect()
                console.print("[green]✓ Connected[/green]")

            elif cmd.startswith('submit '):
                if not client:
                    console.print("[red]Not connected[/red]")
                    continue

                parts = cmd.split()
                if len(parts) < 4:
                    console.print("[red]Usage: submit SYMBOL SIDE QTY [TYPE] [PRICE][/red]")
                    continue

                symbol = parts[1]
                side = parts[2].upper()
                qty = int(parts[3])
                order_type = parts[4].upper() if len(parts) > 4 else 'MARKET'
                price = float(parts[5]) if len(parts) > 5 else None

                cl_ord_id = client.submit_order(symbol, side, qty, order_type, price)
                console.print(f"[green]✓ Order submitted: {cl_ord_id}[/green]")

            elif cmd.startswith('cancel '):
                if not client:
                    console.print("[red]Not connected[/red]")
                    continue

                order_id = cmd.split()[1]
                order = client.order_manager.get_order(order_id)
                if order:
                    client.cancel_order(order_id, order['symbol'], order['side'])
                    console.print("[green]✓ Cancel sent[/green]")
                else:
                    console.print("[red]Order not found[/red]")

            elif cmd == 'list':
                if not client:
                    console.print("[red]Not connected[/red]")
                    continue

                orders = client.order_manager.list_orders()
                if orders:
                    for order in orders[:10]:  # Show last 10
                        console.print(f"  {order['cl_ord_id'][:20]} | {order['symbol']} | {order['side']} | {order['quantity']} | {order['status']}")
                else:
                    console.print("[yellow]No orders[/yellow]")

            else:
                console.print(f"[red]Unknown command: {cmd}[/red]")

        except KeyboardInterrupt:
            console.print("\nUse 'quit' to exit")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

if __name__ == '__main__':
    cli()
```

---

#### 2.2 CLI Entry Point Script

**File**: `scripts/fix-client`

```bash
#!/usr/bin/env python3
"""FIX Client CLI Entry Point"""
import sys
from client.cli import cli

if __name__ == '__main__':
    sys.exit(cli())
```

Make it executable:
```bash
chmod +x scripts/fix-client
```

---

### Phase 3: Background Service Mode

**Goal**: Run client as persistent service with API interface

#### 3.1 Service Implementation

**File**: `client/service.py`

```python
import threading
import time
from flask import Flask, jsonify, request
from client.fix_client import FIXClient
from client.config import ClientConfig

class FIXClientService:
    def __init__(self, config_path='config/client_config.yaml'):
        self.config = ClientConfig(config_path)
        self.client = None
        self.running = False

        # Create Flask app for API
        self.app = Flask(__name__)
        self._setup_routes()

    def start(self):
        """Start FIX client and API server"""
        # Connect FIX client
        self.client = FIXClient(
            host=self.config.connection_host,
            port=self.config.connection_port,
            sender_comp_id=self.config.sender_comp_id,
            target_comp_id=self.config.target_comp_id
        )
        self.client.connect()

        # Set up callbacks
        self.client.on_execution_report(self._handle_execution_report)
        self.client.on_cancel_reject(self._handle_cancel_reject)

        self.running = True

        # Start Flask API in separate thread
        api_thread = threading.Thread(target=self._run_api)
        api_thread.daemon = True
        api_thread.start()

        print("FIX Client Service started")

    def stop(self):
        """Stop service"""
        self.running = False
        if self.client:
            self.client.disconnect()

    def _run_api(self):
        """Run Flask API server"""
        self.app.run(host='0.0.0.0', port=5001, debug=False)

    def _setup_routes(self):
        """Setup Flask routes"""

        @self.app.route('/api/health', methods=['GET'])
        def health():
            return jsonify({
                'status': 'running',
                'connected': self.client.is_connected() if self.client else False
            })

        @self.app.route('/api/orders', methods=['POST'])
        def submit_order():
            data = request.json
            try:
                cl_ord_id = self.client.submit_order(
                    symbol=data['symbol'],
                    side=data['side'],
                    quantity=data['quantity'],
                    order_type=data.get('order_type', 'MARKET'),
                    price=data.get('price'),
                    time_in_force=data.get('time_in_force', 'DAY')
                )
                return jsonify({'cl_ord_id': cl_ord_id}), 201
            except Exception as e:
                return jsonify({'error': str(e)}), 400

        @self.app.route('/api/orders', methods=['GET'])
        def list_orders():
            status = request.args.get('status')
            symbol = request.args.get('symbol')
            orders = self.client.order_manager.list_orders(status=status, symbol=symbol)
            return jsonify(orders)

        @self.app.route('/api/orders/<cl_ord_id>', methods=['GET'])
        def get_order(cl_ord_id):
            order = self.client.order_manager.get_order(cl_ord_id)
            if order:
                return jsonify(order)
            return jsonify({'error': 'Order not found'}), 404

        @self.app.route('/api/orders/<cl_ord_id>/cancel', methods=['POST'])
        def cancel_order(cl_ord_id):
            order = self.client.order_manager.get_order(cl_ord_id)
            if not order:
                return jsonify({'error': 'Order not found'}), 404

            try:
                cancel_id = self.client.cancel_order(
                    cl_ord_id=cl_ord_id,
                    symbol=order['symbol'],
                    side=order['side']
                )
                return jsonify({'cancel_cl_ord_id': cancel_id})
            except Exception as e:
                return jsonify({'error': str(e)}), 400

        @self.app.route('/api/orders/<cl_ord_id>/amend', methods=['POST'])
        def amend_order(cl_ord_id):
            data = request.json
            order = self.client.order_manager.get_order(cl_ord_id)
            if not order:
                return jsonify({'error': 'Order not found'}), 404

            try:
                new_id = self.client.amend_order(
                    orig_cl_ord_id=cl_ord_id,
                    symbol=order['symbol'],
                    side=order['side'],
                    new_quantity=data.get('quantity'),
                    new_price=data.get('price')
                )
                return jsonify({'new_cl_ord_id': new_id})
            except Exception as e:
                return jsonify({'error': str(e)}), 400

        @self.app.route('/api/orders/<cl_ord_id>/executions', methods=['GET'])
        def get_executions(cl_ord_id):
            executions = self.client.order_manager.get_executions(cl_ord_id)
            return jsonify(executions)

    def _handle_execution_report(self, report):
        """Handle execution report from FIX client"""
        print(f"Execution: {report['cl_ord_id']} - {report['exec_type']} - {report['status']}")

    def _handle_cancel_reject(self, reject):
        """Handle cancel reject from FIX client"""
        print(f"Cancel Rejected: {reject['orig_cl_ord_id']} - {reject['reason']}")

if __name__ == '__main__':
    service = FIXClientService()
    service.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        service.stop()
```

---

### Dependencies

Add to `pyproject.toml`:

```toml
[project.dependencies]
# ... existing dependencies ...
"click>=8.0.0",           # CLI framework
"pyyaml>=6.0",            # Configuration files
"rich>=13.0.0",           # Rich terminal output
"tabulate>=0.9.0",        # Table formatting
```

---

### Testing Strategy

**File**: `tests/client/test_fix_client.py`

```python
import pytest
from client.fix_client import FIXClient
from client.order_manager import OrderManager

@pytest.fixture
def fix_client():
    """Create FIX client for testing"""
    client = FIXClient(
        host='localhost',
        port=15001,
        sender_comp_id='TEST_CLIENT',
        target_comp_id='BROKER'
    )
    yield client
    if client.is_connected():
        client.disconnect()

def test_connection(fix_client):
    """Test FIX connection"""
    fix_client.connect()
    assert fix_client.is_connected()

def test_submit_order(fix_client):
    """Test order submission"""
    fix_client.connect()
    cl_ord_id = fix_client.submit_order(
        symbol='AAPL',
        side='BUY',
        quantity=100,
        order_type='MARKET'
    )
    assert cl_ord_id is not None

    # Verify order in cache
    order = fix_client.order_manager.get_order(cl_ord_id)
    assert order is not None
    assert order['symbol'] == 'AAPL'
    assert order['side'] == 'BUY'
    assert order['quantity'] == 100

def test_cancel_order(fix_client):
    """Test order cancellation"""
    fix_client.connect()

    # Submit order
    cl_ord_id = fix_client.submit_order('AAPL', 'BUY', 100, 'LIMIT', 230.00)

    # Cancel order
    cancel_id = fix_client.cancel_order(cl_ord_id, 'AAPL', 'BUY')
    assert cancel_id is not None

def test_amend_order(fix_client):
    """Test order amendment"""
    fix_client.connect()

    # Submit order
    cl_ord_id = fix_client.submit_order('AAPL', 'BUY', 100, 'LIMIT', 230.00)

    # Amend order
    new_id = fix_client.amend_order(cl_ord_id, 'AAPL', 'BUY', new_quantity=150)
    assert new_id is not None
    assert new_id != cl_ord_id

def test_list_orders(fix_client):
    """Test listing orders"""
    fix_client.connect()

    # Submit multiple orders
    fix_client.submit_order('AAPL', 'BUY', 100, 'MARKET')
    fix_client.submit_order('MSFT', 'SELL', 50, 'LIMIT', 420.00)

    # List all orders
    orders = fix_client.order_manager.list_orders()
    assert len(orders) >= 2

    # Filter by symbol
    aapl_orders = fix_client.order_manager.list_orders(symbol='AAPL')
    assert all(o['symbol'] == 'AAPL' for o in aapl_orders)
```

---

### File Structure Summary

```
client/
├── __init__.py
├── fix_client.py          # Core FIX client (500+ lines)
├── order_manager.py       # Order state tracking (200+ lines)
├── config.py              # Configuration management (100+ lines)
├── cli.py                 # CLI application (400+ lines)
└── service.py             # Background service (200+ lines)

config/
└── client_config.yaml     # Default configuration

scripts/
├── fix-client             # CLI entry point script
└── README.md              # Updated with client instructions

tests/
└── client/
    ├── __init__.py
    ├── test_fix_client.py
    ├── test_order_manager.py
    └── test_cli.py

logs/
└── fix_client.log         # Client logs

client_orders.db           # SQLite database (created at runtime)
```

---

### Implementation Timeline

**Phase 1: Core Library** (4-6 hours)
- Day 1 Morning: Connection management and logon
- Day 1 Afternoon: Order operations (submit, cancel, amend)
- Day 2 Morning: Response handling and callbacks
- Day 2 Afternoon: Order state tracking and configuration

**Phase 2: CLI Application** (2-3 hours)
- Day 3 Morning: CLI commands (submit, cancel, amend, list)
- Day 3 Afternoon: Interactive mode and output formatting

**Phase 3: Service Mode** (2-3 hours)
- Day 4: Background service and REST API wrapper

**Testing & Documentation** (1-2 hours)
- Day 4-5: Write tests and update documentation

**Total: 9-14 hours across 4-5 days**

---

### Success Criteria

✅ Client connects to broker FIX server
✅ Client sends Logon and receives Logon response
✅ Client submits orders (market and limit)
✅ Client receives ExecutionReports and updates order state
✅ Client cancels orders via OrderCancelRequest
✅ Client amends orders via OrderCancelReplaceRequest
✅ Client handles OrderCancelReject appropriately
✅ Client maintains sequence numbers correctly
✅ Client auto-reconnects on disconnection
✅ CLI provides user-friendly interface
✅ CLI supports both command and interactive modes
✅ Service mode provides REST API interface
✅ All order history persisted to database
✅ Test coverage >80%
✅ Comprehensive documentation

---

### Usage Examples

#### Command Mode
```bash
# Connect and submit order
$ fix-client submit --symbol AAPL --side BUY --qty 100 --type MARKET

# Cancel order
$ fix-client cancel --order-id CLIENT_001_20251023120000

# Amend order
$ fix-client amend --order-id CLIENT_001_20251023120000 --qty 150

# List orders
$ fix-client list --status NEW

# Check order status
$ fix-client status --order-id CLIENT_001_20251023120000
```

#### Interactive Mode
```bash
$ fix-client interactive
FIX Client Interactive Mode
Type 'help' for commands, 'quit' to exit

> connect
✓ Connected to broker

> submit AAPL BUY 100 MARKET
✓ Order submitted: CLIENT_001_20251023120000

> list
  CLIENT_001_20251023120000 | AAPL | BUY | 100 | NEW | 0 | 100

> cancel CLIENT_001_20251023120000
✓ Cancel request sent

> quit
Goodbye!
```

#### Service Mode
```bash
# Start service
$ python -m client.service

# Use REST API
$ curl -X POST http://localhost:5001/api/orders \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL", "side": "BUY", "quantity": 100, "order_type": "MARKET"}'

$ curl http://localhost:5001/api/orders
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- UV package manager
- Running FIX server (broker)

### Installation

```bash
# Clone repository
git clone <repo-url>
cd fix_agent

# Install dependencies
uv sync

# Initialize database
uv run python -c "from broker.models import init_db; init_db()"

# Load stock universe
uv run python scripts/load_stocks.py
```

### Running the System

**1. Start FIX Server (Broker):**
```bash
uv run python -m broker.fix_server
```

**2. Start Backend API (Optional):**
```bash
uv run flask --app broker.app run
```

**3. Use Client:**
```bash
# CLI mode
uv run python scripts/fix-client submit --symbol AAPL --side BUY --qty 100

# Interactive mode
uv run python scripts/fix-client interactive

# Service mode
uv run python -m client.service
```

### Running Tests

```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov

# Specific test file
uv run pytest tests/broker/test_fix_execution.py

# Watch mode
uv run pytest --watch
```

---

## Questions?

For issues or questions:
- Check logs in `logs/` directory
- Review FIX messages in `test_logs/`
- See `test_logs/fix_message_examples.md` for protocol reference

---

**End of Document**
