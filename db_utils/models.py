from sqlalchemy import Column, String, Integer, func
from sqlalchemy.dialects.postgresql import TIMESTAMP

from db_utils.database import base, session


class FutureAlert(base):
    __tablename__ = 'alerts'

    alert_id = Column(Integer, primary_key=True)
    future = Column(String)
    date_time = Column(TIMESTAMP)

    def __str__(self):
        return f"{self.date_time}"

