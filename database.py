from credentials import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase

DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

db_engine = create_engine(DB_URL)


class Base(DeclarativeBase):
    pass
