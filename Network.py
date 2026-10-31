"""
Network.py  -  online play for Platform Fighter. Pure standard library (no pygame), so Server.py can run it on any machine.

HOW ONLINE PLAY WORKS  (read this first!)
  The game uses "lockstep": every player's computer runs the WHOLE fight itself, and the only thing sent over the internet
  is each player's buttons, once per frame. A LobbyServer collects everyone's buttons for frame N, then sends them all
  back out as one "bundle". Nobody simulates on the server, so it needs no game files and no pygame.

  LobbyServer  -> lobbies + relays the buttons.  Run it with Server.py on a VPS, or let a player host it from the game menu.
  Client       -> what the game uses to talk to a server (runs a reader thread, the game polls it each frame).
  HostInfo     -> starts a LobbyServer inside the game and works out the address friends should type (+ optional UPnP).

Messages are JSON, each with a 4 byte length in front. Every message has a "t" (type).
"""
import json, socket, struct, threading, queue, time, random, math, zlib, os, re

DEFAULT_PORT = 7777
PROTOCOL = 1                    # bump when the messages change, so old and new versions refuse to talk
MAX_LOBBY_PLAYERS = 4
MAX_MESSAGE = 1 << 16
WAIT_TIMEOUT = 12.0             # seconds the game waits for a missing player's buttons before giving up


#==========================================================
# WIRE FORMAT
#==========================================================

def pack(message):
    data = json.dumps(message, separators=(",", ":")).encode("utf-8")
    return struct.pack(">I", len(data)) + data

def _read_exact(sock, n):
    chunks = []
    while n > 0:
        chunk = sock.recv(n)
        if not chunk:
            raise ConnectionError("connection closed")
        chunks.append(chunk)
        n -= len(chunk)
    return b"".join(chunks)

def read_message(sock):
    (length,) = struct.unpack(">I", _read_exact(sock, 4))
    if length > MAX_MESSAGE:
        raise ConnectionError("message too big")
    return json.loads(_read_exact(sock, length).decode("utf-8"))

def _clean(text, limit=24):
    text = re.sub(r"[\x00-\x1f\x7f]", "", str(text)).strip()
    return text[:limit]

def build_id(paths):
    """A fingerprint of the game files that affect the fight. Players must match exactly or they'd desync.
    Line endings are ignored so Windows / Mac / Linux copies of the same code agree."""
    crc = 0
    for path in paths:
        try:
            with open(path, "rb") as f:
                crc = zlib.crc32(f.read().replace(b"\r\n", b"\n"), crc)
        except OSError:
            pass
    return f"{crc:08x}"

def parse_address(text, default_port=DEFAULT_PORT):
    """'1.2.3.4' -> ('1.2.3.4', 7777)   '1.2.3.4:9000' -> ('1.2.3.4', 9000)"""
    text = text.strip()
    if text.count(":") == 1:
        host, _, port = text.partition(":")
        if port.isdigit() and 0 < int(port) < 65536:
            return host.strip(), int(port)
        raise ValueError("That port isn't a number")
    return text, default_port


#==========================================================
# SERVER
#==========================================================

class _Peer:
    def __init__(self, server, sock, addr, pid):
        self.server, self.sock, self.addr, self.id = server, sock, addr, pid
        self.name = f"Player{pid}"
        self.build = ""
        self.lobby = None
        self.slot = None
        self.character = ""
        self.ready = False
        self.ping = 0.0
        self.alive = True
        self.out = queue.Queue()
        threading.Thread(target=self._writer, daemon=True).start()

    def send(self, message):
        if self.alive:
            self.out.put(pack(message))

    def _writer(self):                              # sending happens on its own thread so one slow player can't stall everyone
        while True:
            data = self.out.get()
            if data is None:
                return
            try:
                self.sock.sendall(data)
            except OSError:
                self.server.drop(self)
                return


class _Match:
    def __init__(self, slots, delay):
        self.slots = set(slots)
        self.delay = delay
        self.inputs = {}            # frame -> {slot: [held, pressed]}
        self.next = 0               # the next frame to send out
        self.gone = set()           # slots that left mid match (their buttons are zero from now on)
        self.announce = []          # leavers still to be announced in the next bundle
        self.done = set()           # slots that finished (or left)
        self.hashes = {}            # frame -> {slot: state fingerprint}, for spotting desyncs


