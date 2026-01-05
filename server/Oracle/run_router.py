# client.py
import asyncio
import websockets
from Oracle.parsing.router import Router
from Oracle.services.event_bus import EventBus

async def main():
    event_bus = EventBus()
    router = Router(event_bus)

    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        print("Connected to WS server")

        async for message in websocket:
            print("Received:", message)
            # message is a log line from WS server
            await router.feed_line(message)

            async for result in router.results():
                print("Parsed:", result)

if __name__ == "__main__":
    asyncio.run(main())
