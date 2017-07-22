import os
import asyncio  # noqa: F401
import discord
import logging
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils import checks


class SuggestionBox:
    """custom cog for a configureable suggestion box"""

    __author__ = "mikeshardmind"
    __version__ = "1.2"

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/suggestionbox/settings.json')
        for s in self.settings:
            self.settings[s]['usercache'] = []

    def save_json(self):
        dataIO.save_json("data/suggestionbox/settings.json", self.settings)

    @commands.group(name="setsuggest", pass_context=True, no_pm=True)
    async def setsuggest(self, ctx):
        """configuration settings"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    def initial_config(self, server_id):
        """makes an entry for the server, defaults to turned off"""

        if server_id not in self.settings:
            self.settings[server_id] = {'inactive': True,
                                        'output': [],
                                        'cleanup': False,
                                        'usercache': [],
                                        'multiout': False,
                                        'tickets': 0
                                        }
            self.save_json()

    @checks.admin_or_permissions(Manage_server=True)
    @setsuggest.command(name="fixcache", pass_context=True, no_pm=True)
    async def fix_cache(self, ctx):
        """use this if the bot gets stuck not recording your response"""
        self.initial_config(ctx.message.server.id)
        self.settings[server.id]['usercache'] = []
        self.save_json()

    @checks.admin_or_permissions(Manage_server=True)
    @setsuggest.command(name="output", pass_context=True, no_pm=True)
    async def setoutput(self, ctx, *, chan=None, serv : discord.Server.id=None):
        """sets the output channel(s) by id"""
        if serv==None:
            server = ctx.message.server
        else:
            servers = self.bot.servers
            for s in servers:
                if s.id == serv:
                    server = s
        if server.id not in self.settings:
            self.initial_config(server.id)

        if chan in self.settings[server.id]['output']:
            return await self.bot.say("Channel already set as output")
        for channel in server.channels:
            if str(chan) == str(channel.id):
                if self.settings[server.id]['multiout']:
                    self.settings[server.id]['output'].append(chan)
                    self.save_json()
                    return await self.bot.say("Channel added to output list")
                else:
                    self.settings[server.id]['output'] = [chan]
                    self.save_json()
                    return await self.bot.say("Channel set as output")

        await self.bot.say("I couldn\'t find a channel with that id")

    @checks.admin_or_permissions(Manage_server=True)
    @setsuggest.command(name="toggleactive", pass_context=True, no_pm=True)
    async def suggest_toggle(self, ctx):
        """Toggles whether the suggestion box is enabled or not"""
        server = ctx.message.server
        if server.id not in self.settings:
            self.initial_config(server.id)
        self.settings[server.id]['inactive'] = \
            not self.settings[server.id]['inactive']
        self.save_json()
        if self.settings[server.id]['inactive']:
            await self.bot.say("Suggestions disabled.")
        else:
            await self.bot.say("Suggestions enabled.")

    @checks.admin_or_permissions(manage_server=True)
    @setsuggest.command(name='reset', pass_context=True,no_pm=True)
    async def suggest_reset(self,ctx, value : int = 0):
        '''Reset Ticket Counter for Server'''
        server = ctx.message.server
        if server.id in self.settings:
            self.settings[server.id]['tickets'] = value#0
            self.save_json()
            await self.bot.say('Suggestion counter reset to {}.'.format(value))

    @commands.command(name="suggest", pass_context=True)
    async def makesuggestion(self, ctx, *, suggestion=None):
        "make a suggestion by following the prompts"
        author = ctx.message.author
        server = ctx.message.server

        if server.id not in self.settings:
            return await self.bot.say("Suggestion submissions have not been "
                                      "configured for this server.")
        if self.settings[server.id]['inactive']:
            return await self.bot.say("Suggestion submission is not currently "
                                      "enabled on this server.")

        if author.id in self.settings[server.id]['usercache']:
            return await self.bot.say("Finish making your prior sugggestion "
                                      "before making an additional one")
        if suggestion is None:
            await self.bot.say("I will message you to collect your suggestion.")
            self.settings[server.id]['usercache'].append(author.id)
            self.save_json()
            dm = await self.bot.send_message(author,
                                             "Please respond to this message"
                                             "with your suggestion.\nYour "
                                             "suggestion should be a single "
                                             "message.")
            message = await self.bot.wait_for_message(channel=dm.channel,
                                                      author=author, timeout=120)
        else:
            message = ctx.message

        if message is None:
            await self.bot.send_message(author,
                                        "I can't wait forever, "
                                        "try again when ready")
            self.settings[server.id]['usercache'].remove(author.id)
            self.save_json()
        else:
            self.settings[server.id]['tickets']+=1
            self.save_json()
            await self.send_suggest(message, server, suggestion=suggestion)
            await self.bot.send_message(author, "Your suggestion was "
                                        "submitted.")

    async def send_suggest(self, message, server, suggestion = None):

        author = message.author
        if suggestion is None:
            suggestion = message.clean_content
        timestamp = message.timestamp.strftime('%Y-%m-%d %H:%M')
        avatar = author.avatar_url if author.avatar \
            else author.default_avatar_url
        title = 'Suggestion # {}'.format(self.settings[server.id]['tickets'])
        em = discord.Embed(title=title, description=suggestion,
                           color=discord.Color.purple())
        em.set_author(name='Suggestion from {}'.format(author.name),
                      icon_url=avatar)
        em.set_footer(text='Suggestion made at {} UTC'.format(timestamp))

        for output in self.settings[server.id]['output']:
            where = server.get_channel(output)
            if where is not None:
                message = await self.bot.send_message(where, embed=em)
                await self.bot.add_reaction(message, '\N{UP ARROW}')#':up_arrow:')#'\ud83d\udc4d')#'⬆️')
                await self.bot.add_reaction(message, '\N{DOWN ARROW}')#':down_arrow')#'\ud83d\udc4e')#'⬇️')
                # await self.bot.add_reaction(message,'❌')
        try:
            self.settings[server.id]['usercache'].remove(author.id)
        except:
            pass
        self.save_json()


def check_folder():
    f = 'data/suggestionbox'
    if not os.path.exists(f):
        os.makedirs(f)


def check_file():
    f = 'data/suggestionbox/settings.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})


def setup(bot):
    check_folder()
    check_file()
    n = SuggestionBox(bot)
    bot.add_cog(n)
