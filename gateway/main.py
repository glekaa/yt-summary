import json
import re
from contextlib import asynccontextmanager
from typing import TypedDict, cast

import aio_pika
from aio_pika.abc import AbstractRobustChannel, AbstractRobustConnection
from db import Base, StatusEnum, Task, engine, get_db
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings


class VideoRequest(BaseModel):
    url: str


def get_rabbit_channel(request: Request):
    return cast(AbstractRobustChannel, request.state.rabbit_channel)


@asynccontextmanager
async def lifespan(app: FastAPI):
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    channel = await connection.channel()

    # Создаём таблицы (временно, потом заменим на Alembic)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created.")

    print("Connecting to RabbitMQ...")
    await channel.declare_queue(settings.TRANSCRIPTION_QUEUE_NAME, durable=True)
    print("Connected.")

    yield {"rabbit_connection": connection, "rabbit_channel": channel}

    await channel.close()
    await connection.close()
    print("Disconnected.")


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health(request: Request, session: AsyncSession = Depends(get_db)):
    rabbit_ok = request.state.rabbit_channel is not None
    try:
        await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    if rabbit_ok and db_ok:
        return {"status": "healthy", "db": "ok", "rabbitmq": "ok"}

    return JSONResponse(
        {"status": "unhealthy", "db": db_ok, "rabbitmq": rabbit_ok},
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


@app.post("/process")
async def process_video(
    request: VideoRequest,
    session: AsyncSession = Depends(get_db),
    channel: AbstractRobustChannel = Depends(get_rabbit_channel),
):
    # Create a task in the database
    task = Task(url=request.url)
    session.add(task)
    await session.commit()
    await session.refresh(task)
    task_id = task.id

    # Send task to queue
    message_body = json.dumps({"task_id": task_id, "url": request.url}).encode()
    try:
        await channel.default_exchange.publish(
            aio_pika.Message(body=message_body),
            routing_key=settings.TRANSCRIPTION_QUEUE_NAME,
        )
    except Exception as e:
        task.status = StatusEnum.FAILED
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Queue unavailable"
        )

    return {"task_id": task_id, "status": "queued"}


@app.get("/tasks/{task_id}")
async def get_task(task_id: int, session: AsyncSession = Depends(get_db)):
    task = await session.get(Task, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )
    return {
        "id": task.id,
        "url": task.url,
        "status": task.status.value,
        "result": task.result,
    }
