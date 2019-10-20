# functions.py | function definitions
# Copyright (C) 2019  EraserBird, person_v1.32, hmmm

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import asyncio
import contextlib
import difflib
import os
import string
import urllib.parse
from functools import partial
from io import BytesIO
from mimetypes import guess_all_extensions, guess_extension

import aiohttp
import discord
from google_images_download import google_images_download

from data.data import (GenericError, database, logger, fossils_list)

google_images = google_images_download.googleimagesdownload()
TAXON_CODE_URL = "https://search.macaulaylibrary.org/api/v1/find/taxon?q={}"
CATALOG_URL = (
    "https://search.macaulaylibrary.org/catalog.json?searchField=species" +
    "&taxonCode={}&count={}&mediaType={}&sex={}&age={}&behavior={}&qua=3,4,5"
)
SCINAME_URL = "https://api.ebird.org/v2/ref/taxonomy/ebird?fmt=json&species={}"
COUNT = 20  # set this to include a margin of error in case some urls throw error code 476 due to still being processed

# Valid file types
valid_image_extensions = {"jpg", "png", "jpeg", "gif"}
valid_audio_extensions = {"mp3"}

# sets up new channel
async def channel_setup(ctx):
    logger.info("checking channel setup")
    if database.exists(f"channel:{str(ctx.channel.id)}"):
        logger.info("channel data ok")
    else:
        database.hmset(
            f"channel:{str(ctx.channel.id)}", {
                "bird": "",
                "answered": 1,
                "sBird": "",
                "sAnswered": 1,
                "goatsucker": "",
                "gsAnswered": 1,
                "prevJ": 20,
                "prevB": "",
                "prevS": "",
                "prevK": 20
            }
        )
        # true = 1, false = 0, index 0 is last arg, prevJ is 20 to define as integer
        logger.info("channel data added")
        await ctx.send("Ok, setup! I'm all ready to use!")
    
    if database.zscore("score:global", str(ctx.channel.id)) is not None:
        logger.info("channel score ok")
    else:
        database.zadd("score:global", {str(ctx.channel.id): 0})
        logger.info("channel score added")

# sets up new user
async def user_setup(ctx):
    logger.info("checking user data")
    if database.zscore("users:global", str(ctx.author.id)) is not None:
        logger.info("user global ok")
    else:
        database.zadd("users:global", {str(ctx.author.id): 0})
        logger.info("user global added")
        await ctx.send("Welcome <@" + str(ctx.author.id) + ">!")
    
    if ctx.guild is not None:
        logger.info("no dm")
        if database.zscore(f"users.server:{ctx.guild.id}", str(ctx.author.id)) is not None:
            server_score = database.zscore(f"users.server:{ctx.guild.id}", str(ctx.author.id))
            global_score = database.zscore("users:global", str(ctx.author.id))
            if server_score is global_score:
                logger.info("user server ok")
            else:
                database.zadd(f"users.server:{ctx.guild.id}", {str(ctx.author.id): global_score})
        else:
            score = int(database.zscore("users:global", str(ctx.author.id)))
            database.zadd(f"users.server:{ctx.guild.id}", {str(ctx.author.id): score})
            logger.info("user server added")
    else:
        logger.info("dm context")

# sets up new birds
async def bird_setup(ctx, bird):
    logger.info("checking bird data")
    if database.zscore("incorrect:global", string.capwords(str(bird))) is not None:
        logger.info("bird global ok")
    else:
        database.zadd("incorrect:global", {string.capwords(str(bird)): 0})
        logger.info("bird global added")
    
    if database.zscore(f"incorrect.user:{ctx.author.id}", string.capwords(str(bird))) is not None:
        logger.info("bird user ok")
    else:
        database.zadd(f"incorrect.user:{ctx.author.id}", {string.capwords(str(bird)): 0})
        logger.info("bird user added")
    
    if ctx.guild is not None:
        logger.info("no dm")
        if database.zscore(f"incorrect.server:{ctx.guild.id}", string.capwords(str(bird))) is not None:
            logger.info("bird server ok")
        else:
            database.zadd(f"incorrect.server:{ctx.guild.id}", {string.capwords(str(bird)): 0})
            logger.info("bird server added")
    else:
        logger.info("dm context")

# Function to run on error
def error_skip(ctx):
    logger.info("ok")
    database.hset(f"channel:{str(ctx.channel.id)}", "bird", "")
    database.hset(f"channel:{str(ctx.channel.id)}", "answered", "1")

