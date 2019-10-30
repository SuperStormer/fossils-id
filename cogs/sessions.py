# sessions.py | commands for sessions
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

import datetime
import time

from discord.ext import commands

from data.data import database, logger
from functions import channel_setup, user_setup

class Sessions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def _send_stats(self, ctx):
        start, correct, incorrect, total = map(
            int, database.hmget(f"session.data:{str(ctx.author.id)}", ["start", "correct", "incorrect", "total"])
        )
        elapsed = str(datetime.timedelta(seconds=round(time.time()) - start))
        try:
            accuracy = round(100 * (correct / (correct + incorrect)), 2)
        except ZeroDivisionError:
            accuracy = 0
        await ctx.send(
            f"""**Session Stats:**
*Duration:* {elapsed}
*# Correct:* {correct}
*# Incorrect:* {incorrect}
*Total Fossils:* {total}
*Accuracy:* {accuracy}%"""
        )
    
    @commands.group(
        brief="- Base session command",
        help="- Base session command\n" + "Sessions will record your activity for an amount of time and " +
        "will give you stats on how your performance. "
    )
    async def session(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('**Invalid subcommand passed.**\n*Valid Subcommands:* `start, view, stop`')
    
    # starts session
    @session.command(help="- Starts session", aliases=["st"], usage="")
    @commands.cooldown(1, 3.0, type=commands.BucketType.channel)
    async def start(self, ctx):
        logger.info("command: start session")
        
        await channel_setup(ctx)
        await user_setup(ctx)
        
        if database.exists(f"session.data:{str(ctx.author.id)}"):
            logger.info("already session")
            await ctx.send("**There is already a session running.** *View stats with `f!session`*")
            return
        else:
            database.hmset(
                f"session.data:{str(ctx.author.id)}", {
                    "start": round(time.time()),
                    "stop": 0,
                    "correct": 0,
                    "incorrect": 0,
                    "total": 0
                }
            )
            await ctx.send("**Session started. Your stats are now being tracked**")
    
    # views session
    @session.command(
        brief="- Views session",
        help="- Views session\nSessions will record your activity for an amount of time and " +
        "will give you stats on how your performance. ",
        usage=""
    )
    @commands.cooldown(1, 3.0, type=commands.BucketType.channel)
    async def view(self, ctx):
        logger.info("command: view session")
        
        await channel_setup(ctx)
        await user_setup(ctx)
        
        if database.exists(f"session.data:{str(ctx.author.id)}"):
            await self._send_stats(ctx)
        else:
            await ctx.send("**There is no session running.** *You can start one with `f!session start`*")
    
    # stops session
    @session.command(help="- Stops session", aliases=["stp"])
    @commands.cooldown(1, 3.0, type=commands.BucketType.channel)
    async def stop(self, ctx):
        logger.info("command: stop session")
        
        await channel_setup(ctx)
        await user_setup(ctx)
        
        if database.exists(f"session.data:{str(ctx.author.id)}"):
            database.hset(f"session.data:{str(ctx.author.id)}", "stop", round(time.time()))
            
            await self._send_stats(ctx)
            database.delete(f"session.data:{str(ctx.author.id)}")
        else:
            await ctx.send("**There is no session running.** *You can start one with `f!session start`*")

def setup(bot):
    bot.add_cog(Sessions(bot))
