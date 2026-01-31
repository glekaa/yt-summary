import asyncio
import json
import os

import aio_pika

from config import settings
from download import download_audio
from transcribe import transcribe_audio


async def process_message(message: aio_pika.abc.AbstractIncomingMessage):
    async with message.process():
        body = message.body.decode()
        data = json.loads(body)
        url = data["url"]
        print(f"Received message: {data}")
        try:
            print("[1/2] Downloading...")
            file_path = await asyncio.to_thread(download_audio, url, "downloads")
            print("[2/2] Transcribing...")
            text = await asyncio.to_thread(transcribe_audio, file_path)
            print(text)
            os.remove(file_path)
        except Exception as e:
            print(f"Error: {e}")


async def main():
    print("Connecting to RabbitMQ...")
    rabbit_connection = await aio_pika.connect_robust(settings.rabbitmq_url)

    async with rabbit_connection:
        rabbit_channel = await rabbit_connection.channel()
        await rabbit_channel.set_qos(prefetch_count=1)
        queue = await rabbit_channel.declare_queue(settings.QUEUE_NAME, durable=True)
        print("Connected. Waiting for messages...")

        await queue.consume(process_message)
        await asyncio.get_running_loop().create_future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Interrupted")
