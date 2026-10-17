"""Small process-local review store used when optional Mongo is not configured."""
from threading import RLock

_reviews: dict[str, dict] = {}
_saved: dict[str, dict] = {}
_lock = RLock()

def save_review(review: dict) -> dict:
    with _lock:
        _reviews[review["review_id"]] = review
    return review

def get_review(review_id: str):
    with _lock:
        return _reviews.get(review_id)

def list_reviews():
    with _lock:
        return list(reversed(list(_reviews.values())))

def save_pull_request(url: str):
    with _lock:
        if any(item["url"] == url for item in _saved.values()):
            return next(item for item in _saved.values() if item["url"] == url)
        import uuid
        item = {"saved_id": uuid.uuid4().hex, "url": url, "temporary": True}
        _saved[item["saved_id"]] = item
        return item

def list_saved():
    with _lock:
        return list(_saved.values())

def delete_saved(saved_id: str):
    with _lock:
        return _saved.pop(saved_id, None)
