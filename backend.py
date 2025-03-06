import asyncio
import schedule
import time
from server import get_initial_urls, download_all_chapters

def run_tasks():
    asyncio.run(get_initial_urls())
    asyncio.run(download_all_chapters())

schedule.every().day.at("04:00").do(run_tasks)

if __name__ == "__main__":
    asyncio.run(get_initial_urls())
    asyncio.run(download_all_chapters())
    while True:
        schedule.run_pending()
