# src\study_assistant\tools\web_search_augment.py

from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from study_assistant.config import DB_PATH
from xaihandler.memorystore import MemoryStore
import urllib.parse
import requests
import difflib
import xml.etree.ElementTree as ET

class SearchEngine(Enum):
    """Free, keyless public endpoints only. Bob can reason over these names directly."""
    DUCKDUCKGO   = "https://api.duckduckgo.com/?q={query}&format=json"
    WIKIPEDIA    = "https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={query}&format=json&srwhat=text"
    ARXIV        = "http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results=5"
    SEMANTIC_SCHOLAR = "https://api.semanticscholar.org/graph/v1/paper/search?query={query}&limit=5"

    def build_url(self, query: str) -> str:
        encoded = urllib.parse.quote(query)
        return self.value.format(query=encoded)

class SearchResult(BaseModel):  # unchanged from previous
    title: str
    url: str
    snippet: str = Field(..., max_length=500)
    engine: str
    relevance: float = Field(..., ge=0, le=1)
    is_pdf: bool = False

class WebSearchAugmentResponse(BaseModel):  # unchanged
    queries_executed: List[str]
    results: List[SearchResult] = Field(..., max_items=12)
    graded_summary: str = Field(..., max_length=800)
    sources_count: int
    already_known: bool = False
    token_estimate: int
    error: Optional[str] = Field(None, description="Temporary failure message if any")

def _parse_response(engine: SearchEngine, resp: requests.Response) -> List[Dict]:
    """Updated parsers — handles XML for arXiv, stricter JSON."""
    hits = []
    if engine == SearchEngine.DUCKDUCKGO:
        data = resp.json()
        for r in data.get("RelatedTopics", [])[:3]:
            if "Text" in r:
                hits.append({"title": r.get("Text", ""), "url": r.get("FirstURL", ""), "snippet": r.get("Text", "")})
    elif engine == SearchEngine.WIKIPEDIA:
        data = resp.json()
        for r in data.get("query", {}).get("search", [])[:3]:
            title = r["title"]
            hits.append({"title": title, "url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}", "snippet": r.get("snippet", "")})
    elif engine == SearchEngine.ARXIV:
        root = ET.fromstring(resp.text)
        for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry")[:3]:
            title = entry.findtext(".//{http://www.w3.org/2005/Atom}title", "")
            url = entry.findtext(".//{http://www.w3.org/2005/Atom}id", "")
            snippet = entry.findtext(".//{http://www.w3.org/2005/Atom}summary", "")[:300]
            hits.append({"title": title, "url": url, "snippet": snippet})
    elif engine == SearchEngine.SEMANTIC_SCHOLAR:
        data = resp.json()
        for p in data.get("data", [])[:3]:
            hits.append({"title": p.get("title", ""), "url": p.get("url", ""), "snippet": p.get("abstract", "")[:300]})
    return hits

def search_augment(queries: List[str]) -> List[Dict]:
    """Single round-robin across the four engines defined in SearchEngine."""
    all_hits = []
    engines = list(SearchEngine)
    headers = {"User-Agent": "Mozilla/5.0 (compatible; xAI-Study-Assistant/1.0)"}
    for q in queries:
        for engine in engines:
            try:
                url = engine.build_url(q)
                resp = requests.get(url, timeout=5, headers=headers)
                resp.raise_for_status()
                parsed = _parse_response(engine, resp)  # now robust
                for item in parsed:
                    item["engine"] = engine.name
                    all_hits.append(item)
            except Exception as e:  # keep silent but collect once
                continue
    return all_hits[:30]

def web_search_augment(
    research_query: str,
    assignment_id: Optional[str] = None   # <-- now optional; Bob can omit
) -> Dict:
    # Step 1 – pre-check (handles both modes)

    
    # Step 2 – deterministic queries (unchanged)
    queries = [research_query, f"{research_query} scholarly", f"{research_query} review"]

    # Steps 3–4
    raw = search_augment(queries)

    # Step 5 – grade (unchanged)
    scored = []
    for item in raw:
        overlap = difflib.SequenceMatcher(None, research_query.lower(), (item.get("snippet") or "").lower()).ratio()
        academic_bonus = 0.3 if item.get("engine") in {"ARXIV", "SEMANTIC_SCHOLAR", "WIKIPEDIA"} else 0.0
        score = round(overlap * 0.7 + academic_bonus, 2)
        item["relevance"] = score
        item["is_pdf"] = item.get("url", "").lower().endswith(".pdf") or "arxiv" in item.get("url", "").lower()
        scored.append(item)
    scored.sort(key=lambda x: x["relevance"], reverse=True)
    top = scored[:8]

    error_msg = None
    if not top and raw:  # engines tried but nothing parsed
        error_msg = "Temporary search engine issue; results may appear on retry."

    summary_lines = []
    remaining_chars = 750

    for r in top: 
        engine = r.get("engine", "UNKNOWN")
        title = r.get("title", "Untitled")
        snippet = r.get("snippet", "")[:140]

        line = f"[{engine}] {title}: {snippet}..."
        line = line[:180]

        if len(line) <= remaining_chars: 
            summary_lines.append(line)
            remaining_chars -= len(line) + 1
        else: 
            break

    summary = "\n".join(summary_lines)

    if len(summary) > 750: 
        summary = summary[:747] + "..."

    if not summary and top: 
        summary = "High-relevance results found but summary generation truncated."

    error_msg = None
    if not top: 
        if raw: 
            error_msg = "Engines returned data but none passed relevance threshold."
        else: 
            error_msg = "No response from search engines."

    response = WebSearchAugmentResponse(
        queries_executed=queries,
        results=[SearchResult(**r) for r in top],
        graded_summary=summary,
        sources_count=len(top),
        token_estimate=len(summary) // 4 + 100,
        already_known=False,
        error=error_msg
    )

    if response.results or response.error:
        knowledge_key = f"knowledge:web:{research_query.lower()[:50]}"
        store = MemoryStore(db_path=str(DB_PATH))
        store.upsert_global(
            key=knowledge_key, 
            value=response.model_dump_json(), 
            tags=["type:web-research", knowledge_key, f"query:{research_query[:80]}"]
        )

    return response.model_dump()