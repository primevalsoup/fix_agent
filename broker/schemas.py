"""
Pydantic schemas for API request/response validation
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, Literal
from datetime import datetime
from enum import Enum


# Enums
class OrderSideEnum(str, Enum):
    """Order side enumeration"""
    BUY = "BUY"
    SELL = "SELL"


class OrderTypeEnum(str, Enum):
    """Order type enumeration"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderStatusEnum(str, Enum):
    """Order status enumeration"""
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"


class TimeInForceEnum(str, Enum):
    """Time in force enumeration"""
    DAY = "DAY"
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"


# Request schemas
class OrderCreateRequest(BaseModel):
    """Request model for creating a new order"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symbol": "AAPL",
                "side": "BUY",
                "order_type": "LIMIT",
                "quantity": 100,
                "limit_price": 230.50,
                "time_in_force": "DAY",
                "sender_comp_id": "CLIENT_001"
            }
        }
    )

    symbol: str = Field(..., min_length=1, max_length=10, description="Stock symbol")
    side: OrderSideEnum
    order_type: OrderTypeEnum
    quantity: int = Field(..., gt=0, description="Order quantity must be positive")
    limit_price: Optional[float] = Field(None, gt=0, description="Limit price for LIMIT orders")
    time_in_force: TimeInForceEnum = Field(default=TimeInForceEnum.DAY)
    sender_comp_id: str = Field(..., min_length=1, description="Client identifier")

    @field_validator('limit_price')
    @classmethod
    def validate_limit_price(cls, v, info):
        """Validate that limit_price is provided for LIMIT orders"""
        if info.data.get('order_type') == OrderTypeEnum.LIMIT and v is None:
            raise ValueError('limit_price required for LIMIT orders')
        if info.data.get('order_type') == OrderTypeEnum.STOP_LIMIT and v is None:
            raise ValueError('limit_price required for STOP_LIMIT orders')
        return v

    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v):
        """Validate symbol format"""
        return v.upper().strip()


class OrderUpdateRequest(BaseModel):
    """Request model for updating an order"""
    quantity: Optional[int] = Field(None, gt=0)
    limit_price: Optional[float] = Field(None, gt=0)
    status: Optional[OrderStatusEnum] = None


class ExecutionCreateRequest(BaseModel):
    """Request model for creating an execution"""
    order_id: int = Field(..., gt=0, description="Order ID")
    exec_quantity: int = Field(..., gt=0, description="Execution quantity")
    exec_price: float = Field(..., gt=0, description="Execution price")

    @field_validator('exec_quantity')
    @classmethod
    def validate_exec_quantity(cls, v):
        """Validate execution quantity is positive"""
        if v <= 0:
            raise ValueError('exec_quantity must be positive')
        return v


class StockUpdateRequest(BaseModel):
    """Request model for updating a stock price"""
    last_price: float = Field(..., gt=0, description="Stock price must be positive")


# Response schemas
class OrderResponse(BaseModel):
    """Response model for order data"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    cl_ord_id: str
    symbol: str
    side: str  # Will be "BUY" or "SELL" from enum
    order_type: str  # Will be "MARKET", "LIMIT", etc.
    quantity: int
    limit_price: Optional[float] = None
    time_in_force: str
    status: str
    filled_quantity: int
    remaining_quantity: int
    sender_comp_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    @classmethod
    def from_orm(cls, order):
        """Create response from SQLAlchemy Order model"""
        return cls(
            id=order.id,
            cl_ord_id=order.cl_ord_id,
            symbol=order.symbol,
            side=order.side.value,
            order_type=order.order_type.value,
            quantity=order.quantity,
            limit_price=order.limit_price,
            time_in_force=order.time_in_force.value,
            status=order.status.value,
            filled_quantity=order.filled_quantity,
            remaining_quantity=order.remaining_quantity,
            sender_comp_id=order.sender_comp_id,
            created_at=order.created_at,
            updated_at=order.updated_at
        )


class ExecutionResponse(BaseModel):
    """Response model for execution data"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    exec_id: str
    order_id: int
    exec_quantity: int
    exec_price: float
    created_at: datetime

    @classmethod
    def from_orm(cls, execution):
        """Create response from SQLAlchemy Execution model"""
        return cls(
            id=execution.id,
            exec_id=execution.exec_id,
            order_id=execution.order_id,
            exec_quantity=execution.exec_quantity,
            exec_price=execution.exec_price,
            created_at=execution.created_at
        )


class StockResponse(BaseModel):
    """Response model for stock data"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    last_price: float
    created_at: datetime
    updated_at: Optional[datetime] = None

    @classmethod
    def from_orm(cls, stock):
        """Create response from SQLAlchemy Stock model"""
        return cls(
            id=stock.id,
            symbol=stock.symbol,
            last_price=stock.last_price,
            created_at=stock.created_at,
            updated_at=stock.updated_at
        )


class OrderListResponse(BaseModel):
    """Response model for list of orders"""
    orders: list[OrderResponse]
    total: int
    page: int = 1
    page_size: int = 100


class ExecutionListResponse(BaseModel):
    """Response model for list of executions"""
    executions: list[ExecutionResponse]
    total: int


class StockListResponse(BaseModel):
    """Response model for list of stocks"""
    stocks: list[StockResponse]
    total: int


class ErrorResponse(BaseModel):
    """Response model for errors"""
    error: str
    details: Optional[dict] = None
    status_code: int = 400


class SuccessResponse(BaseModel):
    """Response model for success messages"""
    message: str
    data: Optional[dict] = None