class _Lobby:
    def __init__(self, lid, name, build, max_players):
        self.id, self.name, self.build, self.max = lid, name, build, max_players
        self.members = {}           # slot -> _Peer
        self.host = None            # slot of the host
        self.state = "open"         # "open" or "playing"
        self.config = {"map_tile": 0, "rules": {}}
        self.match = None


class LobbyServer:
    def __init__(self, port=DEFAULT_PORT, bind="0.0.0.0", log=None):
        self.port, self.bind = port, bind
        self.log = log or (lambda *a: None)
        self.lock = threading.RLock()
        self.peers, self.lobbies = {}, {}
        self._next_peer = self._next_lobby = 1
        self._sock = None
        self.running = False

    def start(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.bind, self.port))         # raises OSError if the port is taken
        self._sock.listen(16)
        self.running = True
        threading.Thread(target=self._accept_loop, daemon=True).start()
        threading.Thread(target=self._ping_loop, daemon=True).start()
        self.log(f"Server listening on port {self.port}")

    def stop(self):
        self.running = False
        try:
            self._sock.close()
        except OSError:
            pass
        with self.lock:
            for peer in list(self.peers.values()):
                self.drop(peer)

    def serve_forever(self):
        self.start()
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.log("Shutting down")
            self.stop()

    #---------------- connections ----------------

    def _accept_loop(self):
        while self.running:
            try:
                sock, addr = self._sock.accept()
            except OSError:
                return
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            with self.lock:
                peer = _Peer(self, sock, addr, self._next_peer)
                self._next_peer += 1
                self.peers[peer.id] = peer
            threading.Thread(target=self._reader, args=(peer,), daemon=True).start()

    def _reader(self, peer):
        try:
            peer.sock.settimeout(10)                    # a connection must say hello quickly...
            first = read_message(peer.sock)
            peer.sock.settimeout(None)                  # ...after that it can stay quiet
            self._handle(peer, first)
            while peer.alive:
                self._handle(peer, read_message(peer.sock))
        except (OSError, ValueError, ConnectionError, struct.error):
            pass
        finally:
            self.drop(peer)

    def drop(self, peer):
        with self.lock:
            if not peer.alive:
                return
            peer.alive = False
            self.peers.pop(peer.id, None)
            self._leave_lobby(peer)
        peer.out.put(None)
        try:
            peer.sock.close()
        except OSError:
            pass
        self.log(f"{peer.name} disconnected")

    def _ping_loop(self):
        tick = 0
        while self.running:
            time.sleep(1)
            tick += 1
            with self.lock:
                for peer in list(self.peers.values()):
                    peer.send({"t": "ping", "ts": time.time()})
                if tick % 2 == 0:                       # keeps the pings shown in lobbies fresh
                    for lobby in self.lobbies.values():
                        if lobby.state == "open":
                            self._broadcast_lobby(lobby)

    #---------------- messages ----------------

    def _handle(self, peer, msg):
        kind = msg.get("t")
        with self.lock:
            if kind == "hello":
                if msg.get("proto") != PROTOCOL:
                    peer.send({"t": "error", "msg": "This server runs a different network version"})
                    raise ConnectionError("protocol")
                peer.name = _clean(msg.get("name"), 16) or peer.name
                peer.build = _clean(msg.get("build"), 16)
                peer.send({"t": "welcome", "id": peer.id})
                self.log(f"{peer.name} connected from {peer.addr[0]}")
            elif kind == "pong":
                rtt = max(0.0, (time.time() - float(msg.get("ts", 0))) * 1000)
                peer.ping = rtt if peer.ping == 0 else peer.ping * 0.7 + rtt * 0.3
            elif kind == "list":
                peer.send({"t": "lobbies", "list": self._lobby_list()})
            elif kind == "create":
                self._create(peer, msg)
            elif kind == "join":
                self._join(peer, msg)
            elif kind == "leave":
                self._leave_lobby(peer)
                peer.send({"t": "left"})
            elif peer.lobby is None:
                return
            elif kind == "set":
                self._set(peer, msg)
            elif kind == "config":
                self._config(peer, msg)
            elif kind == "start":
                self._start(peer, msg)
            elif kind == "input":
                self._input(peer, msg)
            elif kind == "hash":
                self._hash(peer, msg)
            elif kind == "leave_match":
                self._finish_match_for(peer, forfeit=True)
            elif kind == "match_done":
                self._finish_match_for(peer, forfeit=False)

    def _lobby_list(self):
        return [{"id": l.id, "name": l.name, "count": len(l.members), "max": l.max, "state": l.state, "build": l.build,
                 "host": l.members[l.host].name if l.host in l.members else ""} for l in self.lobbies.values()]

    def _create(self, peer, msg):
        if peer.lobby is not None:
            return peer.send({"t": "error", "msg": "You are already in a lobby"})
        max_players = max(2, min(MAX_LOBBY_PLAYERS, int(msg.get("max", MAX_LOBBY_PLAYERS))))
        lobby = _Lobby(self._next_lobby, _clean(msg.get("name"), 24) or f"{peer.name}'s Lobby", peer.build, max_players)
        self._next_lobby += 1
        self.lobbies[lobby.id] = lobby
        self.log(f"Lobby '{lobby.name}' created by {peer.name}")
        self._enter(peer, lobby)

    def _join(self, peer, msg):
        lobby = self.lobbies.get(msg.get("id"))
        if peer.lobby is not None:
            return peer.send({"t": "error", "msg": "You are already in a lobby"})
        if lobby is None:
            return peer.send({"t": "error", "msg": "That lobby no longer exists"})
        if lobby.build != peer.build:
            return peer.send({"t": "error", "msg": "That lobby runs a different version of the game"})
        if lobby.state != "open":
            return peer.send({"t": "error", "msg": "That match has already started"})
        if len(lobby.members) >= lobby.max:
            return peer.send({"t": "error", "msg": "That lobby is full"})
        self._enter(peer, lobby)

    def _enter(self, peer, lobby):
        peer.slot = next(s for s in range(lobby.max) if s not in lobby.members)
        peer.lobby, peer.ready, peer.character = lobby, False, ""
        lobby.members[peer.slot] = peer
        if lobby.host is None:
            lobby.host = peer.slot
        self._broadcast_lobby(lobby)

    def _leave_lobby(self, peer):
        lobby = peer.lobby
        if lobby is None:
            return
        if lobby.match is not None and peer.slot in lobby.match.slots:
            self._finish_match_for(peer, forfeit=True, quiet=True)
        lobby.members.pop(peer.slot, None)
        peer.lobby, peer.slot, peer.ready = None, None, False
        if not lobby.members:
            self.lobbies.pop(lobby.id, None)
            self.log(f"Lobby '{lobby.name}' closed")
            return
        if lobby.host not in lobby.members:             # the host left: the lowest seat takes over
            lobby.host = min(lobby.members)
        self._broadcast_lobby(lobby)

    def _broadcast_lobby(self, lobby):
        members = [{"slot": s, "name": p.name, "character": p.character, "ready": p.ready, "ping": int(p.ping)}
                   for s, p in sorted(lobby.members.items())]
        base = {"t": "lobby", "id": lobby.id, "name": lobby.name, "host": lobby.host, "state": lobby.state,
                "max": lobby.max, "config": lobby.config, "members": members}
        for slot, peer in lobby.members.items():
            peer.send(dict(base, you=slot))

    def _set(self, peer, msg):
        lobby = peer.lobby
        if lobby.state != "open":
            return
        if "character" in msg:
            peer.character = _clean(msg["character"], 32)
            peer.ready = False
        if "ready" in msg:
            peer.ready = bool(msg["ready"]) and bool(peer.character)
        self._broadcast_lobby(lobby)

    def _config(self, peer, msg):
        lobby = peer.lobby
        if peer.slot != lobby.host or lobby.state != "open":
            return
        rules = msg.get("rules")
        lobby.config = {"map_tile": int(msg.get("map_tile", 0)), "rules": rules if isinstance(rules, dict) else {}}
        for p in lobby.members.values():                # changing the rules means everyone has to agree again
            p.ready = False
        self._broadcast_lobby(lobby)

    #---------------- matches ----------------

    def _start(self, peer, msg):
        lobby = peer.lobby
        if peer.slot != lobby.host or lobby.state != "open":
            return
        members = lobby.members
        if len(members) < 2 or not all(p.ready and p.character for p in members.values()):
            return peer.send({"t": "error", "msg": "Everyone needs to be ready first"})
        worst = max([p.ping for p in members.values()] + [30.0])
        delay = int(min(24, max(4, math.ceil(worst * 60 / 1000) + 3)))      # input delay in frames, covers the slowest connection
        lobby.state = "playing"
        lobby.match = _Match(members.keys(), delay)
        entries = [{"slot": s, "name": p.name, "character": p.character} for s, p in sorted(members.items())]
        start = {"t": "start", "seed": random.getrandbits(31), "delay": delay, "entries": entries,
                 "map": int(msg.get("map", 0)), "rules": lobby.config["rules"]}
        self.log(f"Match started in '{lobby.name}' ({len(entries)} players, delay {delay} frames)")
        for p in members.values():
            p.send(start)
        self._broadcast_lobby(lobby)

    def _input(self, peer, msg):
        match = peer.lobby.match
        if match is None or peer.slot in match.gone:
            return
        frame = msg.get("f")
        if not isinstance(frame, int) or frame < match.next or frame > match.next + 600:
            return
        match.inputs.setdefault(frame, {})[peer.slot] = [int(msg.get("h", 0)) & 0x1FF, int(msg.get("p", 0)) & 0x1FF]
        self._pump(peer.lobby)

    def _pump(self, lobby):
        """Sends out every frame that now has everyone's buttons."""
        match = lobby.match
        while match is not None:
            need = match.slots - match.gone
            row = match.inputs.get(match.next, {})
            if not need or any(s not in row for s in need):
                break
            bundle = {"t": "bundle", "f": match.next, "left": match.announce,
                      "i": {str(s): row.get(s, [0, 0]) for s in match.slots}}
            match.announce = []
            for slot in need:
                if slot in lobby.members:
                    lobby.members[slot].send(bundle)
            match.inputs.pop(match.next, None)
            match.next += 1

    def _hash(self, peer, msg):
        match = peer.lobby.match
        if match is None or peer.slot in match.gone:
            return
        frame = msg.get("f")
        row = match.hashes.setdefault(frame, {})
        row[peer.slot] = msg.get("h")
        need = match.slots - match.gone
        if all(s in row for s in need):
            if len({row[s] for s in need}) > 1:
                self.log(f"DESYNC in '{peer.lobby.name}' at frame {frame}")
                for slot in need:
                    if slot in peer.lobby.members:
                        peer.lobby.members[slot].send({"t": "desync", "f": frame})
            del match.hashes[frame]
        if len(match.hashes) > 60:                      # a player vanished mid check: forget the oldest
            del match.hashes[min(match.hashes)]

    def _finish_match_for(self, peer, forfeit, quiet=False):
        lobby = peer.lobby
        match = lobby.match
        if match is None or peer.slot not in match.slots:
            return
        if forfeit and peer.slot not in match.gone and peer.slot not in match.done:
            match.gone.add(peer.slot)
            match.announce.append(peer.slot)
        match.done.add(peer.slot)
        self._pump(lobby)
        if not (match.slots - match.gone - match.done):  # nobody is still playing: back to the lobby
            lobby.match, lobby.state = None, "open"
            for p in lobby.members.values():
                p.ready = False
            if not quiet:
                self._broadcast_lobby(lobby)
            self.log(f"Match in '{lobby.name}' finished")
        elif not quiet:
            self._broadcast_lobby(lobby)


