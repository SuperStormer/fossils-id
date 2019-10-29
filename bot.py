# bot.py | main program
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
import errno
import os
import shutil
import sys

import aiohttp
import discord
import redis
import wikipedia
from discord.ext import commands, tasks

from data.data import database, logger, bot_name
from functions import channel_setup, precache

BACKUPS_CHANNEL = 622547928946311188

if __name__ == '__main__':
    # Initialize bot
    bot = commands.Bot(command_prefix=['f!', 'f.', 'f#'], case_insensitive=True, description=bot_name)
    
    @bot.event
    async def on_ready():
        print("Ready!")
        logger.info("Logged in as:")
        logger.info(bot.user.name)
        logger.info(bot.user.id)
        # Change discord activity
        await bot.change_presence(activity=discord.Activity(type=3, name="f!help"))
        
        #refresh_cache.start()
    
    for extension in ('cogs.get_fossils', 'cogs.check', 'cogs.skip', 'cogs.hint', 'cogs.score', 'cogs.sessions', 'cogs.other'):
        try:
            bot.load_extension(extension)
        except (discord.ClientException, ModuleNotFoundError):
            logger.exception(f'Failed to load extension {extension}.')
    if sys.platform == 'win32':
        asyncio.set_event_loop(asyncio.ProactorEventLoop())
    
    ######
    # Global Command Checks
    ######
    
    # Global check for dms - remove cooldowns
    @bot.check
    async def dm_cooldown(ctx):
        if ctx.command.is_on_cooldown(ctx) and ctx.guild is None:
            ctx.command.reset_cooldown(ctx)
        return True
    
    # Global check for correct permissions
    @bot.check
    def bot_has_permissions(ctx):
        # code copied from @commands.bot_has_permissions(send_messages=True, embed_links=True, attach_files=True)
        if ctx.guild is not None:
            perms = {"send_messages": True, "embed_links": True, "attach_files": True}
            guild = ctx.guild
            me = guild.me if guild is not None else ctx.bot.user
            permissions = ctx.channel.permissions_for(me)
            
            missing = [perm for perm, value in perms.items() if getattr(permissions, perm, None) != value]
            
            if not missing:
                return True
            
            raise commands.BotMissingPermissions(missing)
        else:
            return True
    
    ######
    # GLOBAL ERROR CHECKING
    ######
    @bot.event
    async def on_command_error(ctx, error):
        logger.error("Error: " + str(error))
        # don't handle errors with local handlers
        if hasattr(ctx.command, 'on_error'):
            return
        
        if isinstance(error, commands.CommandOnCooldown):  # send cooldown
            await ctx.send("**Cooldown.** Try again after " + str(round(error.retry_after)) + " s.", delete_after=5.0)
        
        elif isinstance(error, commands.CommandNotFound):
            await ctx.send("Sorry, the command was not found.")
        
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("This command requires an argument!")
        
        elif isinstance(error, commands.BadArgument):
            logger.error("bad argument")
            await ctx.send("The argument passed was invalid. Please try again.")
        
        elif isinstance(error, commands.ArgumentParsingError):
            logger.error("quote error")
            await ctx.send("An invalid character was detected. Please try again.")
        
        elif isinstance(error, commands.BotMissingPermissions):
            logger.error("missing permissions error")
            await ctx.send(
                f"""**The bot does not have enough permissions to fully function.**
**Permissions Missing:** `{', '.join(map(str, error.missing_perms))}`
*Please try again once the correct permissions are set.*"""
            )
        
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send("**This command is unavaliable in DMs!**")
        
        elif isinstance(error, commands.CommandInvokeError):
            if isinstance(error.original, redis.exceptions.ResponseError):
                if database.exists(f"channel:{str(ctx.channel.id)}"):
                    await ctx.send(
                        """**An unexpected ResponseError has occurred.**
*Please log this message in #support in the support server below, or try again.*
**Error:** """ + str(error)
                    )
                    await ctx.send("https://discord.gg/husFeGG")
                else:
                    await channel_setup(ctx)
                    await ctx.send("Please run that command again.")
            
            elif isinstance(error.original, wikipedia.exceptions.DisambiguationError):
                await ctx.send("Wikipedia page not found. (Disambiguation Error)")
            
            elif isinstance(error.original, wikipedia.exceptions.PageError):
                await ctx.send("Wikipedia page not found. (Page Error)")
            
            elif isinstance(error.original, wikipedia.exceptions.WikipediaException):
                await ctx.send("Wikipedia page unavaliable. Try again later.")
            
            elif isinstance(error.original, aiohttp.ClientOSError):
                if error.original.errno != errno.ECONNRESET:
                    await ctx.send(
                        """**An unexpected ClientOSError has occurred.**
*Please log this message in #support in the support server below, or try again.*
**Error:** """ + str(error)
                    )
                    await ctx.send("https://discord.gg/husFeGG")
                else:
                    await ctx.send("**An error has occured with discord. :(**\n*Please try again.*")
            
            else:
                logger.error("uncaught command error")
                await ctx.send(
                    """**An uncaught command error has occurred.**
*Please log this message in #support in the support server below, or try again.*
**Error:**  """ + str(error)
                )
                await ctx.send("https://discord.gg/husFeGG")
                raise error
        
        else:
            logger.error("uncaught non-command")
            await ctx.send(
                """**An uncaught non-command error has occurred.**
*Please log this message in #support in the support server below, or try again.*
**Error:**  """ + str(error)
            )
            await ctx.send("https://discord.gg/husFeGG")
            raise error
    
    @tasks.loop(hours=48.0)
    async def refresh_cache():
        logger.info("clear cache")
        try:
            shutil.rmtree(r'cache/images/', ignore_errors=True)
            logger.info("Cleared image cache.")
        except FileNotFoundError:
            logger.info("Already cleared image cache.")
        await precache()
    
    refresh_cache.start()
    token = os.getenv("token")
    bot.run(token)
