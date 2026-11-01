import os

from dotenv import load_dotenv

load_dotenv()
_base = os.environ["DATABASE_URL"].rsplit("/", 1)[0]
os.environ["DATABASE_URL"] = f"{_base}/mcp_demo_test"
# Seguro anti-desastre: los tests hacen drop_all, solo contra la base de pruebas.
assert os.environ["DATABASE_URL"].endswith("_test")

import pytest  # noqa: E402

from app import crud, schemas  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def user(db):
    return crud.create_user(
        db, schemas.UserCreate(name="Test", email="t@example.com", password="x")
    )


@pytest.fixture
def product(db):
    return crud.create_product(db, schemas.ProductCreate(name="Keyboard", price=10, stock=5))