#==========================================================
# CLIENT
#==========================================================

class Client:
    """The game's end of the connection. A thread reads messages; the game just looks at the attributes / polls."""

    def __init__(self):
        self.sock = None
        self.connected = False
        self.id = None
        self.lobby = None                   # the newest "lobby" message while you are in one, else None
        self.lobbies = []                   # the newest lobby list
        self.desync_frame = None
        self.reason = ""                    # why the connection ended
        self._inbox = queue.Queue()         # start / error / disconnected messages
        self._bundles = {}
        self._lock = threading.Lock()
        self._send_lock = threading.Lock()

    def connect(self, host, port, name, build, timeout=6):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.sock.sendall(pack({"t": "hello", "proto": PROTOCOL, "name": name, "build": build}))
        reply = read_message(self.sock)
        if reply.get("t") != "welcome":
            raise ConnectionError(reply.get("msg", "The server refused the connection"))
        self.sock.settimeout(None)
        self.id = reply["id"]
        self.connected = True
        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self):
        try:
            while True:
                msg = read_message(self.sock)
                kind = msg.get("t")
                if kind == "ping":
                    self.send({"t": "pong", "ts": msg.get("ts")})
                elif kind == "bundle":
                    with self._lock:
                        self._bundles[msg["f"]] = msg
                elif kind == "lobby":
                    self.lobby = msg
                elif kind == "left":
                    self.lobby = None
                elif kind == "lobbies":
                    self.lobbies = msg["list"]
                elif kind == "desync":
                    self.desync_frame = msg.get("f", 0)
                else:
                    self._inbox.put(msg)
        except (OSError, ValueError, ConnectionError, struct.error) as e:
            self.reason = self.reason or "Connection lost"
        finally:
            self.connected = False
            self._inbox.put({"t": "disconnected"})

    def send(self, message):
        if not self.connected:
            return False
        try:
            with self._send_lock:
                self.sock.sendall(pack(message))
            return True
        except OSError:
            self.connected = False
            return False

    def send_input(self, frame, held, pressed):
        self.send({"t": "input", "f": frame, "h": held, "p": pressed})

    def take_bundle(self, frame):
        with self._lock:
            return self._bundles.pop(frame, None)

    def clear_match_state(self):
        with self._lock:
            self._bundles.clear()
        self.desync_frame = None

    def poll(self):
        """Every start / error / disconnected message since last time."""
        out = []
        while True:
            try:
                out.append(self._inbox.get_nowait())
            except queue.Empty:
                return out

    def my_ping(self):
        if self.lobby:
            for m in self.lobby["members"]:
                if m["slot"] == self.lobby.get("you"):
                    return m["ping"]
        return 0

    def close(self):
        self.connected = False
        try:
            self.sock.close()
        except (OSError, AttributeError):
            pass


