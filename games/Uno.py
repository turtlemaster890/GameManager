from .GameProtocol import GameProtocol
class UnoGame(GameProtocol):
    name = "Uno"
    minPlayers = 4

    async def run(self):
        print("uno")