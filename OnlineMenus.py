"""
OnlineMenus.py  -  every screen for online play. It only draws menus and talks to Network.py; the fight itself is run by
Platform_Fighter.py, which hands us a `play_match(client, payload)` function to call when the host starts a match.

  Online menu  ->  Join a Server  -> (connect) -> Lobby list -> Lobby room -> match -> back to the Lobby room
                   Host a Server  -> (starts a server on this PC) -> Lobby room (you are the host)
"""
import threading
from collections import namedtuple
from GameSnake import *
from Controls import MAX_PLAYERS, PLAYER_COLOURS
from Menus import Nav, Menu, Item, Text, _text_entry, MENU_BG, WHITE, GREY, DARK, GOLD, GREEN, RED
import MatchSystem as ms
import Network

__all__ = ["online_menu"]


def _notice(title, text):
    Menu(title, [Item("OK", result="ok")], subtitle=text, spacing=68, width=420, back_result="ok").run()

def _set_visible(sprites, on):
    for s in sprites:
        s.visible = on

def _delete(sprites):
    for s in sprites:
        s.delete()


#==========================================================
# A dynamic list (the lobby list and the lobby room both use it)
#==========================================================

Row = namedtuple("Row", "label value colour vcolour disabled", defaults=("", None, None, False))

class _Rows:
    def __init__(self, top, spacing, count, width):
        cx = Screen.width / 2
        self.count, self.width = count, width
        self.boxes = [Box(width, spacing - 6, GOLD, cx, top + i * spacing, alpha=40, border=2, border_colour=GOLD, radius=8) for i in range(count)]
        self.left = [Text("", cx, top + i * spacing, 28, WHITE) for i in range(count)]
        self.right = [Text("", cx, top + i * spacing, 28, WHITE) for i in range(count)]
        self.sprites = self.boxes + self.left + self.right

    def show(self, rows, selected=None):
        cx = Screen.width / 2
        lx, rx = cx - self.width / 2 + 24, cx + self.width / 2 - 24
        for i in range(self.count):
            on = i < len(rows)
            for group in (self.boxes, self.left, self.right):
                group[i].visible = on
            if not on:
                continue
            row, sel = rows[i], i == selected
            colour = row.colour or (DARK if row.disabled else (WHITE if sel else GREY))
            self.boxes[i].visible = sel
            self.left[i].text, self.left[i].colour = row.label, colour
            self.left[i].x = lx + self.left[i].width / 2
            self.right[i].text, self.right[i].colour = row.value or "", row.vcolour or (GOLD if sel and not row.disabled else colour)
            self.right[i].x = rx - self.right[i].width / 2


def _step(rows, selected, direction):
    for _ in range(len(rows)):
        selected = (selected + direction) % len(rows)
        if not rows[selected].disabled:
            return selected
    return selected


#==========================================================
# ONLINE MENU
#==========================================================

def online_menu(settings, characters, maps, rules, build, play_match):
    """characters = {name: class}, maps = MAPS, rules = ms.Rules, build = fingerprint of the game files,
    play_match(client, payload) = runs one online match (returns True for a rematch)."""
    ctx = dict(settings=settings, characters=characters, maps=maps, rules=rules, build=build, play_match=play_match)

    def rename():
        new = _text_entry("Your online name", settings.online_name, "Other players see this", max_len=16)
        if new and new.strip():
            settings.online_name = new.strip()
            settings.save()

    while Screen.running:
        items = [Item("Join a Server", result="join"),
                 Item("Host a Server", result="host"),
                 Item("Player Name", value=lambda: settings.online_name, on_confirm=rename),
                 Item("Back", result="back")]
        choice = Menu("Online", items, subtitle="Play with friends over the internet",
                      hint="Online uses your Player 1 keyboard controls (or your first controller)     Esc: back",
                      spacing=64, width=620).run()
        if choice == "join":
            _join_flow(ctx)
        elif choice == "host":
            _host_flow(ctx)
        else:
            break


