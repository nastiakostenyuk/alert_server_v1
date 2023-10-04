import os
from dotenv import load_dotenv

load_dotenv()

# Application
UPDATE_SYMBOLS_COOLDOWN = 300

# WS Server
WS_IP = os.getenv('WS_IP', '127.0.0.1')
WS_PORT = int(os.getenv('WS_PORT', 8004))

# Strategy
MAXIMUM_KLINES = int(os.getenv('STRATEGY_MAXIMUM_KLINES', '10'))
AVG_INCREASE = float(os.getenv('STRATEGY_VOLUME_AVG_INCREASE', '3500000'))
VOLUME_MULTIPLE = float(os.getenv('STRATEGY_VOLUME_MULTIPLE', '3.5'))
PERCENT_TO_MAX_PRICE_EXCEEDS_MIN = float(os.getenv('STRATEGY_PERCENT_TO_MAX_PRICE_EXCEEDS_MIN', '3'))
WITHIN_THRESHOLD = float(os.getenv('STRATEGY_PERCENT_TO_MAX_PRICE_WITHIN_MIN', '9'))
TIME_PASSED = int(os.getenv('STRATEGY_TIME_PASSED', '90'))
MIN_DAILY_VOLUME = int(os.getenv('STRATEGY_MIN_DAILY_VOLUME', '70000000'))

# DB
DATABASE = os.getenv('DB_DATABASE', None)


# Telegram
TOKEN_MAIN_BOT = os.getenv('TG_TOKEN_MAIN_BOT', None)
GROUP_ID = int(os.getenv('GROUP_ID', None))
