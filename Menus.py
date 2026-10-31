from GameSnake import *
from Controls import *
import pygame
import MatchSystem as ms     # crowns + the renameable match awards

#Really, Really Overly Complicated Menu System, That Is essentially verbatim copied from around the internet.



__all__ = ["MENU_BG", "Item", "Menu", "main_menu", "settings_menu", "controls_menu", "player_controls_menu",
           "character_select", "pause_menu", "awards_menu"]

#==========================================================
# MENUS
#==========================================================

MENU_BG = (18, 18, 28)
WHITE = (240, 240, 245)
GREY = (140, 140, 158)
DARK = (80, 80, 92)
GOLD = (255, 210, 80)
GREEN = (110, 220, 130)
RED = (240, 100, 100)

REPEAT_DELAY = 22          # frames you hold a direction before it starts repeating
REPEAT_RATE = 5            #  repeats every this many frames

_DIRS = ("up", "down", "left", "right")

#The keys that work in every normal menu (arrows OR WASD, enter/space to pick, escape to go back)
_SHARED_KEYS = {"up": ("up", "w"), "down": ("down", "s"), "left": ("left", "a"), "right": ("right", "d"),
                "confirm": ("return", "space"), "back": ("escape", "backspace")}

MENU_FONT = "Pixelart"   # Font changing shecanary (idek how this works, but it does)

_Text = Text
def Text(*args, **kwargs):
    kwargs.setdefault("font", MENU_FONT)
    return _Text(*args, **kwargs)#What the hell is a kwargs

#==========================================================
# INPUT: turns keyboards and controllers into simple menu events
#==========================================================

class Nav:

    def __init__(self, settings=None, profiles=False):
        self.settings, self.profiles = settings, profiles
        self._age = {}
        self._blocked = self._snapshot()

    def _snapshot(self):
        down = set()
        shared = ("key", 0)
        for action, keys in _SHARED_KEYS.items():
            if any(Keyboard.held(key) for key in keys):
                down.add((shared, action))
        if Keyboard.held("return"):
            down.add((shared, "start"))

        for i in range(Gamepad.count):
            pad = ("pad", i)
            for d in _DIRS:
                if Gamepad.held(i, d):
                    down.add((pad, d))
            if Gamepad.held(i, "a"):
                down.add((pad, "confirm"))
            if Gamepad.held(i, ("b", "back")):
                down.add((pad, "back"))
            if Gamepad.held(i, "start"):
                down.add((pad, "start"))

        if self.profiles:
            for slot in range(MAX_PLAYERS):
                keys = self.settings.keyboard[slot]
                profile = ("profile", slot)
                held = lambda *actions: any(keys[a] and Keyboard.held(keys[a]) for a in actions) #This Scares Me Still, Thank the docs for this one
                for d in _DIRS:
                    if held(d):
                        down.add((profile, d))
                if held("jump", "light"):
                    down.add((profile, "confirm"))
                if held("heavy", "parry"):
                    down.add((profile, "back"))
        return down

    def poll(self):
        down = self._snapshot()
        self._blocked &= down
        events = []
        for item in sorted(down - self._blocked, key=repr):
            age = self._age.get(item, 0) + 1
            self._age[item] = age
            repeating = item[1] in _DIRS and age > REPEAT_DELAY and (age - REPEAT_DELAY) % REPEAT_RATE == 0
            if age == 1 or repeating:
                events.append(item)
        for item in list(self._age):
            if item not in down:
                del self._age[item]
        return events


#==========================================================
# A LIST MENU
#==========================================================

class Item: #I found this online, its acctually pretty cool, it allows you to "make a menu item with a label, a result, and optional callbacks for when the item is confirmed or when the left/right keys are pressed. It also has an optional value that can be displayed next to the label, and an enabled flag that determines whether the item can be selected." acording to someone
    def __init__(self, label, result=None, on_confirm=None, on_left=None, on_right=None, value=None, enabled=True):
        self.label, self.result, self.value, self.enabled = label, result, value, enabled
        self.on_confirm, self.on_left, self.on_right = on_confirm, on_left, on_right
        self.box = self.label_text = self.value_text = None


