from aiohttp import ClientSession
from asyncio import gather, run
from pathlib import Path
from PIL import Image
from io import BytesIO


BASE_JSONS_URL = "https://raw.communitydragon.org/json/latest/game/assets/loadouts/"
BASE_DOWNLOAD_URL = "https://raw.communitydragon.org/latest/game/assets/loadouts/"
DOWNLOAD_DIR = Path("assets/loadouts")

files_to_download = set()


# If its an directory we have go to inside it and get the files
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


async def download_file(session: ClientSession, relative_path: str):
    url = BASE_DOWNLOAD_URL + relative_path

    output_path = DOWNLOAD_DIR / relative_path.replace('.png', '.webp')

    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            data = await response.read()
        
        image = Image.open(BytesIO(data))

        output_path.parent.mkdir(parents=True, exist_ok=True)

        image.save(
            output_path,
            "WEBP",
            lossless=True
        )

    except Exception as e:
        print(f"Failed: {relative_path} -> {e}")


async def main():
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    async with ClientSession() as session:
        await get_files(session, "")

        print(f"Found {len(files_to_download)} files")

        await gather(*[
            download_file(session, file)
            for file in files_to_download
        ])

    print("Done!")


if __name__ == "__main__":
    run(main())