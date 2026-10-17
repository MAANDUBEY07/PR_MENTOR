import asyncio
import pytest
import httpx
from app.main import app
from app.database import reviews

@pytest.fixture
def client():
    with reviews._lock:
        reviews._reviews.clear()
        reviews._saved.clear()
    class Client:
        def request(self, method, url, **kwargs):
            async def send():
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as session:
                    return await session.request(method, url, **kwargs)
            return asyncio.run(send())
        def get(self, url, **kwargs): return self.request("GET", url, **kwargs)
        def post(self, url, **kwargs): return self.request("POST", url, **kwargs)
        def delete(self, url, **kwargs): return self.request("DELETE", url, **kwargs)
    yield Client()
