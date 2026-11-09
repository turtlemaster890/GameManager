# GameManager

A modular Discord bot using Pycord that allows users to play games in their own servers!

## Features
- Private Channels: Games automatically create channels for each player, as a way to share information privately
- Multiple Supported Games:
  Uno and Secret Hitler (More to come)
- Server Configurations: Configurable 'games' category for all your channels to go into, per server

## Prerequisites
- Python (Tested with 3.14, unsure if it will work with lower)
- Discord bot token (obtained from the [Discord Developer Portal](https://discord.com/developers/applications))
- Bot Permissions:
  Manage Channels, Manage Roles / Permissions, Send Messages, Embed Links, Use Slash Commands, Connect / Speak (Or just administrator)

## Setup and Installation
1. Clone repo:
```bash
git clone https://github.com/turtlemaster890/gamemanager.git
cd gamemanager
```
2. Create and activate python venv
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOs/Linux:
source venv/bin/activate
```
3. Install Dependencies
```bash
pip install py-cord[voice] python-dotenv
```
4. Environment Configuration
Create a `.env` file in the root directory with
```bash
TOKEN=your_bot_token
```

Or just join my testing server [here](https://discord.gg/evJFQPZsFx)!

## Usage
1. Run Bot
```bash
python main.py
```
2. Configure category channel
```bash
/set_games-category category:<CategoryChannel>
```
3. Start a Game
```bash
/gameroom game:<Uno | SecretHitler>
```
4. Lobby and Game
Players can join and leave using the buttons, the host starts the game with the start button, and can end the game with the end game button to clean up the channels once it's over

## Adding New Games
To add a new game:
1. Subclass GameProtocol
2. Implement `setup()` and `async run()`
3. Register in `Games.py`
