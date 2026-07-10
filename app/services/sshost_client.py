"""
SSHost (ScreenServer) TCP client.

Client Portal opens a TCP socket to SSHost,
sends a login request, receives Login Successful/Failed, then closes the
socket — one request/response per connection.

IMPORTANT: This client does not directly validate against Oracle/Postgres.
It simply forwards credentials to the external SSHOST/ScreenServer service.
Local DB password validation remains a fallback inside `auth_service.py`.

NOTE: The wire protocol below (length-prefixed JSON) is a placeholder.
Once the real request/response format with the SSHost owner is confirmed we will
update `_encode` / `_decode` accordingly.
"""
import asyncio
import json
import logging

from app.core.config import settings
from app.core.exceptions import SSHostError

logger = logging.getLogger("sshost_client")

CONNECT_TIMEOUT = 5.0
RESPONSE_TIMEOUT = 5.0


def _encode(payload: dict) -> bytes:
    body = json.dumps(payload).encode("utf-8")
    length = len(body).to_bytes(4, byteorder="big")
    return length + body


async def _decode(reader: asyncio.StreamReader) -> dict:
    length_bytes = await reader.readexactly(4)
    length = int.from_bytes(length_bytes, byteorder="big")
    body = await reader.readexactly(length)
    return json.loads(body.decode("utf-8"))


async def authenticate_user(username: str, password: str) -> bool:
    """
    Opens a TCP connection to SSHost, sends the login request, reads the
    Login Successful / Failed response, and closes the socket.

    Returns True on success, False on failed credentials.
    Raises SSHostError if SSHost is unreachable or responds unexpectedly.
    """
    request = {
        "op": "AUTHENTICATE_USER",
        "username": username,
        "password": password,
    }

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(settings.sshost_host, settings.sshost_port),
            timeout=CONNECT_TIMEOUT,
        )
    except (OSError, asyncio.TimeoutError) as e:
        logger.error("Could not connect to SSHost: %s", e)
        raise SSHostError("SSHost unreachable") from e

    try:
        writer.write(_encode(request))
        await writer.drain()

        response = await asyncio.wait_for(_decode(reader), timeout=RESPONSE_TIMEOUT)

    except (OSError, asyncio.TimeoutError, json.JSONDecodeError) as e:
        logger.error("SSHost communication error: %s", e)
        raise SSHostError("SSHost response error") from e
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass

    status = response.get("status")
    if status == "SUCCESS":
        return True
    if status == "FAILED":
        return False

    raise SSHostError(f"Unexpected SSHost response: {response}")