import discord

from games.GameManager import GameManager
from games.Games import Games


class LobbyView(discord.ui.BaseView):
    def __init__(self, manager: GameManager, *items, **kwargs):
        super().__init__(*items, **kwargs)
        self.manager = manager

    @discord.ui.button(label="Join Lobby", style=discord.ButtonStyle.primary)
    async def join_lobby(self, button, interaction: discord.interactions.Interaction):
        if not isinstance(interaction.user, discord.Member):
            return
        self.manager.add_player(interaction.user)


class GameBot:
    def __init__(self, intents: discord.Intents) -> None:
        self.managers: list[GameManager] = []
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
            manager = GameManager(game.value(), ctx.user)
            self.managers.append(manager)
            embed = manager.make_embed()
            view = LobbyView(manager)
            await ctx.respond(embed=embed, view=view)

        return bot