def error_skip_song(ctx):
    logger.info("ok")
    database.hset(f"channel:{str(ctx.channel.id)}", "sBird", "")
    database.hset(f"channel:{str(ctx.channel.id)}", "sAnswered", "1")

def error_skip_goat(ctx):
    logger.info("ok")
    database.hset(f"channel:{str(ctx.channel.id)}", "goatsucker", "")
    database.hset(f"channel:{str(ctx.channel.id)}", "gsAnswered", "1")

# fetch scientific name from common name or taxon code
async def get_sciname(bird, session=None):
    logger.info(f"getting sciname for {bird}")
    async with contextlib.AsyncExitStack() as stack:
        if session is None:
            session = await stack.enter_async_context(aiohttp.ClientSession())
        try:
            code = await get_taxon(bird, session)
        except GenericError as e:
            if e.code == 111:
                code = bird
            else:
                raise
        
        sciname_url = SCINAME_URL.format(urllib.parse.quote(code))
        async with session.get(sciname_url) as sciname_response:
            if sciname_response.status != 200:
                raise GenericError(
                    f"An http error code of {sciname_response.status} occured" + f" while fetching {sciname_url} for {code}",
                    code=201
                )
            sciname_data = await sciname_response.json()
            try:
                sciname = sciname_data[0]["sciName"]
            except IndexError:
                raise GenericError(f"No sciname found for {code}", code=111)
    logger.info(f"sciname: {sciname}")
    return sciname

# fetch taxonomic code from common/scientific name
async def get_taxon(bird, session=None):
    logger.info(f"getting taxon code for {bird}")
    async with contextlib.AsyncExitStack() as stack:
        if session is None:
            session = await stack.enter_async_context(aiohttp.ClientSession())
        taxon_code_url = TAXON_CODE_URL.format(urllib.parse.quote(bird.replace("-", " ").replace("'s", "")))
        async with session.get(taxon_code_url) as taxon_code_response:
            if taxon_code_response.status != 200:
                raise GenericError(
                    f"An http error code of {taxon_code_response.status} occured" +
                    f" while fetching {taxon_code_url} for {bird}",
                    code=201
                )
            taxon_code_data = await taxon_code_response.json()
            try:
                logger.info(f"raw data: {taxon_code_data}")
                taxon_code = taxon_code_data[0]["code"]
                logger.info(f"first item: {taxon_code_data[0]}")
                if len(taxon_code_data) > 1:
                    logger.info("entering check")
                    for item in taxon_code_data:
                        logger.info(f"checking: {item}")
                        if spellcheck(item["name"].split(" - ")[0], bird, 6) or spellcheck(item["name"].split(" - ")[1], bird, 6):
                            logger.info("ok")
                            taxon_code = item["code"]
                            break
                        logger.info("fail")
            except IndexError:
                raise GenericError(f"No taxon code found for {bird}", code=111)
    logger.info(f"taxon code: {taxon_code}")
    return taxon_code

def session_increment(ctx, item, amount):
    logger.info(f"incrementing {item} by {amount}")
    value = int(database.hget(f"session.data:{ctx.author.id}", item))
    value += int(amount)
    database.hset(f"session.data:{ctx.author.id}", item, str(value))

def incorrect_increment(ctx, bird, amount):
    logger.info(f"incrementing incorrect {bird} by {amount}")
    database.zincrby("incorrect:global", amount, str(bird))
    database.zincrby(f"incorrect.user:{ctx.author.id}", amount, str(bird))
    if ctx.guild is not None:
        logger.info("no dm")
        database.zincrby(f"incorrect.server:{ctx.guild.id}", amount, str(bird))
    else:
        logger.info("dm context")

def score_increment(ctx, amount):
    logger.info(f"incrementing score by {amount}")
    database.zincrby("score:global", amount, str(ctx.channel.id))
    database.zincrby("users:global", amount, str(ctx.author.id))
    if ctx.guild is not None:
        logger.info("no dm")
        database.zincrby(f"users.server:{ctx.guild.id}", amount, str(ctx.author.id))
    else:
        logger.info("dm context")

def owner_check(ctx):
    owners = set(str(os.getenv("ids")).split(","))
    return str(ctx.message.author.id) in owners

