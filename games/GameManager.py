import discord
from discord.ui import Button, View, ViewItem, button

from .GameProtocol import GameProtocol


class LobbyView(View):
    def __init__(
        self,
        manager: "GameManager",
        *items: ViewItem,
        timeout: float | None = 180,
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

    @button(label="Join Lobby", style=discord.ButtonStyle.green)
    async def join_lobby(
        self, button: Button, interaction: discord.interactions.Interaction
    ):
        if not isinstance(interaction.user, discord.Member):
            return
        if interaction.user in self.manager.players:
            await interaction.respond("You're already in this lobby!", ephemeral=True)
            return
        self.manager.add_player(interaction.user)
        await self.manager.update_embed()
        await interaction.respond("Joined game!", ephemeral=True)


class GameManager:
    def __init__(self, game: GameProtocol, host: discord.Member | None = None):
        self.players: set[discord.Member] = set()
        self.lobby_message: discord.Interaction | discord.WebhookMessage | None = None
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

    async def send_embed(self, ctx: discord.ApplicationContext):
        self.lobby_message = await ctx.respond(
            embed=self._make_embed(), view=LobbyView(self)
        )

    async def update_embed(self):
        if self.lobby_message:
            await self.lobby_message.edit(embed=self._make_embed())
