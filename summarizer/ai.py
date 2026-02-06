from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import settings

llm = ChatOllama(
    model=settings.OLLAMA_MODEL,
    base_url=settings.OLLAMA_HOST,
)

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an expert content summarizer. "
            "Your goal is to provide a concise, structured summary of the provided text. "
            "Focus on key insights and actionable takeaways. "
            "Format the summary as bullet points.",
        ),
        ("human", "Please summarize the following text:\n\n{text}"),
    ]
)

chain = prompt | llm | StrOutputParser()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    reraise=True,
)
async def summarize_text(text: str) -> str:
    return await chain.ainvoke({"text": text})
