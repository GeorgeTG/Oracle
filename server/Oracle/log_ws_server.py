import asyncio
import os
from pathlib import Path

import websockets

from Oracle.tooling.config import Config

# -------------------------------------------------
# 1. Load config
# -------------------------------------------------
config = Config()

parser_config = config.get("parser")
LOG_PATH = Path(parser_config["log_path"])

ws_config = config.get("websocket")
WS_HOST = ws_config.get("host", "127.0.0.1")
WS_PORT = int(ws_config.get("port", 8765))

# -------------------------------------------------
# 2. Global set of connected websocket clients
# -------------------------------------------------
connected_clients = set()


async def log_tail_producer(queue: asyncio.Queue):
    """
    Simple tail-follower for the log.
    Reads new lines and pushes them to asyncio.Queue.
    """
    # Wait for file to exist
    while not LOG_PATH.exists():
        print(f"[log-tail] Waiting for log file: {LOG_PATH}")
        await asyncio.sleep(2)

    print(f"[log-tail] Following log: {LOG_PATH}")

    with open(LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
        # Seek to end to avoid sending the entire old log
        f.seek(0, os.SEEK_END)

        while True:
            line = f.readline()
            if not line:
                # No new line, short sleep
                await asyncio.sleep(0.1)
                continue

            line = line.rstrip("\r\n")
            print(line)
            if line:
                await queue.put(line)


async def broadcaster(queue: asyncio.Queue):
    """
    Παίρνει γραμμές από την ουρά και τις στέλνει σε όλους τους clients.
    """
    while True:
        line = await queue.get()
        if not connected_clients:
            # κανένας client, απλά συνέχισε
            continue

        dead_clients = set()
        msg = line

        for ws in connected_clients:
            try:
                await ws.send(msg)
            except Exception as e:
                print(f"[broadcaster] client error: {e}")
                dead_clients.add(ws)

        # Καθαρισμός dead clients
        for ws in dead_clients:
            connected_clients.discard(ws)


async def ws_handler(websocket):
    """
    Handler για κάθε νέο WebSocket client.
    """
    print(f"[ws] client connected: {websocket.remote_address}")
    connected_clients.add(websocket)
    try:
        # Αν θες να λαμβάνεις μηνύματα από client, κάνε loop εδώ.
        async for _ in websocket:
            # Προς το παρόν αγνοούμε input, είμαστε μόνο broadcast.
            pass
    finally:
        print(f"[ws] client disconnected: {websocket.remote_address}")
        connected_clients.discard(websocket)


async def main():
    queue = asyncio.Queue()

    # Task που ακολουθεί το log
    tail_task = asyncio.create_task(log_tail_producer(queue))

    # Task που κάνει broadcast
    broad_task = asyncio.create_task(broadcaster(queue))

    # WebSocket server
    server = await websockets.serve(ws_handler, WS_HOST, WS_PORT)
    async with server:
        print(f"[ws] Server listening on ws://{WS_HOST}:{WS_PORT}")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exiting...")
