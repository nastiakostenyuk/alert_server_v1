from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

from settings import DATABASE

db_string = DATABASE

db = create_engine(db_string)
base = declarative_base()

Session = sessionmaker(db)
session = scoped_session(Session)

base.query = session.query_property()


def create_db():
    base.metadata.create_all(db)


def delete_tables():
    base.metadata.drop_all(db)
