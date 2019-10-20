# get_birds.py | commands for getting bird images or songs
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

import itertools
import random
from discord.ext import commands
from data.data import fossils_list, database, logger
from functions import (channel_setup, error_skip, send_bird, user_setup, session_increment)

BASE_MESSAGE = (
    "*Here you go!* \n**Use `b!{new_cmd}` again to get a new {media} of the same bird, " +
    "or `b!{skip_cmd}` to get a new bird. Use `b!{check_cmd} guess` to check your answer. " + "Use `b!{hint_cmd}` for a hint.**"
)

BIRD_MESSAGE = BASE_MESSAGE.format(media="image", new_cmd="bird", skip_cmd="skip", check_cmd="check", hint_cmd="hint")

class Birds(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    # Bird command - no args
    # help text
    @commands.command(help='- Sends a random bird image for you to ID', aliases=["b"], usage="")
    # 5 second cooldown
    @commands.cooldown(1, 5.0, type=commands.BucketType.channel)
    async def bird(self, ctx):
        logger.info("command: bird")
        
        await channel_setup(ctx)
        await user_setup(ctx)
        logger.info("bird: " + str(database.hget(f"channel:{str(ctx.channel.id)}", "bird"))[2:-1])
        
        answered = int(database.hget(f"channel:{str(ctx.channel.id)}", "answered"))
        logger.info(f"answered: {answered}")
        # check to see if previous bird was answered
        if answered:  # if yes, give a new bird
            if database.exists(f"session.data:{ctx.author.id}"):
                logger.info("session active")
                session_increment(ctx, "total", 1)
            logger.info(f"number of fossils: {len(fossils_list)}")
            
            currentBird = random.choice(fossils_list)
            prevB = str(database.hget(f"channel:{str(ctx.channel.id)}", "prevB"))[2:-1]
            while currentBird == prevB:
                currentBird = random.choice(fossils_list)
            database.hset(f"channel:{str(ctx.channel.id)}", "prevB", str(currentBird))
            database.hset(f"channel:{str(ctx.channel.id)}", "bird", str(currentBird))
            logger.info("currentBird: " + str(currentBird))
            await send_bird(ctx, currentBird, on_error=error_skip, message=BIRD_MESSAGE)
            database.hset(f"channel:{str(ctx.channel.id)}", "answered", "0")
        else:  # if no, give the same bird
            await send_bird(
                ctx,
                str(database.hget(f"channel:{str(ctx.channel.id)}", "bird"))[2:-1],
                on_error=error_skip,
                message=BIRD_MESSAGE
            )

def setup(bot):
    bot.add_cog(Birds(bot))
