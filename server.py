import aiohttp
import asyncio
import re
import json
from tqdm import tqdm
import os
import collections
import aiofiles
from flask import Flask, render_template_string, jsonify, request, send_from_directory
import os



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

app = Flask(__name__)

DOWNLOADS_FOLDER = os.path.join(os.getcwd(), "downloads")

def get_chapters():
    """Return a sorted list of chapter numbers (as integers) from the downloads folder."""
    chapters = []
    if os.path.exists(DOWNLOADS_FOLDER):
        for d in os.listdir(DOWNLOADS_FOLDER):
            path = os.path.join(DOWNLOADS_FOLDER, d)
            if os.path.isdir(path):
                try:
                    chapters.append(int(d))
                except ValueError:
                    continue
    chapters.sort()
    return chapters

def get_images_in_chapter(chapter):
    """Return a sorted list of PNG filenames in the chapter directory."""
    chapter_dir = os.path.join(DOWNLOADS_FOLDER, str(chapter))
    if not os.path.isdir(chapter_dir):
        return []
    return sorted([f for f in os.listdir(chapter_dir) if f.endswith('.png')])

@app.route('/')
def index():
    chapters = get_chapters()
    start_chapter = chapters[0] if chapters else 0
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
  <title>Image Viewer</title>
  <style>
    body { margin: 0; padding: 0; }
    img { display: block; margin: auto; max-width: 100%; }
  </style>
</head>
<body>
  <div id="image-container"></div>
  <script>
    // Start with the first chapter and image index 0.
    let chapter = {{ start_chapter }};
    let start = 0;
    const count = 5; // load 5 images at a time

    function loadImages() {
      fetch(`/load_images?chapter=${chapter}&start=${start}&count=${count}`)
        .then(response => response.json())
        .then(data => {
          data.images.forEach(function(item) {
            // Create an img element with lazy loading enabled
            let img = document.createElement("img");
            img.src = `/chapter_image/${item.chapter}/${item.filename}`;
            img.loading = 'lazy';
            document.getElementById("image-container").appendChild(img);
          });
          // Update pointers for the next batch
          if (data.next_chapter !== null) {
            chapter = data.next_chapter;
            start = data.next_start;
          }
        });
    }

    // Initial load of images
    loadImages();

    // Infinite scroll: load more when near the bottom of the page
    window.addEventListener('scroll', () => {
      if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 100) {
        loadImages();
      }
    });
  </script>
</body>
</html>
''', start_chapter=start_chapter)

@app.route('/load_images')
def load_images():
    chapter = request.args.get('chapter', type=int)
    start = request.args.get('start', type=int)
    count = request.args.get('count', type=int)
    chapters = get_chapters()
    if chapter not in chapters:
        return jsonify({"images": [], "next_chapter": None, "next_start": 0})
    
    current_index = chapters.index(chapter)
    images = []
    remaining = count
    current_chapter = chapter
    current_start = start

    while remaining > 0 and current_index < len(chapters):
        imgs = get_images_in_chapter(chapters[current_index])
        if current_start >= len(imgs):
            current_index += 1
            if current_index < len(chapters):
                current_chapter = chapters[current_index]
                current_start = 0
            continue
        take = imgs[current_start: current_start + remaining]
        for filename in take:
            images.append({"chapter": chapters[current_index], "filename": filename})
        num_taken = len(take)
        remaining -= num_taken
        current_start += num_taken
        if current_start >= len(imgs):
            current_index += 1
            if current_index < len(chapters):
                current_chapter = chapters[current_index]
                current_start = 0
    next_chapter = chapters[current_index] if current_index < len(chapters) else None
    return jsonify({"images": images, "next_chapter": next_chapter, "next_start": current_start})

@app.route('/chapter_image/<chapter>/<filename>')
def chapter_image(chapter, filename):
    return send_from_directory(os.path.join(DOWNLOADS_FOLDER, chapter), filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=1234, debug=True)
