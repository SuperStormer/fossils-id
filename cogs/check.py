# check.py | commands to check answers
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

import discord
import wikipedia
from discord.ext import commands

from data.data import database, logger
from functions import (
    fossil_setup, channel_setup, incorrect_increment, score_increment, session_increment, spellcheck, user_setup
)

#TODO
achievements = (1, )
#achievements = (1, 10, 25, 50, 100, 150, 200, 250, 400, 420, 500, 650, 666, 690)

class Check(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    # Check command - argument is the guess
    @commands.command(help='- Checks your answer.', usage="guess", aliases=["guess", "c"])
    @commands.cooldown(1, 3.0, type=commands.BucketType.channel)
    async def check(self, ctx, *, guess):
        logger.info("command: check")
        
        await channel_setup(ctx)
        await user_setup(ctx)
        current_fossil = str(database.hget(f"channel:{str(ctx.channel.id)}", "fossil"))[2:-1]
        if current_fossil == "":
            await ctx.send("You must ask for a fossil first!")
        else:  # if there is a fossil, it checks answer
            await fossil_setup(ctx, current_fossil)
            database.hset(f"channel:{str(ctx.channel.id)}", "fossil", "")
            database.hset(f"channel:{str(ctx.channel.id)}", "answered", "1")
            if spellcheck(guess.split(" ")[:-1], current_fossil.split(" ")[:-1]):
                logger.info("correct")
                
                if database.exists(f"session.data:{ctx.author.id}"):
                    logger.info("session active")
                    session_increment(ctx, "correct", 1)
                
                await ctx.send("Correct! Good job!")
                page = wikipedia.page(current_fossil)
                await ctx.send(page.url)
                score_increment(ctx, 1)
                if int(database.zscore("users:global", str(ctx.author.id))) in achievements:
                    number = str(int(database.zscore("users:global", str(ctx.author.id))))
                    await ctx.send(f"Wow! You have answered {number} fossils correctly!")
                    filename = 'achievements/' + number + ".PNG"
                    with open(filename, 'rb') as img:
                        await ctx.send(file=discord.File(img, filename="award.png"))
            
            else:
                logger.info("incorrect")
                
                if database.exists(f"session.data:{ctx.author.id}"):
                    logger.info("session active")
                    session_increment(ctx, "incorrect", 1)
                
                incorrect_increment(ctx, str(current_fossil), 1)
                await ctx.send("Sorry, the fossil was actually " + current_fossil.lower() + ".")
                page = wikipedia.page(current_fossil)
                await ctx.send(page.url)
            logger.info("current_fossil: " + str(current_fossil.lower().replace("-", " ")))
            logger.info("guess: " + str(guess.lower().replace("-", " ")))

def setup(bot):
    bot.add_cog(Check(bot))