# Gets a bird picture and sends it to user:
# ctx - context for message (discord thing)
# bird - bird picture to send (str)
# on_error - function to run when an error occurs (function)
# message - text message to send before bird picture (str)
async def send_bird(ctx, bird, on_error=None, message=None):
    if bird == "":
        logger.error("error - bird is blank")
        await ctx.send("**There was an error fetching birds.**\n*Please try again.*")
        if on_error is not None:
            on_error(ctx)
        return
    
    delete = await ctx.send("**Fetching.** This may take a while.")
    # trigger "typing" discord message
    await ctx.trigger_typing()
    
    try:
        response = await get_image(ctx, bird)
    except GenericError as e:
        await delete.delete()
        await ctx.send(f"**An error has occurred while fetching images.**\n*Please try again.*\n**Reason:** {str(e)}")
        if on_error is not None:
            on_error(ctx)
        return
    
    filename = str(response[0])
    extension = str(response[1])
    statInfo = os.stat(filename)
    if statInfo.st_size > 8000000:  # another filesize check
        await delete.delete()
        await ctx.send("**Oops! File too large :(**\n*Please try again.*")
    else:
        if message is not None:
            await ctx.send(message)
        
        # change filename to avoid spoilers
        file_obj = discord.File(filename, filename=f"bird.{extension}")
        await ctx.send(file=file_obj)
        await delete.delete()

# Function that gets bird images to run in pool (blocking prevention)
# Chooses one image to send
async def get_image(ctx, bird):
    # fetch scientific names of birds
    images = await get_files(bird, "images")
    logger.info("images: " + str(images))
    prevJ = int(str(database.hget(f"channel:{str(ctx.channel.id)}", "prevJ"))[2:-1])
    # Randomize start (choose beginning 4/5ths in case it fails checks)
    if images:
        j = (prevJ + 1) % len(images)
        logger.debug("prevJ: " + str(prevJ))
        logger.debug("j: " + str(j))
        
        for x in range(j, len(images)):  # check file type and size
            image_link = images[x]
            extension = image_link.split('.')[-1]
            logger.debug("extension: " + str(extension))
            statInfo = os.stat(image_link)
            logger.debug("size: " + str(statInfo.st_size))
            if extension.lower() in valid_image_extensions and statInfo.st_size < 8000000:  # 8mb discord limit
                logger.info("found one!")
                break
            elif x == len(images) - 1:
                j = (j + 1) % (len(images))
                raise GenericError("No Valid Images Found", code=999)
        
        database.hset(f"channel:{str(ctx.channel.id)}", "prevJ", str(j))
    else:
        raise GenericError("No Images Found", code=100)
    
    return [image_link, extension]

# Manages cache
async def get_files(sciBird, media_type):
    directory = f"cache/{media_type}/{sciBird}/"
    try:
        logger.info("trying")
        files_dir = os.listdir(directory)
        logger.info(directory)
        if not files_dir:
            raise GenericError("No Files", code=100)
        return [f"{directory}{path}" for path in files_dir]
    except (FileNotFoundError, GenericError):
        logger.info("fetching files")
        # if not found, fetch images
        logger.info("scibird: " + str(sciBird))
        paths = fetch_images(sciBird)
        print("paths: " + str(paths))
        paths = paths[0]
        images = [paths[i] for i in sorted(paths.keys())]
        images = images[0]
        print("images: " + str(images))
        return images

def fetch_images(name):
    directory = f"cache/images/{name}/"
    return google_images.download({"keywords": name, "limit": 15, "output_directory": directory})

#FIXME
async def precache():
    pass

"""
    timeout = aiohttp.ClientTimeout(total=10 * 60)
    conn = aiohttp.TCPConnector(limit=100)
    async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
        logger.info("Starting cache")
        await asyncio.gather(*(download_media(bird, "images", session=session) for bird in fossils_list))
        logger.info("Starting females")
        await asyncio.gather(*(download_media(bird, "images", addOn="female", session=session) for bird in fossils_list))
        logger.info("Starting juveniles")
        await asyncio.gather(*(download_media(bird, "images", addOn="juvenile", session=session) for bird in fossils_list))
        logger.info("Starting songs")
        await asyncio.gather(*(download_media(bird, "songs", session=session) for bird in sciSongBirdsMaster))
    logger.info("Images Cached")
"""

# spellcheck - allows one letter off/extra
# cutoff - allows for difference of that amount
def spellcheck(worda, wordb, cutoff=3):
    worda = worda.lower().replace("-", " ").replace("'", "")
    wordb = wordb.lower().replace("-", " ").replace("'", "")
    shorterword = min(worda, wordb, key=len)
    if worda != wordb:
        if len(list(difflib.Differ().compare(worda, wordb))) - len(shorterword) >= cutoff:
            return False
    return True
