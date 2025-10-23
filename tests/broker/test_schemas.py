"""
Tests for Pydantic schemas
"""
import pytest
from pydantic import ValidationError
from datetime import datetime
from broker.schemas import (
    OrderCreateRequest, OrderUpdateRequest, OrderResponse,
    ExecutionCreateRequest, ExecutionResponse,
    StockUpdateRequest, StockResponse,
    OrderSideEnum, OrderTypeEnum, OrderStatusEnum, TimeInForceEnum,
    ErrorResponse
)


class TestOrderCreateRequest:
    """Tests for OrderCreateRequest schema"""

    def test_valid_market_order(self):
        """Test creating valid market order"""
        order = OrderCreateRequest(
            symbol="AAPL",
            side=OrderSideEnum.BUY,
            order_type=OrderTypeEnum.MARKET,
            quantity=100,
            sender_comp_id="CLIENT_001"
        )
        assert order.symbol == "AAPL"
        assert order.side == OrderSideEnum.BUY
        assert order.quantity == 100
        assert order.time_in_force == TimeInForceEnum.DAY

    def test_valid_limit_order(self):
        """Test creating valid limit order"""
        order = OrderCreateRequest(
            symbol="MSFT",
            side=OrderSideEnum.SELL,
            order_type=OrderTypeEnum.LIMIT,
            quantity=50,
            limit_price=420.50,
            time_in_force=TimeInForceEnum.GTC,
            sender_comp_id="CLIENT_001"
        )
        assert order.limit_price == 420.50
        assert order.time_in_force == TimeInForceEnum.GTC

    def test_symbol_normalization(self):
        """Test symbol is normalized to uppercase"""
        order = OrderCreateRequest(
            symbol="  aapl  ",
            side=OrderSideEnum.BUY,
            order_type=OrderTypeEnum.MARKET,
            quantity=100,
            sender_comp_id="CLIENT_001"
        )
        assert order.symbol == "AAPL"

    def test_limit_order_missing_price(self):
        """Test limit order validation requires price"""
        with pytest.raises(ValidationError) as exc:
            OrderCreateRequest(
                symbol="AAPL",
                side=OrderSideEnum.BUY,
                order_type=OrderTypeEnum.LIMIT,
                quantity=100,
                sender_comp_id="CLIENT_001"
            )
        assert "limit_price required" in str(exc.value).lower()

    def test_invalid_quantity(self):
        """Test negative quantity is rejected"""
        with pytest.raises(ValidationError):
            OrderCreateRequest(
                symbol="AAPL",
                side=OrderSideEnum.BUY,
                order_type=OrderTypeEnum.MARKET,
                quantity=-10,
                sender_comp_id="CLIENT_001"
            )

    def test_zero_quantity(self):
        """Test zero quantity is rejected"""
        with pytest.raises(ValidationError):
            OrderCreateRequest(
                symbol="AAPL",
                side=OrderSideEnum.BUY,
                order_type=OrderTypeEnum.MARKET,
                quantity=0,
                sender_comp_id="CLIENT_001"
            )

    def test_invalid_limit_price(self):
        """Test negative limit price is rejected"""
        with pytest.raises(ValidationError):
            OrderCreateRequest(
                symbol="AAPL",
                side=OrderSideEnum.BUY,
                order_type=OrderTypeEnum.LIMIT,
                quantity=100,
                limit_price=-10.0,
                sender_comp_id="CLIENT_001"
            )

    def test_empty_symbol(self):
        """Test empty symbol is rejected"""
        with pytest.raises(ValidationError):
            OrderCreateRequest(
                symbol="",
                side=OrderSideEnum.BUY,
                order_type=OrderTypeEnum.MARKET,
                quantity=100,
                sender_comp_id="CLIENT_001"
            )


