"""
MatchSystem.py  -  everything AROUND a fight: rules, lives (stocks), stats, crowns and the screens that go with them.

Platform_Fighter.py imports this as `ms`. It uses GameSnake only (no Menus / Controls), so it also works on its own.

  Rules          -> what kind of match it is (stocks, time limit, damage rate...). Saved between sessions.
  PlayerStats    -> one per fighter: kills, deaths, self destructs, damage, hits, parries, streaks...
  MatchResult    -> everything the results screen needs once a match is over
  Records        -> lifetime wins + WHO HOLDS THE CROWN (saved to records.json next to this file)
  Crown          -> a little gold crown sprite you can drop anywhere (match tags, results, character select)
  rules_menu()   -> the rules screen shown before a match
  countdown()    -> 3 - 2 - 1 - FIGHT!
  results_screen() -> the match end screen with the stats table
  KillFeed / Banner / MatchClock -> small in-match UI helpers
"""
import os
import json
import textwrap
import pygame
import GameSnake
from GameSnake import *

FPS = 60
CREDIT_FRAMES = 300         # a self destruct only counts as a KO if someone hit you in the last 5 seconds
SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "records.json")
GOLD = (255, 205, 50)


class State:
    frame = 0               # match frame counter (run_match bumps it every frame the game actually advances)


