"""
PHONES AS CONTROLLERS.

The computer running the game also runs a tiny web server. A phone on the same Wi-Fi opens its address, gets a full-screen
controller page (ControllerPage.py), and streams the buttons it is holding to the game over a WebSocket. To the rest of the
game a phone is just another controller: it can join from the character screen, move through the menus and fight.

  Remote.start()               start the server (the "Phone Controllers" screen does this); returns the address to show
  Remote.held(id, "jump")      is this phone holding that button?
  Remote.pressed(id, "jump")   did it press it this frame?
  Remote.clients               the phones that are connected right now

The phone also SHOWS THE GAME: every few frames the finished picture is shrunk, turned into a JPEG and sent down the same
WebSocket, so a phone can be used as a handheld screen + controller. (The phone can switch this off with its SCREEN button.)

No extra libraries: the HTTP and WebSocket parts are done by hand with asyncio (they are small). Nothing leaves your own network.
A short random key is part of the address, so someone else on the same Wi-Fi can't just wander in.
"""
import asyncio, base64, hashlib, io, json, random, socket, string, struct, time

import pygame
from GameSnake import Screen
from ControllerPage import PAGE

# The order of the buttons in the number the phone sends (bit 0 first). Must match BITS in ControllerPage.py.
BITS = ("left", "right", "up", "down", "jump", "dash", "parry", "heavy", "light", "confirm", "back", "pause")

VIDEO_SIZE = (768, 432)       # the picture sent to phones (the game is 1280 x 720)
VIDEO_FPS = 20                # at most this many pictures a second per phone
VIDEO_BACKLOG = 120_000       # a phone with more than this many bytes still waiting to be sent is skipped, so a slow Wi-Fi never lags the game
DEFAULT_PORT = 8765
MAX_CLIENTS = 8
TIMEOUT = 4.0                 # seconds of silence before a phone counts as gone (phones talk at least once a second)
_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"        # fixed by the WebSocket standard


