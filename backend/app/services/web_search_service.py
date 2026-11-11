
import logging

from ddgs import DDGS

logger = logging.getLogger(__name__)


def search_web(query: str, max_results: int = 5) -> list[dict]:
    """
    Search external information using the Wikipedia backend.

    Returns:
        A list of results containing title, url, and content.
    """

    try:
        with DDGS() as ddgs:
            results = ddgs.text(
                query,
                max_results=max_results,
                backend="wikipedia",
            )

        return [
            {
                "title": result.get("title", ""),
                "url": result.get("href", ""),
                "content": result.get("body", ""),
            }
            for result in results
        ]

    except Exception:
        logger.exception("External web search failed")
        return []
