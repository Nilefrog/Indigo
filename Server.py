"""
Server.py  -  a dedicated Platform Fighter lobby server. Needs NO pygame and NO game files, only Network.py.

    python Server.py              (port 7777)
    python Server.py 9000         (another port)

Put it on a VPS / always-on PC, open that TCP port in its firewall, and give players "your.server.address".
They choose  Online > Join a Server  and type the address. Anyone can create lobbies on it.
"""
import sys, time
from Network import LobbyServer, DEFAULT_PORT

def log(*args):
    print(time.strftime("[%H:%M:%S]"), *args, flush=True)

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    try:
        LobbyServer(port, log=log).serve_forever()
    except OSError as e:
        print(f"Couldn't start on port {port}: {e}")
