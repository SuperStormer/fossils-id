# data.py | import data from lists
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

import logging
import logging.handlers
import os
import string
import sys

import redis
from discord.ext import commands

# define database for one connection
database = redis.from_url(os.getenv("REDIS_URL"))

# Database Format Definitions

# prevJ - makes sure it sends a diff image
# prevB - makes sure it sends a diff fossil (img)
# prevS - makes sure it sends a diff fossil (sounds)
# prevK - makes sure it sends a diff sound

# server format = {
# channel:channel_id : { "fossil", "answered","prevJ", "prevB"}
# }

# session format:
# session.data:user_id : {"start": 0, "stop": 0,
#                         "correct": 0, "incorrect": 0, "total": 0}

# leaderboard format = {
#    "users:global":[user id, # of correct]
#    "users.server:server_id":[user id, # of correct]
# }

# incorrect fossil format = {
#    "incorrect:global":[name, # incorrect]
#    "incorrect.server:server_id":[name, # incorrect]
#    "incorrect.user:user_id:":[name, # incorrect]
# }

# channel score format = {
#   "score:global":[channel id, # of correct]
# }

# setup logging
logger = logging.getLogger("fossils-id")
logger.setLevel(logging.DEBUG)
logger.propagate = False
os.makedirs("logs", exist_ok=True)

file_handler = logging.handlers.TimedRotatingFileHandler("logs/log.txt", backupCount=4, when="midnight")
file_handler.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.WARNING)

file_handler.setFormatter(logging.Formatter("{asctime} - {filename:10} -  {levelname:8} - {message}", style="{"))
stream_handler.setFormatter(logging.Formatter("{filename:10} -  {levelname:8} - {message}", style="{"))

logger.addHandler(file_handler)
logger.addHandler(stream_handler)
# log uncaught exceptions

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception

bot_name = "Fossils ID - A Paleontology Bot"

class GenericError(commands.CommandError):
    def __init__(self, message=None, code=0):
        self.code = code
        super().__init__(message=message)

# Error codes: (can add more if needed)
# 0 - no code
# 111 - Index Error
# 201 - HTTP Error
# 999 - Invalid
# 100 - Blank

def _fossils_list():
    with open("data/fossils_list.txt") as f:
        return [string.capwords(line.strip()) for line in f]

fossils_list = _fossils_list()
