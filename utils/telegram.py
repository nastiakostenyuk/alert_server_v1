import httpx
from loguru import logger

import settings


async def send_alert(symbol):
    try:
        async with httpx.AsyncClient() as client:
            url = f"https://api.telegram.org/bot{settings.TOKEN_MAIN_BOT}/sendMessage"
            params = {"chat_id": settings.GROUP_ID, "text": symbol}
            response = await client.get(url, params=params)
            if response.status_code != 200:
                logger.error(f'Status code: {response.status_code}')
    except Exception as exp:
        logger.error(f"Error in send alert to telegram - {exp}")
