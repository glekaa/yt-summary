import asyncio
import json
import os

import aio_pika
from aio_pika.abc import AbstractIncomingMessage
from db import AsyncSessionLocal, StatusEnum, Task
from sqlalchemy.exc import OperationalError
from tenacity import retry, stop_after_attempt, stop_never, wait_exponential, retry_if_exception_type

from config import settings
from download import download_audio
from transcribe import Transcriber


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


@db_retry()
async def get_task_exists(task_id: int) -> bool:
    """Check if task exists with retry logic."""
    async with AsyncSessionLocal() as session:
        task = await session.get(Task, task_id)
        return task is not None


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


async def main():
    # Graceful startup: wait for RabbitMQ
    rabbit_connection = await connect_to_rabbitmq()
    
    # Initialize Whisper model
    print("Loading Whisper model...")
    transcriber = Transcriber()

    async with rabbit_connection:
        rabbit_channel = await rabbit_connection.channel()
        await rabbit_channel.set_qos(prefetch_count=1)
        transcription_queue = await rabbit_channel.declare_queue(
            settings.TRANSCRIPTION_QUEUE_NAME, durable=True
        )
        await rabbit_channel.declare_queue(settings.SUMMARY_QUEUE_NAME, durable=True)

        print("Ready. Waiting for messages...")

        async def process_message(message: AbstractIncomingMessage):
            async with message.process():
                body = message.body.decode()
                data = json.loads(body)
                url = data["url"]
                task_id = data["task_id"]
                file_path = None

                # Check if task exists
                if not await get_task_exists(task_id):
                    print(f"ERROR: Task {task_id} not found, skipping")
                    return

                # Update status to PROCESSING
                await update_task_status(task_id, StatusEnum.PROCESSING)

                print(f"Processing task {task_id}: {url}")
                try:
                    print("[1/2] Downloading...")
                    file_path = await asyncio.to_thread(
                        download_audio, url, "downloads"
                    )
                    print("[2/2] Transcribing...")
                    text = await asyncio.to_thread(
                        transcriber.transcribe_audio, file_path
                    )

                    # Publish to summary queue with retry
                    @retry(
                        stop=stop_after_attempt(3),
                        wait=wait_exponential(multiplier=1, min=2, max=30),
                        reraise=True,
                    )
                    async def publish_to_summary():
                        payload = json.dumps({"task_id": task_id, "text": text}).encode()
                        await rabbit_channel.default_exchange.publish(
                            aio_pika.Message(body=payload),
                            routing_key=settings.SUMMARY_QUEUE_NAME,
                        )

                    await publish_to_summary()
                    print(f"Sent to {settings.SUMMARY_QUEUE_NAME}")

                except Exception as e:
                    print(f"Error processing task {task_id}: {e}")
                    await update_task_status(task_id, StatusEnum.FAILED)
                finally:
                    # Cleanup downloaded file
                    if file_path and os.path.exists(file_path):
                        os.remove(file_path)

        await transcription_queue.consume(process_message)
        await asyncio.get_running_loop().create_future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Interrupted")
