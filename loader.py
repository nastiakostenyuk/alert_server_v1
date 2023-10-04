import os

from loguru import logger
from aio_binance.futures.usdt import Client
from unicorn_binance_rest_api import BinanceRestApiManager
from unicorn_binance_websocket_api import BinanceWebSocketApiManager

BINANCE_API_CLIENT = BinanceRestApiManager(exchange="binance.com-futures")
AIO_BINANCE_API_CLIENT = Client(show_limit_usage=True)
BINANCE_WEBSOCKET_MANAGER = BinanceWebSocketApiManager(exchange="binance.com-futures")
KLINES_DATA = {}

FIRST_KLINE_STREAM_ID = ""
SECOND_KLINE_STREAM_ID = ""

log_folder = "./logs"
os.makedirs(log_folder, exist_ok=True)

logger.add(f"{log_folder}/file_{{time:DD-MM}}_{{time:HH-mm}}.log", rotation="100 MB", retention="1 day",
           encoding='utf-8')

__all__ = [
    'BINANCE_API_CLIENT', 'BINANCE_WEBSOCKET_MANAGER',
    'FIRST_KLINE_STREAM_ID', 'SECOND_KLINE_STREAM_ID',
    'KLINES_DATA', 'AIO_BINANCE_API_CLIENT',
]