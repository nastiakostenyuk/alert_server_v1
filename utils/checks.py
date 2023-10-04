from statistics import fmean
from datetime import datetime, timedelta

from loguru import logger
from sqlalchemy import desc

import loader
import settings
from db_utils.database import session as db_session
from db_utils.models import FutureAlert


def get_min_candle(lst_candles: list) -> dict:
    """
    The function finds the lowest price from the given candles
    :param lst_candles:
    :return: dict with min_price and max price in this min candle
    """

    min_price = min(float(elem["l"]) for elem in lst_candles[:-1])
    max_in_min_price = max(float(elem["h"]) for elem in lst_candles[:-1] if float(elem["l"]) == min_price)

    return {"min_price": min_price, "max_in_min_price": max_in_min_price}


def get_average_volume(lst_candles: list) -> float:
    """
    The function calculates the average volume in dollars from a list candles
    :param lst_candles:
    :return: average volume
    """
    average_volume = fmean([float(elem["q"]) for elem in lst_candles])
    return average_volume


def check_candle_volume_multiple(new_candle, average_volume, multiple) -> tuple:
    """
    Checks whether the volume of the new candle is greater than the average volume of the last candles by 350%
    """
    result = float(new_candle["q"]) >= (average_volume * multiple)
    return result, f"volume new kline: {new_candle['q']} > average_volume: {average_volume} * {multiple}"


def check_average_volume_greater(lst_candles: dict,  volume: float) -> tuple:
    """
    The function checks if the total volume of the last candles is more than parameters Volume in dollars
    """
    sum_volume = sum(float(elem["q"]) for elem in lst_candles)
    result = sum_volume > volume
    return result, f"sum_volume: {sum_volume} > {volume}$"


def check_max_candle_price_exceeds_min_threshold(min_price, new_candle, percentage: float) -> tuple:
    """
    The function checks whether the maximum price of the new candle is higher than the lowest
    price of the last candles by at least 3%
    """
    result = (float(new_candle["h"]) - min_price) >= (min_price * (percentage / 100))
    return result, f"hight new kline: {new_candle['h']} >= min price: {min_price} by {percentage}%"


def check_max_candle_price_within_percent_threshold(new_candle, penultimate_candle, percentage: float) -> tuple:
    """
    The function checks whether the maximum price of the new candle is greater than the minimum
    of the previous candle not more than 9%

    """
    result = (float(new_candle["h"]) - float(penultimate_candle["l"])) <= (
            float(penultimate_candle["l"]) * (percentage / 100)
    )
    return result, f"high new kline: {new_candle['h']} > penultimate kline min price: " \
                   f"{penultimate_candle['l']} not more than {percentage}%"


def check_max_candle(new_candle, max_in_min_price) -> tuple:
    """
    Function checks whether the high of the new candle is greater than the high of the candle that had the low price
    :param new_candle: last candle
    :param max_in_min_price: high of the candle that had the lowest price
    :return bool
    """
    result = float(new_candle["h"]) >= max_in_min_price
    return result, f"high new kline: {new_candle['h']} >= max in min kline: {max_in_min_price}"


def time_passed(symbol, last_candle, minute) -> tuple:
    """
    The function checks whether a certain time has passed since the last alert
    """
    # last alert by symbol
    last_alert = (
        db_session.query(FutureAlert)
        .filter(FutureAlert.future == symbol)
        .order_by(desc(FutureAlert.alert_id))
        .first()
    )
    # last candle datetime
    last_candle_dt = datetime.fromtimestamp(
        last_candle["t"] / 1000
    )
    result = (last_alert is None) or (last_candle_dt >= (last_alert.date_time + timedelta(minutes=minute)))
    return result, f"time new kline: {last_candle_dt} > last_alert: {last_alert} for 90 minutes"


async def all_checks(symbol: str) -> bool:
    candle = loader.KLINES_DATA[symbol]

    min_candle = get_min_candle(candle)
    average_volume = get_average_volume(candle)

    # Check if candle volume exceeds the average volume threshold
    is_exceeds_percentage, log_1 = check_candle_volume_multiple(candle[-1], average_volume,
                                                                settings.VOLUME_MULTIPLE)

    # Check if average volume is greater than the threshold
    average_volume_is_greater, log_2 = check_average_volume_greater(candle, settings.AVG_INCREASE)

    # Check if the max candle price exceeds the min threshold
    above_percent, log_3 = check_max_candle_price_exceeds_min_threshold(min_candle['min_price'], candle[-1],
                                                                        settings.PERCENT_TO_MAX_PRICE_EXCEEDS_MIN)

    # Check if the max candle price is within the percent threshold
    not_higher_percent, log_4 = check_max_candle_price_within_percent_threshold(candle[-1], candle[-2],
                                                                                settings.WITHIN_THRESHOLD)

    # Check the max candle
    max_candle, log_5 = check_max_candle(candle[-1], min_candle['max_in_min_price'])

    # Check the time passed
    t_passed, log_6 = time_passed(symbol, candle[-1], settings.TIME_PASSED)

    logger.info(f"[ {symbol} \t|\t "
                f"check №1 ({is_exceeds_percentage} {log_1}) "
                f"check №2 ({average_volume_is_greater} {log_2}) "
                f"check №3 ({above_percent} {log_3}) "
                f"check №4 ({not_higher_percent} {log_4}) "
                f"check №5 ({max_candle} {log_5}) "
                f"check №6 ({t_passed} {log_6}) ]")

    # Combine all the checks using logical AND
    return all([is_exceeds_percentage, average_volume_is_greater,
                above_percent, not_higher_percent, max_candle, t_passed])
