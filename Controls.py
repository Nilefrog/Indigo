from GameSnake import *
import copy, json, os

__all__ = ["MAX_PLAYERS", "ACTIONS", "ACTION_LABELS", "PLAYER_COLOURS", "Settings", "key_label", "pad_label"]

#==========================================================
# CONTROLS + SETTINGS
#   Every player slot (P1-P4) has its OWN keyboard layout and its OWN controller layout.
#   A layout is a dictionary of  action -> key name  (or button name for controllers), exactly like P1_CONTROLS in the main script.
#   An action set to None is "unbound", it just does nothing.
#   Everything here is saved to settings.json (next to this file) so it is remembered next time you play.
#==========================================================

MAX_PLAYERS = 4

ACTIONS = ("left", "right", "up", "down", "jump", "dash", "parry", "heavy", "light")

ACTION_LABELS = {"left": "Move Left", "right": "Move Right", "up": "Up", "down": "Down",
                 "jump": "Jump", "dash": "Dash", "parry": "Parry", "heavy": "Heavy Attack", "light": "Light Attack"}

#Each player slot has a colour, used for their name tag, damage counter and menus
PLAYER_COLOURS = [(235, 80, 80), (80, 140, 255), (90, 210, 110), (245, 205, 70)]

#Keys the menus need for themselves, so players can't bind them
RESERVED_KEYS = ("escape", "return")

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

_PAD_LABELS = {"left": "Stick/D-pad Left", "right": "Stick/D-pad Right", "up": "Stick/D-pad Up", "down": "Stick/D-pad Down"}


#How a binding is shown on screen
def key_label(key):
    return "none" if not key else key.upper()

def pad_label(name):
    if not name:
        return "none"
    if isinstance(name, (tuple, list)):
        return " / ".join(pad_label(n) for n in name)
    return _PAD_LABELS.get(name, name.upper())


def _blank():
    return {action: None for action in ACTIONS}

#A layout with EVERY action in it (anything missing becomes unbound)
def _full(bindings):
    layout = _blank()
    for action in ACTIONS:
        if bindings and bindings.get(action) is not None:
            layout[action] = bindings[action]
    return layout

#Asks GameSnake whether a name is real. Its input functions raise a ValueError for names that don't exist
def _valid_key(key):
    try:
        Keyboard.held(key)
        return True
    except (ValueError, TypeError, AttributeError):
        return False

def _valid_pad(name):
    try:
        Gamepad.held(0, name)
        return True
    except (ValueError, TypeError, AttributeError):
        return False


class Settings:
    """
    keyboard[slot]  - that player's keyboard layout (None-filled = they have no keyboard keys)
    pad[slot]       - that player's controller layout
    volume, fullscreen
    default_keys / default_pad are what "Reset to default" goes back to.
    """

    def __init__(self, default_keys, default_pad, path=SETTINGS_FILE):
        self.path = path
        keys = [_full(k) for k in default_keys][:MAX_PLAYERS]
        while len(keys) < MAX_PLAYERS:
            keys.append(_blank())                       # players without a default keyboard layout are controller-only until you bind keys
        self.default_keys = keys
        self.default_pad = _full(default_pad)
        self.keyboard = copy.deepcopy(self.default_keys)
        self.pad = [dict(self.default_pad) for _ in range(MAX_PLAYERS)]
        self.volume = 100
        self.fullscreen = False
        self.online_name = "Player"          # shown to other players online
        self.last_address = ""            # the last server you joined
        self.load()

    #---------------- rebinding ----------------

    def has_keyboard(self, slot):
        return any(self.keyboard[slot].values())

    #Binds a key. Returns None if it worked, or a message explaining why it didn't.
    #A key another player already uses is refused. A key YOU already use for something else swaps places with it.
    def set_key(self, slot, action, key):
        if key in RESERVED_KEYS:
            return f"{key_label(key)} is used by the menus"
        if not _valid_key(key):
            return "That key can't be used"
        for other in range(MAX_PLAYERS):
            if other != slot:
                for used_action, used_key in self.keyboard[other].items():
                    if used_key == key:
                        return f"Already used by Player {other + 1} ({ACTION_LABELS[used_action]})"
        mine = self.keyboard[slot]
        for used_action, used_key in mine.items():
            if used_key == key and used_action != action:
                mine[used_action] = mine[action]          # swap, so nothing is ever bound twice
        mine[action] = key
        return None

    #Same idea for controller buttons. Different players have different controllers, so only YOUR OWN layout can clash.
    def set_pad(self, slot, action, name):
        mine = self.pad[slot]
        for used_action, used in mine.items():
            if used == name and used_action != action:
                mine[used_action] = mine[action]
        mine[action] = name

    def reset_keyboard(self, slot):
        self.keyboard[slot] = copy.deepcopy(self.default_keys[slot])

    def reset_pad(self, slot):
        self.pad[slot] = dict(self.default_pad)

    #---------------- applying + saving ----------------

    def apply(self):
        Sound.volume = self.volume
        if Screen.is_fullscreen != self.fullscreen:
            Screen.fullscreen(self.fullscreen)

    def save(self):
        data = {"keyboard": self.keyboard, "pad": self.pad, "volume": self.volume, "fullscreen": self.fullscreen,
                "online_name": self.online_name, "last_address": self.last_address}
        try:
            with open(self.path, "w") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            print(f"Warning!: Could not save settings ({e})")

    #Anything in the file that isn't a real key / button / number is quietly ignored, so a hand-edited file can't crash the game
    def load(self):
        if not os.path.isfile(self.path):
            return
        try:
            with open(self.path) as f:
                data = json.load(f)
            for slot, saved in enumerate(data.get("keyboard", [])[:MAX_PLAYERS]):
                self.keyboard[slot] = self._clean(saved, _valid_key)
            for slot, saved in enumerate(data.get("pad", [])[:MAX_PLAYERS]):
                self.pad[slot] = self._clean(saved, _valid_pad)
            if isinstance(data.get("volume"), (int, float)):
                self.volume = max(0, min(100, int(data["volume"])))
            if isinstance(data.get("fullscreen"), bool):
                self.fullscreen = data["fullscreen"]
            if isinstance(data.get("online_name"), str) and data["online_name"].strip():
                self.online_name = data["online_name"].strip()[:16]
            if isinstance(data.get("last_address"), str):
                self.last_address = data["last_address"][:60]
        except (OSError, ValueError, TypeError, AttributeError) as e:
            print(f"Warning!: Could not read settings ({e}), using the defaults.")

    def _clean(self, saved, is_valid):
        layout = _blank()
        for action in ACTIONS:
            value = saved.get(action)
            if isinstance(value, list):
                value = tuple(value)                      # json turns tuples into lists
            if value is not None and is_valid(value):
                layout[action] = value
        return layout
