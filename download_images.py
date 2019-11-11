import asyncio
import contextlib
import copy
import itertools
import json
import logging
import os
from concurrent.futures import ProcessPoolExecutor

import aiofiles
import aiohttp
import magic
from bs4 import BeautifulSoup, SoupStrainer

GOOGLE_URL = "https://www.google.com/search?q={}&source=lnms&tbm=isch"
GOOGLE_HEADERS = {
    "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"
}
VALID_IMAGE_EXTENSIONS = {"jpg", "png", "jpeg", "gif", "svg"}

IDIGBIO_JSON_URL = "https://search.idigbio.org/v2/search/records/"
IDIGBIO_JSON_REQUEST_PARAMS = {
    "rq": {
        "genus": "",
        "hasImage": True
    },
    "sort": [{
        "genus": "asc"
    }, {
        "specificepithet": "asc"
    }, {
        "datecollected": "asc"
    }],
    "limit": 0,
    "offset": 100
}
IDIGBIO_IMAGE_BASE_URL = "https://api.idigbio.org/v2/media/"

async def get_idigbio_urls(keyword, limit=15, session=None, executor=None, logger=None):
    #executor is ignored to match get_google_images' signature
    if logger is None:
        logger = logging
    logger.info("fetching image urls for " + keyword)
    async with contextlib.AsyncExitStack() as stack:
        if session is None:
            session = await stack.enter_async_context(aiohttp.ClientSession())
        request_params = copy.deepcopy(IDIGBIO_JSON_REQUEST_PARAMS)
        request_params["rq"]["genus"] = keyword
        request_params["limit"] = limit
        async with session.post(IDIGBIO_JSON_URL, json=request_params) as response:
            data = await response.json()
            urls = itertools.chain.from_iterable(
                (IDIGBIO_IMAGE_BASE_URL + suffix for suffix in item["indexTerms"]["mediarecords"]) for item in data["items"]
            )
            return itertools.islice(urls, limit)

def _parse_image_html(text, limit=15):
    only_image_info = SoupStrainer("div")
    soup = BeautifulSoup(text, "lxml", parse_only=only_image_info)
    return tuple(json.loads(str(info.string))["ou"] for info in soup.find_all(class_="rg_meta", limit=limit))

async def get_google_urls(keyword, limit=15, session=None, executor=None, logger=None):
    if logger is None:
        logger = logging
    logger.info("fetching image urls for " + keyword)
    async with contextlib.AsyncExitStack() as stack:
        if session is None:
            session = await stack.enter_async_context(aiohttp.ClientSession())
        if executor is None:
            executor = stack.enter_context(ProcessPoolExecutor(max_workers=1))
        async with session.get(
            GOOGLE_URL, params={
                "q": keyword,
                "source": "lnms",
                "tbm": "isch"
            }, headers=GOOGLE_HEADERS
        ) as response:
            loop = asyncio.get_event_loop()
            #return _parse_image_html(await response.text(), limit)
            return await loop.run_in_executor(executor, _parse_image_html, await response.text(), limit)

async def _download_helper(path, url, session, logger=None):
    if logger is None:
        logger = logging
    logger.info("downloading image at " + url)
    try:
        async with session.get(url) as response:
            # from https://stackoverflow.com/questions/38358521/alternative-of-urllib-urlretrieve-in-python-3-5
            async with aiofiles.open(path, 'wb') as out_file:
                block_size = 1024 * 8
                while True:
                    block = await response.content.read(block_size)  # pylint: disable=no-member
                    if not block:
                        break
                    await out_file.write(block)
            ext = magic.from_file(path, mime=True).partition("/")[2]
            if ext not in VALID_IMAGE_EXTENSIONS:
                logger.error(f"Invalid Extension {ext} for {url}")
                return
            new_path = f"{path}.{ext}"
            os.rename(path, new_path)
            return new_path
    except aiohttp.client_exceptions.ClientConnectionError as e:
        logger.exception(e)

async def download_images(directory, keyword, limit=10, session=None, executor=None, logger=None, use_google_images=True):
    if use_google_images:
        get_urls = get_google_urls
    else:
        get_urls = get_idigbio_urls
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

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(download_images("download", "Exogyra", use_google_images=False))