def _connect(ctx, host, port, label):
    settings = ctx["settings"]
    job = Network.Connector(host, port, settings.online_name, ctx["build"])
    cx, cy = Screen.width / 2, Screen.height / 2
    sprites = [Text(f"Connecting to {label}...", cx, cy, 40, WHITE), Text("Esc to cancel", cx, cy + 60, 22, GREY)]
    cancelled = False
    while Screen.running and not job.done:
        Screen.update()
        if Keyboard.pressed("escape"):
            cancelled = True
            break
    _delete(sprites)
    if cancelled or not Screen.running:
        threading.Thread(target=lambda: (job.join(), job.client.close()), daemon=True).start()   # tidy up if it connects late
        return None
    if job.error:
        _notice("Couldn't connect", job.error)
        return None
    return job.client


def _join_flow(ctx):
    settings = ctx["settings"]
    text = _text_entry("Server address", settings.last_address, "IP or name.  Add :port if it isn't 7777   (Shift + ; makes a colon)", max_len=60)
    if not text or not text.strip():
        return
    try:
        host, port = Network.parse_address(text)
    except ValueError as e:
        return _notice("Bad address", str(e))
    settings.last_address = text.strip()
    settings.save()
    label = f"{host}:{port}"
    client = _connect(ctx, host, port, label)
    if client is None:
        return
    try:
        while Screen.running:
            result = _browser(ctx, client, label)
            if result != "room":
                break
            if _room(ctx, client, label, None) == "lost":
                _notice("Disconnected", client.reason or "Connection lost")
                break
    finally:
        client.close()


def _host_flow(ctx):
    settings = ctx["settings"]
    host = Network.HostInfo(Network.DEFAULT_PORT)
    try:
        host.start()
    except OSError as e:
        return _notice("Couldn't host", f"Port {host.port} is busy or blocked: {e}"[:80])
    client = None
    try:
        client = _connect(ctx, "127.0.0.1", host.port, "your own server")
        if client is None:
            return
        client.send({"t": "create", "name": f"{settings.online_name}'s Lobby", "max": MAX_PLAYERS})
        if _room(ctx, client, "your server", host) == "lost":
            _notice("Disconnected", client.reason or "Connection lost")
    finally:
        if client:
            client.close()
        host.stop()


#==========================================================
# LOBBY LIST
#==========================================================

def _browser(ctx, client, label):
    """Returns 'room' once you are inside a lobby, or 'leave'."""
    settings = ctx["settings"]
    W, H = Screen.width, Screen.height
    sprites = [Text("Lobbies", W / 2, 70, 60, WHITE, outline=3),
               Text(f"Server: {label}", W / 2, 124, 24, GREY),
               Text("Up / Down: choose     Enter / A: join     Esc: disconnect", W / 2, H - 26, 20, GREY)]
    status = Text("", W / 2, H - 70, 26, RED)
    sprites.append(status)
    rows = _Rows(top=200, spacing=56, count=9, width=960)
    sprites += rows.sprites

    selected, frame, result = 0, 0, None
    nav = Nav(settings)
    client.send({"t": "list"})
    while Screen.running and result is None:
        Screen.update()
        frame += 1
        if frame % 90 == 0:
            client.send({"t": "list"})
        for msg in client.poll():
            if msg["t"] == "error":
                status.text = msg["msg"]
            elif msg["t"] == "disconnected":
                status.text = client.reason or "Connection lost"
                result = "leave"
        if client.lobby is not None:
            result = "room"
            break

        lobbies = client.lobbies[:7]
        view = []
        for lob in lobbies:
            reason = (None if lob["state"] == "open" and lob["count"] < lob["max"] and lob["build"] == ctx["build"] else
                      "Different game version" if lob["build"] != ctx["build"] else
                      "In a match" if lob["state"] != "open" else "Full")
            view.append(Row(f"{lob['name']}   (host: {lob['host']})", f"{lob['count']}/{lob['max']}   {reason or 'Open'}", disabled=reason is not None))
        if not lobbies:
            status.colour = GREY
            status.text = status.text or "No lobbies yet. Create one!"
        view.append(Row("+  Create a Lobby", None))
        view.append(Row("Disconnect", None))
        selected = min(selected, len(view) - 1)
        rows.show(view, selected)

        for device, action in nav.poll():
            if action == "start" and device[0] == "key":
                continue
            if action == "up":
                selected = (selected - 1) % len(view)
            elif action == "down":
                selected = (selected + 1) % len(view)
            elif action in ("confirm", "start"):
                status.colour = RED
                if selected < len(lobbies):
                    lob = lobbies[selected]
                    if view[selected].disabled:
                        status.text = view[selected].value.split("   ")[-1]
                    else:
                        status.text = ""
                        client.send({"t": "join", "id": lob["id"]})
                elif selected == len(lobbies):
                    _set_visible(sprites, False)
                    name = _text_entry("Lobby name", f"{settings.online_name}'s Lobby", "", max_len=24)
                    _set_visible(sprites, True)
                    nav = Nav(settings)
                    if name and name.strip():
                        client.send({"t": "create", "name": name.strip(), "max": MAX_PLAYERS})
                    break
                else:
                    result = "leave"
            elif action == "back":
                result = "leave"
    _delete(sprites)
    return result or "leave"


