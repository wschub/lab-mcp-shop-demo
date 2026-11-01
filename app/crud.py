import csv
import hashlib
import io
import os
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app import models, schemas
import secrets

# ---------- helpers ----------
def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return f"{salt.hex()}${digest.hex()}"


# ---------- products ----------
def list_products(db: Session, category: str | None = None):
    stmt = select(models.Product).order_by(models.Product.id)
    if category:
        stmt = stmt.where(models.Product.category.ilike(category))
    return db.scalars(stmt).all()


def search_products(db: Session, query: str):
    like = f"%{query}%"
    stmt = (
        select(models.Product)
        .where(or_(models.Product.name.ilike(like), models.Product.description.ilike(like)))
        .order_by(models.Product.id)
    )
    return db.scalars(stmt).all()


def get_product(db: Session, product_id: int):
    product = db.get(models.Product, product_id)
    if not product:
        raise LookupError(f"Product {product_id} not found")
    return product


def create_product(db: Session, data: schemas.ProductCreate):
    product = models.Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product(db: Session, product_id: int, data: schemas.ProductUpdate):
    product = get_product(db, product_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product_id: int):
    product = get_product(db, product_id)
    db.delete(product)
    db.commit()


def total_stock(db: Session) -> int:
    return db.scalar(select(func.coalesce(func.sum(models.Product.stock), 0)))


def import_products_csv(db: Session, csv_text: str) -> int:
    reader = csv.DictReader(io.StringIO(csv_text))
    required = {"name", "price", "stock"}
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        raise ValueError("CSV needs columns: name, price, stock (optional: description, category)")
    products = []
    for line, row in enumerate(reader, start=2):
        try:
            products.append(
                models.Product(
                    name=row["name"].strip(),
                    description=(row.get("description") or "").strip(),
                    price=Decimal(row["price"]),
                    stock=int(row["stock"]),
                    category=(row.get("category") or "general").strip(),
                )
            )
        except (InvalidOperation, ValueError, AttributeError):
            raise ValueError(f"Invalid data on CSV line {line}")
    db.add_all(products)
    db.commit()
    return len(products)


# ---------- users ----------
def list_users(db: Session):
    return db.scalars(select(models.User).order_by(models.User.id)).all()


def get_user(db: Session, user_id: int):
    user = db.get(models.User, user_id)
    if not user:
        raise LookupError(f"User {user_id} not found")
    return user


def create_user(db: Session, data: schemas.UserCreate):
    exists = db.scalar(select(models.User).where(models.User.email == data.email))
    if exists:
        raise ValueError("Email already registered")
    user = models.User(
        name=data.name, email=data.email, password_hash=hash_password(data.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

#Token management
def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_token(db: Session, user_id: int) -> str:
    """Genera un token nuevo para el usuario (reemplaza el anterior). Se guarda solo el hash."""
    user = get_user(db, user_id)
    token = secrets.token_urlsafe(32)
    user.token_hash = hash_token(token)
    db.commit()
    return token


def get_user_by_token(db: Session, token: str):
    return db.scalar(select(models.User).where(models.User.token_hash == hash_token(token)))


# ---------- cart ----------
def get_cart(db: Session, user_id: int):
    get_user(db, user_id)
    items = db.scalars(
        select(models.CartItem).where(models.CartItem.user_id == user_id).order_by(models.CartItem.id)
    ).all()
    total = sum((i.product.price * i.quantity for i in items), Decimal("0"))
    return {"items": items, "total": total}


def add_to_cart(db: Session, user_id: int, product_id: int, quantity: int = 1):
    if quantity < 1:
        raise ValueError("Quantity must be at least 1")
    get_user(db, user_id)
    product = get_product(db, product_id)
    item = db.scalar(
        select(models.CartItem).where(
            models.CartItem.user_id == user_id, models.CartItem.product_id == product_id
        )
    )
    new_quantity = (item.quantity if item else 0) + quantity
    if new_quantity > product.stock:
        raise ValueError(f"Only {product.stock} units of '{product.name}' in stock")
    if item:
        item.quantity = new_quantity
    else:
        db.add(models.CartItem(user_id=user_id, product_id=product_id, quantity=quantity))
    db.commit()
    return get_cart(db, user_id)


def remove_from_cart(db: Session, user_id: int, product_id: int):
    get_user(db, user_id)
    item = db.scalar(
        select(models.CartItem).where(
            models.CartItem.user_id == user_id, models.CartItem.product_id == product_id
        )
    )
    if item:
        db.delete(item)
        db.commit()
    return get_cart(db, user_id)


# ---------- orders ----------
def checkout(db: Session, user_id: int):
    cart = get_cart(db, user_id)
    if not cart["items"]:
        raise ValueError("Cart is empty")
    order = models.Order(user_id=user_id, total=cart["total"])
    db.add(order)
    for item in cart["items"]:
        product = item.product
        if item.quantity > product.stock:
            db.rollback()
            raise ValueError(f"Not enough stock for '{product.name}' (available: {product.stock})")
        product.stock -= item.quantity
        order.items.append(
            models.OrderItem(
                product_id=product.id, quantity=item.quantity, unit_price=product.price
            )
        )
        db.delete(item)
    db.commit()
    db.refresh(order)
    return order


def list_orders(db: Session, user_id: int):
    get_user(db, user_id)
    stmt = select(models.Order).where(models.Order.user_id == user_id).order_by(models.Order.id.desc())
    return db.scalars(stmt).all()


def top_product(db: Session):
    units = func.sum(models.OrderItem.quantity)
    row = db.execute(
        select(models.Product, units)
        .join(models.OrderItem, models.OrderItem.product_id == models.Product.id)
        .group_by(models.Product.id)
        .order_by(units.desc())
        .limit(1)
    ).first()
    if not row:
        return None
    return {"product": row[0], "units_sold": int(row[1])}