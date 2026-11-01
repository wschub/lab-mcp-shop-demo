import os
import re

from dotenv import load_dotenv

load_dotenv()

_raw_url = os.getenv("DATABASE_URL", "")
# Railway entrega postgres:// o postgresql://; lo llevamos al driver psycopg2.
DATABASE_URL = re.sub(r"^postgres(ql)?(\+\w+)?://", "postgresql+psycopg2://", _raw_url)