#==========================================================
# LOBBY ROOM
#==========================================================

def _room(ctx, client, label, host_info):
    """Returns 'left' (you chose to leave) or 'lost' (connection died)."""
    settings, characters, maps, rules = ctx["settings"], list(ctx["characters"]), ctx["maps"], ctx["rules"]
    classes = ctx["characters"]
    W, H = Screen.width, Screen.height
    title_of = lambda name: getattr(classes[name], "title", name) if name in classes else "..."

    title = Text("", W / 2, 56, 52, WHITE, outline=3)
    sub = Text("", W / 2, 104, 22, GREY)
    line1, line2 = Text("", W / 2, 136, 20, GOLD), Text("", W / 2, 160, 20, GREY)
    status = Text("", W / 2, H - 64, 24, RED)
    hint = Text("Up / Down: choose     Left / Right: change     Enter / A: select     Esc: leave lobby", W / 2, H - 26, 20, GREY)
    roster = _Rows(top=212, spacing=54, count=MAX_PLAYERS, width=1000)
    actions = _Rows(top=452, spacing=46, count=6, width=760)
    sprites = [title, sub, line1, line2, status, hint] + roster.sprites + actions.sprites

    view_rules = ms.Rules()
    nav = Nav(settings)
    selected, frame, seen, want_ready, result = 0, 0, False, False, None
    my_character = characters[0]

    def me_of(lobby):
        return next((m for m in lobby["members"] if m["slot"] == lobby["you"]), None)

    while Screen.running and result is None:
        Screen.update()
        frame += 1
        lobby = client.lobby
        for msg in client.poll():
            if msg["t"] == "disconnected":
                result = "lost"
            elif msg["t"] == "error":
                status.text = msg["msg"]
            elif msg["t"] == "start":
                for e in msg["entries"]:                                   # never trust the network: unknown fighter -> the first one
                    if e["character"] not in classes:
                        e["character"] = characters[0]
                _set_visible(sprites, False)
                want_ready = bool(ctx["play_match"](client, msg))
                Screen.background = MENU_BG
                _set_visible(sprites, True)
                nav = Nav(settings)
                status.text = ""
        if result:
            break
        if lobby is None:
            if seen or frame > 240:
                result = "left"
                break
            title.text, sub.text = "Creating lobby...", ""
            continue
        seen = True

        me = me_of(lobby)
        is_host = lobby["host"] == lobby["you"]
        playing = lobby["state"] != "open"
        cfg = lobby["config"]
        view_rules.load(cfg.get("rules", {}))
        if is_host and not cfg.get("rules"):                              # a brand new lobby: publish the host's rules
            client.send({"t": "config", "map_tile": cfg.get("map_tile", 0), "rules": rules.to_dict()})
        if me and not me["character"]:
            client.send({"t": "set", "character": my_character})
        if want_ready and not playing and me and me["character"] and not me["ready"]:
            client.send({"t": "set", "ready": True})
            want_ready = False
        elif want_ready and not playing:
            want_ready = False

        #------- draw -------
        title.text = lobby["name"]
        sub.text = f"{len(lobby['members'])}/{lobby['max']} players     Your ping: {client.my_ping()} ms     Server: {label}"
        if host_info:
            line1.text = f"Friends on the internet join:  {host_info.internet_line()}"
            line2.text = f"Same Wi-Fi:  {host_info.lan_ip}:{host_info.port}      Port: {host_info.upnp}"
        else:
            line1.text = line2.text = ""
        by_slot = {m["slot"]: m for m in lobby["members"]}
        roster_rows = []
        for slot in range(lobby["max"]):
            m = by_slot.get(slot)
            if m is None:
                roster_rows.append(Row(f"P{slot + 1}   (empty)", None, colour=DARK))
            else:
                tag = "  [host]" if slot == lobby["host"] else ""
                tag += "  (you)" if slot == lobby["you"] else ""
                ready = "READY" if m["ready"] else "not ready"
                roster_rows.append(Row(f"P{slot + 1}   {m['name']}{tag}", f"{title_of(m['character'])}    {ready}    {m['ping']} ms",
                                       colour=PLAYER_COLOURS[slot], vcolour=GREEN if m["ready"] else GREY))
        roster.show(roster_rows)

        members = lobby["members"]
        all_ready = len(members) >= 2 and all(m["ready"] for m in members)
        map_name = maps[cfg["map_tile"]]["name"] if 0 <= cfg.get("map_tile", 0) < len(maps) else "Random"
        if is_host:
            start_note = "Match in progress..." if playing else ("GO!" if all_ready else "waiting for everyone to be ready")
        else:
            start_note = "the host starts the match"
        arrows = lambda text: f"<  {text}  >"
        rows = [Row("Fighter", arrows(title_of(my_character)) if selected == 0 else title_of(my_character), disabled=playing),
                Row("Ready", "YES" if me and me["ready"] else "no", disabled=playing),
                Row("Map", map_name, disabled=not is_host or playing),
                Row("Rules", view_rules.summary(), disabled=not is_host or playing),
                Row("Start Match", start_note, disabled=not (is_host and all_ready and not playing)),
                Row("Leave Lobby", None)]
        if rows[selected].disabled:
            selected = _step(rows, selected, 1)
        actions.show(rows, selected)
        if not status.text and playing:
            status.colour, status.text = GREY, "A match is running. You'll be back when it ends."
        elif status.text and not playing and status.colour == GREY:
            status.text = ""

        #------- input -------
        for device, action in nav.poll():
            if action == "start" and device[0] == "key":
                continue
            status.colour = RED
            if action == "up":
                selected = _step(rows, selected, -1)
            elif action == "down":
                selected = _step(rows, selected, 1)
            elif action == "back":
                client.send({"t": "leave"})
                result = "left"
            elif action in ("left", "right") and selected == 0 and not playing:
                i = characters.index(my_character) + (1 if action == "right" else -1)
                my_character = characters[i % len(characters)]
                client.send({"t": "set", "character": my_character})
            elif action in ("confirm", "start") and not rows[selected].disabled:
                status.text = ""
                if selected == 0:
                    my_character = characters[(characters.index(my_character) + 1) % len(characters)]
                    client.send({"t": "set", "character": my_character})
                elif selected == 1:
                    client.send({"t": "set", "ready": not (me and me["ready"])})
                elif selected == 2:
                    _set_visible(sprites, False)
                    picked = ms.map_select(maps, cfg.get("map_tile", 0))
                    _set_visible(sprites, True)
                    if picked is not None:
                        client.send({"t": "config", "map_tile": picked[0], "rules": view_rules.to_dict()})
                    nav = Nav(settings)
                    break
                elif selected == 3:
                    rules.load(cfg.get("rules", {}))
                    entries = [{"slot": m["slot"], "character": title_of(m["character"])} for m in members]
                    _set_visible(sprites, False)
                    ms.rules_menu(rules, entries, PLAYER_COLOURS, map_name)
                    Screen.background = MENU_BG
                    _set_visible(sprites, True)
                    client.send({"t": "config", "map_tile": cfg.get("map_tile", 0), "rules": rules.to_dict()})
                    nav = Nav(settings)
                    break
                elif selected == 4:
                    tile = cfg.get("map_tile", 0)
                    pick = tile if tile < len(maps) else random_number(0, len(maps) - 1)
                    client.send({"t": "start", "map": pick})
                else:
                    client.send({"t": "leave"})
                    result = "left"
    _delete(sprites)
    return result or "left"
