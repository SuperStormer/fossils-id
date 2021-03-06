# skip.py | commands for skipping fossils
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

import wikipedia
from discord.ext import commands
from data.data import database, logger
from functions import channel_setup, user_setup

class Skip(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    # Skip command - no args
    @commands.command(help="- Skip the current fossil to get a new one", aliases=["sk", "s"])
    @commands.cooldown(1, 5.0, type=commands.BucketType.channel)
    async def skip(self, ctx):
        logger.info("command: skip")
        
        await channel_setup(ctx)
        await user_setup(ctx)
        
        current_fossil = str(database.hget(f"channel:{str(ctx.channel.id)}", "fossil"))[2:-1]
        database.hset(f"channel:{str(ctx.channel.id)}", "fossil", "")
        database.hset(f"channel:{str(ctx.channel.id)}", "answered", "1")
        if current_fossil != "":  # check if there is fossil
            fossil_page = wikipedia.page(current_fossil)
            await ctx.send(f"Ok, skipping {current_fossil.title()}\n{fossil_page.url}")  # sends wiki page
        else:
            await ctx.send("You need to ask for a fossil first!")

def setup(bot):
    bot.add_cog(Skip(bot))
