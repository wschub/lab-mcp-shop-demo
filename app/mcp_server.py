from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from app import crud, schemas
from app.database import SessionLocal
##auth token
from app.auth import current_user_id

# Protección DNS-rebinding desactivada: con ngrok el header Host no es localhost.
# Cuando añadamos auth por token, esto queda cubierto.
mcp = FastMCP(
    "Shop Demo",
    stateless_http=True,
    json_response=True,
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)

#DEFAULT_USER_ID = 1  # usuario demo del seed; desaparece cuando haya auth
def _uid() -> int:
    uid = current_user_id.get()
    if uid is None:
        raise PermissionError("Not authenticated")
    return uid

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


# ---------- cart & orders (siempre del usuario autenticado) ----------
@mcp.tool()
def whoami() -> dict:
    """Return the authenticated user."""
    with SessionLocal() as db:
        return schemas.UserOut.model_validate(crud.get_user(db, _uid())).model_dump()


@mcp.tool()
def view_cart() -> dict:
    """Show the cart items and total of the authenticated user."""
    with SessionLocal() as db:
        return _cart(crud.get_cart(db, _uid()))


@mcp.tool()
def add_to_cart(product_id: int, quantity: int = 1) -> dict:
    """Add a product to my cart (stock is NOT reduced until checkout)."""
    with SessionLocal() as db:
        return _cart(crud.add_to_cart(db, _uid(), product_id, quantity))


@mcp.tool()
def remove_from_cart(product_id: int) -> dict:
    """Remove a product from my cart."""
    with SessionLocal() as db:
        return _cart(crud.remove_from_cart(db, _uid(), product_id))


@mcp.tool()
def checkout() -> dict:
    """Complete my purchase: creates the order and reduces stock."""
    with SessionLocal() as db:
        return _order(crud.checkout(db, _uid()))


@mcp.tool()
def list_orders() -> list[dict]:
    """My purchase history, newest first."""
    with SessionLocal() as db:
        return [_order(o) for o in crud.list_orders(db, _uid())]
    
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