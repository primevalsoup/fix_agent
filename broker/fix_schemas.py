"""
Pydantic schemas for FIX Protocol 4.2 messages
Provides validation and serialization for FIX messages
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, Literal
from datetime import datetime
import simplefix


# FIX Tag constants
TAG_BEGIN_STRING = 8
TAG_MSG_TYPE = 35
TAG_SENDER_COMP_ID = 49
TAG_TARGET_COMP_ID = 56
TAG_MSG_SEQ_NUM = 34
TAG_SENDING_TIME = 52
TAG_CLORDID = 11
TAG_ORIG_CLORDID = 41
TAG_SYMBOL = 55
TAG_SIDE = 54
TAG_ORDERQTY = 38
TAG_ORDTYPE = 40
TAG_PRICE = 44
TAG_EXECID = 17
TAG_EXECTYPE = 150
TAG_ORDSTATUS = 39
TAG_CUMQTY = 14
TAG_LEAVESQTY = 151
TAG_AVGPX = 6
TAG_LASTQTY = 32
TAG_LASTPX = 31
TAG_TRANSACT_TIME = 60
TAG_HANDLINST = 21
TAG_TIMEINFORCE = 59
TAG_ENCRYPT_METHOD = 98
TAG_HEARTBTINT = 108
TAG_CXL_REJ_REASON = 434
TAG_TEXT = 58


class FIXHeader(BaseModel):
    """FIX message header"""
    begin_string: str = Field(default="FIX.4.2")
    sender_comp_id: str = Field(..., min_length=1, description="Sender identifier")
    target_comp_id: str = Field(..., min_length=1, description="Target identifier")
    msg_seq_num: int = Field(..., ge=1, description="Message sequence number")
    sending_time: datetime = Field(default_factory=datetime.now)

    @field_validator('begin_string')
    @classmethod
    def validate_fix_version(cls, v):
        """Validate FIX version"""
        if v != "FIX.4.2":
            raise ValueError('Only FIX.4.2 is supported')
        return v


class FIXLogon(BaseModel):
    """FIX Logon message (MsgType=A)"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    header: FIXHeader
    encrypt_method: Literal["0"] = "0"  # None
    heartbeat_interval: int = Field(..., ge=1, le=3600, description="Heartbeat interval in seconds")

    @classmethod
    def from_fix_message(cls, msg: simplefix.FixMessage) -> 'FIXLogon':
        """Parse from FIX message"""
        return cls(
            header=FIXHeader(
                begin_string=msg.get(TAG_BEGIN_STRING).decode('utf-8'),
                sender_comp_id=msg.get(TAG_SENDER_COMP_ID).decode('utf-8'),
                target_comp_id=msg.get(TAG_TARGET_COMP_ID).decode('utf-8'),
                msg_seq_num=int(msg.get(TAG_MSG_SEQ_NUM).decode('utf-8')),
                sending_time=datetime.strptime(
                    msg.get(TAG_SENDING_TIME).decode('utf-8'), '%Y%m%d-%H:%M:%S'
                ) if msg.get(TAG_SENDING_TIME) else datetime.now()
            ),
            encrypt_method=msg.get(TAG_ENCRYPT_METHOD).decode('utf-8') if msg.get(TAG_ENCRYPT_METHOD) else "0",
            heartbeat_interval=int(msg.get(TAG_HEARTBTINT).decode('utf-8'))
        )

    def to_fix_message(self) -> bytes:
        """Convert to FIX message format"""
        msg = simplefix.FixMessage()
        msg.append_pair(TAG_BEGIN_STRING, self.header.begin_string.encode())
        msg.append_pair(TAG_MSG_TYPE, b'A')
        msg.append_pair(TAG_SENDER_COMP_ID, self.header.sender_comp_id.encode())
        msg.append_pair(TAG_TARGET_COMP_ID, self.header.target_comp_id.encode())
        msg.append_pair(TAG_MSG_SEQ_NUM, str(self.header.msg_seq_num))
        msg.append_pair(TAG_SENDING_TIME, self.header.sending_time.strftime('%Y%m%d-%H:%M:%S'))
        msg.append_pair(TAG_ENCRYPT_METHOD, self.encrypt_method)
        msg.append_pair(TAG_HEARTBTINT, str(self.heartbeat_interval))
        return msg.encode()