class Menu:
    def __init__(self, title, items, subtitle="", hint="", spacing=56, width=620, top=None, title_colour=WHITE, back_result="back"):
        self.items = items
        self.back_result = back_result        # what escape / B returns. None = they can't back out of this menu
        self.width = width
        self.selected = next((i for i, item in enumerate(items) if item.enabled), 0)
        self._sprites = []
        cx = Screen.width / 2
        if top is None:
            top = max(200, (Screen.height - (len(items) - 1) * spacing) / 2 + 40)

        self._make(Text(title, cx, 80, 64, title_colour, outline=3))
        if subtitle:
            self._make(Text(subtitle, cx, 134, 24, GREY))
        if hint:
            self._make(Text(hint, cx, Screen.height - 26, 20, GREY))
        for i, item in enumerate(items):         # all the Boxes first, so every bit of Text sits on top of them
            item.box = self._make(Box(width, spacing - 6, GOLD, cx, top + i * spacing, alpha=40, border=2, border_colour=GOLD, radius=8))
        for i, item in enumerate(items):
            y = top + i * spacing
            item.label_text = self._make(Text(item.label, cx, y, 34, WHITE))
            item.value_text = self._make(Text("", cx, y, 34, WHITE))
        self._nav = None
        self._refresh()

    def _make(self, sprite):
        self._sprites.append(sprite)
        return sprite

    def _hide(self):
        for s in self._sprites:
            s.visible = False

    def _show(self):
        for s in self._sprites:
            s.visible = True
        self._refresh()

    def close(self):
        for s in self._sprites:
            s.delete()
        self._sprites = []

    #Runs the menu until something closes it. Returns that item's result (None if the window was closed)
    def run(self):
        self._nav = Nav()
        last_mouse = (Mouse.x, Mouse.y)
        result = None
        while Screen.running and result is None:
            Screen.update()
            nav = self._nav
            for device, action in nav.poll():
                if action == "start" and device[0] == "key":     # Enter already counts as "confirm", so don't press it twice
                    continue
                result = self._handle(action)
                if result is not None or self._nav is not nav:   # (a screen opened from here makes a fresh Nav, so the old events are stale)
                    break

            if result is None:
                if (Mouse.x, Mouse.y) != last_mouse:           # the mouse only steals the selection when it actually MOVES
                    last_mouse = (Mouse.x, Mouse.y)
                    for i, item in enumerate(self.items):
                        if item.enabled and item.box.touching_mouse():
                            self.selected = i
                if Mouse.clicked:
                    for i, item in enumerate(self.items):
                        if item.enabled and item.box.touching_mouse():
                            self.selected = i
                            result = self._activate()
            self._refresh()
        self.close()
        return result

    def _handle(self, action):
        item = self.items[self.selected]
        if action == "up":
            self._move(-1)
        elif action == "down":
            self._move(1)
        elif action == "left" and item.on_left:
            item.on_left()
        elif action == "right" and item.on_right:
            item.on_right()
        elif action in ("confirm", "start"):
            return self._activate()
        elif action == "back":
            return self.back_result
        return None

    def _move(self, step):
        for _ in range(len(self.items)):
            self.selected = (self.selected + step) % len(self.items)
            if self.items[self.selected].enabled:
                return

    def _activate(self):
        item = self.items[self.selected]
        if not item.enabled:
            return None
        if item.result is not None:
            return item.result
        if item.on_confirm:
            self._hide()
            item.on_confirm()
            self._nav = Nav()
            self._show()
        return None

    def _refresh(self):
        cx = Screen.width / 2
        left, right = cx - self.width / 2 + 28, cx + self.width / 2 - 28
        for i, item in enumerate(self.items):
            selected = i == self.selected
            colour = WHITE if selected else (GREY if item.enabled else DARK)
            item.box.visible = selected
            item.label_text.colour = colour
            item.label_text.text = item.label
            if item.value is None:                               # a lone label is centred
                item.label_text.x = cx
                item.value_text.visible = False
            else:                                                # a label with a value is split left / right
                value = str(item.value())
                if selected and (item.on_left or item.on_right):
                    value = f"<  {value}  >"
                item.value_text.text = value
                item.value_text.colour = GOLD if selected else colour
                item.value_text.visible = True
                item.label_text.x = left + item.label_text.width / 2
                item.value_text.x = right - item.value_text.width / 2


#==========================================================
# MAIN MENU + SETTINGS
#==========================================================

