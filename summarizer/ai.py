from ollama import AsyncClient

from config import settings

client = AsyncClient()


async def summarize_text(text: str) -> str:
    response = await client.generate(
        model=settings.OLLAMA_MODEL,
        prompt=f"Please summarize the following text into concise bullet points:\n\n{text}",
        system="You are an expert content summarizer. Your goal is to provide a concise, structured summary of the provided text. Focus on key insights and actionable takeaways.",
        stream=False,
    )
    return response["response"]