class FIXNewOrderSingle(BaseModel):
    """FIX NewOrderSingle message (MsgType=D)"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    header: FIXHeader
    cl_ord_id: str = Field(..., min_length=1, description="Client Order ID")
    handl_inst: Literal["1", "2", "3"] = "1"  # 1=Automated, 2=Manual, 3=Manual Private
    symbol: str = Field(..., min_length=1, max_length=10, description="Stock symbol")
    side: Literal["1", "2"]  # 1=Buy, 2=Sell
    transact_time: datetime = Field(default_factory=datetime.now)
    ord_type: Literal["1", "2", "3", "4"]  # 1=Market, 2=Limit, 3=Stop, 4=StopLimit
    order_qty: int = Field(..., gt=0, description="Order quantity")
    price: Optional[float] = Field(None, gt=0, description="Limit price")
    time_in_force: Literal["0", "1", "3", "4"] = "0"  # 0=Day, 1=GTC, 3=IOC, 4=FOK

    @field_validator('price')
    @classmethod
    def validate_price(cls, v, info):
        """Validate that price is provided for LIMIT orders"""
        ord_type = info.data.get('ord_type')
        if ord_type in ["2", "4"] and v is None:  # LIMIT or STOP_LIMIT
            raise ValueError('price required for LIMIT and STOP_LIMIT orders')
        return v

    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v):
        """Normalize symbol"""
        return v.upper().strip()

    @classmethod
    def from_fix_message(cls, msg: simplefix.FixMessage) -> 'FIXNewOrderSingle':
        """Parse from FIX message"""
        return cls(
            header=FIXHeader(
                begin_string=msg.get(TAG_BEGIN_STRING).decode('utf-8') if msg.get(TAG_BEGIN_STRING) else "FIX.4.2",
                sender_comp_id=msg.get(TAG_SENDER_COMP_ID).decode('utf-8'),
                target_comp_id=msg.get(TAG_TARGET_COMP_ID).decode('utf-8'),
                msg_seq_num=int(msg.get(TAG_MSG_SEQ_NUM).decode('utf-8')),
                sending_time=datetime.strptime(
                    msg.get(TAG_SENDING_TIME).decode('utf-8'), '%Y%m%d-%H:%M:%S'
                ) if msg.get(TAG_SENDING_TIME) else datetime.now()
            ),
            cl_ord_id=msg.get(TAG_CLORDID).decode('utf-8'),
            handl_inst=msg.get(TAG_HANDLINST).decode('utf-8') if msg.get(TAG_HANDLINST) else "1",
            symbol=msg.get(TAG_SYMBOL).decode('utf-8'),
            side=msg.get(TAG_SIDE).decode('utf-8'),
            transact_time=datetime.strptime(
                msg.get(TAG_TRANSACT_TIME).decode('utf-8'), '%Y%m%d-%H:%M:%S'
            ) if msg.get(TAG_TRANSACT_TIME) else datetime.now(),
            ord_type=msg.get(TAG_ORDTYPE).decode('utf-8'),
            order_qty=int(msg.get(TAG_ORDERQTY).decode('utf-8')),
            price=float(msg.get(TAG_PRICE).decode('utf-8')) if msg.get(TAG_PRICE) else None,
            time_in_force=msg.get(TAG_TIMEINFORCE).decode('utf-8') if msg.get(TAG_TIMEINFORCE) else "0"
        )

    def to_fix_message(self) -> bytes:
        """Convert to FIX message format"""
        msg = simplefix.FixMessage()
        msg.append_pair(TAG_BEGIN_STRING, self.header.begin_string.encode())
        msg.append_pair(TAG_MSG_TYPE, b'D')
        msg.append_pair(TAG_SENDER_COMP_ID, self.header.sender_comp_id.encode())
        msg.append_pair(TAG_TARGET_COMP_ID, self.header.target_comp_id.encode())
        msg.append_pair(TAG_MSG_SEQ_NUM, str(self.header.msg_seq_num))
        msg.append_pair(TAG_SENDING_TIME, self.header.sending_time.strftime('%Y%m%d-%H:%M:%S'))
        msg.append_pair(TAG_CLORDID, self.cl_ord_id.encode())
        msg.append_pair(TAG_HANDLINST, self.handl_inst)
        msg.append_pair(TAG_SYMBOL, self.symbol.encode())
        msg.append_pair(TAG_SIDE, self.side)
        msg.append_pair(TAG_TRANSACT_TIME, self.transact_time.strftime('%Y%m%d-%H:%M:%S'))
        msg.append_pair(TAG_ORDTYPE, self.ord_type)
        if self.price:
            msg.append_pair(TAG_PRICE, str(self.price))
        msg.append_pair(TAG_ORDERQTY, str(self.order_qty))
        msg.append_pair(TAG_TIMEINFORCE, self.time_in_force)
        return msg.encode()


class FIXExecutionReport(BaseModel):
    """FIX ExecutionReport message (MsgType=8)"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    header: FIXHeader
    cl_ord_id: str = Field(..., description="Client Order ID")
    exec_id: str = Field(..., description="Execution ID")
    exec_type: Literal["0", "1", "2", "4", "5", "8"]  # New, PartialFill, Fill, Canceled, Replaced, Rejected
    ord_status: Literal["0", "1", "2", "4", "8"]  # New, PartiallyFilled, Filled, Canceled, Rejected
    symbol: str = Field(..., description="Stock symbol")
    side: Literal["1", "2"]  # Buy, Sell
    order_qty: int = Field(..., gt=0)
    cum_qty: int = Field(..., ge=0, description="Cumulative filled quantity")
    leaves_qty: int = Field(..., ge=0, description="Remaining quantity")
    avg_px: float = Field(..., ge=0, description="Average execution price")
    ord_type: Optional[Literal["1", "2", "3", "4"]] = None
    last_qty: Optional[int] = Field(None, gt=0, description="Last fill quantity")
    last_px: Optional[float] = Field(None, gt=0, description="Last fill price")
    orig_cl_ord_id: Optional[str] = None  # For cancel/replace

    @field_validator('cum_qty')
    @classmethod
    def validate_cum_qty(cls, v, info):
        """Validate cumulative quantity"""
        order_qty = info.data.get('order_qty')
        if order_qty and v > order_qty:
            raise ValueError('cum_qty cannot exceed order_qty')
        return v

    @field_validator('leaves_qty')
    @classmethod
    def validate_leaves_qty(cls, v, info):
        """Validate remaining quantity"""
        order_qty = info.data.get('order_qty')
        cum_qty = info.data.get('cum_qty', 0)
        if order_qty and v != (order_qty - cum_qty):
            raise ValueError('leaves_qty must equal order_qty - cum_qty')
        return v

    @classmethod
    def from_fix_message(cls, msg: simplefix.FixMessage) -> 'FIXExecutionReport':
        """Parse from FIX message"""
        return cls(
            header=FIXHeader(
                begin_string=msg.get(TAG_BEGIN_STRING).decode('utf-8') if msg.get(TAG_BEGIN_STRING) else "FIX.4.2",
                sender_comp_id=msg.get(TAG_SENDER_COMP_ID).decode('utf-8'),
                target_comp_id=msg.get(TAG_TARGET_COMP_ID).decode('utf-8'),
                msg_seq_num=int(msg.get(TAG_MSG_SEQ_NUM).decode('utf-8')),
                sending_time=datetime.strptime(
                    msg.get(TAG_SENDING_TIME).decode('utf-8'), '%Y%m%d-%H:%M:%S'
                ) if msg.get(TAG_SENDING_TIME) else datetime.now()
            ),
            cl_ord_id=msg.get(TAG_CLORDID).decode('utf-8'),
            exec_id=msg.get(TAG_EXECID).decode('utf-8'),
            exec_type=msg.get(TAG_EXECTYPE).decode('utf-8'),
            ord_status=msg.get(TAG_ORDSTATUS).decode('utf-8'),
            symbol=msg.get(TAG_SYMBOL).decode('utf-8'),
            side=msg.get(TAG_SIDE).decode('utf-8'),
            order_qty=int(msg.get(TAG_ORDERQTY).decode('utf-8')),
            cum_qty=int(msg.get(TAG_CUMQTY).decode('utf-8')),
            leaves_qty=int(msg.get(TAG_LEAVESQTY).decode('utf-8')),
            avg_px=float(msg.get(TAG_AVGPX).decode('utf-8')),
            ord_type=msg.get(TAG_ORDTYPE).decode('utf-8') if msg.get(TAG_ORDTYPE) else None,
            last_qty=int(msg.get(TAG_LASTQTY).decode('utf-8')) if msg.get(TAG_LASTQTY) else None,
            last_px=float(msg.get(TAG_LASTPX).decode('utf-8')) if msg.get(TAG_LASTPX) else None,
            orig_cl_ord_id=msg.get(TAG_ORIG_CLORDID).decode('utf-8') if msg.get(TAG_ORIG_CLORDID) else None
        )

    def to_fix_message(self) -> bytes:
        """Convert to FIX message format"""
        msg = simplefix.FixMessage()
        msg.append_pair(TAG_BEGIN_STRING, self.header.begin_string.encode())
        msg.append_pair(TAG_MSG_TYPE, b'8')
        msg.append_pair(TAG_SENDER_COMP_ID, self.header.sender_comp_id.encode())
        msg.append_pair(TAG_TARGET_COMP_ID, self.header.target_comp_id.encode())
        msg.append_pair(TAG_MSG_SEQ_NUM, str(self.header.msg_seq_num))
        msg.append_pair(TAG_CLORDID, self.cl_ord_id.encode())
        msg.append_pair(TAG_EXECID, self.exec_id.encode())
        msg.append_pair(TAG_EXECTYPE, self.exec_type)
        msg.append_pair(TAG_ORDSTATUS, self.ord_status)
        msg.append_pair(TAG_SYMBOL, self.symbol.encode())
        msg.append_pair(TAG_SIDE, self.side)
        msg.append_pair(TAG_ORDERQTY, str(self.order_qty))
        if self.ord_type:
            msg.append_pair(TAG_ORDTYPE, self.ord_type)
        if self.last_qty:
            msg.append_pair(TAG_LASTQTY, str(self.last_qty))
        if self.last_px:
            msg.append_pair(TAG_LASTPX, str(self.last_px))
        msg.append_pair(TAG_CUMQTY, str(self.cum_qty))
        msg.append_pair(TAG_AVGPX, str(self.avg_px))
        msg.append_pair(TAG_LEAVESQTY, str(self.leaves_qty))
        if self.orig_cl_ord_id:
            msg.append_pair(TAG_ORIG_CLORDID, self.orig_cl_ord_id.encode())
        msg.append_pair(TAG_SENDING_TIME, self.header.sending_time.strftime('%Y%m%d-%H:%M:%S'))
        return msg.encode()


