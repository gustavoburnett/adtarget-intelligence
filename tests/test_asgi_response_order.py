"""Exercise the actual Streamlit middleware, including excluded/static media.

Starlette changes to its private responders must not send body before headers.
No live server, credentials, or application data needed.
"""
import asyncio
import gzip
import pytest
from streamlit.web.server.starlette.starlette_gzip_middleware import SelectiveGZipMiddleware

@pytest.mark.parametrize("encoding", [b"identity", b"gzip"])
@pytest.mark.parametrize("path,media,status", [
    ("/", b"text/html", 200),
    ("/static/app.js", b"application/javascript", 200),
    ("/favicon.png", b"image/png", 200),
    ("/media/test.wav", b"audio/wav", 200),
    ("/media/test.mp4", b"video/mp4", 206),
    ("/_stcore/health", b"text/plain", 200),
])
def test_response_start_precedes_body(encoding, path, media, status):
    body = b"response-content-" * 100
    messages = []
    async def endpoint(scope, receive, send):
        await send({"type": "http.response.start", "status": status,
                    "headers": [(b"content-type", media), (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})
    async def receive():
        return {"type": "http.request", "body": b""}
    async def send(message):
        if not messages:
            assert message["type"] == "http.response.start", "ASGI body before response headers"
        messages.append(message)
    scope = {"type": "http", "path": path, "headers": [(b"accept-encoding", encoding)]}
    asyncio.run(SelectiveGZipMiddleware(endpoint)(scope, receive, send))
    assert [m["type"] for m in messages] == ["http.response.start", "http.response.body"]
    headers = dict(messages[0]["headers"])
    actual = messages[1]["body"]
    if headers.get(b"content-encoding") == b"gzip":
        actual = gzip.decompress(actual)
    assert actual == body
    assert messages[0]["status"] == status
