import asyncio
import logging
import os
from typing import Any, Dict, Literal, NamedTuple

import carehare
import msgpack

from .intercom import IntercomMockClient, IntercomRestClient

logger = logging.getLogger(__name__)


class Message(NamedTuple):
    method: Literal["POST"]
    path: str
    data: Dict[str, Any]


def read_message(msgpacked_data):
    """Read a message or raise ValueError."""
    data = msgpack.unpackb(msgpacked_data)  # or ValueError
    if set(data.keys()) != {"method", "path", "data"}:
        raise ValueError(
            "Expected message to have keys {method, path, data}; got: %r" % (data,)
        )
    return Message(**data)


async def rabbitmq_connect(url: str):
    while True:
        connection = carehare.Connection(url=url, connect_timeout=10)
        try:
            await connection.connect()
            return connection
        except (
            asyncio.TimeoutError,
            carehare.ConnectionClosedByServer,
            carehare.ConnectionClosedByHeartbeatMonitor,
            OSError,
        ):
            logger.exception("Failure connecting to RabbitMQ. Will retry")
            await asyncio.sleep(1)
        # raise any other exception


async def main(rabbitmq_url: str, queue_name: str, intercom_api_token: str):
    if intercom_api_token == "mock":
        intercom_client = IntercomMockClient()
    else:
        intercom_client = IntercomRestClient(api_token=intercom_api_token)

    try:
        connection = await rabbitmq_connect(rabbitmq_url)
        try:
            await connection.queue_declare(queue_name, durable=True)
            async with connection.acking_consumer(queue_name) as consumer:
                async for msgpacked_message in consumer:
                    try:
                        message = read_message(msgpacked_message)
                    except ValueError:
                        logger.exception("Invalid message")
                    await intercom_client.send(*message)
        finally:
            await connection.close()
    finally:
        await intercom_client.close()


if __name__ == "__main__":
    rabbitmq_url = os.environ["CJW_RABBITMQ_HOST"]
    queue_name = os.environ["CJW_INTERCOM_QUEUE_NAME"]
    intercom_api_token = os.environ["CJW_INTERCOM_API_TOKEN"]

    logging.basicConfig(level=logging.INFO)

    asyncio.run(main(rabbitmq_url, queue_name, intercom_api_token))