class FIXOrderCancelRequest(BaseModel):
    """FIX OrderCancelRequest message (MsgType=F)"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    header: FIXHeader
    orig_cl_ord_id: str = Field(..., min_length=1, description="Original Client Order ID to cancel")
    cl_ord_id: str = Field(..., min_length=1, description="New Client Order ID for this cancel request")
    symbol: str = Field(..., description="Stock symbol")
    side: Literal["1", "2"]  # Buy, Sell
    transact_time: datetime = Field(default_factory=datetime.now)

    @classmethod
    def from_fix_message(cls, msg: simplefix.FixMessage) -> 'FIXOrderCancelRequest':
        """Parse from FIX message"""
        return cls(
            header=FIXHeader(
                begin_string=msg.get(TAG_BEGIN_STRING).decode('utf-8') if msg.get(TAG_BEGIN_STRING) else "FIX.4.2",
                sender_comp_id=msg.get(TAG_SENDER_COMP_ID).decode('utf-8'),
                target_comp_id=msg.get(TAG_TARGET_COMP_ID).decode('utf-8'),
                msg_seq_num=int(msg.get(TAG_MSG_SEQ_NUM).decode('utf-8')),
                sending_time=datetime.strptime(
                    msg.get(TAG_SENDING_TIME).decode('utf-8'), '%Y%m%d-%H:%M:%S'
                ) if msg.get(TAG_SENDING_TIME) else datetime.now()
            ),
            orig_cl_ord_id=msg.get(TAG_ORIG_CLORDID).decode('utf-8'),
            cl_ord_id=msg.get(TAG_CLORDID).decode('utf-8'),
            symbol=msg.get(TAG_SYMBOL).decode('utf-8'),
            side=msg.get(TAG_SIDE).decode('utf-8'),
            transact_time=datetime.strptime(
                msg.get(TAG_TRANSACT_TIME).decode('utf-8'), '%Y%m%d-%H:%M:%S'
            ) if msg.get(TAG_TRANSACT_TIME) else datetime.now()
        )

    def to_fix_message(self) -> bytes:
        """Convert to FIX message format"""
        msg = simplefix.FixMessage()
        msg.append_pair(TAG_BEGIN_STRING, self.header.begin_string.encode())
        msg.append_pair(TAG_MSG_TYPE, b'F')
        msg.append_pair(TAG_SENDER_COMP_ID, self.header.sender_comp_id.encode())
        msg.append_pair(TAG_TARGET_COMP_ID, self.header.target_comp_id.encode())
        msg.append_pair(TAG_MSG_SEQ_NUM, str(self.header.msg_seq_num))
        msg.append_pair(TAG_SENDING_TIME, self.header.sending_time.strftime('%Y%m%d-%H:%M:%S'))
        msg.append_pair(TAG_ORIG_CLORDID, self.orig_cl_ord_id.encode())
        msg.append_pair(TAG_CLORDID, self.cl_ord_id.encode())
        msg.append_pair(TAG_SYMBOL, self.symbol.encode())
        msg.append_pair(TAG_SIDE, self.side)
        msg.append_pair(TAG_TRANSACT_TIME, self.transact_time.strftime('%Y%m%d-%H:%M:%S'))
        return msg.encode()


class FIXOrderCancelReplaceRequest(BaseModel):
    """FIX OrderCancelReplaceRequest message (MsgType=G) - Amend order"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    header: FIXHeader
    orig_cl_ord_id: str = Field(..., min_length=1, description="Original Client Order ID to amend")
    cl_ord_id: str = Field(..., min_length=1, description="New Client Order ID for amended order")
    handl_inst: Literal["1", "2", "3"] = "1"
    symbol: str = Field(..., description="Stock symbol")
    side: Literal["1", "2"]  # Buy, Sell
    transact_time: datetime = Field(default_factory=datetime.now)
    ord_type: Literal["1", "2", "3", "4"]  # Market, Limit, Stop, StopLimit
    order_qty: int = Field(..., gt=0, description="New order quantity")
    price: Optional[float] = Field(None, gt=0, description="New limit price")

    @classmethod
    def from_fix_message(cls, msg: simplefix.FixMessage) -> 'FIXOrderCancelReplaceRequest':
        """Parse from FIX message"""
        return cls(
            header=FIXHeader(
                begin_string=msg.get(TAG_BEGIN_STRING).decode('utf-8') if msg.get(TAG_BEGIN_STRING) else "FIX.4.2",
                sender_comp_id=msg.get(TAG_SENDER_COMP_ID).decode('utf-8'),
                target_comp_id=msg.get(TAG_TARGET_COMP_ID).decode('utf-8'),
                msg_seq_num=int(msg.get(TAG_MSG_SEQ_NUM).decode('utf-8')),
                sending_time=datetime.strptime(
                    msg.get(TAG_SENDING_TIME).decode('utf-8'), '%Y%m%d-%H:%M:%S'
                ) if msg.get(TAG_SENDING_TIME) else datetime.now()
            ),
            orig_cl_ord_id=msg.get(TAG_ORIG_CLORDID).decode('utf-8'),
            cl_ord_id=msg.get(TAG_CLORDID).decode('utf-8'),
            handl_inst=msg.get(TAG_HANDLINST).decode('utf-8') if msg.get(TAG_HANDLINST) else "1",
            symbol=msg.get(TAG_SYMBOL).decode('utf-8'),
            side=msg.get(TAG_SIDE).decode('utf-8'),
            transact_time=datetime.strptime(
                msg.get(TAG_TRANSACT_TIME).decode('utf-8'), '%Y%m%d-%H:%M:%S'
            ) if msg.get(TAG_TRANSACT_TIME) else datetime.now(),
            ord_type=msg.get(TAG_ORDTYPE).decode('utf-8'),
            order_qty=int(msg.get(TAG_ORDERQTY).decode('utf-8')),
            price=float(msg.get(TAG_PRICE).decode('utf-8')) if msg.get(TAG_PRICE) else None
        )

    def to_fix_message(self) -> bytes:
        """Convert to FIX message format"""
        msg = simplefix.FixMessage()
        msg.append_pair(TAG_BEGIN_STRING, self.header.begin_string.encode())
        msg.append_pair(TAG_MSG_TYPE, b'G')
        msg.append_pair(TAG_SENDER_COMP_ID, self.header.sender_comp_id.encode())
        msg.append_pair(TAG_TARGET_COMP_ID, self.header.target_comp_id.encode())
        msg.append_pair(TAG_MSG_SEQ_NUM, str(self.header.msg_seq_num))
        msg.append_pair(TAG_SENDING_TIME, self.header.sending_time.strftime('%Y%m%d-%H:%M:%S'))
        msg.append_pair(TAG_ORIG_CLORDID, self.orig_cl_ord_id.encode())
        msg.append_pair(TAG_CLORDID, self.cl_ord_id.encode())
        msg.append_pair(TAG_HANDLINST, self.handl_inst)
        msg.append_pair(TAG_SYMBOL, self.symbol.encode())
        msg.append_pair(TAG_SIDE, self.side)
        msg.append_pair(TAG_TRANSACT_TIME, self.transact_time.strftime('%Y%m%d-%H:%M:%S'))
        msg.append_pair(TAG_ORDTYPE, self.ord_type)
        if self.price:
            msg.append_pair(TAG_PRICE, str(self.price))
        msg.append_pair(TAG_ORDERQTY, str(self.order_qty))
        return msg.encode()


