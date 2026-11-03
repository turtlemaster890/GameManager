import discord

from .GameProtocol import GameProtocol


class GameManager:
    def __init__(self, game: GameProtocol, host: discord.Member | None = None):
        self.players: set[discord.Member] = set()
        self.host = host
        if host:
            self.add_player(host)
        self.game = game

    def add_player(self, player: discord.Member):
        self.players.add(player)

    def remove_player(self, player: discord.Member):
        self.players.discard(player)

    def make_embed(self):
        embed = discord.Embed(
            title=f"{self.game.name} Lobby",
            description=f"Host: {self.host and self.host.mention}",
        )
        embed.add_field(
            name="Players",
            value=f"{len(self.players)}/{self.game.maxPlayers or ":infinity:"} ({", ".join([m.mention for m in self.players])})",
        )
        return embed