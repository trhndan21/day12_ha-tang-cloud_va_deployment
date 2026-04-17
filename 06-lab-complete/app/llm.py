from openai import OpenAI
from .config import settings

# Initialize OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)

def ask_llm(question: str, history: list = None) -> str:
    """
    Call the real OpenAI LLM.
    Supports conversation history for multi-turn conversations.
    """
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant deployed in production."}
    ]

    # Add conversation history if provided
    if history:
        messages.extend(history)

    # Add the current user question
    messages.append({"role": "user", "content": question})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=512,
        temperature=0.7,
    )

    return response.choices[0].message.content