class FIXOrderCancelReject(BaseModel):
    """FIX OrderCancelReject message (MsgType=9)"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    header: FIXHeader
    cl_ord_id: str = Field(..., description="ClOrdID of the cancel/replace request")
    orig_cl_ord_id: str = Field(..., description="Original ClOrdID")
    ord_status: Literal["0", "1", "2", "4", "8"]  # Current order status
    cxl_rej_reason: Literal["0", "1", "2", "3", "4", "5", "6"]
    # 0=TooLate, 1=UnknownOrder, 2=BrokerOption, 3=AlreadyPending, 4=UnableToProcess, 5=OrigOrdModTime, 6=DuplicateClOrdID
    text: Optional[str] = None  # Human-readable reason

    @classmethod
    def from_fix_message(cls, msg: simplefix.FixMessage) -> 'FIXOrderCancelReject':
        """Parse from FIX message"""
        return cls(
            header=FIXHeader(
                begin_string=msg.get(TAG_BEGIN_STRING).decode('utf-8') if msg.get(TAG_BEGIN_STRING) else "FIX.4.2",
                sender_comp_id=msg.get(TAG_SENDER_COMP_ID).decode('utf-8'),
                target_comp_id=msg.get(TAG_TARGET_COMP_ID).decode('utf-8'),
                msg_seq_num=int(msg.get(TAG_MSG_SEQ_NUM).decode('utf-8')),
                sending_time=datetime.strptime(
                    msg.get(TAG_SENDING_TIME).decode('utf-8'), '%Y%m%d-%H:%M:%S'
                ) if msg.get(TAG_SENDING_TIME) else datetime.now()
            ),
            cl_ord_id=msg.get(TAG_CLORDID).decode('utf-8'),
            orig_cl_ord_id=msg.get(TAG_ORIG_CLORDID).decode('utf-8'),
            ord_status=msg.get(TAG_ORDSTATUS).decode('utf-8'),
            cxl_rej_reason=msg.get(TAG_CXL_REJ_REASON).decode('utf-8'),
            text=msg.get(TAG_TEXT).decode('utf-8') if msg.get(TAG_TEXT) else None
        )

    def to_fix_message(self) -> bytes:
        """Convert to FIX message format"""
        msg = simplefix.FixMessage()
        msg.append_pair(TAG_BEGIN_STRING, self.header.begin_string.encode())
        msg.append_pair(TAG_MSG_TYPE, b'9')
        msg.append_pair(TAG_SENDER_COMP_ID, self.header.sender_comp_id.encode())
        msg.append_pair(TAG_TARGET_COMP_ID, self.header.target_comp_id.encode())
        msg.append_pair(TAG_MSG_SEQ_NUM, str(self.header.msg_seq_num))
        msg.append_pair(TAG_SENDING_TIME, self.header.sending_time.strftime('%Y%m%d-%H:%M:%S'))
        msg.append_pair(TAG_CLORDID, self.cl_ord_id.encode())
        msg.append_pair(TAG_ORIG_CLORDID, self.orig_cl_ord_id.encode())
        msg.append_pair(TAG_ORDSTATUS, self.ord_status)
        msg.append_pair(TAG_CXL_REJ_REASON, self.cxl_rej_reason)
        if self.text:
            msg.append_pair(TAG_TEXT, self.text.encode())
        return msg.encode()