def main_menu(settings, title="PLATFORM FIGHTER"):
    items = [Item("Play", result="play"),
             Item("Online", result="online"),
             Item("Settings", on_confirm=lambda: settings_menu(settings)),
             Item("Quit", result="quit")]
    return Menu(title, items, hint="Arrows / WASD / controller to move     Enter / Space / A to pick",
                spacing=68, width=420, back_result=None).run()


def settings_menu(settings):
    def toggle_fullscreen():
        settings.fullscreen = not settings.fullscreen
        settings.apply()

    def change_volume(step):
        settings.volume = max(0, min(100, settings.volume + step))
        settings.apply()

    def cycle_volume():                                          # pressing confirm on the slider steps up, then wraps round to 0
        settings.volume = 0 if settings.volume >= 100 else min(100, settings.volume + 10)
        settings.apply()

    items = [Item("Controls", on_confirm=lambda: controls_menu(settings)),
             Item("Fullscreen", value=lambda: "On" if settings.fullscreen else "Off",
                  on_confirm=toggle_fullscreen, on_left=toggle_fullscreen, on_right=toggle_fullscreen),
             Item("Volume", value=lambda: f"{settings.volume}%",
                  on_confirm=cycle_volume, on_left=lambda: change_volume(-10), on_right=lambda: change_volume(10)),
             Item("Award Names", on_confirm=awards_menu),
             Item("Back", result="back")]
    Menu("Settings", items, hint="Left / Right to change     Esc to go back", spacing=64, width=520).run()
    settings.save()


def controls_menu(settings):
    def summary(slot):
        return "Keyboard + Controller" if settings.has_keyboard(slot) else "Controller only"

    items = [Item(f"Player {slot + 1}", value=lambda s=slot: summary(s),
                  on_confirm=lambda s=slot: player_controls_menu(settings, s)) for slot in range(MAX_PLAYERS)]
    items.append(Item("Back", result="back"))
    Menu("Controls", items, subtitle="Every player has their own keyboard and controller layout",
         hint="Pick a player to change their controls     Esc to go back", spacing=64, width=700).run()


def player_controls_menu(settings, slot):
    tab = ["keyboard"]                                           # a list, so the little functions below can change it

    def flip_tab():
        tab[0] = "pad" if tab[0] == "keyboard" else "keyboard"

    def binding(action):
        if tab[0] == "keyboard":
            return key_label(settings.keyboard[slot][action])
        return pad_label(settings.pad[slot][action])

    def reset():
        if tab[0] == "keyboard":
            settings.reset_keyboard(slot)
        else:
            settings.reset_pad(slot)

    items = [Item("Device", value=lambda: "Keyboard" if tab[0] == "keyboard" else "Controller",
                  on_confirm=flip_tab, on_left=flip_tab, on_right=flip_tab)]
    for action in ACTIONS:
        items.append(Item(ACTION_LABELS[action], value=lambda a=action: binding(a),
                          on_confirm=lambda a=action: _capture(settings, slot, a, tab[0])))
    items.append(Item("Reset to Default", on_confirm=reset))
    items.append(Item("Back", result="back"))
    Menu(f"Player {slot + 1} Controls", items, hint="Left / Right: keyboard or controller     Enter: change a control     Esc: back",
         spacing=42, width=620, title_colour=PLAYER_COLOURS[slot]).run()
    settings.save()


#Waits for the player to press the key / button they want. Escape cancels. Returns True if something was bound.
def _capture(settings, slot, action, device):
    cx, cy = Screen.width / 2, Screen.height / 2
    sprites = [Box(Screen.width, Screen.height, "black", cx, cy, alpha=235),
               Text(ACTION_LABELS[action].upper(), cx, cy - 80, 60, PLAYER_COLOURS[slot], outline=3),
               Text("Press a key..." if device == "keyboard" else "Press a controller button...", cx, cy, 36, WHITE),
               Text("Esc to cancel", cx, cy + 60, 22, GREY)]
    message = Text("", cx, cy + 115, 28, RED)
    sprites.append(message)

    bound = False
    while Screen.running and not bound:
        Screen.update()
        if Keyboard.pressed("escape"):
            break
        if device == "keyboard":
            for key in Keyboard.pressed_keys():
                error = settings.set_key(slot, action, key)
                if error:
                    message.text = error
                else:
                    bound = True
                    break
        elif Gamepad.count == 0:
            message.text = "No controller detected, plug one in!"
        else:
            name = Gamepad.any_pressed()
            if name:
                settings.set_pad(slot, action, name)
                bound = True
    for s in sprites:
        s.delete()
    return bound


