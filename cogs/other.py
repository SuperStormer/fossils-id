# other.py | misc. commands
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
from difflib import get_close_matches

import discord
import wikipedia
from discord.ext import commands

from data.data import fossils_list, database, logger, bot_name
from functions import channel_setup, send_fossil, user_setup, owner_check

class Other(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    # Info - Gives call+image of 1 fossil
    @commands.command(help="- Gives an image and call of a fossil", aliases=['i'])
    @commands.cooldown(1, 10.0, type=commands.BucketType.channel)
    async def info(self, ctx, *, arg):
        logger.info("command: info")
        
        await channel_setup(ctx)
        await user_setup(ctx)
        
        matches = get_close_matches(arg, fossils_list + fossils_list, n=1)
        if matches:
            fossil = matches[0]
            
            delete = await ctx.send("Please wait a moment.")
            await send_fossil(ctx, str(fossil), message="Here's the image!")
            await delete.delete()
        
        else:
            await ctx.send("Fossil not found. Are you sure it's on the list?")
    
    # Wiki command - argument is the wiki page
    @commands.command(help="- Fetch the wikipedia page for any given argument")
    @commands.cooldown(1, 8.0, type=commands.BucketType.channel)
    async def wiki(self, ctx, *, arg):
        logger.info("command: wiki")
        
        await channel_setup(ctx)
        await user_setup(ctx)
        
        try:
            page = wikipedia.page(arg)
            await ctx.send(page.url)
        except wikipedia.exceptions.DisambiguationError:
            await ctx.send("Sorry, that page was not found. Try being more specific.")
        except wikipedia.exceptions.PageError:
            await ctx.send("Sorry, that page was not found.")
    
    # bot info command - gives info on bot
    @commands.command(help="- Gives info on bot, support server invite, stats", aliases=["bot_info", "support", "stats"])
    @commands.cooldown(1, 5.0, type=commands.BucketType.channel)
    async def botinfo(self, ctx):
        logger.info("command: botinfo")
        
        await channel_setup(ctx)
        await user_setup(ctx)
        
        embed = discord.Embed(type="rich", colour=discord.Color.blurple())
        embed.set_author(name=bot_name)
        embed.add_field(
            name="Bot Info",
            value="This bot was created by EraserBird, person_v1.32 and hmmm" +
            "for helping people practice fossil identification for Science Olympiad.",
            inline=False
        )
        embed.add_field(
            name="Support",
            value="If you are experiencing any issues, have feature requests, " +
            "or want to get updates on bot status, join our support server below.",
            inline=False
        )
        embed.add_field(
            name="Stats",
            value=f"This bot can see {len(self.bot.users)} users and is in {len(self.bot.guilds)} servers. " +
            f"There are {int(database.zcard('users:global'))} active users in {int(database.zcard('score:global'))} channels. " +
            f"The WebSocket latency is {str(round((self.bot.latency*1000)))} ms.",
            inline=False
        )
        await ctx.send(embed=embed)
        await ctx.send("https://discord.gg/fXxYyDJ")
    
    # invite command - sends invite link
    @commands.command(help="- Get the invite link for this bot")
    @commands.cooldown(1, 5.0, type=commands.BucketType.channel)
    async def invite(self, ctx):
        logger.info("command: invite")
        
        await channel_setup(ctx)
        await user_setup(ctx)
        
        embed = discord.Embed(type="rich", colour=discord.Color.blurple())
        embed.set_author(name=bot_name)
        embed.add_field(
            name="Invite",
            value="""To invite this bot to your own server, use the following invite link:
https://discordapp.com/api/oauth2/authorize?client_id=635564806962675732&permissions=0&scope=bot""",
            inline=False
        )
        await ctx.send(embed=embed)
        await ctx.send("https://discord.gg/fXxYyDJ")
    
    # Send command - for testing purposes only
    @commands.command(help="- send command", hidden=True, aliases=["sendas"])
    @commands.check(owner_check)
    async def send_as_bot(self, ctx, *, args):
        logger.info("command: send")
        logger.info(f"args: {args}")
        channel_id = int(args.split(' ')[0])
        message = args.strip(str(channel_id))
        channel = self.bot.get_channel(channel_id)
        await channel.send(message)
        await ctx.send("Ok, sent!")

def setup(bot):
    bot.add_cog(Other(bot))
