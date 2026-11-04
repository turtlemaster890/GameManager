import discord
from discord.interactions import Interaction
from discord.ui import Button, View, ViewItem, button

from .GameProtocol import GameProtocol


class LobbyView(View):
    def __init__(
        self,
        manager: "GameManager",
        *items: ViewItem,
        timeout: float | None = None,
        disable_on_timeout: bool = False,
        store: bool = True,
        **kwargs,
    ):
        super().__init__(
            *items,
            timeout=timeout,
            disable_on_timeout=disable_on_timeout,
            store=store,
            **kwargs,
        )
        self.manager = manager

    @button(label="Join", style=discord.ButtonStyle.green)
    async def join_lobby(self, button: Button, interaction: Interaction):
        if not isinstance(interaction.user, discord.Member):
            return
        if interaction.user in self.manager.players:
            await interaction.response.send_message(
                "You're already in this lobby!", ephemeral=True
            )
            return
        self.manager.add_player(interaction.user)
        await self.manager.update_embed()
        await interaction.response.send_message("Joined game!", ephemeral=True)

    @button(label="Leave", style=discord.ButtonStyle.red)
    async def leave_lobby(self, button: Button, interaction: Interaction):
        if not isinstance(interaction.user, discord.Member):
            return
        if interaction.user not in self.manager.players:
            await interaction.response.send_message(
                "You aren't in this lobby!", ephemeral=True
            )
            return
        if interaction.user == self.manager.host:
            await interaction.response.send_message(
                "You're the host of this lobby! If you want to close it, use the Close button.",
                ephemeral=True,
            )
            return
        self.manager.remove_player(interaction.user)
        await self.manager.update_embed()
        await interaction.response.send_message("Left game!", ephemeral=True)

    @button(label="Start", style=discord.ButtonStyle.blurple)
    async def start_game(self, button: Button, interaction: Interaction):
        if interaction.user != self.manager.host:
            await interaction.response.send_message(
                "You're not the host of this lobby!", ephemeral=True
            )
            return
        await interaction.response.defer(invisible=True)
        await self.manager.start_game()

    @button(label="Close", style=discord.ButtonStyle.gray)
    async def close_lobby(self, button: Button, interaction: Interaction):
        if interaction.user != self.manager.host:
            await interaction.response.send_message(
                "You're not the host of this lobby!", ephemeral=True
            )
            return
        await interaction.response.defer(invisible=True)
        await self.manager.delete_embed()


class GameManager:
    def __init__(self, game: GameProtocol, host: discord.Member | None = None):
        self.players: set[discord.Member] = set()
        self.lobby_message: discord.InteractionMessage | None = None
        self.host = host
        if host:
            self.add_player(host)
        self.game = game

    def add_player(self, player: discord.Member):
        self.players.add(player)

    def remove_player(self, player: discord.Member):
        self.players.discard(player)

    def _make_embed(self):
        embed = discord.Embed(
            title=f"{self.game.name} Lobby",
            description=f"Host: {self.host and self.host.mention}",
        )
        embed.add_field(
            name="Players",
            value=f"{len(self.players)}/{self.game.maxPlayers or ":infinity:"} ({", ".join([m.mention for m in self.players])})",
        )
        return embed

    async def send_embed(self, ctx: discord.ApplicationContext) -> None:
        await ctx.respond(embed=self._make_embed(), view=LobbyView(self))
        self.lobby_message = await ctx.interaction.original_response()

    async def update_embed(self):
        if self.lobby_message:
            await self.lobby_message.edit(embed=self._make_embed())

    async def delete_embed(self):
        if self.lobby_message:
            await self.lobby_message.delete()

    async def start_game(self):
        await self.game.run()