def local_ip():
    """This computer's address on the local network (what a phone has to type). No data is actually sent."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("10.255.255.255", 1))
        return probe.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "127.0.0.1"
    finally:
        probe.close()


def _hex(colour):
    c = pygame.Color(colour)
    return "#%02x%02x%02x" % (c.r, c.g, c.b)


class Client:
    def __init__(self, cid, writer):
        self.id = cid
        self.writer = writer
        self.name = f"Phone {cid + 1}"
        self.down = set()               # buttons held right now (as last reported)
        self._press_events = set()      # buttons pressed since the last frame (so even a very quick tap is seen)
        self.frame_held = set()         # what the game sees this frame
        self.pressed = set()
        self.last_seen = time.monotonic()
        self.slot = None                # which player this phone is in a fight (set by start_match)
        self.colour = None
        self._sent = None               # the last "state" message we sent it
        self.open = True
        self.wants_video = True         # the phone shows the game screen (its SCREEN button turns this off)


class _Remote:
    def __init__(self):
        self.clients = {}
        self.port = None
        self.key = None
        self.running = False
        self._server = None
        self._next_id = 0
        self.in_match = False           # set by the match code: phones show the fight buttons instead of the menu buttons
        self._menus_open = 0            # >0 while any menu is on screen (the pause menu opens during a fight)
        self._last_picture = 0.0
        Screen.frame_hooks.append(self._new_frame)
        Screen.overlays.append(self._send_picture)

    #---------------- starting and stopping ----------------

    async def start(self, port=DEFAULT_PORT):
        """Starts listening (if it isn't already). Returns the address to type on the phone. Raises OSError if no port is free."""
        if not self.running:
            self.key = "".join(random.SystemRandom().choice(string.ascii_lowercase + string.digits) for _ in range(6))
            last_error = None
            for p in range(port, port + 20):                         # if 8765 is busy, try the next ones
                try:
                    self._server = await asyncio.start_server(self._handle, "0.0.0.0", p)
                    self.port, self.running = p, True
                    break
                except OSError as e:
                    last_error = e
            if not self.running:
                raise last_error
        return self.url

    async def stop(self):
        for c in list(self.clients.values()):
            self._drop(c)
        if self._server is not None:
            self._server.close()
            self._server = None
        self.running = False

    @property
    def url(self):
        return f"http://{local_ip()}:{self.port}/?k={self.key}" if self.running else None

    #---------------- fight buttons or menu buttons? ----------------

    @property
    def mode(self):
        return "game" if self.in_match and self._menus_open == 0 else "menu"

    def set_in_match(self, value):
        self.in_match = value

    def menu_opened(self):
        self._menus_open += 1

    def menu_closed(self):
        self._menus_open = max(0, self._menus_open - 1)

    #---------------- what the game asks ----------------

    def held(self, cid, action):
        c = self.clients.get(cid)
        return c is not None and action in c.frame_held

    def pressed(self, cid, action):
        c = self.clients.get(cid)
        return c is not None and action in c.pressed

    def pause_pressed(self):
        return any("pause" in c.pressed for c in self.clients.values() if c.slot is not None)

    def label(self, cid):
        c = self.clients.get(cid)
        return c.name if c is not None else "Phone"

    def assign(self, cid, slot, colour):
        """Tells a phone which player it is, so it can show the right colour."""
        c = self.clients.get(cid)
        if c is not None:
            c.slot, c.colour = slot, _hex(colour)

    def clear_assignments(self):
        for c in self.clients.values():
            c.slot = c.colour = None

    #---------------- once per frame ----------------

    def _new_frame(self):
        if not self.clients:
            return
        now = time.monotonic()
        mode = self.mode
        for c in list(self.clients.values()):
            if now - c.last_seen > TIMEOUT:
                self._drop(c)
                continue
            c.pressed = c._press_events
            c._press_events = set()
            c.frame_held = c.down | c.pressed
            state = (mode, c.slot, c.colour, c.name)
            if state != c._sent:                                      # only tell the phone when something changed
                c._sent = state
                self._send(c, {"t": "state", "mode": mode, "slot": c.slot, "colour": c.colour, "name": c.name})

    def _send_picture(self, surface):
        """Called with every finished picture. Sends it (as a small JPEG) to the phones that are watching, at most VIDEO_FPS a second."""
        if not self.clients:
            return
        now = time.monotonic()
        if now - self._last_picture < 1.0 / VIDEO_FPS:
            return
        viewers = []
        for c in self.clients.values():
            transport = c.writer.transport
            if c.wants_video and c.open and transport is not None and transport.get_write_buffer_size() < VIDEO_BACKLOG:
                viewers.append(c)
        if not viewers:
            return
        self._last_picture = now
        try:
            small = pygame.transform.smoothscale(surface, VIDEO_SIZE)
            buffer = io.BytesIO()
            pygame.image.save(small, buffer, "picture.jpg")
        except Exception:                                              # no JPEG support in this pygame: just don't stream
            return
        data = buffer.getvalue()
        for c in viewers:
            self._frame(c, 0x2, data)                                  # a binary WebSocket message

    def _drop(self, c):
        c.open = False
        self.clients.pop(c.id, None)
        try:
            c.writer.close()
        except Exception:
            pass

    #---------------- web server ----------------

    async def _handle(self, reader, writer):
        client = None
        try:
            sock = writer.get_extra_info("socket")
            if sock is not None:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)          # send each little message straight away
            head = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 5)
            lines = head.decode("latin-1").split("\r\n")
            method, target, _ = lines[0].split(" ", 2)
            headers = {}
            for line in lines[1:]:
                if ":" in line:
                    k, v = line.split(":", 1)
                    headers[k.strip().lower()] = v.strip()
            path, _, query = target.partition("?")
            params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)

            if headers.get("upgrade", "").lower() == "websocket" and path == "/ws":
                if params.get("k") != self.key or len(self.clients) >= MAX_CLIENTS or "sec-websocket-key" not in headers:
                    writer.write(b"HTTP/1.1 403 Forbidden\r\nConnection: close\r\nContent-Length: 0\r\n\r\n")
                    await writer.drain()
                    return
                accept = base64.b64encode(hashlib.sha1((headers["sec-websocket-key"] + _GUID).encode()).digest()).decode()
                writer.write(("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                              f"Sec-WebSocket-Accept: {accept}\r\n\r\n").encode())
                await writer.drain()
                client = Client(self._next_id, writer)
                self._next_id += 1
                self.clients[client.id] = client
                await self._read_frames(client, reader)
            elif method == "GET" and path in ("/", "/index.html"):
                body = PAGE.encode("utf-8")
                writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nCache-Control: no-store\r\n"
                             b"Connection: close\r\nContent-Length: " + str(len(body)).encode() + b"\r\n\r\n" + body)
                await writer.drain()
            else:
                writer.write(b"HTTP/1.1 404 Not Found\r\nConnection: close\r\nContent-Length: 0\r\n\r\n")
                await writer.drain()
        except (asyncio.IncompleteReadError, asyncio.TimeoutError, asyncio.LimitOverrunError, ConnectionError, ValueError, OSError):
            pass
        finally:
            if client is not None:
                self._drop(client)
            else:
                try:
                    writer.close()
                except Exception:
                    pass

    async def _read_frames(self, c, reader):
        """Reads WebSocket messages from one phone until it goes away."""
        message = b""
        while c.open:
            b1, b2 = await reader.readexactly(2)
            fin, opcode, masked, length = b1 & 0x80, b1 & 0x0F, b2 & 0x80, b2 & 0x7F
            if length == 126:
                length = struct.unpack(">H", await reader.readexactly(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", await reader.readexactly(8))[0]
            if length > 16384:                                          # our messages are tiny; anything huge is not ours
                return
            mask = await reader.readexactly(4) if masked else b""
            data = await reader.readexactly(length)
            if masked:
                data = bytes(byte ^ mask[i % 4] for i, byte in enumerate(data))
            if opcode == 0x8:                                           # close
                return
            if opcode == 0x9:                                           # ping -> pong
                self._frame(c, 0xA, data)
                continue
            if opcode in (0x1, 0x0):                                    # text (0x0 = continuation of a split message)
                message += data
                if fin:
                    self._message(c, message)
                    message = b""

    def _message(self, c, raw):
        c.last_seen = time.monotonic()
        try:
            msg = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return
        if not isinstance(msg, dict):                                  # valid JSON, but not a message from our page
            return
        kind = msg.get("t")
        if kind == "in":
            mask = msg.get("h")
            if isinstance(mask, int):
                held = {name for i, name in enumerate(BITS) if mask >> i & 1}
                c._press_events |= held - c.down                        # newly pressed
                c.down = held
        elif kind == "view":                                           # the phone's SCREEN button
            c.wants_video = bool(msg.get("on"))
        elif kind == "hello":
            name = str(msg.get("name", "")).strip()[:14]
            if name:
                c.name = name
                c._sent = None                                          # tell it again, with the name

    #---------------- sending to a phone ----------------

    def _frame(self, c, opcode, payload):
        n = len(payload)
        head = bytes([0x80 | opcode])
        if n < 126:
            head += bytes([n])
        elif n < 65536:
            head += bytes([126]) + struct.pack(">H", n)
        else:
            head += bytes([127]) + struct.pack(">Q", n)
        try:
            c.writer.write(head + payload)
        except Exception:
            self._drop(c)

    def _send(self, c, obj):
        self._frame(c, 0x1, json.dumps(obj).encode("utf-8"))


Remote = _Remote()
