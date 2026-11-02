import discord
from games.Games import Games
from games.GameManager import GameManager

# bot = discord.Bot()

class GameBot(discord.Bot):
    # games: dict[str, type[GameProtocol]] = {
    #     "Uno": Uno
    # }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.managers: list[GameManager] = []

    # @discord.event
    # async def on_ready():
    #     print(f"{bot.user} online")

    # async def get_games(self, ctx: discord.AutocompleteContext):
    #     return self.games

    @discord.slash_command(name="makeroom", description="Make a game room")
    async def makeRoom(
        ctx: discord.ApplicationContext,
        game: discord.Option(Games)
    ):
        manager = GameManager(game)