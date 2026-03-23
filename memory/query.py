import math
from datetime import datetime

from memory.store import _get_collection

OUTCOME_WEIGHTS = {1: 1.0, 0: 0.5, -1: 0.75}


def _recency_weight(date_str: str) -> float:
    year, month = map(int, date_str.split("-"))
    now = datetime.now()
    months_ago = (now.year - year) * 12 + (now.month - month)
    return math.exp(-0.05 * months_ago)


def _parse_list(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()] if value else []


def retrieve(jd_text: str, top_k: int = 5) -> list[dict]:
    """
    Query memory store for experiences relevant to the given JD text.

    Returns top_k experiences sorted by composite score, each as:
    {
        "id": str,
        "title": str,
        "refined": str,
        "raw": str,
        "type": str,
        "source": str,
        "themes": list[str],
        "impact": str,
        "relevance_signals": list[str],
        "used_in": list[str],
        "interview_led_to": int,
        "score": float,
        "similarity": float,
    }
    """
    col = _get_collection()
    results = col.query(
        query_texts=[jd_text],
        n_results=20,
        include=["documents", "metadatas", "distances"],
    )

    ids = results["ids"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    scored = []
    for id_, doc, meta, dist in zip(ids, documents, metadatas, distances):
        similarity = 1 - dist
        recency = _recency_weight(meta.get("date", "2000-01"))
        outcome_key = int(meta.get("interview_led_to", -1))
        outcome = OUTCOME_WEIGHTS.get(outcome_key, 0.75)

        composite = (similarity * 0.5) + (recency * 0.3) + (outcome * 0.2)

        scored.append({
            "id": id_,
            "title": meta.get("title", ""),
            "refined": doc,
            "raw": meta.get("raw", ""),
            "type": meta.get("type", ""),
            "source": meta.get("source", ""),
            "themes": _parse_list(meta.get("themes", "")),
            "impact": meta.get("impact", ""),
            "relevance_signals": _parse_list(meta.get("relevance_signals", "")),
            "used_in": _parse_list(meta.get("used_in", "")),
            "interview_led_to": outcome_key,
            "score": composite,
            "similarity": similarity,
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]