#==========================================================
# AWARD NAMES  (Settings > Award Names)
#   Players can type their own name for every match award, e.g. "Gravity's Biggest Fan" -> "Best At Falling".
#   They're saved in records.json and show up on the match end screen.
#==========================================================

#What shift turns each key into (letters just become capitals)
_SHIFTED = {"1": "!", "2": "@", "3": "#", "4": "$", "5": "%", "6": "^", "7": "&", "8": "*", "9": "(", "0": ")",
            "-": "_", "=": "+", "'": '"', ";": ":", ",": "<", ".": ">", "/": "?"}
_PLAIN_KEYS = set("abcdefghijklmnopqrstuvwxyz0123456789-=',.;/")


#Reads this frame's typed characters from the keyboard. Returns (characters, backspace_pressed, enter_pressed, escape_pressed)
def _typed_this_frame():
    shift = bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)
    chars, backspace, enter, escape = "", False, False, False
    for name in Keyboard.pressed_keys():
        if len(name) == 3 and name[0] == "[" and name[2] == "]" and name[1].isdigit():   # number pad keys are called "[1]"
            name = name[1]
        if name == "space":
            chars += " "
        elif name == "backspace":
            backspace = True
        elif name in ("return", "enter"):
            enter = True
        elif name == "escape":
            escape = True
        elif name in _PLAIN_KEYS:
            chars += (name.upper() if name.isalpha() else _SHIFTED.get(name, name)) if shift else name
    return chars, backspace, enter, escape


