import asyncio
import schedule
import time
import re
import aiohttp
import json
from tqdm import tqdm
import os
import collections
import aiofiles

cwd = os.getcwd()
path = str(cwd) + "/" + "urls.json"
path_down = str(cwd) + "/" + "urls_down.json"


async def fetch_chapter_urls(session, url):
    async with session.get(url) as response:
        content = await response.text()
        urls = re.findall(r'href="([^"]*)"', content)
        
        chapters = []
        for url in urls:
            if "chapter" in url:
                chapter_num = re.findall(r'\d+', url)
                num = chapter_num[1]
                full_url = "https://tcbonepiecechapters.com" + url
                chapters.append((num, full_url))
        
        return chapters

async def process_chapter(session, num, url):
    async with session.get(url) as response:
        content = await response.text()
        image_urls = re.findall(r'https:\/\/cdn\.onepiecechapters\.com\/file[^"]*', content)
        return (num, image_urls)

async def get_initial_urls():
    all_urls = {}
    async with aiohttp.ClientSession() as session:
        main_url = "https://tcbonepiecechapters.com/mangas/5/one-piece"
        chapters = await fetch_chapter_urls(session, main_url)
        
        pbar = tqdm(total=len(chapters), desc="Processing chapters", unit="chapter")
        
        tasks = [process_chapter(session, num, url) for num, url in chapters]
        for task in asyncio.as_completed(tasks):
            num, urls = await task
            all_urls[num] = urls
            pbar.update(1)
            pbar.set_postfix_str(f"Chapter {num}")
        
        pbar.close()
        

        with open(path, "w") as f:
            json.dump(all_urls, f, indent=2)
        
        print(f"\nSuccessfully saved {len(all_urls)} chapters to {path}")

async def download_image(session, url, chapter_path, index, pbar):
    filename = f"{index:03d}.png"
    filepath = os.path.join(chapter_path, filename)
    try:
        async with session.get(url) as response:
            if response.status == 200:
                content = await response.read()
                async with aiofiles.open(filepath, 'wb') as f:
                    await f.write(content)
                pbar.update(1)
                return True
            else:
                print(f"Failed to download {url}: HTTP status {response.status}")
                return False
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

async def fetch_chapter(session, chapter_urls, chapter_num, pbar, base_path, downloaded_path):
    async with aiofiles.open(downloaded_path, 'r') as f:
        content = await f.read()
        downloaded = json.loads(content) if content.strip() else []
    if chapter_num in downloaded:
        return

    chapter_path = os.path.join(base_path, chapter_num)
    os.makedirs(chapter_path, exist_ok=True)

    tasks = []
    for idx, url in enumerate(chapter_urls):
        tasks.append(download_image(session, url, chapter_path, idx, pbar))
    results = await asyncio.gather(*tasks)

    if all(results):
        async with aiofiles.open(downloaded_path, 'r') as f:
            content = await f.read()
            downloaded = json.loads(content) if content.strip() else []
        if chapter_num not in downloaded:
            downloaded.append(chapter_num)
            async with aiofiles.open(downloaded_path, 'w') as f:
                await f.write(json.dumps(downloaded))
    else:
        print(f"Chapter {chapter_num} had errors; not marked as completed.")

async def download_all_chapters():
    urls_path = "urls.json"
    downloaded_path = "downloaded.json"
    download_base_path = "downloads"
    if not os.path.exists(downloaded_path):
        async with aiofiles.open(downloaded_path, 'w') as f:
            await f.write(json.dumps([]))

    with open(urls_path, 'r') as f:
        chapters = json.load(f)

    async with aiofiles.open(downloaded_path, 'r') as f:
        content = await f.read()
        downloaded = json.loads(content) if content.strip() else []

    total_images = sum(len(urls) for ch, urls in chapters.items() if ch not in downloaded)
    
    with tqdm(total=total_images, desc="Downloading chapters") as pbar:
        async with aiohttp.ClientSession() as session:
            for ch_num, urls in chapters.items():
                if ch_num in downloaded:
                    continue
                await fetch_chapter(session, urls, ch_num, pbar, download_base_path, downloaded_path)

def run_tasks():
    asyncio.run(get_initial_urls())
    asyncio.run(download_all_chapters())

schedule.every().day.at("04:00").do(run_tasks)

if __name__ == "__main__":
    asyncio.run(get_initial_urls())
    asyncio.run(download_all_chapters())
    while True:
        schedule.run_pending()