def fmt_time(frames):
    seconds = int(frames // FPS)
    return f"{seconds // 60}:{seconds % 60:02d}"


# ==========================================================
# RULES
# ==========================================================

# (attribute, label shown, [(shown value, real value), ...], description)
RULE_OPTIONS = [
    ("mode", "Mode", [("Stock", "Stock"), ("Time Attack", "Time Attack")],
     "Stock: lose all your lives and you're out.  Time Attack: respawn forever, most points when time runs out wins."),
    ("stocks", "Stocks (Lives)", [(str(n), n) for n in range(1, 11)],
     "How many lives everyone starts with. (Stock mode only)"),
    ("minutes", "Time Limit", [("Off", 0), ("1:00", 1), ("2:00", 2), ("3:00", 3), ("5:00", 5), ("8:00", 8)],
     "When time is up the player with the most stocks (fewest damage on a tie) wins. Time Attack always needs a limit."),
    ("damage_mult", "Damage Rate", [("50%", 0.5), ("100%", 1.0), ("150%", 1.5), ("200%", 2.0)],
     "Multiplies all damage dealt. Higher = people fly further, sooner."),
    ("start_damage", "Starting Damage", [("0%", 0), ("50%", 50), ("100%", 100), ("150%", 150)],
     "Everyone starts the match with this much damage already on them."),
    ("shield", "Respawn Shield", [("Off", 0), ("1s", 1), ("2s", 2), ("3s", 3)],
     "Seconds of invincibility after respawning (you'll blink while it lasts)."),
    ("sudden_death", "Sudden Death", [("On", True), ("Off", False)],
     "A tie when the timer ends (or a double KO on the last stock) is settled with one life each at 300% damage."),
]


class Rules:
    def __init__(self):
        self.mode = "Stock"
        self.stocks = 3
        self.minutes = 0            # 0 = no time limit
        self.damage_mult = 1.0
        self.start_damage = 0
        self.shield = 2             # seconds
        self.sudden_death = True

    @property
    def is_stock(self):
        return self.mode == "Stock"

    @property
    def time_limit_frames(self):    # 0 = no limit
        minutes = self.minutes
        if self.mode == "Time Attack" and minutes == 0:
            minutes = 3             # Time Attack can't run forever
        return minutes * 60 * FPS

    @property
    def shield_frames(self):
        return int(self.shield * FPS)

    def to_dict(self):
        return {key: getattr(self, key) for key, *_ in RULE_OPTIONS}

    def load(self, data):
        for key, _, values, _ in RULE_OPTIONS:
            if key in data and data[key] in [v for _, v in values]:
                setattr(self, key, data[key])

    def summary(self):
        if self.mode == "Stock":
            text = f"Stock match  -  {self.stocks} {'life' if self.stocks == 1 else 'lives'}"
        else:
            text = "Time Attack"
        if self.time_limit_frames:
            text += f"  -  {fmt_time(self.time_limit_frames)} limit"
        return text


# ==========================================================
# STATS
# ==========================================================

class PlayerStats:
    def __init__(self, slot, character, colour, stocks):
        self.slot, self.character, self.colour = slot, character, colour
        self.kills = 0
        self.deaths = 0
        self.self_destructs = 0         # "SD" - died without anyone recently hitting you
        self.damage_dealt = 0.0
        self.damage_taken = 0.0
        self.hits = 0
        self.parries = 0
        self.streak = 0
        self.best_streak = 0
        self.score = 0                  # Time Attack: kills - self destructs
        self.stocks = stocks
        self.invuln = 0                 # frames of respawn shield left
        self.out_order = None           # set when eliminated (later = lasted longer)
        self.final_health = 0
        self.last_attacker = None       # the PlayerStats of whoever hit this player last...
        self.last_attacker_frame = -99999   # ...and when
        self.life_start = 0
        self.longest_life = 0


class MatchResult:
    def __init__(self, stats, winners, rules, frames, sudden_death):
        self.stats = stats              # every fighter, best placed first
        self.winners = winners          # list of slots. One = a winner, several = a draw
        self.rules = rules
        self.frames = frames
        self.sudden_death = sudden_death
        self.map_name = ""              # filled in by the game after the match

    @property
    def draw(self):
        return len(self.winners) != 1


def record_hit(attacker, target, damage):
    """Called from Hitbox.hit every time damage really lands."""
    t = getattr(target, "stats", None)
    a = getattr(attacker, "stats", None)
    if t is None:
        return
    t.damage_taken += damage
    if a is not None and a is not t:
        a.damage_dealt += damage
        a.hits += 1
        t.last_attacker = a
        t.last_attacker_frame = State.frame


def credit_ko(stats, stock_mode, all_stats):
    """Works out who gets the kill for a death. Returns a list of (message, colour) for the kill feed."""
    out = []
    killer = stats.last_attacker
    if killer is not None and State.frame - stats.last_attacker_frame > CREDIT_FRAMES:
        killer = None
    stats.deaths += 1
    stats.streak = 0
    stats.longest_life = max(stats.longest_life, State.frame - stats.life_start)
    stats.life_start = State.frame
    stats.last_attacker = None
    if stock_mode:
        stats.stocks -= 1
    first_blood = sum(s.kills for s in all_stats) == 0

    if killer is not None and killer is not stats:
        killer.kills += 1
        killer.streak += 1
        killer.best_streak = max(killer.best_streak, killer.streak)
        killer.score += 1
        out.append((f"P{killer.slot + 1}  KO'd  P{stats.slot + 1}", killer.colour))
        if first_blood:
            out.append(("FIRST BLOOD!", killer.colour))
        if killer.streak >= 3:
            out.append((f"P{killer.slot + 1} is on a {killer.streak} KO streak!", killer.colour))
    else:
        stats.self_destructs += 1
        stats.score -= 1
        out.append((f"P{stats.slot + 1}  self-destructed", stats.colour))
    return out


def rank(stats_list, winners, stock_mode):
    """Best placed first."""
    def key(s):
        if s.slot in winners:
            return (0, 0, 0, 0)
        if s.out_order is None:
            if stock_mode:
                return (1, -s.stocks, s.final_health, -s.kills)
            return (1, -s.score, s.deaths, 0)
        return (2, -s.out_order, -s.score, s.deaths)
    return sorted(stats_list, key=key)


def leaders(players, stock_mode):
    """The player(s) in front right now (used when the clock runs out)."""
    def key(p):
        s = p.stats
        return (s.stocks, -p.health) if stock_mode else (s.score, -s.deaths)
    best = max(key(p) for p in players)
    return [p for p in players if key(p) == best]


# (key, stat it is won with, what it's for (shown in the settings menu), default name, minimum value to win it)
AWARD_DEFS = [
    ("damage",   "damage_dealt",   "Most damage dealt",    "Heavy Hitter",          1),
    ("parry",    "parries",        "Most parries",         "Parry Master",          1),
    ("streak",   "best_streak",    "Longest KO streak",    "Streak King",           2),
    ("fall",     "self_destructs", "Most self-destructs",  "Gravity's Biggest Fan", 1),
    ("bag",      "damage_taken",   "Most damage taken",    "Punching Bag",          1),
]
AWARD_MAX_LEN = 24


def build_awards(stats):
    """Returns [(award name, PlayerStats, value)]. The names are whatever the players typed in Settings > Award Names."""
    awards = []
    for key, attr, _, _, minimum in AWARD_DEFS:
        top = max(stats, key=lambda s: getattr(s, attr))
        value = getattr(top, attr)
        if value >= minimum and sum(1 for s in stats if getattr(s, attr) == value) == 1:
            awards.append((records.award_label(key), top, int(value)))
    return awards[:4]


# ==========================================================
# RECORDS + CROWN
# ==========================================================

class Records:
    """Lifetime wins and the crown. ONE player wears the crown at a time: whoever won the last match."""
    def __init__(self):
        self.crown_slot = None
        self.crown_character = None
        self.wins = [0, 0, 0, 0]
        self.matches = [0, 0, 0, 0]
        self.rules = {}
        self.map_choice = 0             # last tile picked on the map select screen (len(maps) = Random)
        self.award_names = {}           # award key -> the name the players typed (missing = default)
        self.load()

    def load(self):
        try:
            with open(SAVE_FILE, "r") as f:
                data = json.load(f)
            self.crown_slot = data.get("crown_slot")
            self.crown_character = data.get("crown_character")
            self.wins = (list(data.get("wins", [])) + [0] * 4)[:4]
            self.matches = (list(data.get("matches", [])) + [0] * 4)[:4]
            self.rules = data.get("rules", {})
            self.map_choice = int(data.get("map_choice", 0))
            self.award_names = {k: v for k, v in data.get("award_names", {}).items() if isinstance(v, str)}
        except Exception:
            pass                        # no save yet (or a broken one): start fresh

    def save(self):
        try:
            with open(SAVE_FILE, "w") as f:
                json.dump({"crown_slot": self.crown_slot, "crown_character": self.crown_character,
                           "wins": self.wins, "matches": self.matches, "rules": self.rules,
                           "award_names": self.award_names, "map_choice": self.map_choice}, f, indent=2)
        except Exception as error:
            print("Couldn't save records:", error)

    def award(self, result):
        for s in result.stats:
            self.matches[s.slot] += 1
        if not result.draw:
            winner = next(s for s in result.stats if s.slot == result.winners[0])
            self.wins[winner.slot] += 1
            self.crown_slot = winner.slot
            self.crown_character = winner.character
        self.save()

    def save_rules(self, rules):
        self.rules = rules.to_dict()
        self.save()

    def set_map_choice(self, tile):
        self.map_choice = tile
        self.save()

    def award_label(self, key):
        default = next(d for k, _, _, d, _ in AWARD_DEFS if k == key)
        return self.award_names.get(key) or default

    def set_award_name(self, key, text):
        text = " ".join(text.split())[:AWARD_MAX_LEN]       # tidy spaces, cap the length
        if text:
            self.award_names[key] = text
        else:
            self.award_names.pop(key, None)                 # blank = back to the default
        self.save()

    def reset_award_names(self):
        self.award_names = {}
        self.save()

    def clear_crown(self):
        self.crown_slot = None
        self.crown_character = None
        self.save()


records = Records()


def load_rules():
    rules = Rules()
    rules.load(records.rules)
    return rules


class Crown(GameSnake._Drawn):
    """A gold crown. Use it like any sprite:   Crown(x, y, 56)   then .go_to(), .hide(), .delete()
    fixed=True sticks it to the screen (menus), fixed=False puts it in the world (above a player)."""
    _LOOKS = ("px",)

    def __init__(self, x=None, y=None, px=48, fixed=True):
        self.px = px
        super().__init__("crown", x, y, fixed)

    def _render(self):
        w = max(8, int(self.px))
        h = max(6, int(self.px * 0.8))
        image = pygame.Surface((w, h), pygame.SRCALPHA)
        points = [(0.08, 0.95), (0.02, 0.18), (0.27, 0.52), (0.50, 0.05), (0.73, 0.52), (0.98, 0.18), (0.92, 0.95)]
        shape = [(int(px * (w - 1)), int(py * (h - 1))) for px, py in points]
        pygame.draw.polygon(image, GOLD, shape)
        pygame.draw.polygon(image, (140, 95, 0), shape, max(1, w // 24))
        band = max(1, int(h * 0.18))
        pygame.draw.rect(image, (200, 150, 20), (int(0.09 * w), int(0.74 * h), int(0.82 * w), band))
        for px, py, colour in ((0.02, 0.18, (230, 60, 70)), (0.50, 0.05, (90, 200, 255)), (0.98, 0.18, (230, 60, 70))):
            pygame.draw.circle(image, colour, (int(px * (w - 1)), int(py * (h - 1)) + max(2, w // 18)), max(2, w // 14))
        return [("crown", image)]


# ==========================================================
# INPUT + SCREEN HELPERS
# ==========================================================

def read_nav():
    """Menu input from the keyboard AND every controller."""
    nav = dict.fromkeys(("up", "down", "left", "right", "ok", "back"), False)
    keys = (("up", ("up", "w")), ("down", ("down", "s")), ("left", ("left", "a")), ("right", ("right", "d")),
            ("ok", ("return", "space")), ("back", ("escape", "backspace")))
    for name, options in keys:
        if any(Keyboard.pressed(k) for k in options):
            nav[name] = True
    pads = (("up", "up"), ("down", "down"), ("left", "left"), ("right", "right"), ("ok", "a"), ("back", "b"))
    for slot in range(Gamepad.count):
        for name, button in pads:
            if Gamepad.pressed(slot, button):
                nav[name] = True
    return nav


class _Layer:
    """Keeps track of every sprite a screen makes, so they can all be deleted in one go."""
    def __init__(self):
        self.items = []

    def text(self, s, x, y, size=32, colour="white", anchor="center", outline=2, bold=False):
        t = Text(s, x, y, size, colour, bold=bold, outline=outline)
        if anchor == "left":
            t.x = x + t.width / 2
        elif anchor == "right":
            t.x = x - t.width / 2
        self.items.append(t)
        return t

    def box(self, w, h, colour, x, y, alpha=255, border=0, border_colour="white", radius=0):
        b = Box(w, h, colour, x, y, alpha=alpha, border=border, border_colour=border_colour, radius=radius)
        self.items.append(b)
        return b

    def add(self, sprite):
        self.items.append(sprite)
        return sprite

    def clear(self):
        for item in self.items:
            try:
                item.delete()
            except ValueError:
                pass
        self.items = []


MENU_DARK = (16, 16, 26)


# ==========================================================
# RULES MENU
# ==========================================================

def rules_menu(rules, entries, colours, map_name=""):
    """Returns True to start the match, False to go back to character select."""
    layer = _Layer()
    old_background = Screen.background
    Screen.background = MENU_DARK
    W, H = Screen.width, Screen.height
    Screen.update()                     # lets the button that opened this screen pass

    layer.text("MATCH RULES", W / 2, 62, 72, GOLD, outline=4)
    if map_name:
        layer.text(f"Map: {map_name}", W / 2, 108, 26, (200, 200, 220), outline=2)

    # who is playing (and who wears the crown)
    n = len(entries)
    for i, entry in enumerate(entries):
        x = W * (i + 1) / (n + 1)
        slot = entry["slot"]
        layer.text(f"P{slot + 1}", x, 160, 38, colours[slot], outline=3)
        layer.text(str(entry["character"]), x, 192, 24, "white")
        if records.crown_slot == slot:
            layer.add(Crown(x, 128, 36))

    layer.box(900, 410, (30, 30, 48), W / 2, 402, alpha=220, border=3, border_colour=(90, 90, 130), radius=14)

    row_labels, row_values = [], []
    top = 255
    for i, (_, label, _, _) in enumerate(RULE_OPTIONS):
        y = top + i * 42
        row_labels.append(layer.text(label, W / 2 - 400, y, 32, "white", anchor="left"))
        row_values.append(layer.text("", W / 2 + 400, y, 32, "white", anchor="right"))
    start_y = top + len(RULE_OPTIONS) * 42 + 18
    start_text = layer.text("START MATCH", W / 2, start_y, 44, "white", outline=3)
    cursor = layer.add(Box(880, 38, GOLD, W / 2, top, alpha=60, border=2, border_colour=GOLD, radius=8))
    description = layer.text("", W / 2, H - 70, 24, (200, 200, 220), outline=1)
    hint = layer.text("Up / Down: choose     Left / Right: change     Enter / A: select     Esc / B: back", W / 2, H - 28, 20, (140, 140, 170), outline=1)

    index = 0
    count = len(RULE_OPTIONS) + 1       # + the start button
    result = None

    def current(attr):
        return getattr(rules, attr)

    def step(attr, values, direction):
        options = [v for _, v in values]
        i = options.index(current(attr)) if current(attr) in options else 0
        setattr(rules, attr, options[(i + direction) % len(options)])

    while Screen.running and result is None:
        nav = read_nav()
        if nav["up"]:
            index = (index - 1) % count
        if nav["down"]:
            index = (index + 1) % count
        if nav["back"]:
            result = False
        if index < len(RULE_OPTIONS):
            attr, _, values, desc = RULE_OPTIONS[index]
            direction = (1 if nav["right"] else 0) - (1 if nav["left"] else 0)
            if nav["ok"] and not direction:
                direction = 1
            if direction:
                step(attr, values, direction)
        elif nav["ok"]:
            result = True

        for i, (attr, label, values, _) in enumerate(RULE_OPTIONS):
            shown = dict((v, s) for s, v in values).get(current(attr), "?")
            greyed = attr == "stocks" and not rules.is_stock
            if attr == "minutes" and rules.mode == "Time Attack" and rules.minutes == 0:
                shown = "3:00 (required)"
            row_values[i].text = "-" if greyed else shown
            colour = (110, 110, 130) if greyed else ("white" if i != index else GOLD)
            row_labels[i].colour = colour
            row_values[i].colour = colour
        start_text.colour = GOLD if index == len(RULE_OPTIONS) else "white"
        if index < len(RULE_OPTIONS):
            cursor.y = top + index * 42
            cursor.x = W / 2
            cursor.width, cursor.height = 880, 38
            description.text = RULE_OPTIONS[index][3]
        else:
            cursor.y, cursor.width, cursor.height = start_y, 420, 56
            description.text = "Ready? Press Enter / A to fight!"
        description.x = W / 2
        hint.x = W / 2
        Screen.update()

    layer.clear()
    Screen.background = old_background
    if result:
        records.save_rules(rules)
    return bool(result)


# ==========================================================
# IN MATCH UI
# ==========================================================

def countdown(update=None, each=48):
    """3 - 2 - 1 - FIGHT! Nobody can move until it's over."""
    W, H = Screen.width, Screen.height
    t = Text("", W / 2, H / 2 - 60, 160, "white", outline=6)
    for label, colour in (("3", "white"), ("2", "white"), ("1", "white"), ("FIGHT!", GOLD)):
        t.text, t.colour = label, colour
        for f in range(each):
            if not Screen.running:
                break
            t.font_size = 120 + int(80 * (1 - f / each) ** 2)       # pops in big, settles down
            if update:
                update()
            Screen.update()
    t.delete()


class Banner:
    """Big message in the middle of the screen for a short time."""
    def __init__(self):
        self.text = Text("", Screen.width / 2, Screen.height / 2 - 120, 84, "white", outline=5)
        self.text.hide()
        self.left = 0

    def show(self, message, frames=100, colour="white"):
        self.text.text, self.text.colour = message, colour
        self.text.x = Screen.width / 2
        self.text.show()
        self.left = frames

    def update(self):
        if self.left > 0:
            self.left -= 1
            if self.left == 0:
                self.text.hide()

    def delete(self):
        self.text.delete()


class KillFeed:
    """The little list in the top left: who KO'd who."""
    MAX = 5
    LIFE = 260

    def __init__(self):
        self.lines = []                 # [Text, age]

    def add(self, message, colour):
        t = Text(message, 0, 0, 26, colour, outline=3)
        self.lines.append([t, 0])
        while len(self.lines) > self.MAX:
            old = self.lines.pop(0)
            old[0].delete()
        self._place()

    def _place(self):
        for i, (t, _) in enumerate(self.lines):
            t.x = 18 + t.width / 2
            t.y = 26 + i * 30

    def update(self):
        for line in self.lines[:]:
            line[1] += 1
            if line[1] >= self.LIFE:
                line[0].delete()
                self.lines.remove(line)
                self._place()

    def delete(self):
        for t, _ in self.lines:
            t.delete()
        self.lines = []


class MatchClock:
    def __init__(self):
        self.text = Text("", Screen.width / 2, 30, 44, "white", outline=3)

    def update(self, frame, limit, sudden_death):
        if sudden_death:
            self.text.text, self.text.colour = "SUDDEN DEATH", (255, 70, 70)
        elif limit:
            left = max(0, limit - frame)
            self.text.text = fmt_time(left + FPS - 1)       # rounds up, so 0:00 only shows when it's really over
            self.text.colour = (255, 70, 70) if left < 10 * FPS and (left // 15) % 2 == 0 else "white"
        else:
            self.text.text, self.text.colour = fmt_time(frame), (190, 190, 210)

    def delete(self):
        self.text.delete()


# ==========================================================
# RESULTS SCREEN
# ==========================================================

RESULT_ACTIONS = (("Rematch", "rematch"), ("Change Map", "map"), ("Change Rules", "rules"), ("Character Select", "select"), ("Main Menu", "menu"))

COLUMNS = (   # (heading, x, value)
    ("KILLS", 560, lambda s: s.kills),
    ("DEATHS", 650, lambda s: s.deaths),
    ("SDs", 735, lambda s: s.self_destructs),
    ("DMG DEALT", 840, lambda s: int(s.damage_dealt)),
    ("DMG TAKEN", 955, lambda s: int(s.damage_taken)),
    ("HITS", 1050, lambda s: s.hits),
    ("PARRIES", 1130, lambda s: s.parries),
    ("STREAK", 1215, lambda s: s.best_streak),
)


def results_screen(result, colours):
    """Returns 'rematch', 'rules', 'select' or 'menu'."""
    layer = _Layer()
    old_background = Screen.background
    Screen.background = MENU_DARK
    W, H = Screen.width, Screen.height
    Screen.update()

    # ---- title ----
    if result.draw:
        layer.text("DRAW!", W / 2, 70, 84, "white", outline=5)
    else:
        winner = next(s for s in result.stats if s.slot == result.winners[0])
        layer.add(Crown(W / 2, 30, 64))
        layer.text(f"PLAYER {winner.slot + 1} WINS!", W / 2, 92, 80, winner.colour, outline=5)
    sub = result.rules.summary() + (f"  -  {result.map_name}" if result.map_name else "") + f"  -  {fmt_time(result.frames)}"
    if result.sudden_death:
        sub += "  -  went to SUDDEN DEATH"
    layer.text(sub, W / 2, 142, 24, (200, 200, 220), outline=1)
    wins = "     ".join(f"P{s.slot + 1}: {records.wins[s.slot]} {'win' if records.wins[s.slot] == 1 else 'wins'}"
                        for s in sorted(result.stats, key=lambda s: s.slot))
    layer.text("Lifetime  -  " + wins, W / 2, 172, 22, (140, 140, 170), outline=1)

    # ---- table ----
    head_y = 215
    layer.text("PLAYER", 150, head_y, 22, (150, 150, 185), outline=1)
    layer.text("FIGHTER", 350, head_y, 22, (150, 150, 185), outline=1)
    for heading, x, _ in COLUMNS:
        layer.text(heading, x, head_y, 22, (150, 150, 185), outline=1)
    row_h = 58
    for i, s in enumerate(result.stats):
        y = head_y + 48 + i * row_h
        won = s.slot in result.winners and not result.draw
        layer.box(1200, row_h - 8, (34, 34, 54), W / 2, y, alpha=230,
                  border=3 if won else 1, border_colour=GOLD if won else (70, 70, 100), radius=10)
        layer.text(f"#{i + 1}  P{s.slot + 1}", 150, y, 36, colours[s.slot], outline=3)
        layer.text(s.character, 350, y, 28, "white", outline=2)
        for _, x, value in COLUMNS:
            layer.text(str(value(s)), x, y, 34, "white", outline=2)
        if won:
            layer.add(Crown(238, y - 14, 30))

    # ---- awards ----
    awards = build_awards(result.stats)
    ay = head_y + 48 + len(result.stats) * row_h + 36
    if awards:
        layer.text("MATCH AWARDS", W / 2, ay - 12, 24, GOLD, outline=2)
        for i, (label, s, value) in enumerate(awards):
            x = W * (i + 0.5) / len(awards)
            size = 26 if len(label) <= 18 else max(16, int(26 * 18 / len(label)))      # long names shrink to fit
            layer.text(label, x, ay + 24, size, "white", outline=2)
            layer.text(f"P{s.slot + 1}  ({value})", x, ay + 54, 28, colours[s.slot], outline=2)

    # ---- buttons ----
    by = H - 38
    n = len(RESULT_ACTIONS)
    buttons = []
    for i, (label, _) in enumerate(RESULT_ACTIONS):
        buttons.append(layer.text(label, W * (i + 0.5) / n, by, 30, "white", outline=3))
    cursor = layer.add(Box(236, 46, GOLD, buttons[0].x, by, alpha=70, border=2, border_colour=GOLD, radius=10))
    # (the cursor box is made after the text, so push it behind by redrawing text colours instead of relying on order)
    choice = 0
    action = None
    while Screen.running and action is None:
        nav = read_nav()
        if nav["left"]:
            choice = (choice - 1) % n
        if nav["right"]:
            choice = (choice + 1) % n
        if nav["ok"]:
            action = RESULT_ACTIONS[choice][1]
        if nav["back"]:
            action = "select"
        cursor.x = buttons[choice].x
        for i, b in enumerate(buttons):
            b.colour = GOLD if i == choice else "white"
        Screen.update()

    layer.clear()
    Screen.background = old_background
    return action or "menu"


# ==========================================================
# MAP SELECT
# ==========================================================

_MAP_COLOURS = {"x": (26, 28, 48), "0": (160, 172, 215), "#": (120, 120, 150), "Z": (110, 35, 45), "Q": (110, 35, 45),
                "b": (210, 130, 60)}


def _layout_rows(layout):
    rows = textwrap.dedent(layout).split("\n")             # same tidy-up the TileMap does
    while rows and not rows[0].strip():
        rows.pop(0)
    while rows and not rows[-1].strip():
        rows.pop()
    cols = max(len(r) for r in rows)
    return [r.ljust(cols, "x") for r in rows]


class MapPreview(GameSnake._Drawn):
    """A little picture of a stage: ground is light, blast zones are red, spawn points are gold dots."""
    _LOOKS = ("max_w", "max_h")

    def __init__(self, layout, x, y, max_w, max_h, fixed=True):
        self.rows = _layout_rows(layout)
        self.max_w, self.max_h = max_w, max_h
        super().__init__("mappreview", x, y, fixed)

    def _render(self):
        rows = self.rows
        cols, count = len(rows[0]), len(rows)
        small = pygame.Surface((cols, count))
        for r, line in enumerate(rows):
            for c, ch in enumerate(line):
                small.set_at((c, r), (255, 215, 90) if ch in "1234" else _MAP_COLOURS.get(ch, _MAP_COLOURS["x"]))
        scale = max(1, min(self.max_w // cols, self.max_h // count))
        image = pygame.transform.scale(small, (cols * scale, count * scale))
        if scale == 1 and (self.max_w > cols or self.max_h > count):          # tiny stage on a big preview: stretch it
            factor = min(self.max_w / cols, self.max_h / count)
            image = pygame.transform.scale(small, (int(cols * factor), int(count * factor)))
        return [("mappreview", image.convert_alpha())]


def map_select(maps, choice=0):
    """maps = [{'name':..., 'blurb':..., 'layout':...}, ...]. A 'Random' tile is added on the end.
    Returns (tile_picked, map_index_to_play), or None if they backed out."""
    layer = _Layer()
    old_background = Screen.background
    Screen.background = MENU_DARK
    W, H = Screen.width, Screen.height
    Screen.update()
    n = len(maps)
    total = n + 1
    choice = max(0, min(total - 1, choice))

    layer.text("CHOOSE A MAP", W / 2, 52, 64, GOLD, outline=4)
    layer.add(Box(780, 380, (20, 20, 34), W / 2, 285, border=3, border_colour=(90, 90, 130), radius=12))
    previews = [layer.add(MapPreview(m["layout"], W / 2, 285, 760, 360)) for m in maps]
    random_mark = layer.text("?", W / 2, 285, 220, (120, 120, 150), outline=4)
    name_text = layer.text("", W / 2, 520, 52, "white", outline=3)
    blurb_text = layer.text("", W / 2, 565, 26, (200, 200, 220), outline=2)
    layer.text("<", 150, 285, 90, GOLD, outline=3)
    layer.text(">", W - 150, 285, 90, GOLD, outline=3)

    thumb_w, gap = 130, 22
    start_x = W / 2 - (total * thumb_w + (total - 1) * gap) / 2 + thumb_w / 2
    frames, thumbs = [], []
    for i in range(total):
        x = start_x + i * (thumb_w + gap)
        frames.append(layer.add(Box(thumb_w + 8, 76, (255, 215, 90), x, 640, alpha=0, border=3, border_colour=(70, 70, 100), radius=6)))
        if i < n:
            thumbs.append(layer.add(MapPreview(maps[i]["layout"], x, 640, thumb_w, 68)))
        else:
            thumbs.append(layer.text("?", x, 640, 54, (150, 150, 180), outline=2))
    layer.text("Left / Right: browse     Enter / A: pick     Esc / B: back", W / 2, H - 22, 20, (140, 140, 170), outline=1)

    result = None
    done = False
    while Screen.running and not done:
        nav = read_nav()
        if nav["left"]:
            choice = (choice - 1) % total
        if nav["right"]:
            choice = (choice + 1) % total
        if nav["back"]:
            done = True
        if nav["ok"]:
            pick = choice if choice < n else random_number(0, n - 1)
            result, done = (choice, pick), True
        for i, p in enumerate(previews):
            p.visible = i == choice
        random_mark.visible = choice == n
        if choice < n:
            name_text.text, blurb_text.text = maps[choice]["name"], maps[choice]["blurb"]
        else:
            name_text.text, blurb_text.text = "Random", "A surprise stage every time."
        name_text.x = blurb_text.x = W / 2
        for i, f in enumerate(frames):
            on = i == choice
            f.border_colour = (255, 215, 90) if on else (70, 70, 100)
            f.alpha = 50 if on else 0
        Screen.update()

    layer.clear()
    Screen.background = old_background
    return result