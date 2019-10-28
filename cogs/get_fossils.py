# get_fossils.py | commands for getting fossil images
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

import random
from discord.ext import commands
from data.data import fossils_list, database, logger
from functions import (channel_setup, error_skip, send_fossil, user_setup, session_increment)

BASE_MESSAGE = (
    "*Here you go!* \n**Use `f!{new_cmd}` again to get a new {media} of the same fossil, " +
    "or `f!{skip_cmd}` to get a new fossil. Use `f!{check_cmd} guess` to check your answer. " + "Use `f!{hint_cmd}` for a hint.**"
)

FOSSIL_MESSAGE = BASE_MESSAGE.format(media="image", new_cmd="fossil", skip_cmd="skip", check_cmd="check", hint_cmd="hint")

class Fossils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    # Fossil command - no args
    # help text
    @commands.command(help='- Sends a random fossil image for you to ID', aliases=["f"], usage="")
    # 5 second cooldown
    @commands.cooldown(1, 5.0, type=commands.BucketType.channel)
    async def fossil(self, ctx):
        logger.info("command: fossil")
        
        await channel_setup(ctx)
        await user_setup(ctx)
        logger.info("fossil: " + str(database.hget(f"channel:{str(ctx.channel.id)}", "fossil"))[2:-1])
        
        answered = int(database.hget(f"channel:{str(ctx.channel.id)}", "answered"))
        logger.info(f"answered: {answered}")
        # check to see if previous fossil was answered
        if answered:  # if yes, give a new fossil
            if database.exists(f"session.data:{ctx.author.id}"):
                logger.info("session active")
                session_increment(ctx, "total", 1)
            logger.info(f"number of fossils: {len(fossils_list)}")
            
            current_fossil = random.choice(fossils_list)
            prevB = str(database.hget(f"channel:{str(ctx.channel.id)}", "prevB"))[2:-1]
            while current_fossil == prevB:
                current_fossil = random.choice(fossils_list)
            database.hset(f"channel:{str(ctx.channel.id)}", "prevB", str(current_fossil))
            database.hset(f"channel:{str(ctx.channel.id)}", "fossil", str(current_fossil))
            logger.info("current fossil: " + str(current_fossil))
            await send_fossil(ctx, current_fossil, on_error=error_skip, message=FOSSIL_MESSAGE)
            database.hset(f"channel:{str(ctx.channel.id)}", "answered", "0")
        else:  # if no, give the same fossil
            await send_fossil(
                ctx,
                str(database.hget(f"channel:{str(ctx.channel.id)}", "fossil"))[2:-1],
                on_error=error_skip,
                message=FOSSIL_MESSAGE
            )

def setup(bot):
    bot.add_cog(Fossils(bot))
