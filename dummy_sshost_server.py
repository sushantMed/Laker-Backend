"""
Dummy SSHost server for local testing ONLY.

Speaks the same length-prefixed JSON protocol as app/services/sshost_client.py:
  request:  4-byte big-endian length + JSON body {"op", "username", "password"}
  response: 4-byte big-endian length + JSON body {"status": "SUCCESS" | "FAILED"}

Run:
    python dummy_sshost_server.py

Then point your app's settings at:
    sshost_host = "127.0.0.1"
    sshost_port = 9000

By default it returns SUCCESS for every request. To test the failure path,
pass a username containing "fail", e.g. "fail@example.com" -> returns FAILED.
To test the "SSHost unreachable" fallback path, just don't run this script
(or kill it) — your app's SSHostError / fallback-to-DB logic will fire.
"""

import asyncio
import contextlib
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("dummy_sshost")

HOST = "0.0.0.0"
PORT = 9000


async def _read_exact(reader: asyncio.StreamReader, n: int) -> bytes:
    return await reader.readexactly(n)


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    peer = writer.get_extra_info("peername")
    try:
        length_bytes = await _read_exact(reader, 4)
        length = int.from_bytes(length_bytes, byteorder="big")
        body = await _read_exact(reader, length)
        request = json.loads(body.decode("utf-8"))

        logger.info("Request from %s: %s", peer, request)

        username = request.get("username", "")
        status = "FAILED" if "fail" in username.lower() else "SUCCESS"

        response = {"status": status}
        response_bytes = json.dumps(response).encode("utf-8")
        writer.write(len(response_bytes).to_bytes(4, byteorder="big") + response_bytes)
        await writer.drain()

        logger.info("Responded to %s: %s", peer, response)

    except (asyncio.IncompleteReadError, json.JSONDecodeError) as e:
        logger.warning("Bad request from %s: %s", peer, e)
    finally:
        writer.close()
        with contextlib.suppress(Exception):
            await writer.wait_closed()


async def main():
    server = await asyncio.start_server(handle_client, HOST, PORT)
    logger.info("Dummy SSHost listening on %s:%s", HOST, PORT)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
