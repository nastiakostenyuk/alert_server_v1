import asyncio
import threading

from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import ProgrammingError
from sqlalchemy_utils import database_exists, create_database
from loguru import logger


import loader
import settings
from utils.alerts_ws import start_server
from utils.telegram import send_alert
from utils.binance import update_markets, receive_data_from_stream, create_streams
from settings import WS_IP, WS_PORT
from db_utils.models import FutureAlert
from db_utils.database import create_db


def check_database(db_uri) -> None:
    engine = create_engine(db_uri)

    # check if database not exists
    if not database_exists(engine.url):
        try:
            create_database(engine.url)
            create_db()
            logger.info("Create database, table")

        except ProgrammingError as exp:
            logger.error(f"Error in create db {exp}")
    else:
        try:
            inspector = inspect(engine)
            # check if table exists
            if not inspector.has_table(FutureAlert.__tablename__):
                create_db()
                logger.info("Create table")
        except ProgrammingError as exp:
            logger.error(f"Error in create table {exp}")


def run_receive_data_from_stream():
    asyncio.run(receive_data_from_stream())


def run_update_markets():
    asyncio.run(update_markets())


async def main():
    """
    Main function to start the program.

    Notes:
        - It runs two separate threads:
        - One for updating symbols.
        - One for receiving data from the stream.
    """

    await send_alert("start alert server")
    check_database(settings.DATABASE)

    loader.FIRST_KLINE_STREAM_ID, loader.SECOND_KLINE_STREAM_ID = await create_streams()

    threading.Thread(target=run_receive_data_from_stream, daemon=True).start()  # Receive data from stream
    threading.Thread(target=run_update_markets, daemon=True).start()

    tasks = [
        asyncio.ensure_future(start_server(WS_IP, WS_PORT)),  # Alerts WS,
    ]
    await asyncio.gather(*tasks)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped manually.")
    except Exception as e:
        logger.exception(e)
