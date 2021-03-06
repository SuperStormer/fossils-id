# hint.py | commands for giving hints
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

from discord.ext import commands

from data.data import database, logger
from functions import channel_setup, user_setup

class Hint(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    # give hint
    @commands.command(help="- Gives first letter of current fossil", aliases=["h"])
    @commands.cooldown(1, 3.0, type=commands.BucketType.channel)
    async def hint(self, ctx):
        logger.info("command: hint")
        
        await channel_setup(ctx)
        await user_setup(ctx)
        
        current_fossil = str(database.hget(f"channel:{str(ctx.channel.id)}", "fossil"))[2:-1]
        if current_fossil != "":
            await ctx.send(f"The first letter is {current_fossil[0]}")
        else:
            await ctx.send("You need to ask for a fossil first!")

def setup(bot):
    bot.add_cog(Hint(bot))
