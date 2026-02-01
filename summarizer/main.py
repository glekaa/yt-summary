import asyncio
import json

import aio_pika
from aio_pika.abc import AbstractIncomingMessage

from ai import summarize_text
from config import settings


async def process_message(message: AbstractIncomingMessage) -> dict:
    async with message.process():
        print("Received a task, working...")
        body = message.body.decode()
        data = json.loads(body)
        summarized_text = await summarize_text(data["text"])
        processed_data = {"url": data["url"], "text": summarized_text}
        print(processed_data)
        return processed_data


async def main():
    rabbit_connection = await aio_pika.connect_robust(settings.rabbitmq_url)

    async with rabbit_connection:
        rabbit_channel = await rabbit_connection.channel()
        await rabbit_channel.set_qos(prefetch_count=1)
        summary_queue = await rabbit_channel.declare_queue(
            settings.SUMMARY_QUEUE_NAME, durable=True
        )
        await summary_queue.consume(process_message)
        await asyncio.get_running_loop().create_future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Interrupted")
