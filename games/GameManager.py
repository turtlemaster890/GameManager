import discord
from .GameProtocol import GameProtocol

class GameManager:
    def __init__(self, game: GameProtocol):
        self.players: set[discord.user] = set()
        self.game = game

    def add_player(self, player: discord.user):
        self.players.add(player)

    def remove_player(self, player: discord.user):
        self.players.discard(player)