#Pops up a box where the player types. Enter saves, Escape cancels. Returns the new text, or None if they cancelled.
def _text_entry(prompt, current, hint_text="", max_len=ms.AWARD_MAX_LEN):
    cx, cy = Screen.width / 2, Screen.height / 2
    sprites = [Box(Screen.width, Screen.height, "black", cx, cy, alpha=235),
               Text(prompt, cx, cy - 130, 40, GOLD, outline=3)]
    if hint_text:
        sprites.append(Text(hint_text, cx, cy - 80, 22, GREY))
    sprites.append(Box(820, 70, WHITE, cx, cy, alpha=25, border=3, border_colour=GOLD, radius=10))
    field = Text("", cx, cy, 44, WHITE, outline=2)
    count = Text("", cx + 340, cy + 56, 20, GREY)
    sprites += [field, count,
                Text("Type on the keyboard     Enter: save     Esc: cancel     Leave it blank to go back to the default", cx, cy + 110, 22, GREY)]

    text, frame, held_backspace = current, 0, 0
    result = None
    done = False
    while Screen.running and not done:
        Screen.update()
        chars, backspace, enter, escape = _typed_this_frame()
        if escape:
            done = True
        elif enter:
            result, done = text, True
        else:
            for c in chars:
                if len(text) < max_len:
                    text += c
            if backspace:
                text = text[:-1]
            if Keyboard.held("backspace"):                     # holding backspace keeps deleting
                held_backspace += 1
                if held_backspace > 25 and held_backspace % 3 == 0:
                    text = text[:-1]
            else:
                held_backspace = 0
        frame += 1
        field.text = text + ("|" if (frame // 30) % 2 == 0 else " ")
        field.x = cx
        count.text = f"{len(text)} / {max_len}"
        count.x = cx + 410 - count.width / 2
    for s in sprites:
        s.delete()
    return result


def awards_menu():
    def rename(key, what):
        new = _text_entry(f"Rename:  {what}", ms.records.award_label(key), "Shown on the match end screen")
        if new is not None:
            ms.records.set_award_name(key, new)

    def reset_all():
        ms.records.reset_award_names()

    items = [Item(what, value=lambda k=key: ms.records.award_label(k),
                  on_confirm=lambda k=key, w=what: rename(k, w))
             for key, _, what, _, _ in ms.AWARD_DEFS]
    items.append(Item("Reset All to Default", on_confirm=reset_all))
    items.append(Item("Back", result="back"))
    Menu("Award Names", items, subtitle="Pick an award to type your own name for it",
         hint="Enter: rename (keyboard needed to type)     Esc: back", spacing=60, width=1000, title_colour=GOLD).run()


#==========================================================
# PAUSE
#==========================================================

def pause_menu():
    dim = Box(Screen.width, Screen.height, "black", Screen.width / 2, Screen.height / 2, alpha=170)    # made first, so it sits BEHIND the menu's text
    items = [Item("Resume", result="resume"), Item("Quit to Menu", result="quit")]
    result = Menu("Paused", items, hint="Esc to resume", spacing=68, width=420, back_result="resume").run()
    dim.delete()
    return result


#==========================================================
# CHARACTER SELECT
#   Up to 4 players. Each joins with their own keyboard layout or controller, moves their own cursor, and locks in.
#   Characters come from the dictionary you pass in (name -> class). Each class can define:
#       title (shown name), blurb (one line), preview (sprite name), preview_size (percent)
#   so adding a character to the game adds it to this screen automatically.
#==========================================================

def character_select(settings, characters):
    W, H = Screen.width, Screen.height
    names = list(characters)
    tiles = names + ["Random"]
    count = len(tiles)
    sprites = []

    def make(sprite):
        sprites.append(sprite)
        return sprite

    def title_of(tile):
        return tile if tile == "Random" else getattr(characters[tile], "title", tile)

    def blurb_of(tile):
        return "Let fate decide." if tile == "Random" else getattr(characters[tile], "blurb", "")

    #---------- layout ----------
    make(Text("Choose Your Fighter", W / 2, 60, 56, WHITE, outline=3))
    status = make(Text("", W / 2, 118, 26, GREY))
    make(Text("Join / pick: Jump or Light     Back: Heavy or Parry     Controller: A / B     Esc: main menu", W / 2, H - 26, 20, GREY))

    cols = min(count, 5)
    rows = -(-count // cols)
    gap, tile_w = 22, 170
    top, bottom = 150, 440
    tile_h = min(190, (bottom - top - (rows - 1) * gap) // rows)
    first_x = (W - (cols * tile_w + (cols - 1) * gap)) / 2 + tile_w / 2
    first_y = top + ((bottom - top) - (rows * tile_h + (rows - 1) * gap)) / 2 + tile_h / 2

    def tile_pos(i):
        return first_x + (i % cols) * (tile_w + gap), first_y + (i // cols) * (tile_h + gap)

    tile_boxes = [make(Box(tile_w, tile_h, GREY, *tile_pos(i), alpha=18, border=2, border_colour=GREY, radius=12)) for i in range(count)]

    for i, tile in enumerate(tiles):
        x, y = tile_pos(i)
        if tile == "Random":
            make(Text("?", x, y - 20, 90, GREY))
        else:
            cls = characters[tile]
            try:
                preview = make(Sprite(getattr(cls, "preview", "player"), x, y - 20, size=getattr(cls, "preview_size", 300)))
                preview.fixed = True
            except FileNotFoundError:                            # a character with no art yet still gets a tile
                make(Text(tile[:1], x, y - 20, 90, GREY))
        make(Text(title_of(tile), x, y + tile_h / 2 - 42, 26, WHITE))

    tags = [make(Text("", 0, 0, 26, PLAYER_COLOURS[s], outline=2)) for s in range(MAX_PLAYERS)]
    for tag in tags:
        tag.visible = False

    pgap = 20
    pw = (W - pgap * (MAX_PLAYERS + 1)) / MAX_PLAYERS
    py = H - 165
    panels, headers, devices, bodies, subs = [], [], [], [], []
    for s in range(MAX_PLAYERS):
        px = pgap + pw / 2 + s * (pw + pgap)
        panels.append(make(Box(pw, 180, GREY, px, py, alpha=18, border=2, border_colour=GREY, radius=12)))
        headers.append(make(Text(f"PLAYER {s + 1}", px, py - 68, 30, PLAYER_COLOURS[s])))
        if ms.records.crown_slot == s:                       # whoever won the last match wears the crown
            make(ms.Crown(headers[-1].x - headers[-1].width / 2 - 26, py - 70, 38))
        devices.append(make(Text("", px, py - 40, 20, GREY)))
        bodies.append(make(Text("", px, py - 4, 24, GREY, wrap=int(pw - 30))))
        subs.append(make(Text("", px, py + 50, 19, GREY, wrap=int(pw - 30))))

    #---------- state ----------
    joined = {}

    def free_slot():
        return next((s for s in range(MAX_PLAYERS) if s not in joined), None)

    def join_prompt(slot):
        keys = settings.keyboard[slot]
        key = keys["jump"] or keys["light"]
        if key:
            return f"Press {key_label(key)} to join\n(or A on a controller)"
        return "Press A on a controller to join"

    def all_ready():
        return len(joined) >= 2 and all(p["locked"] for p in joined.values())

    def move_cursor(p, action):
        i = p["cursor"]
        if action == "left":
            i = (i - 1) % count
        elif action == "right":
            i = (i + 1) % count
        elif action == "down":
            i = i + cols if i + cols < count else i % cols
        elif action == "up":
            i = i - cols if i - cols >= 0 else i + cols * ((count - 1 - i) // cols)
        p["cursor"] = i

    def finish():
        picks = []
        for slot in sorted(joined):
            tile = tiles[joined[slot]["cursor"]]
            if tile == "Random":
                tile = names[random_number(0, len(names) - 1)]
            picks.append({"slot": slot, "character": tile, "device": joined[slot]["device"]})
        return picks

    def refresh():
        on_tile = {}
        for slot in sorted(joined):
            on_tile.setdefault(joined[slot]["cursor"], []).append(slot)
        for i, box in enumerate(tile_boxes):
            here = on_tile.get(i)
            colour = PLAYER_COLOURS[here[0]] if here else GREY
            box.colour, box.border_colour = colour, colour
            box.alpha, box.border = (55, 4) if here else (18, 2)

        for slot in range(MAX_PLAYERS):
            p = joined.get(slot)
            colour = PLAYER_COLOURS[slot] if p else GREY
            panels[slot].colour = panels[slot].border_colour = colour
            panels[slot].alpha = (70 if p["locked"] else 30) if p else 18
            tags[slot].visible = p is not None
            if p is None:
                devices[slot].text = ""
                bodies[slot].text, bodies[slot].font_size, bodies[slot].colour = join_prompt(slot), 22, GREY
                subs[slot].text = ""
                continue
            tile = tiles[p["cursor"]]
            here = on_tile[p["cursor"]]
            tx, ty = tile_pos(p["cursor"])
            tags[slot].text = f"[P{slot + 1}]" if p["locked"] else f"P{slot + 1}"
            tags[slot].go_to(tx + (here.index(slot) - (len(here) - 1) / 2) * 58, ty + tile_h / 2 - 16)
            devices[slot].text = "Keyboard" if p["device"][0] == "profile" else f"Controller {p['device'][1] + 1}"
            bodies[slot].text, bodies[slot].font_size, bodies[slot].colour = title_of(tile), 38, WHITE
            if p["locked"]:
                subs[slot].text, subs[slot].colour = "READY", GREEN
            else:
                subs[slot].text, subs[slot].colour = blurb_of(tile), GREY

        if all_ready():
            status.text, status.colour = "Everyone is ready! Press Enter, Start, or confirm again to fight", GREEN
        elif len(joined) < 2:
            status.text, status.colour = "Join with your keyboard or a controller. At least 2 players needed", GREY
        else:
            status.text, status.colour = "Waiting for everyone to lock in...", GOLD

    #---------- loop ----------
    nav = Nav(settings, profiles=True)
    result, done = None, False
    refresh()
    while Screen.running and not done:
        Screen.update()
        for device, action in nav.poll():
            kind = device[0]
            if kind == "key":
                if action == "back":
                    done = True
                elif action == "start" and all_ready():
                    result, done = finish(), True
                continue

            slot = next((s for s, p in joined.items() if p["device"] == device), None)
            if slot is None:                                     # not playing yet
                if action == "confirm":
                    slot = device[1] if kind == "profile" else free_slot()
                    if slot is not None and slot not in joined:
                        joined[slot] = {"device": device, "cursor": slot % len(names), "locked": False}
                elif action == "back" and not joined:
                    done = True
                continue

            p = joined[slot]
            if action in _DIRS:
                if not p["locked"]:
                    move_cursor(p, action)
            elif action == "confirm":
                if not p["locked"]:
                    p["locked"] = True
                elif all_ready():
                    result, done = finish(), True
            elif action == "start":
                if all_ready():
                    result, done = finish(), True
            elif action == "back":
                if p["locked"]:
                    p["locked"] = False
                else:
                    del joined[slot]
            if done:
                break
        refresh()

    for s in sprites:
        s.delete()
    return result