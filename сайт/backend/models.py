from sqlalchemy import Column, Integer, String, Date, DateTime, func, ForeignKey, Text
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import declarative_base, relationship
from datetime import date

Base = declarative_base()

class Product(AsyncAttrs, Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    description = Column(String, nullable=False, default="")
    image_path = Column(String, nullable=False, default="")

class CartItem(AsyncAttrs, Base):
    __tablename__ = "cart_items"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1)
    product = relationship("Product")

class DeliveryDate(AsyncAttrs, Base):
    __tablename__ = "delivery_date"
    id = Column(Integer, primary_key=True, index=True)
    delivery_date = Column(Date, nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

# НОВЫЕ МОДЕЛИ
class Order(AsyncAttrs, Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    delivery_date = Column(Date, nullable=False)
    delivery_time = Column(String, nullable=False)
    delivery_address = Column(Text, nullable=False)
    status = Column(String, default="pending")  # pending, onWay, delivered, cancelled
    total_price = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=func.now())
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(AsyncAttrs, Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    product_name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Integer, nullable=False)
    order = relationship("Order", back_populates="items")
