import os

import discord
from dotenv import load_dotenv

from bot import GameBot

intents = discord.Intents.default() + discord.Intents.voice_states
bot = GameBot(intents=intents)


load_dotenv()
bot.bot.run(os.getenv("TOKEN"))
