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
from tenacity import retry, stop_after_attempt, stop_never, wait_exponential, retry_if_exception_type

from config import settings


class VideoRequest(BaseModel):
    url: str


def get_rabbit_channel(request: Request):
    return cast(AbstractRobustChannel, request.state.rabbit_channel)


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


@retry(
    stop=stop_never,
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception_type((ConnectionError, OSError, Exception)),
)
async def wait_for_database():
    """Wait for database to be available."""
    print("Connecting to database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database ready.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Graceful startup: wait for database
    await wait_for_database()
    
    # Graceful startup: wait for RabbitMQ
    connection = await connect_to_rabbitmq()
    channel = await connection.channel()

    await channel.declare_queue(settings.TRANSCRIPTION_QUEUE_NAME, durable=True)
    print("Gateway ready.")

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

    # Send task to queue with retry logic
    message_body = json.dumps({"task_id": task_id, "url": request.url}).encode()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def publish_message():
        await channel.default_exchange.publish(
            aio_pika.Message(body=message_body),
            routing_key=settings.TRANSCRIPTION_QUEUE_NAME,
        )
    
    try:
        await publish_message()
    except Exception as e:
        task.status = StatusEnum.FAILED
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Queue unavailable after retries"
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
