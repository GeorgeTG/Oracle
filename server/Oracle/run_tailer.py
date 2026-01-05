import asyncio
from Oracle.parsing.utils.log_reader import LogReader

LOG_PATH = r"G:/SteamLibrary/steamapps/common/Torchlight Infinite/UE_game/TorchLight/Saved/Logs/UE_game.log"

async def main():
    print("📄 Starting LogReader test...")

    async with LogReader(LOG_PATH) as tail:
        async for line in tail:
            print(f"[TAIL] {line}")

if __name__ == "__main__":
    asyncio.run(main())
