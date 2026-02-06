from ollama import AsyncClient, ResponseError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import settings

client = AsyncClient()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((ConnectionError, TimeoutError, ResponseError)),
    reraise=True,
)
async def summarize_text(text: str) -> str:
    response = await client.generate(
        model=settings.OLLAMA_MODEL,
        prompt=f"Please summarize the following text into concise bullet points:\n\n{text}",
        system="You are an expert content summarizer. Your goal is to provide a concise, structured summary of the provided text. Focus on key insights and actionable takeaways.",
        stream=False,
    )
    return response["response"]
