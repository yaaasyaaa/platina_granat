import uuid
import os
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from sqlalchemy.orm import selectinload
from datetime import date, datetime
from typing import List

from database import get_db, engine
from models import Base, Product, CartItem, DeliveryDate, Order, OrderItem
from schemas import (
    ProductCreate,
    Product as ProductSchema,
    CartItemCreate,
    CartItem as CartItemSchema,
    DeliveryDateBase,
    OrderCreate,
    Order as OrderSchema,
    OrderItemCreate,
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

IMG_DIR = Path("static/imgs")
IMG_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR = Path("static")
STATIC_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        delivery = (await session.execute(select(DeliveryDate))).scalar_one_or_none()
        if not delivery:
            session.add(DeliveryDate(id=1, delivery_date=date.today()))
            await session.commit()

        count = (await session.execute(select(Product))).scalars().first()
        if not count:
            products = [
                Product(
                    name="Платиновый гранат - Мини",
                    price=1500,
                    description="Концентрированная сыворотка для чувствительной кожи.",
                    image_path=""
                ),
                Product(
                    name="Платиновый гранат - Стандарт",
                    price=3200,
                    description="Универсальная сыворотка для ежедневного ухода.",
                    image_path=""
                ),
                Product(
                    name="Платиновый гранат - Максимум",
                    price=5800,
                    description="Роскошная сыворотка с экстрактом граната и платины.",
                    image_path=""
                ),
            ]
            session.add_all(products)
            await session.commit()


@app.get("/api/products/", response_model=List[ProductSchema])
async def read_products(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product))
    products = result.scalars().all()
    for p in products:
        if p.image_path and os.path.exists(p.image_path):
            filename = Path(p.image_path).name
            p.image_url = f"/static/imgs/{filename}"
        else:
            if p.id == 1:
                p.image_url = "/static/imgs/mini.png"
            elif p.id == 2:
                p.image_url = "/static/imgs/standart.png"
            elif p.id == 3:
                p.image_url = "/static/imgs/max.png"
            else:
                p.image_url = "/static/imgs/default.png"
    return products


@app.post("/api/products/", response_model=ProductSchema, status_code=201)
async def create_product(
        name: str = Form(...),
        price: int = Form(...),
        description: str = Form(...),
        image: UploadFile = File(...),
        db: AsyncSession = Depends(get_db)
):
    if not image.content_type.startswith("image/"):
        raise HTTPException(400, "Только изображения")

    ext = image.filename.split('.')[-1].lower()
    if ext not in {"jpg", "jpeg", "png", "webp"}:
        raise HTTPException(400, "Неподдерживаемый формат")

    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = IMG_DIR / filename

    with open(filepath, "wb") as f:
        content = await image.read()
        f.write(content)

    db_product = Product(
        name=name,
        price=price,
        description=description,
        image_path=str(filepath)
    )
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)

    db_product.image_url = f"/static/imgs/{filename}"
    return db_product


@app.get("/api/cart/", response_model=List[CartItemSchema])
async def get_cart(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CartItem).options(selectinload(CartItem.product)))
    return result.scalars().all()


@app.post("/api/cart/", response_model=CartItemSchema, status_code=status.HTTP_201_CREATED)
async def add_to_cart(item: CartItemCreate, db: AsyncSession = Depends(get_db)):
    product = await db.get(Product, item.product_id)
    if not product:
        raise HTTPException(404, "Product not found")

    db_item = CartItem(**item.model_dump())
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)
    return db_item


@app.delete("/api/cart/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_cart(item_id: int, db: AsyncSession = Depends(get_db)):
    item = await db.get(CartItem, item_id)
    if not item:
        raise HTTPException(404, "Cart item not found")
    await db.delete(item)
    await db.commit()


@app.get("/api/delivery/", response_model=DeliveryDateBase)
async def get_delivery_date(db: AsyncSession = Depends(get_db)):
    delivery = await db.get(DeliveryDate, 1)
    return DeliveryDateBase(delivery_date=delivery.delivery_date)


@app.get("/api/orders/", response_model=List[OrderSchema])
async def get_orders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc())
    )
    orders = result.scalars().all()
    return orders


@app.post("/api/orders/", response_model=OrderSchema, status_code=status.HTTP_201_CREATED)
async def create_order(order_data: OrderCreate, db: AsyncSession = Depends(get_db)):
    if isinstance(order_data.delivery_date, str):
        from datetime import datetime
        try:
            order_data.delivery_date = datetime.strptime(order_data.delivery_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD")

    db_order = Order(
        delivery_date=order_data.delivery_date,
        delivery_time=order_data.delivery_time,
        delivery_address=order_data.delivery_address,
        status=order_data.status,
        total_price=order_data.total_price
    )
    db.add(db_order)
    await db.flush()

    for item in order_data.items:
        db_order_item = OrderItem(
            order_id=db_order.id,
            product_id=item.product_id,
            product_name=item.product_name,
            quantity=item.quantity,
            price=item.price
        )
        db.add(db_order_item)

    await db.execute(delete(CartItem))

    await db.commit()

    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == db_order.id)
    )
    order_with_items = result.scalar_one()

    return order_with_items


@app.patch("/api/orders/{order_id}", response_model=OrderSchema)
async def update_order(
        order_id: int,
        update_data: dict,
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(404, "Order not found")

    allowed_fields = ["delivery_date", "delivery_time", "delivery_address", "status"]
    for field in allowed_fields:
        if field in update_data:
            if field == "delivery_date" and isinstance(update_data[field], str):
                try:
                    from datetime import datetime
                    date_obj = datetime.strptime(update_data[field], "%Y-%m-%d").date()
                    setattr(order, field, date_obj)
                except ValueError:
                    raise HTTPException(400, f"Invalid date format: {update_data[field]}. Use YYYY-MM-DD")
            else:
                setattr(order, field, update_data[field])

    await db.commit()
    await db.refresh(order)

    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == order_id)
    )
    updated_order = result.scalar_one()

    return updated_order


@app.delete("/api/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_order(order_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(404, "Order not found")

    order.status = "cancelled"
    await db.commit()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def get_html():
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))

    possible_paths = [
        os.path.join(current_dir, "index.html"),
        os.path.join(current_dir, "..", "frontend", "index.html"),
        os.path.join(current_dir, "..", "index.html"),
    ]

    for path in possible_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())

    return HTMLResponse(content="<h1>Файл index.html не найден</h1>")

@app.get("/static/imgs/{filename}")
async def get_image(filename: str):
    filepath = IMG_DIR / filename
    if filepath.exists():
        return FileResponse(filepath)
    else:
        placeholder = IMG_DIR / "default.png"
        if placeholder.exists():
            return FileResponse(placeholder)
        else:
            raise HTTPException(404, "Image not found")