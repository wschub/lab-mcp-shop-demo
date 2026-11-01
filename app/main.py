from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app import crud, models, schemas

from app.database import Base, engine, get_db
#MCP 
from fastapi.responses import JSONResponse
from app.mcp_server import mcp, mcp_app 
from app.auth import MCPAuthMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    async with mcp.session_manager.run():
        yield


app = FastAPI(title="MCP Shop Demo", lifespan=lifespan)
app.add_middleware(MCPAuthMiddleware)


def verify_token(authorization: str = Header(default=""), db: Session = Depends(get_db)):
    """Devuelve el usuario dueño del token Bearer, o responde 401."""
    token = authorization[len("Bearer "):].strip() if authorization.startswith("Bearer ") else ""
    user = crud.get_user_by_token(db, token) if token else None
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return user

@app.exception_handler(LookupError)
async def not_found_handler(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ValueError)
async def bad_request_handler(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------- products ----------
@app.get("/products", response_model=list[schemas.ProductOut], dependencies=[Depends(verify_token)])
def list_products(category: str | None = None, db: Session = Depends(get_db)):
    return crud.list_products(db, category)


@app.get("/products/search", response_model=list[schemas.ProductOut], dependencies=[Depends(verify_token)])
def search_products(q: str, db: Session = Depends(get_db)):
    return crud.search_products(db, q)


@app.get("/products/{product_id}", response_model=schemas.ProductOut, dependencies=[Depends(verify_token)])
def get_product(product_id: int, db: Session = Depends(get_db)):
    return crud.get_product(db, product_id)


@app.post("/products", response_model=schemas.ProductOut, status_code=201, dependencies=[Depends(verify_token)])
def create_product(data: schemas.ProductCreate, db: Session = Depends(get_db)):
    return crud.create_product(db, data)


@app.patch("/products/{product_id}", response_model=schemas.ProductOut, dependencies=[Depends(verify_token)])
def update_product(product_id: int, data: schemas.ProductUpdate, db: Session = Depends(get_db)):
    return crud.update_product(db, product_id, data)


@app.delete("/products/{product_id}", status_code=204, dependencies=[Depends(verify_token)])
def delete_product(product_id: int, db: Session = Depends(get_db)):
    crud.delete_product(db, product_id)


@app.post("/products/import-csv", dependencies=[Depends(verify_token)])
async def import_csv(file: UploadFile, db: Session = Depends(get_db)):
    text = (await file.read()).decode("utf-8-sig")
    return {"imported": crud.import_products_csv(db, text)}


@app.get("/stock/total", dependencies=[Depends(verify_token)])
def stock_total(db: Session = Depends(get_db)):
    return {"total_stock": crud.total_stock(db)}


# ---------- users ----------
@app.get("/users", response_model=list[schemas.UserOut], dependencies=[Depends(verify_token)])
def list_users(db: Session = Depends(get_db)):
    return crud.list_users(db)


@app.post("/users", response_model=schemas.UserOut, status_code=201, dependencies=[Depends(verify_token)])
def create_user(data: schemas.UserCreate, db: Session = Depends(get_db)):
    return crud.create_user(db, data)


# ---------- cart & orders (usuario autenticado) ----------
@app.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(verify_token)):
    return user


@app.get("/me/cart", response_model=schemas.CartOut)
def get_cart(user: models.User = Depends(verify_token), db: Session = Depends(get_db)):
    return crud.get_cart(db, user.id)


@app.post("/me/cart", response_model=schemas.CartOut)
def add_to_cart(data: schemas.CartAdd, user: models.User = Depends(verify_token), db: Session = Depends(get_db)):
    return crud.add_to_cart(db, user.id, data.product_id, data.quantity)


@app.delete("/me/cart/{product_id}", response_model=schemas.CartOut)
def remove_from_cart(product_id: int, user: models.User = Depends(verify_token), db: Session = Depends(get_db)):
    return crud.remove_from_cart(db, user.id, product_id)


@app.post("/me/checkout", response_model=schemas.OrderOut)
def checkout(user: models.User = Depends(verify_token), db: Session = Depends(get_db)):
    return crud.checkout(db, user.id)


@app.get("/me/orders", response_model=list[schemas.OrderOut])
def list_orders(user: models.User = Depends(verify_token), db: Session = Depends(get_db)):
    return crud.list_orders(db, user.id)

# ---------- KPI ----------
@app.get("/kpi/top-product", response_model=schemas.TopProductOut | None, dependencies=[Depends(verify_token)])
def top_product(db: Session = Depends(get_db)):
    return crud.top_product(db)

app.mount("/", mcp_app)