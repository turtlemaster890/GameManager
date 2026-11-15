from enum import Enum

from .RockPaperScissors import RockPaperScissorsGame
from .SecretHitler import SecretHitlerGame
from .Uno import UnoGame
from .Werewolf import WerewolfGame


class Games(Enum):
    Uno = UnoGame
    SecretHitler = SecretHitlerGame
    Werewolf = WerewolfGame
    RockPaperScissors = RockPaperScissorsGame
