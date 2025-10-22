"""
Database models for the Broker service
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import enum

Base = declarative_base()


class OrderSide(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(enum.Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class TimeInForce(enum.Enum):
    DAY = "DAY"
    GTC = "GTC"  # Good Till Cancel
    IOC = "IOC"  # Immediate or Cancel
    FOK = "FOK"  # Fill or Kill


class OrderStatus(enum.Enum):
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"


class Stock(Base):
    """Stock universe - ticker symbols and last prices"""
    __tablename__ = 'stocks'

    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), unique=True, nullable=False, index=True)
    last_price = Column(Float, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Order(Base):
    """Orders received from clients via FIX"""
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)

    # FIX fields
    cl_ord_id = Column(String(50), unique=True, nullable=False, index=True)  # Client Order ID
    sender_comp_id = Column(String(50), nullable=False)  # Client identifier

    # Order details
    symbol = Column(String(10), nullable=False, index=True)
    side = Column(Enum(OrderSide), nullable=False)
    order_type = Column(Enum(OrderType), nullable=False)
    quantity = Column(Integer, nullable=False)
    limit_price = Column(Float, nullable=True)  # NULL for market orders
    time_in_force = Column(Enum(TimeInForce), nullable=False)

    # Order status
    status = Column(Enum(OrderStatus), default=OrderStatus.NEW, nullable=False)
    filled_quantity = Column(Integer, default=0, nullable=False)
    remaining_quantity = Column(Integer, nullable=False)

    # Rejection reason
    reject_reason = Column(String(200), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    executions = relationship("Execution", back_populates="order", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Order {self.cl_ord_id} {self.symbol} {self.side.value} {self.quantity}@{self.limit_price}>"


class Execution(Base):
    """Execution records (full or partial fills)"""
    __tablename__ = 'executions'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)

    # Execution details
    exec_id = Column(String(50), unique=True, nullable=False)  # Unique execution ID
    exec_quantity = Column(Integer, nullable=False)
    exec_price = Column(Float, nullable=False)

    # Timestamps
    executed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    order = relationship("Order", back_populates="executions")

    def __repr__(self):
        return f"<Execution {self.exec_id} {self.exec_quantity}@{self.exec_price}>"


# Database setup
def init_db(db_path='broker.db'):
    """Initialize the database"""
    engine = create_engine(f'sqlite:///{db_path}', echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return engine, Session


def get_session(db_path='broker.db'):
    """Get a new database session"""
    engine = create_engine(f'sqlite:///{db_path}', echo=False)
    Session = sessionmaker(bind=engine)
    return Session()
