"""Optional MongoDB connectivity. Demo operation does not require this module."""
from __future__ import annotations
import os

_client = None

def connect():
    global _client
    uri = os.getenv("MONGODB_URI")
    if not uri:
        return None
    try:
        from pymongo import MongoClient
    except ImportError as exc:
        raise RuntimeError("MongoDB is configured but pymongo is not installed.") from exc
    _client = MongoClient(uri, serverSelectionTimeoutMS=3000, connectTimeoutMS=3000)
    _client.admin.command("ping")
    return _client[os.getenv("MONGODB_DATABASE", "pr_mentor")]

def close():
    global _client
    if _client is not None:
        _client.close()
        _client = None

def is_ready() -> bool:
    if not os.getenv("MONGODB_URI"):
        return True
    if _client is None:
        return False
    try:
        _client.admin.command("ping")
        return True
    except Exception:
        return False
