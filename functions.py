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
import difflib
import os
import string
import sys
from concurrent.futures import ThreadPoolExecutor

import discord
from google_images_download import google_images_download

from data.data import GenericError, database, fossils_list, logger

google_images = google_images_download.googleimagesdownload()
# Valid file types
valid_image_extensions = {"jpg", "png", "jpeg", "gif"}
valid_audio_extensions = {"mp3"}

# sets up new channel
async def channel_setup(ctx):
    logger.info("checking channel setup")
    if database.exists(f"channel:{str(ctx.channel.id)}"):
        logger.info("channel data ok")
    else:
        database.hmset(f"channel:{str(ctx.channel.id)}", {"fossil": "", "answered": 1, "prevJ": 20, "prevB": ""})
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

# sets up new fossils
async def fossil_setup(ctx, fossil):
    logger.info("checking fossil data")
    if database.zscore("incorrect:global", string.capwords(str(fossil))) is not None:
        logger.info("fossil global ok")
    else:
        database.zadd("incorrect:global", {string.capwords(str(fossil)): 0})
        logger.info("fossil global added")
    
    if database.zscore(f"incorrect.user:{ctx.author.id}", string.capwords(str(fossil))) is not None:
        logger.info("fossil user ok")
    else:
        database.zadd(f"incorrect.user:{ctx.author.id}", {string.capwords(str(fossil)): 0})
        logger.info("fossil user added")
    
    if ctx.guild is not None:
        logger.info("no dm")
        if database.zscore(f"incorrect.server:{ctx.guild.id}", string.capwords(str(fossil))) is not None:
            logger.info("fossil server ok")
        else:
            database.zadd(f"incorrect.server:{ctx.guild.id}", {string.capwords(str(fossil)): 0})
            logger.info("fossil server added")
    else:
        logger.info("dm context")

# Function to run on error
def error_skip(ctx):
    logger.info("ok")
    database.hset(f"channel:{str(ctx.channel.id)}", "fossil", "")
    database.hset(f"channel:{str(ctx.channel.id)}", "answered", "1")

def session_increment(ctx, item, amount):
    logger.info(f"incrementing {item} by {amount}")
    value = int(database.hget(f"session.data:{ctx.author.id}", item))
    value += int(amount)
    database.hset(f"session.data:{ctx.author.id}", item, str(value))

def incorrect_increment(ctx, fossil, amount):
    logger.info(f"incrementing incorrect {fossil} by {amount}")
    database.zincrby("incorrect:global", amount, str(fossil))
    database.zincrby(f"incorrect.user:{ctx.author.id}", amount, str(fossil))
    if ctx.guild is not None:
        logger.info("no dm")
        database.zincrby(f"incorrect.server:{ctx.guild.id}", amount, str(fossil))
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

# Gets a fossil picture and sends it to user:
# ctx - context for message (discord thing)
# fossil - fossil picture to send (str)
# on_error - function to run when an error occurs (function)
# message - text message to send before fossil picture (str)
async def send_fossil(ctx, fossil, on_error=None, message=None):
    if fossil == "":
        logger.error("error - fossil is blank")
        await ctx.send("**There was an error fetching fossils.**\n*Please try again.*")
        if on_error is not None:
            on_error(ctx)
        return
    
    delete = await ctx.send("**Fetching.** This may take a while.")
    # trigger "typing" discord message
    await ctx.trigger_typing()
    
    try:
        response = await get_image(ctx, fossil)
    except GenericError as e:
        logger.exception(e)
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
        file_obj = discord.File(filename, filename=f"fossil.{extension}")
        await ctx.send(file=file_obj)
        await delete.delete()

# Function that gets fossil images to run in pool (blocking prevention)
# Chooses one image to send
async def get_image(ctx, fossil):
    # fetch scientific names of fossils
    images = await get_files(fossil, "images")
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
async def get_files(fossil, media_type):
    directory = f"cache/{media_type}/{fossil}/"
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
        logger.info("fossil: " + str(fossil))
        paths = fetch_images(fossil)
        print("paths: " + str(paths))
        paths = paths[0]
        images = [paths[i] for i in sorted(paths.keys())]
        images = images[0]
        print("images: " + str(images))
        return images

def fetch_images(name):
    directory = f"cache/images/"
    if name.lower() == "acer":
        name = "acer fossil"
    return google_images.download({"keywords": name, "limit": 15, "silent_mode": True, "output_directory": directory})

async def precache():
    logger.info("Starting caching")
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=20) as executor:
        await asyncio.gather(*(loop.run_in_executor(executor, fetch_images, fossil) for fossil in fossils_list))
    logger.info("Finished caching")

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
