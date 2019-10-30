import asyncio
import contextlib
import json
import os
from concurrent.futures import ProcessPoolExecutor
from mimetypes import guess_all_extensions

import logging
import aiofiles
import aiohttp
from bs4 import BeautifulSoup, SoupStrainer

URL = "https://www.google.com/search?q={}&source=lnms&tbm=isch"
HEADERS = {
    "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"
}
VALID_IMAGE_EXTENSIONS = {"jpg", "png", "jpeg", "gif", "svg"}

def _parse_image_html(text, limit=15):
    only_image_info = SoupStrainer("div")
    soup = BeautifulSoup(text, "lxml", parse_only=only_image_info)
    return tuple(json.loads(str(info.string))["ou"] for info in soup.find_all(class_="rg_meta", limit=limit))

async def get_urls(keyword, limit=15, session=None, executor=None, logger=None):
    if logger is None:
        logger = logging
    logger.info("fetching image urls for " + keyword)
    async with contextlib.AsyncExitStack() as stack:
        if session is None:
            session = await stack.enter_async_context(aiohttp.ClientSession())
        if executor is None:
            executor = stack.enter_context(ProcessPoolExecutor(max_workers=1))
        async with session.get(URL, params={"q": keyword, "source": "lnms", "tbm": "isch"}, headers=HEADERS) as response:
            loop = asyncio.get_event_loop()
            #return _parse_image_html(await response.text(), limit)
            return await loop.run_in_executor(executor, _parse_image_html, await response.text(), limit)

async def _download_helper(path, url, session, logger=None):
    if logger is None:
        logger = logging
    logger.info("downloading image at " + url)
    try:
        async with session.get(url) as response:
            # from https://stackoverflow.com/questions/29674905/convert-content-type-header-into-file-extension
            try:
                content_type = response.headers['content-type'].partition(';')[0].strip()
            except KeyError:
                logger.warning(f"No content-type for {url}; extension cannot be detected.")
                return
            if content_type.partition("/")[0] == "image":
                extensions = guess_all_extensions(content_type)
                try:
                    ext = "." + (set(ext[1:] for ext in extensions).intersection(VALID_IMAGE_EXTENSIONS)).pop()
                except KeyError:
                    logger.warning(f"No valid extensions found for {url}. Extensions: {extensions}")
                    return
            
            else:
                logger.warning(f"Invalid content-type {content_type} for {url}")
                return
            
            filename = f"{path}{ext}"
            # from https://stackoverflow.com/questions/38358521/alternative-of-urllib-urlretrieve-in-python-3-5
            async with aiofiles.open(filename, 'wb') as out_file:
                block_size = 1024 * 8
                while True:
                    block = await response.content.read(block_size)  # pylint: disable=no-member
                    if not block:
                        break
                    await out_file.write(block)
            return filename
    except aiohttp.client_exceptions.ClientConnectionError as e:
        logger.exception(e)

async def download_images(directory, keyword, limit=15, session=None, executor=None, logger=None):
    if logger is None:
        logger = logging
    logger.info("fetching images for " + keyword)
    if not os.path.exists(directory):
        os.makedirs(directory)
    async with contextlib.AsyncExitStack() as stack:
        if session is None:
            session = await stack.enter_async_context(aiohttp.ClientSession())
        if executor is None:
            executor = stack.enter_context(ProcessPoolExecutor(max_workers=1))
        urls = await get_urls(keyword, limit, session, executor)
        paths = (_download_helper(f"{directory}/{i}", url, session, logger) for i, url in enumerate(urls))
        return await asyncio.gather(*(path for path in paths if path is not None))