class TestExecutionCreateRequest:
    """Tests for ExecutionCreateRequest schema"""

    def test_valid_execution(self):
        """Test creating valid execution request"""
        exec_req = ExecutionCreateRequest(
            order_id=1,
            exec_quantity=100,
            exec_price=230.50
        )
        assert exec_req.order_id == 1
        assert exec_req.exec_quantity == 100
        assert exec_req.exec_price == 230.50

    def test_invalid_order_id(self):
        """Test zero or negative order_id is rejected"""
        with pytest.raises(ValidationError):
            ExecutionCreateRequest(
                order_id=0,
                exec_quantity=100,
                exec_price=230.50
            )

    def test_invalid_quantity(self):
        """Test zero or negative quantity is rejected"""
        with pytest.raises(ValidationError):
            ExecutionCreateRequest(
                order_id=1,
                exec_quantity=0,
                exec_price=230.50
            )

    def test_invalid_price(self):
        """Test zero or negative price is rejected"""
        with pytest.raises(ValidationError):
            ExecutionCreateRequest(
                order_id=1,
                exec_quantity=100,
                exec_price=0
            )


class TestStockUpdateRequest:
    """Tests for StockUpdateRequest schema"""

    def test_valid_stock_update(self):
        """Test valid stock price update"""
        stock_update = StockUpdateRequest(last_price=150.75)
        assert stock_update.last_price == 150.75

    def test_invalid_price(self):
        """Test zero or negative price is rejected"""
        with pytest.raises(ValidationError):
            StockUpdateRequest(last_price=0)

        with pytest.raises(ValidationError):
            StockUpdateRequest(last_price=-10.0)


class TestOrderResponse:
    """Tests for OrderResponse schema"""

    def test_order_response_from_orm(self):
        """Test creating OrderResponse from SQLAlchemy model"""
        # Mock SQLAlchemy order object
        from broker.models import Order, OrderSide, OrderType, OrderStatus, TimeInForce

        mock_order = type('MockOrder', (), {
            'id': 1,
            'cl_ord_id': 'TEST_001',
            'symbol': 'AAPL',
            'side': OrderSide.BUY,
            'order_type': OrderType.MARKET,
            'quantity': 100,
            'limit_price': None,
            'time_in_force': TimeInForce.DAY,
            'status': OrderStatus.NEW,
            'filled_quantity': 0,
            'remaining_quantity': 100,
            'sender_comp_id': 'CLIENT_001',
            'created_at': datetime.now(),
            'updated_at': None
        })()

        response = OrderResponse.from_orm(mock_order)
        assert response.id == 1
        assert response.cl_ord_id == 'TEST_001'
        assert response.symbol == 'AAPL'
        assert response.side == 'BUY'


class TestErrorResponse:
    """Tests for ErrorResponse schema"""

    def test_simple_error(self):
        """Test creating simple error response"""
        error = ErrorResponse(error="Order not found")
        assert error.error == "Order not found"
        assert error.details is None
        assert error.status_code == 400

    def test_error_with_details(self):
        """Test error with additional details"""
        error = ErrorResponse(
            error="Validation failed",
            details={"field": "quantity", "reason": "must be positive"},
            status_code=422
        )
        assert error.details["field"] == "quantity"
        assert error.status_code == 422


class TestEnums:
    """Tests for enum validation"""

    def test_order_side_enum(self):
        """Test OrderSideEnum"""
        assert OrderSideEnum.BUY == "BUY"
        assert OrderSideEnum.SELL == "SELL"

    def test_order_type_enum(self):
        """Test OrderTypeEnum"""
        assert OrderTypeEnum.MARKET == "MARKET"
        assert OrderTypeEnum.LIMIT == "LIMIT"
        assert OrderTypeEnum.STOP == "STOP"
        assert OrderTypeEnum.STOP_LIMIT == "STOP_LIMIT"

    def test_order_status_enum(self):
        """Test OrderStatusEnum"""
        assert OrderStatusEnum.NEW == "NEW"
        assert OrderStatusEnum.PARTIALLY_FILLED == "PARTIALLY_FILLED"
        assert OrderStatusEnum.FILLED == "FILLED"
        assert OrderStatusEnum.CANCELED == "CANCELED"
        assert OrderStatusEnum.REJECTED == "REJECTED"

    def test_time_in_force_enum(self):
        """Test TimeInForceEnum"""
        assert TimeInForceEnum.DAY == "DAY"
        assert TimeInForceEnum.GTC == "GTC"
        assert TimeInForceEnum.IOC == "IOC"
        assert TimeInForceEnum.FOK == "FOK"
