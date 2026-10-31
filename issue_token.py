import sys

from app.crud import issue_token
from app.database import SessionLocal

user_id = int(sys.argv[1])
with SessionLocal() as db:
    print(issue_token(db, user_id))