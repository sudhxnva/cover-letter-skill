from .store import _get_collection


def record_outcome(company: str, got_interview: bool) -> list[str]:
    """
    Update interview_led_to on all experiences used for the given company.

    Finds experiences where company appears in used_in (case-insensitive).
    Updates interview_led_to: 1 if got_interview else 0.
    Returns list of experience ids that were updated.
    """
    col = _get_collection()
    result = col.get(include=["metadatas"])
    if not result["ids"]:
        return []

    company_lower = company.lower()
    matched_ids = []
    for id_, meta in zip(result["ids"], result["metadatas"]):
        used_in = meta.get("used_in", "")
        companies = [c.strip().lower() for c in used_in.split(",") if c.strip()]
        if any(company_lower in c or c in company_lower for c in companies):
            matched_ids.append(id_)

    if not matched_ids:
        return []

    outcome = 1 if got_interview else 0
    for id_ in matched_ids:
        col.update(ids=[id_], metadatas=[{"interview_led_to": outcome}])

    return matched_ids


def record_outcome_for_ids(ids: list[str], got_interview: bool) -> None:
    """
    Update interview_led_to on specific experience ids.
    For when the caller knows exactly which experiences were used.
    """
    col = _get_collection()
    outcome = 1 if got_interview else 0
    for id_ in ids:
        col.update(ids=[id_], metadatas=[{"interview_led_to": outcome}])


def get_outcome_stats() -> dict:
    """
    Return aggregate outcome stats across all experiences.
    """
    col = _get_collection()
    result = col.get(include=["metadatas"])

    total = len(result["ids"])
    positive = 0
    negative = 0
    unknown = 0

    for meta in result["metadatas"]:
        val = meta.get("interview_led_to", -1)
        if val == 1:
            positive += 1
        elif val == 0:
            negative += 1
        else:
            unknown += 1

    return {
        "total": total,
        "with_outcome": positive + negative,
        "positive": positive,
        "negative": negative,
        "unknown": unknown,
    }
