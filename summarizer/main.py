import asyncio
import json

import aio_pika
from aio_pika.abc import AbstractIncomingMessage
from db import AsyncSessionLocal, StatusEnum, Task

from ai import summarize_text
from config import settings


async def process_message(message: AbstractIncomingMessage):
    async with message.process():
        print("Received a task, working...")
        body = message.body.decode()
        data = json.loads(body)
        task_id = data["task_id"]
        summarized_text = await summarize_text(data["text"])
        async with AsyncSessionLocal() as session:
            task = await session.get(Task, task_id)
            if not task:
                print(f"ERROR: Task {task_id} not found, skipping")
                return
            task.status = StatusEnum.DONE
            task.result = summarized_text
            await session.commit()


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
