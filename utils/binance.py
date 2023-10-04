import asyncio
from datetime import datetime as dt
from typing import List

from loguru import logger

import loader
import settings
import utils
import utils.alerts_ws
import utils.telegram
from db_utils.database import session as db_session
from db_utils.models import FutureAlert
from loader import BINANCE_WEBSOCKET_MANAGER
from utils.checks import all_checks
from utils.other_func import distribute_pairs_to_threads


async def receive_data_from_stream():
    """
    Receives data from the stream buffer and passes it to the event adapter.

    Notes:
        - This function runs indefinitely in a loop.
    """

    logger.info("Thread \'Receive data from stream\' started!")
    while True:
        data_from_stream_buffer = BINANCE_WEBSOCKET_MANAGER.pop_stream_data_from_stream_buffer()

        if data_from_stream_buffer:
            await event_adapter(data_from_stream_buffer)
        else:
            await asyncio.sleep(0.1)


async def event_adapter(data: dict):
    """
    Adapts the received event data from the stream and performs specific actions based on the event type.

    Args:
        data (dict): The event data received from the stream.
    """
    event_data = data.get('data', None) if 'stream' in data else data

    if event_data:
        event_type = event_data.get('e', None)

        if event_type == 'kline':
            asyncio.create_task(event_kline(event_data))


async def event_kline(data: dict):
    """
    Processes the kline event data from the stream.

    Args:
        data (dict): The kline event data.
    """
    kline_data = data.get('k', None)
    if kline_data and kline_data.get('x', False):
        symbol = kline_data.get('s')
        candle = loader.KLINES_DATA.get(symbol, [])
        candle.append(kline_data)

        if len(candle) > settings.MAXIMUM_KLINES:
            candle.pop(0)

        check_status = await all_checks(symbol) if len(candle) >= settings.MAXIMUM_KLINES else False

        if check_status:
            # check daily volume of symbol
            result_check, log = await check_daily_volume(symbol)
            if result_check:
                logger.info(f"Alert {symbol} {result_check} - {log}")
                last_candle_dt = dt.fromtimestamp(
                    kline_data.get('t') / 1000
                )
                # add alert to database
                new_alert = FutureAlert(future=symbol, date_time=last_candle_dt)
                db_session.add(new_alert)
                db_session.commit()

                if len(utils.alerts_ws.CONNECTIONS) > 0:
                    utils.alerts_ws.MESSAGES_QUEUE.append({"symbol": symbol})
                else:
                    await utils.telegram.send_alert({"symbol": symbol})
            else:
                logger.info(f"Remove Alert {symbol} {result_check} - {log}")


async def update_markets():
    """
    Updates the markets by subscribing to new symbols that are not in the current stream.

    Note:
        - This function runs indefinitely in a loop.
    """
    logger.info("Thread \'Update markets\' started!")
    while True:
        bn_symbols = await receive_symbols()
        first_symbols, second_symbols = distribute_pairs_to_threads(bn_symbols, 'K')
        first_stream_info = BINANCE_WEBSOCKET_MANAGER.get_stream_info(loader.FIRST_KLINE_STREAM_ID)
        second_stream_info = BINANCE_WEBSOCKET_MANAGER.get_stream_info(loader.SECOND_KLINE_STREAM_ID)

        for symbol in first_symbols:
            if symbol.lower() not in first_stream_info['markets']:
                await subscribe_to_stream(symbol, loader.FIRST_KLINE_STREAM_ID)

        for symbol in second_symbols:
            if symbol.lower() not in second_stream_info['markets']:
                await subscribe_to_stream(symbol, loader.SECOND_KLINE_STREAM_ID)

        await asyncio.sleep(settings.UPDATE_SYMBOLS_COOLDOWN)


async def subscribe_to_stream(symbol: str, stream_id: str):
    """
    Subscribes to a data stream for a specific symbol.

    Args:
        stream_id: The stream id to subscribe to the symbol.
        symbol (str): The symbol to subscribe to.
    """

    BINANCE_WEBSOCKET_MANAGER.subscribe_to_stream(
        stream_id=stream_id,
        channels="kline_1m",
        markets=symbol
    )

    if symbol not in loader.KLINES_DATA:
        loader.KLINES_DATA[symbol] = []


async def create_streams():
    """
    Creates a data stream (kline_15m)

    Returns:
        stream_id(str) or False
    """
    symbols = await receive_symbols()

    first_pairs, second_pairs = distribute_pairs_to_threads(symbols, 'K')

    first_stream = BINANCE_WEBSOCKET_MANAGER.create_stream(
        channels="kline_1m",
        markets=first_pairs,
        stream_label='kline_1m_first_part',
        output="dict"
    )

    second_stream = BINANCE_WEBSOCKET_MANAGER.create_stream(
        channels="kline_1m",
        markets=second_pairs,
        stream_label='kline_1m_second_part',
        output="dict"
    )

    for symbol in symbols:
        loader.KLINES_DATA[symbol] = []

    return first_stream, second_stream


async def receive_symbols() -> List[str]:
    """
    Fetches symbols from the Binance API and returns a list of symbols ending with 'USDT'.

    Returns:
    - bn_symbols (list): List of symbols ending with 'USDT'.
    """

    try:
        exchange_info = await loader.AIO_BINANCE_API_CLIENT.get_public_exchange_info()

        bn_symbols = [elem["symbol"].upper() for elem in exchange_info['data']["symbols"]
                      if elem["symbol"].endswith("USDT") and elem["contractType"] == "PERPETUAL"
                      and elem["status"] == "TRADING"]

    except Exception as exp:
        logger.error(f'Update symbols {exp}')
        bn_symbols = []

    return bn_symbols


async def get_daily_quote_volume(symbol) -> float:
    """
    Function makes a request to the binance api and returns the quote volume of symbol
    :param symbol:
    :return: float
    """
    try:

        symbol_data = await loader.AIO_BINANCE_API_CLIENT.get_public_ticker_24hr_price_change(symbol)
        return float(symbol_data.get('data', {}).get('quoteVolume', 0))
    except Exception as exp:
        logger.error(f'Get daily volume {exp}')
        return 0


async def check_daily_volume(symbol: str) -> tuple:
    volume = await get_daily_quote_volume(symbol)
    result = volume >= settings.MIN_DAILY_VOLUME
    return result, f"quote volume {volume} > {settings.MIN_DAILY_VOLUME}"
