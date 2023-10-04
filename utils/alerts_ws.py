import asyncio
from copy import copy
from datetime import datetime as dt

import ujson
import websockets
from websockets.legacy.server import WebSocketServerProtocol
from loguru import logger

from utils.telegram import send_alert

PING_COOLDOWN = 15  # In seconds
MESSAGES_QUEUE = []
CONNECTIONS = []


async def start_server(ip: str = "localhost", port: int = 8004) -> None:
    """
        Starts the websocket server.

        Args:
            - ip: The IP address to bind the server to.
            - port: The port number to bind the server to.
        :return: None
    """

    async with websockets.serve(handle_ping,
                                host=ip,
                                port=port):
        logger.info(f"Websocket server started. Address: ws://{ip}:{port}")
        await asyncio.Future()


async def handle_ping(websocket: WebSocketServerProtocol):
    """
        Sends a PING message to the websocket every PING_COOLDOWN seconds,
        otherwise sends a message from the messages_queue
        :param websocket: Websocket connection
    """

    last_ping_time = dt.utcnow()

    CONNECTIONS.append(websocket)
    logger.info(f'New connection: {websocket.remote_address}')
    while True:
        try:
            # Check if it's time to send a PING message
            if (dt.utcnow() - last_ping_time).total_seconds() >= PING_COOLDOWN:
                # Send the PING message as JSON
                await websocket.send(ujson.dumps({
                    "event": "PING",
                    "E": int(dt.utcnow().timestamp())
                }))

                # Update the last ping time
                last_ping_time = dt.utcnow()
            else:
                # Check if there are any messages in the queue
                if MESSAGES_QUEUE:
                    # Get the next message from the queue
                    data = MESSAGES_QUEUE.pop(0)

                    data['event'] = 'Alert'
                    data['E'] = int(dt.utcnow().timestamp())

                    # Send the message as JSON
                    for connection in copy(CONNECTIONS):
                        if not connection.closed:
                            await connection.send(ujson.dumps(data))
                        else:
                            CONNECTIONS.remove(connection)

                    await send_alert(data['symbol'])

            await asyncio.sleep(0.25)
        except (
                websockets.exceptions.ConnectionClosed,
                websockets.exceptions.ConnectionClosedOK,
                websockets.exceptions.ConnectionClosedError
        ):
            CONNECTIONS.remove(websocket)
            break
        except Exception as e:
            logger.exception(e)

    logger.info(f"Websocket connection closed: {websocket.remote_address}")


__all__ = ['start_server', 'MESSAGES_QUEUE']