class Connector(threading.Thread):
    """Connects on a thread so the menu doesn't freeze. Check .done, then .error (None = it worked) and .client"""

    def __init__(self, host, port, name, build):
        super().__init__(daemon=True)
        self.host, self.port, self.name, self.build = host, port, name, build
        self.client, self.error, self.done = Client(), None, False
        self.start()

    def run(self):
        try:
            self.client.connect(self.host, self.port, self.name, self.build)
        except socket.gaierror:
            self.error = "Couldn't find that address"
        except (socket.timeout, TimeoutError):
            self.error = "Timed out. Is the address right, and is the port open?"
        except ConnectionRefusedError:
            self.error = "Nobody is listening there (is the server running?)"
        except (OSError, ConnectionError, ValueError, struct.error) as e:
            self.error = str(e) or "Couldn't connect"
        self.done = True


#==========================================================
# HOSTING FROM INSIDE THE GAME
#==========================================================

def lan_address():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))                  # UDP "connect" sends nothing, it just picks the right network card
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


class HostInfo:
    """Runs a LobbyServer for this player and finds out what address to give friends.
    Friends on the internet can only reach you if TCP port `port` is forwarded on your router.
    We try to do that automatically with UPnP (needs `pip install miniupnpc`); otherwise forward it by hand."""

    def __init__(self, port=DEFAULT_PORT):
        self.port = port
        self.server = LobbyServer(port)
        self.lan_ip = lan_address()
        self.public_ip = None               # filled in by a background thread
        self.upnp = "checking..."           # a short status for the lobby screen
        self._upnp = None

    def start(self):
        self.server.start()
        threading.Thread(target=self._discover, daemon=True).start()

    def _discover(self):
        try:
            import urllib.request
            self.public_ip = urllib.request.urlopen("https://api.ipify.org", timeout=5).read().decode().strip()
        except Exception:
            self.public_ip = "?"
        try:
            import miniupnpc
        except ImportError:
            self.upnp = f"forward TCP {self.port} on your router (or pip install miniupnpc)"
            return
        try:
            u = miniupnpc.UPnP()
            u.discoverdelay = 300
            u.discover()
            u.selectigd()
            u.addportmapping(self.port, "TCP", u.lanaddr, self.port, "Platform Fighter", "")
            self._upnp = u
            self.upnp = "port opened automatically (UPnP)"
        except Exception:
            self.upnp = f"UPnP failed: forward TCP {self.port} on your router"

    def internet_line(self):
        ip = self.public_ip
        return "looking up your public IP..." if ip is None else (f"{ip}:{self.port}" if ip != "?" else "couldn't look up your public IP")

    def stop(self):
        self.server.stop()
        if self._upnp is not None:
            try:
                self._upnp.deleteportmapping(self.port, "TCP")
            except Exception:
                pass
