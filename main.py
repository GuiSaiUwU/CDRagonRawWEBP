from aiohttp import ClientSession
from asyncio import Semaphore, gather, to_thread
from pathlib import Path
from PIL import Image
from io import BytesIO

BASE_JSONS_URL = "https://raw.communitydragon.org/json/latest/game/assets/loadouts/"
BASE_DOWNLOAD_URL = "https://raw.communitydragon.org/latest/game/assets/loadouts/"
DOWNLOAD_DIR = Path("assets/loadouts")
MAX_CONCURRENT = 20

files_to_download = set()


async def get_files(session: ClientSession, path: str):
    url = BASE_JSONS_URL + path
    async with session.get(url) as response:
        data = await response.json()
        files = [f for f in data if f["type"] == "file"]
        files_to_download.update(
            path + f["name"] for f in files
            if not 'particles' in (path + f["name"])
            and (path + f["name"]).endswith('.png')
        )

        directories = [d for d in data if d["type"] == "directory"]
        if directories:
            await gather(*[get_files(session, path + d["name"] + "/") for d in directories])


def _sync_convert(data: bytes, output_path: Path):
    image = Image.open(BytesIO(data))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, "WEBP", quality=85, method=6)


async def download_file(session: ClientSession, sem: Semaphore, relative_path: str):
    output_path = DOWNLOAD_DIR / relative_path.replace(".png", ".webp")
    if output_path.exists():
        return # lol wtf?
    
    async with sem:
        url = BASE_DOWNLOAD_URL + relative_path
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.read()
            
            # Idk seems sus
            await to_thread(_sync_convert, data, output_path)
        except Exception as e:
            print(f"Failed: {relative_path} -> {e}")


async def main():
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    sem = Semaphore(MAX_CONCURRENT)

    async with ClientSession() as session:
        await get_files(session, "")
        print(f"Found {len(files_to_download)} files")

        tasks = [download_file(session, sem, f) for f in files_to_download]
        await gather(*tasks)

    print("Done!")


if __name__ == "__main__":
    try:
        from uvloop import run
        run(main())

    except ImportError as e:
        from asyncio import run
        run(main())