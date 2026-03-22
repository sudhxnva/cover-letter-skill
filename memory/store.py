import os
import chromadb

# To use OpenAI embeddings instead:
# from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
# ef = OpenAIEmbeddingFunction(api_key=os.environ["OPENAI_API_KEY"], model_name="text-embedding-3-small")
# collection = client.get_or_create_collection("experiences", embedding_function=ef)

CHROMA_PATH = "memory/chroma"

_client = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=CHROMA_PATH)
        _collection = _client.get_or_create_collection("experiences")
    return _collection


def add_experience(entry: dict) -> str:
    """Store a new experience. Returns the id."""
    col = _get_collection()
    id_ = entry["id"]
    document = entry["refined"]
    metadata = {k: v for k, v in entry.items() if k not in ("id", "refined")}
    col.add(ids=[id_], documents=[document], metadatas=[metadata])
    return id_


def update_experience(id: str, updates: dict) -> None:
    """Update metadata fields on an existing experience."""
    col = _get_collection()
    col.update(ids=[id], metadatas=[updates])


def mark_used_in(id: str, company: str) -> None:
    """Append company to used_in field."""
    col = _get_collection()
    result = col.get(ids=[id], include=["metadatas"])
    if not result["ids"]:
        raise KeyError(f"No experience with id={id!r}")
    current = result["metadatas"][0].get("used_in", "")
    existing = [c for c in current.split(",") if c]
    if company not in existing:
        existing.append(company)
    col.update(ids=[id], metadatas=[{"used_in": ",".join(existing)}])


def get_experience(id: str) -> dict | None:
    """Retrieve a single experience by id."""
    col = _get_collection()
    result = col.get(ids=[id], include=["documents", "metadatas"])
    if not result["ids"]:
        return None
    return {"id": result["ids"][0], "refined": result["documents"][0], **result["metadatas"][0]}


# Similarity threshold for duplicate detection.
# Entries with similarity > this value are considered duplicates.
# Uses the same distance-to-similarity conversion as query.py: similarity = 1 - dist.
DUPLICATE_SIMILARITY_THRESHOLD = 0.90


def check_duplicate(entry: dict) -> dict | None:
    """
    Check whether a semantically similar experience already exists in the store.

    Queries ChromaDB using the candidate entry's `refined` text and returns the
    closest existing entry if its similarity exceeds DUPLICATE_SIMILARITY_THRESHOLD.

    Args:
        entry: The candidate experience dict (must have a "refined" key).

    Returns:
        The existing entry as a dict (same format as `get_experience`) if a
        duplicate is found, otherwise None.
    """
    col = _get_collection()
    # Guard: if the collection is empty, col.query will error on n_results > count.
    count = col.count()
    if count == 0:
        return None

    results = col.query(
        query_texts=[entry["refined"]],
        n_results=1,
        include=["documents", "metadatas", "distances"],
    )

    ids = results["ids"][0]
    if not ids:
        return None

    dist = results["distances"][0][0]
    similarity = 1 - dist

    if similarity > DUPLICATE_SIMILARITY_THRESHOLD:
        return {
            "id": ids[0],
            "refined": results["documents"][0][0],
            **results["metadatas"][0][0],
        }

    return None


def list_experiences() -> list[dict]:
    """Return all experiences as a list of dicts."""
    col = _get_collection()
    result = col.get(include=["documents", "metadatas"])
    return [
        {"id": id_, "refined": doc, **meta}
        for id_, doc, meta in zip(result["ids"], result["documents"], result["metadatas"])
    ]
