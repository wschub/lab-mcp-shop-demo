from app import models
from app.crud import hash_password
from app.database import Base, SessionLocal, engine

PRODUCTS = [
    ("Mechanical Keyboard", "Hot-swappable 75% keyboard", "89.90", 25, "peripherals"),
    ("Wireless Mouse", "Ergonomic 2.4GHz mouse", "34.50", 40, "peripherals"),
    ("27-inch 4K Monitor", "IPS panel, USB-C input", "349.00", 15, "displays"),
    ("USB-C Cable 2m", "Fast charging braided cable", "9.99", 60, "accessories"),
    ("Laptop Stand", "Aluminum adjustable stand", "45.00", 30, "accessories"),
    ("Noise-Cancelling Headphones", "Bluetooth over-ear headphones", "199.00", 12, "audio"),
    ("Webcam 1080p", "Full HD webcam with microphone", "59.90", 50, "peripherals"),
    ("Portable SSD 1TB", "USB 3.2 external drive", "119.00", 20, "storage"),
]

USERS = [
    ("Demo User", "demo@example.com", "demo1234"),
    ("Ana Gomez", "ana@example.com", "ana12345"),
]


def run():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if db.query(models.Product).count() > 0:
            print("Seed skipped: data already exists")
            return
        for name, description, price, stock, category in PRODUCTS:
            db.add(models.Product(name=name, description=description, price=price,
                                  stock=stock, category=category))
        for name, email, password in USERS:
            db.add(models.User(name=name, email=email, password_hash=hash_password(password)))
        db.commit()
        print("Seed done: 8 products, 2 users")


if __name__ == "__main__":
    run()