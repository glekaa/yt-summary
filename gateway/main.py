import json
from contextlib import asynccontextmanager

import aio_pika
from fastapi import FastAPI
from pydantic import BaseModel

from config import settings
from db import Task, AsyncSessionLocal, engine, Base


class VideoRequest(BaseModel):
    url: str


rabbit_connection = None
rabbit_channel = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global rabbit_connection, rabbit_channel

    # Создаём таблицы (временно, потом заменим на Alembic)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created.")

    print("Connecting to RabbitMQ...")
    rabbit_connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    rabbit_channel = await rabbit_connection.channel()
    await rabbit_channel.declare_queue(settings.TRANSCRIPTION_QUEUE_NAME, durable=True)
    print("Connected.")

    yield

    await rabbit_channel.close()
    await rabbit_connection.close()
    print("Disconnected.")


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "Gateway is alive!"}


@app.post("/process")
async def process_video(request: VideoRequest):
    # Создаём задачу в БД
    async with AsyncSessionLocal() as session:
        task = Task(url=request.url)
        session.add(task)
        await session.commit()
        await session.refresh(task)
        task_id = task.id

    # Отправляем в очередь
    message_body = json.dumps({"task_id": task_id, "url": request.url}).encode()
    await rabbit_channel.default_exchange.publish(
        aio_pika.Message(body=message_body),
        routing_key=settings.TRANSCRIPTION_QUEUE_NAME,
    )

    return {"task_id": task_id, "status": "queued"}


@app.get("/tasks/{task_id}")
async def get_task(task_id: int):
    async with AsyncSessionLocal() as session:
        task = await session.get(Task, task_id)
        if not task:
            return {"error": "Task not found"}
        return {
            "id": task.id,
            "url": task.url,
            "status": task.status.value,
            "result": task.result,
        }
