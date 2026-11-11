from groq import Groq

from app.core.config import settings


# Create Groq API client
client = Groq(api_key=settings.groq_api_key)

MODEL_NAME = "openai/gpt-oss-120b"


def generate_answer(question: str, context: str) -> str:
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are CacheRAG, a document-based question-answering assistant. "
                    "Answer using ONLY the provided document context. "
                    "Do not invent facts. "
                    "If the context is insufficient, say: "
                    "'I could not find enough information in the selected "
                    "documents to answer this question.' "
                    "Include document names and page numbers when available."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"DOCUMENT CONTEXT:\n{context}\n\n"
                    f"USER QUESTION:\n{question}"
                ),
            },
        ],
    )

    answer = response.choices[0].message.content

    if not answer:
        raise RuntimeError("Groq returned an empty response.")

    return answer.strip()


def generate_web_answer(question: str) -> dict:
    """
    Generate an answer using Groq's built-in browser search
    and return the answer with structured web sources.
    """

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are CacheRAG, an assistant with web search access. "
                    "Search the internet for relevant information before "
                    "answering. Use reliable sources, prioritize recent "
                    "information when relevant, and do not invent facts. "
                    "Include source citations in your answer when available."
                ),
            },
            {
                "role": "user",
                "content": question,
            },
        ],
        tools=[
            {"type": "browser_search"}
        ],
        tool_choice="auto",
    )

    message = response.choices[0].message
    answer = message.content

    if not answer:
        raise RuntimeError("Groq returned an empty web-search response.")

    sources = []
    seen_urls = set()

    def add_source(title, url):
        if not url or url in seen_urls:
            return

        seen_urls.add(url)

        sources.append({
            "source_type": "web",
            "title": title or url,
            "url": url,
        })

    for tool in message.executed_tools or []:

        for result in tool.browser_results or []:
            add_source(result.title, result.url)

        if tool.search_results and tool.search_results.results:
            for result in tool.search_results.results:
                add_source(result.title, result.url)

    return {
        "answer": answer.strip(),
        "sources": sources,
    }

