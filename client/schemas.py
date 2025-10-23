"""
Pydantic schemas for Client-side order management
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, Literal
from datetime import datetime


class ClientOrder(BaseModel):
    """Client-side order model with validation"""
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )

    cl_ord_id: str = Field(..., description="Client Order ID")
    orig_cl_ord_id: Optional[str] = Field(None, description="Original ClOrdID for amendments")
    symbol: str = Field(..., min_length=1, max_length=10, description="Stock symbol")
    side: Literal["BUY", "SELL"]
    quantity: int = Field(..., gt=0, description="Order quantity")
    order_type: Literal["MARKET", "LIMIT", "STOP", "STOP_LIMIT"]
    price: Optional[float] = Field(None, gt=0, description="Limit price")
    time_in_force: Literal["DAY", "GTC", "IOC", "FOK"] = "DAY"
    status: Literal[
        "PENDING_NEW",
        "NEW",
        "PARTIALLY_FILLED",
        "FILLED",
        "CANCELED",
        "REJECTED",
        "PENDING_CANCEL",
        "PENDING_REPLACE"
    ]
    filled_quantity: int = Field(default=0, ge=0, description="Filled quantity")
    remaining_quantity: int = Field(..., ge=0, description="Remaining quantity")
    avg_price: float = Field(default=0.0, ge=0, description="Average fill price")
    submitted_at: datetime
    updated_at: Optional[datetime] = None
    cancel_cl_ord_id: Optional[str] = None
    cancel_reject_reason: Optional[str] = None
    cancel_reject_text: Optional[str] = None

    @field_validator('remaining_quantity')
    @classmethod
    def validate_remaining_quantity(cls, v, info):
        """Validate remaining quantity"""
        quantity = info.data.get('quantity')
        filled_quantity = info.data.get('filled_quantity', 0)
        if quantity and v != (quantity - filled_quantity):
            raise ValueError('remaining_quantity must equal quantity - filled_quantity')
        return v

    @field_validator('filled_quantity')
    @classmethod
    def validate_filled_quantity(cls, v, info):
        """Validate filled quantity doesn't exceed total"""
        quantity = info.data.get('quantity')
        if quantity and v > quantity:
            raise ValueError('filled_quantity cannot exceed quantity')
        return v

    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v):
        """Normalize symbol to uppercase"""
        return v.upper().strip()

    @field_validator('price')
    @classmethod
    def validate_price(cls, v, info):
        """Validate price is provided for LIMIT orders"""
        order_type = info.data.get('order_type')
        if order_type in ["LIMIT", "STOP_LIMIT"] and v is None:
            raise ValueError('price required for LIMIT and STOP_LIMIT orders')
        return v


class ClientExecution(BaseModel):
    """Client-side execution model"""
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )

    exec_id: str = Field(..., description="Execution ID")
    exec_quantity: int = Field(..., gt=0, description="Executed quantity")
    exec_price: float = Field(..., gt=0, description="Execution price")
    timestamp: datetime = Field(default_factory=datetime.now)


class OrderSubmitRequest(BaseModel):
    """Request to submit a new order"""
    symbol: str = Field(..., min_length=1, max_length=10)
    side: Literal["BUY", "SELL"]
    quantity: int = Field(..., gt=0)
    order_type: Literal["MARKET", "LIMIT"] = "MARKET"
    price: Optional[float] = Field(None, gt=0)
    time_in_force: Literal["DAY", "GTC", "IOC", "FOK"] = "DAY"

    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v):
        return v.upper().strip()

    @field_validator('price')
    @classmethod
    def validate_price(cls, v, info):
        if info.data.get('order_type') == "LIMIT" and v is None:
            raise ValueError('price required for LIMIT orders')
        return v


class OrderCancelRequest(BaseModel):
    """Request to cancel an order"""
    cl_ord_id: str = Field(..., min_length=1, description="Order to cancel")


class OrderAmendRequest(BaseModel):
    """Request to amend an order"""
    cl_ord_id: str = Field(..., min_length=1, description="Order to amend")
    new_quantity: Optional[int] = Field(None, gt=0, description="New quantity")
    new_price: Optional[float] = Field(None, gt=0, description="New price")

    @field_validator('new_quantity')
    @classmethod
    def validate_at_least_one_change(cls, v, info):
        """Validate that at least one field is being changed"""
        if v is None and info.data.get('new_price') is None:
            raise ValueError('Must specify new_quantity or new_price (or both)')
        return v


class OrderStatusResponse(BaseModel):
    """Response with order status"""
    order: ClientOrder
    executions: list[ClientExecution] = []


class OrderListResponse(BaseModel):
    """Response with list of orders"""
    orders: list[ClientOrder]
    total: int
