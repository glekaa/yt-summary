import asyncio
import json

import aio_pika
from aio_pika.abc import AbstractIncomingMessage
from db import AsyncSessionLocal, StatusEnum, Task
from sqlalchemy.exc import OperationalError
from tenacity import retry, stop_after_attempt, stop_never, wait_exponential, retry_if_exception_type

from ai import summarize_text
from config import settings


# Retry decorator for database operations
def db_retry():
    return retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((OperationalError, ConnectionError, OSError)),
        reraise=True,
    )


@db_retry()
async def update_task_status(task_id: int, status: StatusEnum, result: str | None = None):
    """Update task status with retry logic."""
    async with AsyncSessionLocal() as session:
        task = await session.get(Task, task_id)
        if not task:
            print(f"ERROR: Task {task_id} not found")
            return False
        task.status = status
        if result is not None:
            task.result = result
        await session.commit()
        return True


@retry(
    stop=stop_never,
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception_type((ConnectionError, OSError, aio_pika.AMQPException)),
)
async def connect_to_rabbitmq():
    """Connect to RabbitMQ with infinite retry."""
    print("Connecting to RabbitMQ...")
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    print("Connected to RabbitMQ.")
    return connection


async def process_message(message: AbstractIncomingMessage):
    async with message.process():
        print("Received a task, working...")
        body = message.body.decode()
        data = json.loads(body)
        task_id = data["task_id"]

        try:
            summarized_text = await summarize_text(data["text"])
            new_status = StatusEnum.DONE
            result = summarized_text
        except Exception as e:
            print(f"Summarization failed for {task_id}: {e}")
            new_status = StatusEnum.FAILED
            result = None

        # Update task with retry
        await update_task_status(task_id, new_status, result)
        print(f"Task {task_id} completed with status: {new_status.value}")


async def main():
    # Graceful startup: wait for RabbitMQ
    rabbit_connection = await connect_to_rabbitmq()

    async with rabbit_connection:
        rabbit_channel = await rabbit_connection.channel()
        await rabbit_channel.set_qos(prefetch_count=1)
        summary_queue = await rabbit_channel.declare_queue(
            settings.SUMMARY_QUEUE_NAME, durable=True
        )

        print("Ready. Waiting for messages...")

        await summary_queue.consume(process_message)
        await asyncio.get_running_loop().create_future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Interrupted")
