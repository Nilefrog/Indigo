# Indigo

A simple platform fighter built with Python and Pygame.

# Download

Download the latest release from the [Releases](https://github.com/Nilefrog/Indigo/releases) page.

## Features

- Local and online multiplayer
- Training mode: practice against a dummy with a combo counter
- Up to 4 players
- Keyboard and controller support
- Use phones as wireless controllers that also show the game screen
- Customisable controls
- Multiple stages
- Character selection
- Parrying and combat mechanics
- Customisable match settings

## Characters

Indigo has 9 playable characters, each with their own moves and mechanics.

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

## Phones as Controllers (Same Wi-Fi)

Run the game on a computer and use phones as wireless controllers. Nothing to install on the phone, and no internet is needed, just the same Wi-Fi. The phone also shows the game, so it works as a handheld screen and controller in one.

1. On the computer open **Phone Controllers** from the main menu. It shows an address and a QR code.
2. On each phone (joined to the same Wi-Fi) scan the code or type the address into the browser. Hold the phone sideways.
3. On the character screen press **OK** on the phone to join, like any controller. Up to 8 phones can connect (the game itself is 4 players).

During a fight the phone shows a direction pad, Jump, Light, Heavy, Dash, Parry and a pause button over the game picture. Everywhere else it shows the pad, OK, BACK and START. The edge of the phone's screen takes the colour of its player. The **SCREEN** button (top left) turns the picture off if you'd rather watch the computer. You can mix phones, keyboards and controllers.

Notes:

- The address contains a short random key, so only people you show it to can connect. It changes every time the game starts.
- The first time, Windows or macOS may ask whether to allow the game on the network. Say yes (private networks is enough).
- If the phone can't connect, check that it isn't on a guest Wi-Fi (those often block devices from seeing each other), and that the computer's firewall allows the game.
- The picture is sent as small JPEGs (about 20 a second). A phone on a slow connection is skipped rather than slowing the game down. Expect a small delay, so keep playing off the computer's screen if you need it to be perfectly in time.
- `pip install qrcode` shows the scan-able code on the computer's screen. Without it, type the address in.

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
