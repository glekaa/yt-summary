import asyncio
import json

import aio_pika

from config import settings


async def process_message(message: aio_pika.abc.AbstractIncomingMessage):
    async with message.process():
        body = message.body.decode()
        data = json.loads(body)
        print(f"Received message: {data}")
        print("Processing...")
        await asyncio.sleep(5)
        print("Done.")


async def main():
    print("Connecting to RabbitMQ...")
    rabbit_connection = await aio_pika.connect_robust(settings.rabbitmq_url)

    async with rabbit_connection:
        rabbit_channel = await rabbit_connection.channel()
        queue = await rabbit_channel.declare_queue(settings.QUEUE_NAME, durable=True)
        print("Connected. Waiting for messages...")

        await queue.consume(process_message)
        await asyncio.get_running_loop().create_future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Interrupted")
