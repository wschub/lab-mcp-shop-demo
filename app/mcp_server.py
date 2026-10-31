from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from app import crud, schemas
from app.database import SessionLocal

# Protección DNS-rebinding desactivada: con ngrok el header Host no es localhost.
# Cuando añadamos auth por token, esto queda cubierto.
mcp = FastMCP(
    "Shop Demo",
    stateless_http=True,
    json_response=True,
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)

DEFAULT_USER_ID = 1  # usuario demo del seed; desaparece cuando haya auth


def _product(p) -> dict:
    return schemas.ProductOut.model_validate(p).model_dump()


def _cart(cart) -> dict:
    return schemas.CartOut.model_validate(cart).model_dump()


def _order(o) -> dict:
    return schemas.OrderOut.model_validate(o).model_dump()


# ---------- products ----------
@mcp.tool()
def get_total_stock() -> int:
    """Total units in stock across all products."""
    with SessionLocal() as db:
        return crud.total_stock(db)


@mcp.tool()
def list_products(category: str | None = None) -> list[dict]:
    """List products, optionally filtered by category."""
    with SessionLocal() as db:
        return [_product(p) for p in crud.list_products(db, category)]


@mcp.tool()
def search_products(query: str) -> list[dict]:
    """Search products by name or description."""
    with SessionLocal() as db:
        return [_product(p) for p in crud.search_products(db, query)]


@mcp.tool()
def get_product(product_id: int) -> dict:
    """Get one product (price, stock, category) by its id."""
    with SessionLocal() as db:
        return _product(crud.get_product(db, product_id))


@mcp.tool()
def create_product(
    name: str, price: float, stock: int = 0, description: str = "", category: str = "general"
) -> dict:
    """Create a new product."""
    with SessionLocal() as db:
        data = schemas.ProductCreate(
            name=name, price=price, stock=stock, description=description, category=category
        )
        return _product(crud.create_product(db, data))


@mcp.tool()
def update_product(
    product_id: int,
    name: str | None = None,
    description: str | None = None,
    price: float | None = None,
    stock: int | None = None,
    category: str | None = None,
) -> dict:
    """Update only the provided fields of a product."""
    fields = {
        k: v
        for k, v in dict(
            name=name, description=description, price=price, stock=stock, category=category
        ).items()
        if v is not None
    }
    with SessionLocal() as db:
        return _product(crud.update_product(db, product_id, schemas.ProductUpdate(**fields)))


@mcp.tool()
def import_products_from_csv(csv_text: str) -> dict:
    """Bulk-create products from CSV text. Required columns: name, price, stock.
    Optional columns: description, category. Pass the raw CSV content as csv_text."""
    with SessionLocal() as db:
        return {"imported": crud.import_products_csv(db, csv_text)}


# ---------- cart & orders ----------
@mcp.tool()
def view_cart(user_id: int = DEFAULT_USER_ID) -> dict:
    """Show the cart items and total of a user."""
    with SessionLocal() as db:
        return _cart(crud.get_cart(db, user_id))


@mcp.tool()
def add_to_cart(product_id: int, quantity: int = 1, user_id: int = DEFAULT_USER_ID) -> dict:
    """Add a product to the user's cart (stock is NOT reduced until checkout)."""
    with SessionLocal() as db:
        return _cart(crud.add_to_cart(db, user_id, product_id, quantity))


@mcp.tool()
def remove_from_cart(product_id: int, user_id: int = DEFAULT_USER_ID) -> dict:
    """Remove a product from the user's cart."""
    with SessionLocal() as db:
        return _cart(crud.remove_from_cart(db, user_id, product_id))


@mcp.tool()
def checkout(user_id: int = DEFAULT_USER_ID) -> dict:
    """Complete the purchase: creates the order and reduces stock."""
    with SessionLocal() as db:
        return _order(crud.checkout(db, user_id))


@mcp.tool()
def list_orders(user_id: int = DEFAULT_USER_ID) -> list[dict]:
    """Purchase history of a user, newest first."""
    with SessionLocal() as db:
        return [_order(o) for o in crud.list_orders(db, user_id)]


# ---------- KPI ----------
@mcp.tool()
def get_top_product() -> dict:
    """KPI: the best-selling product by units sold."""
    with SessionLocal() as db:
        top = crud.top_product(db)
        if not top:
            return {"message": "No purchases yet"}
        return {"product": _product(top["product"]), "units_sold": top["units_sold"]}


# App ASGI del MCP (endpoint: /mcp). Debe crearse después de definir las tools.
mcp_app = mcp.streamable_http_app()