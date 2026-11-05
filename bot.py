import json

import discord

from games.GameManager import GameManager
from games.Games import Games


class GameBot:
    def __init__(self, intents: discord.Intents) -> None:
        self.managers: set[GameManager] = set()
        self.bot = self.setup_bot(discord.Bot(intents=intents))

    def setup_bot(self, bot: discord.Bot):
        @bot.event
        async def on_ready():
            print(f"{bot.user and bot.user.name} online")

        @bot.slash_command(
            name="gameroom",
            description="Make a game room",
            guild_ids=[1327416677863784508],
        )
        @discord.option("game", Games)
        async def make_room(ctx: discord.ApplicationContext, game: Games):
            if not isinstance(ctx.user, discord.Member):
                return
            with open("guild_data.json", "r") as f:
                data: dict[str, dict] = json.load(f)
            if str(ctx.guild_id) not in data:
                await ctx.response.send_message("Please set a category for games!")
                return
            guild_data = data[str(ctx.guild_id)]
            if not guild_data["category_channel"]:
                await ctx.response.send_message("Please set a category for games!")
                return
            assert ctx.guild
            category = ctx.guild.get_channel(guild_data["category_channel"])
            if not category:
                await ctx.response.send_message("Games category not set properly - please retry")
                return
            assert isinstance(category, discord.CategoryChannel)
            manager = GameManager(game.value, category, ctx.user)
            manager.on_close = lambda: self.managers.discard(manager)
            self.managers.add(manager)
            await manager.send_embed(ctx)

        return bot
