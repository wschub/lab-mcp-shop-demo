import pytest

from app import crud, schemas


def test_cart_does_not_touch_stock(db, user, product):
    crud.add_to_cart(db, user.id, product.id, 2)
    assert crud.total_stock(db) == 5


def test_checkout_reduces_stock_and_empties_cart(db, user, product):
    crud.add_to_cart(db, user.id, product.id, 2)
    order = crud.checkout(db, user.id)
    assert float(order.total) == 20.0
    assert crud.total_stock(db) == 3
    assert crud.get_cart(db, user.id)["items"] == []
    assert len(crud.list_orders(db, user.id)) == 1


def test_cannot_add_more_than_stock(db, user, product):
    with pytest.raises(ValueError):
        crud.add_to_cart(db, user.id, product.id, 6)


def test_checkout_empty_cart_fails(db, user):
    with pytest.raises(ValueError):
        crud.checkout(db, user.id)


def test_top_product_kpi(db, user, product):
    other = crud.create_product(db, schemas.ProductCreate(name="Mouse", price=5, stock=10))
    crud.add_to_cart(db, user.id, product.id, 1)
    crud.add_to_cart(db, user.id, other.id, 4)
    crud.checkout(db, user.id)
    top = crud.top_product(db)
    assert top["product"].id == other.id
    assert top["units_sold"] == 4


def test_token_identifies_user(db, user):
    token = crud.issue_token(db, user.id)
    assert crud.get_user_by_token(db, token).id == user.id
    assert crud.get_user_by_token(db, "wrong") is None


def test_carts_are_per_user(db, user, product):
    other = crud.create_user(
        db, schemas.UserCreate(name="B", email="b@example.com", password="x")
    )
    crud.add_to_cart(db, user.id, product.id, 1)
    assert crud.get_cart(db, other.id)["items"] == []