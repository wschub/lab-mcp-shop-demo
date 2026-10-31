from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr


class ProductCreate(BaseModel):
    name: str
    description: str = ""
    price: Decimal
    stock: int = 0
    category: str = "general"


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: Decimal | None = None
    stock: int | None = None
    category: str | None = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    price: float
    stock: int
    category: str


class UserCreate(BaseModel):
    name: str
    email: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str


class CartAdd(BaseModel):
    product_id: int
    quantity: int = 1


class CartItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product: ProductOut
    quantity: int


class CartOut(BaseModel):
    items: list[CartItemOut]
    total: float


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    quantity: int
    unit_price: float


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    total: float
    items: list[OrderItemOut]


class TopProductOut(BaseModel):
    product: ProductOut
    units_sold: int