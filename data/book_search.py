from __future__ import annotations

import json
import urllib.parse
import urllib.request


def search_open_library(query: str, limit: int = 8) -> list[dict]:
    url = "https://openlibrary.org/search.json?" + urllib.parse.urlencode(
        {"q": query, "limit": limit}
    )
    with urllib.request.urlopen(url, timeout=5) as response:
        data = json.loads(response.read().decode("utf-8"))

    results = []
    for doc in data.get("docs", []):
        results.append(
            {
                "title": doc.get("title", ""),
                "author": ", ".join(doc.get("author_name", [])) or None,
                "pages": doc.get("number_of_pages_median"),
            }
        )
    return results
