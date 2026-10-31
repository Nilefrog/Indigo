# Indigo

A simple platform fighter built with Python and Pygame.

## Download

Download the latest release from the [Releases](https://github.com/Nilefrog/Indigo/releases) page.

## Features

- Local and online multiplayer
- Up to 4 players
- Keyboard and controller support
- Customisable controls
- Multiple stages
- Character selection
- Parrying and combat mechanics
- Customisable match settings

## Characters

Indigo has 8 playable characters, each with their own moves and mechanics.

See [CHARACTERS.md](CHARACTERS.md) for the full character and moveset reference.

## Running from Source

Requires Python.

Clone the repository:

```bash
git clone https://github.com/Nilefrog/Indigo.git
cd Indigo
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Launch the game:

```bash
python Platform_Fighter.py
```

## Online Multiplayer

Indigo supports online multiplayer through hosted lobbies.

You can host a game directly from the Online menu or connect to an existing server.

For dedicated server hosting:

```bash
python Server.py
```

The server uses port `7777` by default. You can specify a different port:

```bash
python Server.py 9000
```

## Building

Indigo can be compiled using PyInstaller:

```bash
pyinstaller Platform_Fighter.spec
```

## License

This project is licensed under the MIT License.
