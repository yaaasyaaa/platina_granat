from pydantic import BaseModel
from datetime import date, datetime
from typing import List

class ProductBase(BaseModel):
    name: str
    price: int
    description: str

class ProductCreate(ProductBase):
    pass

class Product(ProductBase):
    id: int
    image_path: str
    image_url: str = ""

    class Config:
        from_attributes = True

class CartItemBase(BaseModel):
    product_id: int
    quantity: int = 1

class CartItemCreate(CartItemBase):
    pass

class CartItem(CartItemBase):
    id: int
    product: Product

    class Config:
        from_attributes = True

class DeliveryDateBase(BaseModel):
    delivery_date: date

class OrderItemBase(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    price: int

class OrderItemCreate(OrderItemBase):
    pass

class OrderItem(OrderItemBase):
    id: int
    order_id: int

    class Config:
        from_attributes = True

class OrderBase(BaseModel):
    delivery_date: date
    delivery_time: str
    delivery_address: str
    status: str = "pending"
    total_price: int

class OrderCreate(OrderBase):
    items: List[OrderItemCreate]

class Order(OrderBase):
    id: int
    created_at: datetime
    items: List[OrderItem]

    class Config:
        from_attributes = True
