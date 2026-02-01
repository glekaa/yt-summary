from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASS: str = "guest"
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672

    SUMMARY_QUEUE_NAME: str = "summary_queue"

    OLLAMA_MODEL: str = "qwen3:4b"
    OLLAMA_HOST: str = "http://localhost:11434"

    @property
    def rabbitmq_url(self) -> str:
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASS}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/"

    class Config:
        env_file = ".env"


settings = Settings()
