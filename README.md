# YouTube Video Summarizer

A microservices-based application that automatically transcribes and summarizes YouTube videos using AI.
### Services

| Service | Description |
|---------|-------------|
| **Gateway** | FastAPI REST API that accepts video URLs and tracks task status |
| **Transcriber** | Downloads audio from YouTube and transcribes using OpenAI Whisper |
| **Summarizer** | Generates concise bullet-point summaries using LangChain with Ollama |

### Request Flow

1. **Gateway** receives a YouTube URL via REST API and creates a task in PostgreSQL
2. Gateway publishes a message to RabbitMQ `transcription_queue`
3. **Transcriber** consumes the message, downloads audio, and transcribes it using Whisper
4. Transcriber publishes the transcript to `summary_queue`
5. **Summarizer** consumes the transcript and generates a summary using LangChain + Ollama
6. Summarizer updates the task status and result in PostgreSQL

## Tech Stack

- **Python 3.13+**
- **FastAPI** — REST API framework
- **LangChain** — LLM orchestration framework
- **RabbitMQ** — Message queue for async task processing
- **PostgreSQL** — Task persistence and status tracking
- **OpenAI Whisper** — Speech-to-text transcription
- **Ollama** — Local LLM for summarization
- **Docker Compose** — Container orchestration

## Quick Start

### Prerequisites

- Docker & Docker Compose
- [Ollama](https://ollama.ai/) running locally with a model

### Run

```bash
docker compose up --build
```

This starts all services:
- Gateway API: `http://localhost:8000`
- RabbitMQ Management: `http://localhost:15672` (guest/guest)
- PostgreSQL: `localhost:5433`

## API Usage

### Submit a Video

```bash
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID"}'
```

**Response:**
```json
{
  "task_id": 1,
  "status": "queued"
}
```

### Check Task Status

```bash
curl http://localhost:8000/tasks/1
```

**Response:**
```json
{
  "id": 1,
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "status": "done",
  "result": "• Key point 1\n• Key point 2\n..."
}
```

### Health Check

```bash
curl http://localhost:8000/health
```

## Task Statuses

| Status | Description |
|--------|-------------|
| `pending` | Task created, waiting in queue |
| `processing` | Currently being transcribed/summarized |
| `done` | Completed successfully |
| `failed` | An error occurred |

## Project Structure

```
yt-summary/
├── gateway/           # REST API service
├── transcriber/       # Audio download & transcription
├── summarizer/        # AI summarization
├── libs/db/           # Shared database models
└── docker-compose.yml
```

## Configuration

Environment variables are set in `docker-compose.yml`:

| Variable | Default | Description |
|----------|---------|-------------|
| `RABBITMQ_HOST` | rabbitmq | RabbitMQ hostname |
| `RABBITMQ_PORT` | 5672 | RabbitMQ port |
| `RABBITMQ_USER` | guest | RabbitMQ username |
| `RABBITMQ_PASS` | guest | RabbitMQ password |
| `DATABASE_HOST` | db | PostgreSQL hostname |
| `DATABASE_PORT` | 5432 | PostgreSQL port |
| `DATABASE_USER` | user | PostgreSQL username |
| `DATABASE_PASS` | password | PostgreSQL password |
| `DATABASE_NAME` | ytsummary | PostgreSQL database name |
| `OLLAMA_HOST` | http://host.docker.internal:11434 | Ollama API endpoint |
| `OLLAMA_MODEL` | qwen3:4b | Model for summarization |
