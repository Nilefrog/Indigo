from GameSnake import *
from Controls import *      # per-player key / button layouts + saved settings
from Menus import *         # main menu, settings, character select, pause
import math, random, time, zlib, os
import Network                # online play: lobby server + client
from OnlineMenus import online_menu
import MatchSystem as ms     # rules, lives, stats, crowns, match screens
from types import SimpleNamespace

#Set the Screen Size and FPS
Screen.size(1280, 720)
Screen.fps = 60

#Allows the Screen to be Moved and Altered
Screen.set_resizable(True)

#LEVEL LAYOUTS AND LOADING
default_stage = """
QQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
Zxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx1xxx2xbx3xxx4xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
Zxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx000000000000000xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
Zxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx00000000000xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
Zxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx000000000xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
Zxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx0000000xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
Zxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx00000xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ
"""
twin_islands = """
QQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxbxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
Zxxxxxxxxxxxxxxxxxx1xxxxxx2xxxxxxxxxxxxxxxxxxxxxxxxx3xxxxxx4xxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
Zxxxxxxxxxxxxxx000000000000000xxxxxxxxxxxxxxxxxx000000000000000xxxxxxxxxxxxxxxZ
Zxxxxxxxxxxxxxxxx00000000000xxxxxxxxxxxxxxxxxxxxxx00000000000xxxxxxxxxxxxxxxxxZ
Zxxxxxxxxxxxxxxxxx00000000xxxxxxxxxxxxxxxxxxxxxxxxx000000000xxxxxxxxxxxxxxxxxxZ
Zxxxxxxxxxxxxxxxxxx000000xxxxxxxxxxxxxxxxxxxxxxxxxxx0000000xxxxxxxxxxxxxxxxxxxZ
Zxxxxxxxxxxxxxxxxxxx0000xxxxxxxxxxxxxxxxxxxxxxxxxxxxx00000xxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ
"""
invertigo = """
QQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
Zxxxxxxxxxxxxxxx000000000000xxxxx1xxx2xbx3xxx4xxxxxx000000000000000xxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
Zxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx000000000000000xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ
"""

default_legend = {
    "0": "ground",
    "#": "wall",
}

#---------------- extra stages ----------------
#Stage Builder thingy for when im lazzzyyy
def make_stage(cols, rows, platforms, spawns, barrel):
    grid = [["x"] * cols for _ in range(rows)]
    for c in range(cols):
        grid[0][c], grid[rows - 1][c] = "Q", "Z"
    for r in range(1, rows):
        grid[r][0] = grid[r][cols - 1] = "Z"
    for c, r, w, h in platforms:
        for rr in range(r, r + h):
            for cc in range(c, c + w):
                grid[rr][cc] = "0"
    for i, (c, r) in enumerate(spawns):
        grid[r][c] = str(i + 1)
    grid[barrel[1]][barrel[0]] = "b"
    return "\n".join("".join(row) for row in grid)

# Every stage the map select screen offers. layout = the stage, legend = which tile picture each character uses.
MAPS = [
    {"name": "Sky Isles", "blurb": "The classic. Open sky and one big drifting platform.", "layout": default_stage},
    {"name": "Twin Isles",   "blurb": "Two side by side islands",     "layout": twin_islands},
    {"name": "Invertigo",  "blurb": "Two islands and one tiny platform in the middle.",      "layout": invertigo},
]
allLevels = {i + 1: m["layout"] for i, m in enumerate(MAPS)}
allLegends = {i + 1: default_legend for i in range(len(MAPS))}

def load_level(level_num,LevelList,LegendList):
    global level

    legend = LegendList[level_num]
    if 'level' in globals():
        level.delete()
        
    layout = LevelList[level_num]
    level = TileMap(layout, legend, tile_size=32, solid="0#")


P1_CONTROLS = {"left": "a", "right": "d", "up": "w", "down": "s",
               "jump": "space", "dash": "left shift", "parry": "q",
               "heavy": "h", "light": "j"}

P2_CONTROLS = {"left": "left", "right": "right", "up": "up", "down": "down",
               "jump": "right shift", "dash": "right ctrl", "parry": "/",
               "heavy": ".", "light": ","}

# Controller bindings (shared by every controller). Names: a b x y  lb rb  lt rt  start back  l3 r3
# "left" "right" "up" "down" mean left stick OR d-pad. A binding can be one name or a tuple of names.
# Buttons are named by POSITION, so "a" is the bottom face button (Cross on PlayStation).
PAD_CONTROLS = {"left": "left", "right": "right", "up": "up", "down": "down",
                "jump": "a", "dash": "rt", "parry": "lt",
                "heavy": "y", "light": "x"}

# Every player slot gets its OWN copy of these, which the Settings menu can change. Players 3 and 4 have no keyboard keys by default
# (they are controller players until you bind some in Settings > Controls), and the choices are saved to settings.json.
settings = Settings(default_keys=[P1_CONTROLS, P2_CONTROLS], default_pad=PAD_CONTROLS)
settings.apply()

#Everything that can change how a fight plays out. Online, players must have identical copies or the fights would drift apart.
_HERE = os.path.dirname(os.path.abspath(__file__))
ONLINE_BUILD = Network.build_id([os.path.join(_HERE, f) for f in ("Platform_Fighter.py", "GameSnake.py", "MatchSystem.py")])

#The random numbers that affect gameplay (e.g. how fast a droplet is thrown). Seeded identically for everyone online.
#(random_float() is still fine for particles and sounds, which only change how things LOOK.)
sim_rng = random.Random()

#==========================================================
# MOVEMENT TUNING
#==========================================================

# How many frames you can still jump after leaving the ground. It's also how the game knows you're standing on
# something: touching the floor sets coyote_time to COYOTE_TIME, and "exactly COYOTE_TIME" means "grounded this frame".
COYOTE_TIME = 15

#==========================================================
# PARRY / RIPOSTE TUNING
#==========================================================

PARRY_STUN = 180          # frames an attacker is stunned (and open to a riposte) after being parried
RIPOSTE_RANGE_X = 80     # how close you must be to a parried player for neutral+light to become a riposte
RIPOSTE_RANGE_Y = 45

#==========================================================
# VFX
#==========================================================

HITSTOP_MIN_DAMAGE = 8   # hits weaker than this don't freeze the game at all
HITSTOP_DIVISOR = 3      # frames frozen = damage / this
HITSTOP_MAX = 30         # never freeze for longer than this many frames

BLOOD = ["darkred", (150, 0, 0), (200, 10, 10)]   # every blood particle picks one of these
BLOOD_PER_DAMAGE = 1.5   # blood particles = 4 + damage * this
BLOOD_MAX = 70

#CLASSES

#==========================================================
# COMBAT BUILDING BLOCKS
#   Hitbox     - one damaging rectangle (owns the knockback maths, and what happens when it's parried)
#   Move       - base class for anything that can sit in player.current_attack
#   Attack     - the simple "startup / active / recovery" move (one hitbox)
#   Projectile - a hitbox that travels on its own
#==========================================================

class Hitbox: # Damaging Hitboxes
    """
    mode decides which way a victim is launched:
      "angle"  - fixed angle, mirrored by the attacker's facing (0 = forward, 90 = up, negative = down/spike)
      "radial" - straight away from the centre of this hitbox (explosions)
      "pull"   - horizontally TOWARDS the owner, vertical part still comes from angle (inverse knockback)
    """
    def __init__(self, owner, width, height, offset, damage, kbx, kby, angle, stun, mode="angle", colour="red", hitstop=None):
        self.owner = owner
        self.offset = offset
        self.damage, self.kbx, self.kby, self.angle, self.stun = damage, kbx, kby, angle, stun
        self.mode = mode
        self.hitstop = hitstop            # frames to freeze the game on hit. None = worked out from damage, 0 = never
        self.zone = Zone(0, 0, width, height, colour)
        self.already_hit = set()
        self.active = False
        self.projectile = None        # set by Projectile, so a parry knows to reflect instead of stun
        self.on_hit = None            # optional function(target), called whenever this hitbox lands a hit (not a parried one)
        self._ghosts = []                 # see-through copies of this hitbox that have gone through a portal
        self._deleted = False

    def set_active(self, on):
        if on and not self.active:
            self.already_hit.clear()      # a re-activated box can hit again
        self.active = on
        self.zone.visible = on
        if not on:
            self._hide_ghosts()

    def _hide_ghosts(self):
        for g in self._ghosts:
            g.visible = False

    def place(self, x, y, facing):
        self.zone.x = x + self.offset[0] * facing
        self.zone.y = y + self.offset[1]

    def check(self, targets, facing):
        """Returns True if this call landed at least one hit."""
        if not self.active:
            return False
        boxes = [(self.zone._rect(), None)]
        if self.projectile is None:       # melee only: projectiles teleport as a whole instead
            boxes += portal_slices(self.zone._rect(), self.owner.x)
        while len(self._ghosts) < len(boxes) - 1:
            self._ghosts.append(Zone(0, 0, 1, 1, self.zone.colour))
        for i, g in enumerate(self._ghosts):      # show the slice that came out of the other portal
            if i + 1 < len(boxes):
                r = boxes[i + 1][0]
                g.x, g.y, g.width, g.height = r.centerx, r.centery, r.width, r.height
                g.visible = True
            else:
                g.visible = False
        landed = False
        for t in targets:
            if self._deleted:             # a parry can cancel the whole move mid-loop
                break
            if t in self.already_hit:
                continue
            for rect, centre in boxes:
                if t._hitbox_rect().colliderect(rect):
                    self.already_hit.add(t)
                    if self.hit(t, facing, centre):
                        landed = True
                    break
        return landed

    def hit(self, target, facing, centre=None):
        t_stats = getattr(target, "stats", None)
        if t_stats is not None and t_stats.invuln > 0:      # respawn shield: nothing touches you
            return False
        if target.parrying:
            # Parry Colour Burst
            Particles.burst(
                target.x, target.y,
                count=70,
                colour=(100, 50, 255),
                speed=(10, 12),
                life=(30, 60),
                size=(3, 7),
                gravity=0,
                drag=0.98
            )
            if self.projectile:
                self.projectile.reflect(target)        # parried projectile: sent back at the thrower
            else:
                self.owner.on_parried(target)          # parried melee: attacker is stunned and left open
            target.on_parry_success()
            return False
        hitsfx = ["Dmg","Dmg2","Dmg3"]
        Sound.play(hitsfx[random_number(0,2)])
        dealt = self.damage * match.rules.damage_mult * getattr(self.owner, "power", 1)        # the Damage Rate rule, and the owner's attack power (Sion's Pain Trade)
        target.health += dealt
        ms.record_hit(self.owner, target, dealt)             # stats + remembers who hit you last (for kill credit)
        training_on_hit(self.owner, target, dealt)           # combo counter (does nothing outside training)
        scale = (target.health / 200) + 1
        a = math.radians(self.angle)
        if not self.projectile:
            self.owner.dash_charges = max(self.owner.dash_charges, 1)       # (max, so a character with 2 dashes keeps them)
            self.owner.jump_charges = max(self.owner.jump_charges, 1)

        if self.mode == "radial":
            cx, cy = centre if centre else (self.zone.x, self.zone.y)
            dx = target.x - cx
            dy = target.y - cy
            dist = math.hypot(dx, dy) or 1          # `or 1` avoids dividing by zero
            vx, vy = dx / dist, dy / dist
        elif self.mode == "pull":
            toward_owner = 1 if self.owner.x > target.x else -1
            vx, vy = math.cos(a) * toward_owner, -math.sin(a)
        else:
            vx, vy = math.cos(a) * facing, -math.sin(a)

        target.on_hit()                            # cancels whatever the victim was doing (first, it releases the move's lock)
        target.x_velocity = vx * self.kbx * scale
        target.y_velocity = vy * self.kby * scale
        target.actionableTimer = self.stun
        target.NoGravTimer = 0

        self.hit_effects(target)
        self.owner.on_dealt_hit(self.damage, target)      # lets a character react to landing ANY hit (Cleaning Lady fills her trash bag)
        if self.on_hit:
            self.on_hit(target)
        return True

    def hitstop_frames(self):
        if self.hitstop is not None:
            Sound.play("Heavy Hitter")
            return self.hitstop
        if self.damage < HITSTOP_MIN_DAMAGE:
            return 0
        Sound.play("Heavy Hitter")
        return min(HITSTOP_MAX, round(self.damage / HITSTOP_DIVISOR))

    def hit_effects(self, target):
        # Blood sprays the way the victim is being launched (GameSnake angles: 0 = up, 90 = right)
        vx, vy = target.x_velocity, target.y_velocity
        direction = None if abs(vx) + abs(vy) < 0.1 else math.degrees(math.atan2(vx, -vy)) % 360
        amount = min(BLOOD_MAX, int(4 + self.damage * BLOOD_PER_DAMAGE))
        Particles.burst(target.x, target.y, count=amount, colour=BLOOD,
                        direction=direction, spread=70, speed=(3, 9), life=(15, 35), size=(2, 4), gravity=0.3)
        Particles.burst(target.x, target.y, count=amount // 3, colour=BLOOD,      # a smaller mist going every direction
                        speed=(1, 3), life=(10, 20), size=(1, 3), gravity=0.1)

        frames = self.hitstop_frames()
        if frames > 0:
            Screen.hitstop(frames)

    def delete(self):
        if not self._deleted:
            self._deleted = True
            self.zone.delete()
            for g in self._ghosts:
                g.delete()


class Move:
    """Base class for anything that can be stored in Player.current_attack.
    Needs: update(targets), cancel(), .finished and .total_frames (the lock applied by start_attack)."""
    total_frames = 10 ** 6            # variable-length moves lock the owner "forever" and free them with end()

    def __init__(self, owner):
        self.owner = owner
        self.facing = owner.facing    # snapshot, so holding left/right mid-move can't flip it
        self.finished = False
        self.cancelled = False
        self.hitboxes = []

    def add_hitbox(self, hitbox):
        self.hitboxes.append(hitbox)
        return hitbox

    def update(self, targets):
        pass

    def end(self, recovery=0):
        """Finish the move. recovery = extra frames the owner stays locked afterwards."""
        if not self.cancelled:        # a cancelled move (parried, hit...) must not overwrite the stun that cancelled it
            self.owner.actionableTimer = recovery
        self.finished = True
        self.cancel()

    def cancel(self):
        self.cancelled = True
        for hb in self.hitboxes:
            hb.delete()


class Attack(Move):
    """The simple move: startup -> active -> recovery, with a single hitbox.
    on_fire(owner)    - called once on the first active frame (recoil, spawning projectiles...)
    on_connect(owner) - called whenever the hitbox lands a hit (pogo bounce...)
    hitstop           - frames to freeze the game when it lands (None = worked out from damage, 0 = never)
    active=0 gives a move that never hits, handy for throws that only spawn a projectile."""
    def __init__(self, owner, width, height, offset, startup, active, recovery,
                 damage, knockbackx, knockbacky, angle, stun,
                 mode="angle", on_fire=None, on_connect=None, hitstop=None):
        super().__init__(owner)
        self.startup, self.active, self.recovery = startup, active, recovery
        self.total_frames = startup + active + recovery
        self.frame = 0
        self.on_fire = on_fire
        self.on_connect = on_connect
        self.hitbox = self.add_hitbox(Hitbox(owner, width, height, offset,
                                             damage, knockbackx, knockbacky, angle, stun, mode, hitstop=hitstop))

    def is_active(self):
        return self.startup <= self.frame < self.startup + self.active

    def update(self, targets):
        o = self.owner
        if self.frame == self.startup and self.on_fire:
            self.on_fire(o)

        self.hitbox.set_active(self.is_active())
        self.hitbox.place(o.x, o.y, self.facing)
        if self.hitbox.check(targets, self.facing) and self.on_connect:
            self.on_connect(o)

        self.frame += 1
        if self.frame >= self.total_frames:
            self.finished = True
            self.cancel()


projectiles = []

# Areas where gravity is different (Angellica's gravity zone). Each one has .scale and .contains(player).
gravity_fields = []

def gravity_scale(player):
    """How strongly gravity pulls this player right now (1 = normal). Overlapping fields don't stack: the weakest one wins."""
    return min([f.scale for f in gravity_fields if f.contains(player)], default=1)

class Projectile: #Player Attack Projectiles
    def __init__(self, x, y, facing, speed, lifetime, hitbox, pierce=False, angle=0, gravity=0, ignore_tiles=False):
        self.x, self.y, self.facing = x, y, facing
        self.speed, self.lifetime = speed, lifetime
        self.angle = angle            # degrees away from straight ahead: 0 = forward, 90 = straight up, negative = down
        self.gravity = gravity        # pulls it down a bit more every frame, so shots can arc
        self.fall = 0
        self.ignore_tiles = ignore_tiles   # True = flies straight through walls and the floor
        self.portal_travel = not ignore_tiles       # Rex's ship ignores portals
        self.hitbox = hitbox
        self.hitbox.projectile = self
        self.pierce = pierce          # False = disappears on its first hit
        hitbox.set_active(True)
        projectiles.append(self)

    @property
    def owner(self):                  # whoever it currently belongs to (changes when reflected)
        return self.hitbox.owner

    def reflect(self, parrier):
        """Parried! Send it back the way it came, faster, and make it the parrier's projectile."""
        self.facing = -self.facing
        self.speed = min(self.speed * 1.5, 24)       # capped so it can't skip over a player
        self.lifetime = max(self.lifetime, 45)
        self.hitbox.owner = parrier
        self.hitbox.already_hit = {parrier}          # the old owner can be hit again, the parrier can't

    def update(self, targets, tilemap):
        old_x, old_y = self.x, self.y
        a = math.radians(self.angle)
        self.fall += self.gravity
        self.x += self.speed * math.cos(a) * self.facing
        self.y += -self.speed * math.sin(a) + self.fall
        if self.portal_travel:
            portal_transit(self, old_x, old_y, lambda x, y: not tilemap.is_solid(x, y))
        self.lifetime -= 1
        self.hitbox.place(self.x, self.y, self.facing)
        landed = self.hitbox.check(targets, self.facing)
        if self.lifetime <= 0 or (not self.ignore_tiles and tilemap.is_solid(self.x, self.y)) or (landed and not self.pierce):
            self.hitbox.delete()
            projectiles.remove(self)


#==========================================================
# PLAYER
#==========================================================

class Player(Sprite): #Generalised Player, Superclass for each Character

    # What the character select screen shows. Every character overrides these, so a new character just works there.
    title = "Fighter"                 # the name shown on screen
    blurb = ""                        # a short one line description
    preview = "player"                # which sprite to show (the name of a file in your sprites folder)
    preview_size = 300                # how big to draw it there (a percentage, like Sprite.size)

    def __init__(self,currentLevel, name, x=None, y=None, size=100, spawnIcon = "p", controls=None, pad=None, pad_controls=None, slot=None):
        super().__init__(name, x, y, size)
        self.controls = controls          # a keyboard controls dictionary, or None for no keyboard input
        self.net = None                   # online: a NetInput that replaces the keyboard / controller
        self.pad = pad                    # which controller slot drives this player (0 = first), or None
        self.pad_controls = pad_controls or PAD_CONTROLS    # this player's controller layout
        self.slot = slot                  # which player they are (0 = P1 ... 3 = P4)
        self.spawnIcon = spawnIcon
        self.max_speed = 7
        self.walk_acceleration = 3
        self.air_acceleration = 0.5
        self.walk_decceleration = 1
        self.air_decceleration = 0.2
        self.gravity = 0.4
        self.NoGravTimer = 0
        self.x_velocity = 0
        self.y_velocity = 0
        self.jump_velocity = 8
        self.jump_charges = 0
        self.max_jump_charges = 1
        self.jump_buffer = 0
        self.coyote_time = 0
        self.dash_charges = 0
        self.max_dash_charges = 1
        self.dash_speed = 10
        self.actionable = True
        self.actionableTimer = 0
        self.is_dashing = False
        self.dash_timer = 0
        self.parrying = False
        self.parryTimer = 0
        self.parryCooldown = 0
        self.parried_timer = 0            # >0 = just got parried, wide open to a riposte
        self.facing = 1
        self.current_attack = None
        self.health = 0

        self.set_hitbox(20, 25, 0, 0)     # every player gets the same hitbox

        px, py = currentLevel.find(spawnIcon)[0]
        self.go_to(px,py)

    #---------------- input ----------------
    # Everything reads input through these, so no code mentions a specific key.
    # Actions: left right up down jump dash parry heavy light

    # A player can use the keyboard, a controller, or both at once.

    # An action can be unbound (None) in the Settings menu, in which case it simply never happens.

    def held(self, action):
        if self.net is not None:
            return self.net.held(action)
        key = self.controls.get(action) if self.controls is not None else None
        if key and Keyboard.held(key):
            return True
        button = self.pad_controls.get(action)
        return self.pad is not None and button is not None and Gamepad.held(self.pad, button)

    def pressed(self, action):
        if self.net is not None:
            return self.net.pressed(action)
        key = self.controls.get(action) if self.controls is not None else None
        if key and Keyboard.pressed(key):
            return True
        button = self.pad_controls.get(action)
        return self.pad is not None and button is not None and Gamepad.pressed(self.pad, button)

    #---------------- movement ----------------

    def handle_movement(self,currentLevel: TileMap):
        old_y = self.y
        old_x = self.x

        #Decrementing Movement Related Timers 
        if self.jump_buffer > 0: self.jump_buffer -= 1
        if self.coyote_time > 0: self.coyote_time -= 1
        if self.actionableTimer > 0: self.actionableTimer -= 1
        if self.NoGravTimer > 0: self.NoGravTimer -= 1
        if self.parried_timer > 0: self.parried_timer -= 1

        if self.dash_timer > 0: self.dash_timer -= 1
        if self.dash_timer == 0: self.is_dashing = False 
        else: self.is_dashing = True

        if self.parryCooldown > 0: self.parryCooldown -= 1
        if self.parryTimer > 0: self.parryTimer -= 1
        if self.parryTimer == 0: self.parrying = False 
        else: self.parrying = True

        if self.actionableTimer == 0: #actionability check
            self.actionable = True
        else:
            self.actionable = False 

        if self.NoGravTimer == 0: #account for gravity
            self.y_velocity += self.gravity * gravity_scale(self)
        if self.pressed("jump"):
                self.jump_buffer = 5   

        if self.actionable:
            
            if self.held("left"): self.facing = -1
            if self.held("right"): self.facing = 1

            #Jump Logic
            if self.jump_buffer != 0 and self.jump_charges > 0 and self.coyote_time == 0:
                self.jump_charges -= 1
                self.y_velocity = -(self.jump_velocity + 2)
                self.jump_buffer = 0
            elif self.jump_buffer != 0 and self.coyote_time != 0:
                self.y_velocity = -self.jump_velocity
                self.jump_buffer = 0
                self.coyote_time = 0

            #Walk Logic
            if self.coyote_time == COYOTE_TIME - 1: #A Grounded Check (one frame has already counted down)

                if self.held("left"):
                    if self.x_velocity > -self.max_speed:
                        self.x_velocity -= self.walk_acceleration
                        if self.x_velocity < -self.max_speed:
                            self.x_velocity = -self.max_speed

                if self.held("right"):
                    if self.x_velocity < self.max_speed:
                        self.x_velocity += self.walk_acceleration
                        if self.x_velocity > self.max_speed:
                            self.x_velocity = self.max_speed
            else: # Arial Movement Options

                if self.held("left"):
                    if self.x_velocity > -self.max_speed:
                        self.x_velocity -= self.air_acceleration
                        if self.x_velocity < -self.max_speed:
                            self.x_velocity = -self.max_speed

                if self.held("right"):
                    if self.x_velocity < self.max_speed:
                        self.x_velocity += self.air_acceleration
                        if self.x_velocity > self.max_speed:
                            self.x_velocity = self.max_speed

                if self.pressed("dash") and self.dash_charges > 0:
                    self.dash_charges -= 1
                    currentInputDir = 0
                    if self.held("left"): currentInputDir -= 1
                    if self.held("right"): currentInputDir += 1
                    if currentInputDir == 0:
                        if self.x_velocity > 0:
                            currentInputDir = 1
                        elif self.x_velocity < 0:
                            currentInputDir = -1
                        else:
                            currentInputDir = 1 * self.facing   #Move in last direction facing for if you just dash without moving like a fool
                    self.x_velocity = self.dash_speed * currentInputDir
                    self.actionableTimer = 10
                    self.dash_timer = 10
                    self.NoGravTimer = 10
                    self.y_velocity = 0

            if self.pressed("parry") and self.parryCooldown == 0:
                # Parry Colour Burst
                Particles.burst(
                    self.x, self.y,
                    count=70,
                    colour=(0, 255, 255),
                    speed=(3, 12),
                    life=(10, 20),
                    size=(3, 7),
                    gravity=0,
                    drag=0.98
                )
                self.actionableTimer = 30
                self.parryTimer = 20
                self.x_velocity = 0
                self.y_velocity = 0
                self.NoGravTimer = 20
                self.parryCooldown = 50

        if self.coyote_time == COYOTE_TIME - 1: # Friction Sepreate of actionability
            #Calculate Ground Friction
                if self.x_velocity > 0:
                    self.x_velocity -= self.walk_decceleration
                    if self.x_velocity < 0:
                        self.x_velocity = 0
                if self.x_velocity < 0:
                    self.x_velocity += self.walk_decceleration
                    if self.x_velocity > 0:
                        self.x_velocity = 0
        else:
            #Calculate Air Friction
                if self.x_velocity > 0:
                    self.x_velocity -= self.air_decceleration
                    if self.x_velocity < 0:
                        self.x_velocity = 0
                if self.x_velocity < 0:
                    self.x_velocity += self.air_decceleration
                    if self.x_velocity > 0:
                        self.x_velocity = 0
        
        self.x += self.x_velocity
        if currentLevel.touching(self):
            self.x = old_x
            self.x_velocity = 0

        self.y += self.y_velocity
        if currentLevel.touching(self):
            self.coyote_time = COYOTE_TIME
            self.y = old_y
            if not self.y_velocity < 0:
                self.dash_charges = self.max_dash_charges
                self.jump_charges = self.max_jump_charges
            self.y_velocity = 0

    #---------------- attacks ----------------

    def attackChecks(self, targets=()):
        pass                              # characters override this; targets = every other player

    def start_attack(self, attack):
        if self.current_attack is not None:      # can't start one mid-swing
            attack.cancel()                      # throw away the hitboxes the refused move just built
            return
        self.current_attack = attack
        self.actionableTimer = attack.total_frames   # locks movement for the whole move
        self.actionable = False

    def update_attack(self, targets):
        attack = self.current_attack
        if attack:
            attack.update(targets)
            # The move may have been cancelled during its own update (parried), so check it's still ours
            if attack.finished and self.current_attack is attack:
                self.current_attack = None

    def cancel_attack(self):
        if self.current_attack:
            self.current_attack.cancel()
            self.current_attack = None
            self.actionableTimer = 0      # the move was holding the lock, so let go of it
            self.NoGravTimer = 0

    #---------------- HUD ----------------
    # Characters override these to draw extra UI next to their damage counter.
    # x, y is the centre of that player's HUD column. Anything you put in hud_sprites is deleted for you when the match ends.

    def make_hud(self, x, y):
        self.hud_sprites = []

    def update_hud(self):
        pass

    def cleanup(self):
        """Called when the match ends, before the player is deleted. Characters override it to delete anything extra they made."""
        pass

    def delete_hud(self):
        for sprite in self.hud_sprites:
            sprite.delete()
        self.hud_sprites = []

    def reset_state(self):
        """Back to a clean slate (used when respawning)."""
        self.cancel_attack()
        self.actionableTimer = 0
        self.NoGravTimer = 0
        self.parryTimer = 0
        self.parried_timer = 0
        self.dash_timer = 0
        self.x_velocity = 0
        self.y_velocity = 0
        self.dash_charges = self.max_dash_charges
        self.jump_charges = self.max_jump_charges

    #---------------- getting hit / parrying ----------------

    def on_hit(self):
        # Being hit interrupts whatever you were doing (including charging Consume) and closes any riposte window
        self.cancel_attack()
        self.parried_timer = 0

    def on_parried(self, parrier):
        """Your attack was parried: it's cancelled, you're stunned for a while and open to a riposte."""
        self.cancel_attack()
        self.actionableTimer = PARRY_STUN
        self.parried_timer = PARRY_STUN
        self.NoGravTimer = 0
        direction = 1 if self.x > parrier.x else -1
        self.x_velocity = direction * 4           # small shove away from the parrier

    def on_dealt_hit(self, damage, target):
        """You landed a hit (not a parried one). Characters override this."""
        pass

    def should_die(self):
        """Return True to be sent back to the spawn point this frame (Bombhead's fuse running out). Characters override this."""
        return False

    def on_enemy_death(self, dead):
        """Another player just died / respawned. Characters override this (Bombhead's fuse refills)."""
        pass

    def on_parry_success(self):
        """You parried something: skip the rest of the parry's endlag so you can punish straight away."""
        self.actionableTimer = 0
        self.dash_charges = self.max_dash_charges
        self.jump_charges = self.max_jump_charges
        self.NoGravTimer = 0
        print("Parried!")
        if getattr(self, "stats", None) is not None:
            self.stats.parries += 1

    def try_riposte(self, targets):
        """Neutral light attack next to a parried player = riposte. Returns True if one was started."""
        near = [t for t in targets
                if t.parried_timer > 0
                and abs(t.x - self.x) <= RIPOSTE_RANGE_X
                and abs(t.y - self.y) <= RIPOSTE_RANGE_Y]
        if not near:
            return False
        victim = min(near, key=lambda t: abs(t.x - self.x))
        self.facing = 1 if victim.x >= self.x else -1      # turn to face them before the move snapshots facing
        # Quick to start, very slow to finish (finding the weak point), huge damage, barely any knockback
        self.start_attack(Attack(self, width=90, height=70, offset=(35, 0), startup=3, active=3, recovery=35,
                                 damage=35, knockbackx=3, knockbacky=3, angle=45, stun=30))
        return True

#Dummies <3 (theyre gonna get murdered)

DUMMY_BEHAVIOURS = ["Stand Still", "Walk", "Jump", "Parry Loop", "Parry on Attack"]
DUMMY_REACTION = 14        # frames the "Parry on Attack" dummy needs to notice a nearby attack before it parries

class Dummy(Player):
    """A training partner. 'Stand Still' does nothing. Every other behaviour just presses buttons through the normal
    held() / pressed() functions (see think()), so the dummy moves, jumps, dashes and parries by exactly the same rules as a player."""
    def __init__(self, currentLevel, name, x=None, y=None, size=100, spawnIcon="e", slot=None):
        super().__init__(currentLevel, name, x, y, size, spawnIcon, controls=None, slot=slot)
        self.behaviour = DUMMY_BEHAVIOURS[0]
        self.want_held, self.want_pressed = set(), set()
        self.react = 0

    def think(self, foes):
        """Decides this frame's buttons. Called once per frame, before step_game."""
        f = ms.State.frame
        b = self.behaviour
        self.want_held, self.want_pressed = set(), set()
        if b == "Walk":
            self.want_held.add("left" if (f // 30) % 2 == 0 else "right")
        elif b == "Jump" and f % 75 == 0:
            self.want_pressed.add("jump")
        elif b == "Parry Loop" and f % 60 == 0:
            self.want_pressed.add("parry")
        if b == "Parry on Attack":
            threat = any(o.current_attack is not None and abs(o.x - self.x) < 150 and abs(o.y - self.y) < 110 for o in foes)
            self.react = self.react + 1 if threat else 0
            if self.react == DUMMY_REACTION:
                self.want_pressed.add("parry")
        else:
            self.react = 0

    def held(self, action):
        return action in self.want_held

    def pressed(self, action):
        return action in self.want_pressed

#==========================================================
# CHARACTER: VEN- special moves (multi-stage, so they get their own classes)
#==========================================================
class BlastBouncer(Move):
    """Shoot Downward, and Launch yourself upward"""
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.state, self.timer = "startup", 20
        self.fall_frames = 0
        self.rise = self.add_hitbox(Hitbox(owner, 70, 150, (0, 75), damage=7, kbx=5, kby=25, angle=-90, stun=20))
        Sound.play("BlastBouncePrepare")

    def update(self, targets):
        o = self.owner
        self.timer -= 1
        for hb in self.hitboxes:
            hb.place(o.x, o.y, self.facing)

        if self.state == "startup":
            self.owner.y_velocity = 0
            self.owner.x_velocity = 0
            if self.timer <= 0:
                self.state, self.timer = "rise", 7
                o.NoGravTimer = 12
                o.y_velocity = -9
                o.x_velocity = 5 * self.facing
                self.rise.set_active(True)
                Sound.play("BlastBounceFire")

        elif self.state == "rise":
            self.rise.check(targets, self.facing)
            if self.timer <= 0:
                self.state = "recovery"
                self.rise.set_active(False)
                o.x_velocity = 3 * self.facing
                self.owner.special_ammo -= 1

        elif self.state == "recovery":
            if self.timer <= 0:
                self.end()

class GroundSlam(Move):
    """Slam straight down. The moment you land, a jab-shaped hit (the same box as Rend's down light) goes off on BOTH sides."""
    def __init__(self, owner):
        super().__init__(owner)
        self.state, self.timer = "slam", 0
        self.fall_frames = 0
        owner.x_velocity = 0
        self.right = self.add_hitbox(Hitbox(owner, 40, 50, (25, -5), damage=7, kbx=10, kby=10, angle=80, stun=14))
        self.left = self.add_hitbox(Hitbox(owner, 40, 50, (-25, -5), damage=7, kbx=10, kby=10, angle=80, stun=14))
        self.left.already_hit = self.right.already_hit        # the same set, so someone standing in the middle is only hit once

    def update(self, targets):
        o = self.owner
        if self.state == "slam":
            self.fall_frames += 1
            o.y_velocity = 16
            if o.coyote_time == COYOTE_TIME or self.fall_frames > 120:   # landed (or safety timeout)
                self.state, self.timer = "startup", 5
            return

        self.timer -= 1
        if self.state == "startup" and self.timer <= 0:
            self.state, self.timer = "active", 4
            self.right.set_active(True)
            self.left.set_active(True)
        elif self.state == "active" and self.timer <= 0:
            self.state, self.timer = "recovery", 10
            self.right.set_active(False)
            self.left.set_active(False)
        elif self.state == "recovery" and self.timer <= 0:
            self.end()
            return

        self.right.place(o.x, o.y, 1)          # facing 1 for both: the offsets already put them on opposite sides...
        self.left.place(o.x, o.y, 1)
        self.right.check(targets, 1)           # ...and this makes each one knock its victims AWAY from Ven
        self.left.check(targets, -1)

#==========================================================
# CHARACTER: VEN
#==========================================================

class Ven(Player):

    title = "Ven"
    blurb = "Gunslinger. Rifle shots and ammo-based specials."

    def __init__(self, currentLevel, name, x=None, y=None, size=100, spawnIcon="p", controls=None, pad=None, pad_controls=None, slot=None):
        super().__init__(currentLevel, name, x, y, size, spawnIcon, controls, pad, pad_controls, slot)
        self.special_ammo = 2

    MAX_AMMO = 2

    def make_hud(self, x, y):             # one small box per bullet
        colour = PLAYER_COLOURS[self.slot]
        self.hud_sprites = [Box(14, 28, colour, x - 15 + i * 30, y, border=2, border_colour="black", radius=3)
                            for i in range(self.MAX_AMMO)]

    def update_hud(self):                 # solid while he has the bullet, faded once it's spent
        for i, bullet in enumerate(self.hud_sprites):
            bullet.alpha = 255 if i < self.special_ammo else 40

    def handle_movement(self, currentLevel):
        grounded = self.coyote_time == COYOTE_TIME
        if grounded: self.special_ammo = 2
        return super().handle_movement(currentLevel)

    def reset_state(self):
        super().reset_state()
        self.stored_charge = 0

    def attackChecks(self, targets=()):
        if not self.actionable:
            return

        heavy = self.pressed("heavy")
        light = self.pressed("light")
        if not (heavy or light):
            return

        grounded = self.coyote_time == COYOTE_TIME
        down = self.held("down")
        side = self.held("left") or self.held("right")
        up = self.held("up")
        if heavy:
            if self.special_ammo > 0:                  # every heavy costs a bullet
                if down:
                    self.rifle_shot()
                elif up:
                    self.blast_bouncer()
                elif side:
                    self.back_blast()
                else:
                    self.triple_shot()
        else:
            if down:
                if grounded: self.Breaker()
                else:        self.ground_slam()
            elif up:
                self.Volley()
            elif side:
                self.Blast()
            else:
                # Neutral light: riposte if someone nearby was just parried, otherwise a normal attack
                if not self.try_riposte(targets):
                    self.Punch()

    #---------------- HEAVY ----------------

    def blast_bouncer(self):
        self.start_attack(BlastBouncer(self))

    def rifle_shot(self):
        self.start_attack(Attack(self, width=1000, height=10, offset=(500, -5), startup=14, active=4, recovery=10,damage=10, knockbackx=13, knockbacky=3, angle=10, stun=14))
        self.special_ammo -= 1

    def throw_stone(self):                # (no longer on any input, side + heavy is the back blast now. Kept in case you want it elsewhere)
        # Inverse knockback: victims are dragged TOWARDS Rend instead of away
        def fire(owner):
            stone = Hitbox(owner, 14, 14, (0, 0), damage=3, kbx=6, kby=4, angle=15, stun=8, mode="pull")
            Projectile(owner.x + 20 * owner.facing, owner.y, owner.facing, speed=12, lifetime=45, hitbox=stone)
        # active=0 means the move itself never hits, it only spawns the stone
        self.start_attack(Attack(self, 1, 1, (0, 0), startup=6, active=0, recovery=12,
                                 damage=0, knockbackx=0, knockbacky=0, angle=0, stun=0, on_fire=fire))

    def triple_shot(self):                # neutral + heavy: three bullets in a fan, one up, one straight, one down (15 degrees apart)
        def fire(owner):
            for fan in (15, 0, -15):
                bullet = Hitbox(owner, 12, 12, (0, 0), damage=4, kbx=7, kby=4, angle=15 + fan, stun=8)
                Projectile(owner.x + 22 * owner.facing, owner.y - 3, owner.facing, speed=14, lifetime=40, hitbox=bullet, angle=fan)
        self.start_attack(Attack(self, 1, 1, (0, 0), startup=10, active=0, recovery=16,
                                 damage=0, knockbackx=0, knockbacky=0, angle=0, stun=0, on_fire=fire))
        self.special_ammo -= 1

    def back_blast(self):                 # side + heavy: fire behind you and launch yourself the other way, fairly hard and fairly flat
        def launch(owner):
            owner.x_velocity = -11 * owner.facing
            owner.y_velocity = -3
            owner.NoGravTimer = 8                         # a few frames of no gravity keeps the launch sideways
            Particles.burst(owner.x, owner.y, count=10, colour=[(220, 220, 220), (255, 200, 80)],
                            direction=90 if owner.facing > 0 else 270, spread=40, speed=(4, 9),
                            life=(8, 16), size=(2, 4), gravity=0, drag=0.9)
        self.start_attack(Attack(self, 1, 1, (0, 0), startup=4, active=0, recovery=14,
                                 damage=0, knockbackx=0, knockbacky=0, angle=0, stun=0, on_fire=launch))
        self.special_ammo -= 1

    #---------------- LIGHT ----------------

    def ground_slam(self):                # down + light (in the air): slam down, then a hit on both sides when you land
        self.start_attack(GroundSlam(self))

    def Breaker(self):    # down + light (grounded): Close Range High Damage High Stun Attack
        self.start_attack(Attack(self, width=20, height=20, offset=(25, -5), startup=8, active=4, recovery=17,
                                 damage=20, knockbackx=2, knockbacky=6, angle=80, stun=40))

    def Blast(self):  # side + light: Simple Sideways Hit, Fairly Verical
        self.start_attack(Attack(self, width=45, height=60, offset=(30, 0), startup=3, active=4, recovery=8,
                                 damage=5, knockbackx=11, knockbacky=7, angle=5, stun=10))

    def Punch(self):   # neutral + light: Punch the enemy.
        self.start_attack(Attack(self, width=60, height=40, offset=(40, 0), startup=3, active=4, recovery=2,
                                 damage=3, knockbackx=9, knockbacky=9, angle=25, stun=10))

    def Volley(self):   # up + light: upward blast, launches heavily upward
        self.start_attack(Attack(self, width=70, height=65, offset=(0, -25), startup=4, active=4, recovery=9,
                                 damage=5, knockbackx=5, knockbacky=11, angle=90, stun=12))


#==========================================================
# CHARACTER: REND - special moves (multi-stage, so they get their own classes)
#==========================================================

class FrenzyDive(Move):
    """Frenzy Dive: rise with an upward hit, then slam straight down until you touch the floor.
    If the slam connects with a *person*, Rend is thrown back and up slightly while the victim is spiked."""
    def __init__(self, owner):
        super().__init__(owner)
        self.state, self.timer = "startup", 6
        self.fall_frames = 0
        self.rise = self.add_hitbox(Hitbox(owner, 60, 100, (10, -25), damage=4, kbx=9, kby=10, angle=80, stun=12))
        self.dive = self.add_hitbox(Hitbox(owner, 100, 50, (20, 25), damage=9, kbx=12, kby=25, angle=-75, stun=20))

    def update(self, targets):
        o = self.owner
        self.timer -= 1
        for hb in self.hitboxes:
            hb.place(o.x, o.y, self.facing)

        if self.state == "startup":
            if self.timer <= 0:
                self.state, self.timer = "rise", 12
                o.NoGravTimer = 12                      # clean, controlled ascent
                o.y_velocity = -17
                o.x_velocity = 5 * self.facing
                self.rise.set_active(True)

        elif self.state == "rise":
            self.rise.check(targets, self.facing)
            if self.timer <= 0:
                self.state = "slam"
                self.rise.set_active(False)
                self.dive.set_active(True)
                o.x_velocity = 3 * self.facing

        elif self.state == "slam":
            self.fall_frames += 1
            o.y_velocity = 30
            if self.dive.check(targets, self.facing):
                # Hit something that isn't the floor: bounce back and up, victim already got spiked
                o.x_velocity = -6 * self.facing
                o.y_velocity = -7
                o.NoGravTimer = 0
                self.end(recovery=10)
                return
            if o.coyote_time == COYOTE_TIME or self.fall_frames > 120:   # landed (or safety timeout)
                self.dive.set_active(False)
                self.state, self.timer = "recovery", 12

        elif self.state == "recovery":
            if self.timer <= 0:
                self.end()


class Pierce(Move):
    """Pierce: spike below and in front of the player. Hits things on the same level, mostly things a bit below.
    aerial=True slams the owner to the ground first, and the spike only starts once they land."""
    def __init__(self, owner, aerial=False):
        super().__init__(owner)
        self.fall_frames = 0
        if aerial:
            self.state, self.timer = "slam", 0
            owner.x_velocity = 0
        else:
            self.state, self.timer = "startup", 10
        self.hitbox = self.add_hitbox(Hitbox(owner, 100, 50, (35, 20), damage=10, kbx=10, kby=10, angle=60, stun=14))

    def update(self, targets):
        o = self.owner

        if self.state == "slam":
            self.fall_frames += 1
            o.y_velocity = 16
            if o.coyote_time == COYOTE_TIME or self.fall_frames > 120:   # landed (or safety timeout)
                self.state, self.timer = "startup", 6
            return

        self.timer -= 1
        if self.state == "startup" and self.timer <= 0:
            self.state, self.timer = "active", 4
            self.hitbox.set_active(True)
        elif self.state == "active" and self.timer <= 0:
            self.state, self.timer = "recovery", 16
            self.hitbox.set_active(False)
        elif self.state == "recovery" and self.timer <= 0:
            self.end()
            return

        self.hitbox.place(o.x, o.y, self.facing)
        self.hitbox.check(targets, self.facing)


class Consume(Move):
    """Consume: stand still and charge power (capped). Press heavy again to STORE the charge, or get hit and it's lost.
    Pressing neutral+heavy while a charge is stored (release=True) detonates it around Rend in every direction.
    The longer it was charged, the bigger, stronger and stunnier the burst."""
    MAX_CHARGE = 120               # frames (1.5 seconds at 60fps)

    def __init__(self, owner, release=False):
        super().__init__(owner)
        self.charge = 0
        self.hitbox = None
        if release:
            self.charge = owner.stored_charge
            owner.stored_charge = 0
            power = self.charge / self.MAX_CHARGE          # 0.0 -> 1.0
            size = int(80 + 160 * power)
            kb = 6 + 12 * power
            self.hitbox = self.add_hitbox(Hitbox(owner, size, size, (0, 0),
                                                 damage=4 + 12 * power, kbx=kb, kby=kb, angle=0,
                                                 stun=int(10 + 20 * power), mode="radial"))
            self.state, self.timer = "windup", 5
        else:
            self.state, self.timer = "charge", 0

    def update(self, targets):
        o = self.owner

        if self.state == "charge":
            # `self.charge > 0` skips the very frame the move began, which still has that same press in it
            if self.charge > 0 and o.pressed("heavy"):
                o.stored_charge = self.charge
                self.end(recovery=6)
                return
            self.charge = min(self.charge + 1, self.MAX_CHARGE)
            return

        self.timer -= 1
        if self.state == "windup" and self.timer <= 0:
            self.state, self.timer = "burst", 20
            self.hitbox.set_active(True)
        elif self.state == "burst" and self.timer <= 0:
            self.state, self.timer = "recovery", 14
            self.hitbox.set_active(False)
        elif self.state == "recovery" and self.timer <= 0:
            self.end()
            return

        self.hitbox.place(o.x, o.y, self.facing)
        self.hitbox.check(targets, self.facing)

#==========================================================
# CHARACTER: REND
#==========================================================

class Rend(Player):

    title = "Rend"
    blurb = "Cursed Swordsman"

    def __init__(self, currentLevel, name, x=None, y=None, size=100, spawnIcon="p", controls=None, pad=None, pad_controls=None, slot=None):
        super().__init__(currentLevel, name, x, y, size, spawnIcon, controls, pad, pad_controls, slot)
        self.stored_charge = 0        # Consume charge waiting to be released (in frames)

    BAR_WIDTH = 100

    def make_hud(self, x, y):             # a bar showing the charge Consume has stored
        self.bar_left = x - self.BAR_WIDTH / 2
        back = Box(self.BAR_WIDTH, 10, "black", x, y, alpha=120, border=2, border_colour="black")
        self.fill = Box(1, 10, PLAYER_COLOURS[self.slot], self.bar_left, y)      # made after `back`, so it draws on top
        self.hud_sprites = [back, self.fill]

    def update_hud(self):
        move = self.current_attack
        charging = isinstance(move, Consume) and move.state == "charge"
        charge = move.charge if charging else self.stored_charge      # live while charging, then the stored amount once it's locked in
        self.fill.alpha = 140 if charging else 255                     # slightly see-through until it's stored
        width = max(1, self.BAR_WIDTH * charge / Consume.MAX_CHARGE)
        self.fill.width = width
        self.fill.x = self.bar_left + width / 2       # sprites sit by their centre, so slide it to keep the left edge still

    def reset_state(self):
        super().reset_state()
        self.stored_charge = 0

    def attackChecks(self, targets=()):
        if not self.actionable:
            return

        heavy = self.pressed("heavy")
        light = self.pressed("light")
        if not (heavy or light):
            return

        grounded = self.coyote_time == COYOTE_TIME
        down = self.held("down")
        side = self.held("left") or self.held("right")
        up = self.held("up")

        if heavy:
            if down:
                self.pierce(aerial=not grounded)
            elif up:
                self.frenzy_dive()
            elif side:
                self.throw_stone()
            else:
                self.consume()
        else:
            if down:
                if grounded: self.jab()
                else:        self.pogo()
            elif up:
                self.poke()
            elif side:
                self.slash()
            else:
                # Neutral light: riposte if someone nearby was just parried, otherwise a normal stab
                if not self.try_riposte(targets):
                    self.stab()

    #---------------- HEAVY ----------------

    def frenzy_dive(self):
        self.start_attack(FrenzyDive(self))

    def pierce(self, aerial=False):
        self.start_attack(Pierce(self, aerial))

    def consume(self):
        # Charge stored? release it. Otherwise start charging.
        self.start_attack(Consume(self, release=self.stored_charge > 0))

    def throw_stone(self):
        # Inverse knockback: victims are dragged TOWARDS Rend instead of away
        def fire(owner):
            stone = Hitbox(owner, 14, 14, (0, 0), damage=3, kbx=6, kby=4, angle=15, stun=8, mode="pull")
            Projectile(owner.x + 20 * owner.facing, owner.y, owner.facing, speed=12, lifetime=45, hitbox=stone)
        # active=0 means the move itself never hits, it only spawns the stone
        self.start_attack(Attack(self, 1, 1, (0, 0), startup=6, active=0, recovery=12,
                                 damage=0, knockbackx=0, knockbacky=0, angle=0, stun=0, on_fire=fire))

    #---------------- LIGHT ----------------

    def jab(self):    # down + light (grounded): slow-ish, close range, launches almost straight up
        self.start_attack(Attack(self, width=40, height=50, offset=(25, -5), startup=8, active=4, recovery=10,
                                 damage=7, knockbackx=10, knockbacky=10, angle=80, stun=14))

    def slash(self):  # side + light: simple sideways hit, slightly up
        self.start_attack(Attack(self, width=60, height=40, offset=(40, 0), startup=3, active=4, recovery=8,
                                 damage=5, knockbackx=11, knockbacky=7, angle=25, stun=10))

    def stab(self):   # neutral + light: slash, but angled further up and +1 damage
        self.start_attack(Attack(self, width=60, height=40, offset=(40, 0), startup=3, active=4, recovery=2,
                                 damage=6, knockbackx=9, knockbacky=9, angle=55, stun=10))

    def poke(self):   # up + light: upward slash, launches upward
        self.start_attack(Attack(self, width=45, height=70, offset=(15, -35), startup=4, active=4, recovery=9,
                                 damage=5, knockbackx=11, knockbacky=11, angle=90, stun=12))

    def pogo(self):   # down + light (aerial): downward slash that bounces Rend upward if it hits someone
        def bounce(owner):
            owner.y_velocity = -10
        self.start_attack(Attack(self, width=40, height=45, offset=(0, 28), startup=3, active=10, recovery=8,
                                 damage=4, knockbackx=6, knockbacky=6, angle=-80, stun=10, on_connect=bounce))
#==========================================================
# CHARACTER: CLEANING LADY - special moves (multi-stage, so they get their own classes)
#==========================================================

class Lunge(Move):
    """Mop Lunge: hang in place, dash a short way with a high-stun hit, then a LONG recovery where you just fall.
    Works on the ground too, but it's at its most dangerous (and most punishable) in the air."""
    def __init__(self, owner):
        super().__init__(owner)
        self.state, self.timer = "startup", 14
        self.hitbox = self.add_hitbox(Hitbox(owner, 50, 44, (24, 0), damage=7, kbx=5, kby=4, angle=15, stun=50))

    def update(self, targets):
        o = self.owner
        self.timer -= 1

        if self.state == "startup":                       # stall: no gravity, no speed
            o.x_velocity = 0
            o.y_velocity = 0
            o.NoGravTimer = 2
            if self.timer <= 0:
                self.state, self.timer = "dash", 30
                self.hitbox.set_active(True)

        elif self.state == "dash":                        # short, flat, fast
            o.x_velocity = 13 * self.facing
            o.y_velocity = 0
            o.NoGravTimer = 2
            if self.timer <= 0:
                self.state, self.timer = "recovery", 20
                self.hitbox.set_active(False)
                o.x_velocity = 3 * self.facing

        elif self.state == "recovery":                    # gravity is back, and so is nothing else
            if self.timer <= 0:
                self.end()
                return

        self.hitbox.place(o.x, o.y, self.facing)
        self.hitbox.check(targets, self.facing)


class PoleGrapple(Move):
    """Throw a pole straight up. If it hits someone, you are pulled swiftly to where they are."""
    def __init__(self, owner):
        super().__init__(owner)
        self.state, self.timer = "startup", 8
        self.target = None
        self.projectile = None

    def _connected(self, target):
        self.target = target

    def update(self, targets):
        o = self.owner

        if self.state == "startup":
            self.timer -= 1
            if self.timer <= 0:
                pole = Hitbox(o, 40, 70, (0, 0), damage=5, kbx=1, kby=3, angle=90, stun=24)
                pole.on_hit = self._connected
                self.projectile = Projectile(o.x + 8 * self.facing, o.y - 45, self.facing, speed=30, lifetime=16, hitbox=pole, angle=90)
                self.state = "flight"

        elif self.state == "flight":
            if self.target is not None:
                self.state, self.timer = "pull", 22
            elif self.projectile not in projectiles:      # it flew off without hitting anyone
                self.state, self.timer = "recovery", 18

        elif self.state == "pull":
            self.timer -= 1
            dx, dy = self.target.x - o.x, self.target.y - o.y
            dist = math.hypot(dx, dy) or 1
            if dist < 8 or self.timer <= 0:
                o.x = self.target.x
                o.y = self.target.y
                o.x_velocity *= 0.3
                o.y_velocity = 0
                self.state, self.timer = "recovery", 10
            else:
                o.x_velocity = dx / dist * 16
                o.y_velocity = dy / dist * 16
                o.NoGravTimer = 2

        elif self.state == "recovery":
            self.timer -= 1
            if self.timer <= 0:
                self.end()


#==========================================================
# CHARACTER: CLEANING LADY
#==========================================================

class CleaningLady(Player):

    title = "Cleaning Lady"
    blurb = "Long poles, a squirt bottle, and a trash bag that fills as she fights."

    TRASH_MAX = 100              # how much trash fills the bag
    TRASH_PER_DAMAGE = 3      # every point of damage she deals adds this much trash (so a full bag takes a while)
    BAR_WIDTH = 100

    def __init__(self, currentLevel, name, x=None, y=None, size=100, spawnIcon="p", controls=None, pad=None, pad_controls=None, slot=None):
        super().__init__(currentLevel, name, x, y, size, spawnIcon, controls, pad, pad_controls, slot)
        self.trash = 0
        self.no_trash_timer = 0      # frames after emptying the bag where hits don't fill it straight back up
        self.deny_timer = 0          # flashes the bar when you try to empty a bag that isn't full
        self.hud_tick = 0

    #---------------- passive: the trash bag ----------------

    def on_dealt_hit(self, damage, target):
        if self.no_trash_timer == 0:
            self.trash = min(self.TRASH_MAX, self.trash + damage * self.TRASH_PER_DAMAGE)

    def handle_movement(self, currentLevel):
        if self.no_trash_timer > 0: self.no_trash_timer -= 1
        if self.deny_timer > 0: self.deny_timer -= 1
        return super().handle_movement(currentLevel)

    def reset_state(self):
        super().reset_state()
        self.trash = 0

    def make_hud(self, x, y):
        self.bar_left = x - self.BAR_WIDTH / 2
        back = Box(self.BAR_WIDTH, 10, "black", x, y, alpha=120, border=2, border_colour="black")
        self.fill = Box(1, 10, (140, 105, 60), self.bar_left, y)
        self.label = Text("TRASH BAG", x, y - 17, 16, PLAYER_COLOURS[self.slot], outline=2)
        self.hud_sprites = [back, self.fill, self.label]

    def update_hud(self):
        self.hud_tick += 1
        full = self.trash >= self.TRASH_MAX
        width = max(1, self.BAR_WIDTH * self.trash / self.TRASH_MAX)
        self.fill.width = width
        self.fill.x = self.bar_left + width / 2
        if self.deny_timer > 0:
            self.fill.colour, self.fill.alpha = (230, 60, 60), 255          # red flash: "not full yet!"
        elif full:
            self.fill.colour = (255, 210, 70)                                # gold, and pulsing
            self.fill.alpha = 255 if (self.hud_tick // 8) % 2 else 150
        else:
            self.fill.colour, self.fill.alpha = (140, 105, 60), 255
        self.label.text = "FULL!  DOWN + HEAVY" if full else "TRASH BAG"

    #---------------- input ----------------

    def attackChecks(self, targets=()):
        if not self.actionable:
            return

        heavy = self.pressed("heavy")
        light = self.pressed("light")
        if not (heavy or light):
            return

        grounded = self.coyote_time == COYOTE_TIME
        down = self.held("down")
        side = self.held("left") or self.held("right")
        up = self.held("up")

        if heavy:
            if down:
                self.trash_bag()
            elif up:
                self.pole_grapple()
            elif side:
                self.lunge()
            else:
                self.squirt()
        else:
            if down:
                if grounded: self.soap()
                else:        self.stick_down()
            elif up:
                self.pole_up()
            elif side:
                self.pole_side()
            else:
                # Neutral light: riposte if someone nearby was just parried, otherwise the dashing sweep
                if not self.try_riposte(targets):
                    self.sweep_dash()

    #---------------- sprays (shared by the squirt bottle and the trash bag) ----------------

    def spray(self, owner, angles, speed, lifetime, gravity, damage, kbx, kby, stun):
        """One little projectile per angle. speed is a (min, max) pair so no two droplets are quite the same."""
        for fan in angles:
            drop = Hitbox(owner, 10, 10, (0, 0), damage=damage, kbx=kbx, kby=kby, angle=30, stun=stun)
            Projectile(owner.x + 18 * owner.facing, owner.y - 2, owner.facing,
                       speed=speed[0] + sim_rng.random() * (speed[1] - speed[0]), lifetime=lifetime,
                       hitbox=drop, angle=fan, gravity=gravity)

    #---------------- HEAVY ----------------

    def squirt(self):         # neutral + heavy: 7 small droplets, short range, they fall almost straight down
        def fire(owner):
            self.spray(owner, angles=[24, 16, 8, 0, -8, -16, -24], speed=(5, 7), lifetime=20, gravity=0.3,
                       damage=2, kbx=3, kby=4, stun=6)
        self.start_attack(Attack(self, 1, 1, (0, 0), startup=8, active=0, recovery=22,
                                 damage=0, knockbackx=0, knockbacky=0, angle=0, stun=0, on_fire=fire))

    def lunge(self):          # side + heavy: the mop lunge (see Lunge)
        self.start_attack(Lunge(self))

    def pole_grapple(self):   # up + heavy: throw a pole upward, get pulled to whoever it hits
        self.start_attack(PoleGrapple(self))

    def trash_bag(self):      # down + heavy: only works with a FULL bag. A much bigger squirt: 10 droplets, further, much harder
        if self.trash < self.TRASH_MAX:
            self.deny_timer = 20
            return
        def fire(owner):
            owner.trash = 0
            owner.no_trash_timer = 60                    # so the burst's own hits don't instantly refill the bag
            self.spray(owner, angles=[-20 + i * 70 / 9 for i in range(10)], speed=(9, 12), lifetime=40, gravity=0.12,
                       damage=20, kbx=17, kby=8, stun=14)
        self.start_attack(Attack(self, 1, 1, (0, 0), startup=14, active=0, recovery=30,
                                 damage=0, knockbackx=0, knockbacky=0, angle=0, stun=0, on_fire=fire))

    #---------------- LIGHT ----------------

    def pole_side(self):      # side + light: a long thin pole straight out
        self.start_attack(Attack(self, width=110, height=12, offset=(64, 0), startup=7, active=4, recovery=7,
                                 damage=6, knockbackx=10, knockbacky=6, angle=20, stun=12))

    def pole_up(self):        # up + light: a long thin pole directly above her (no sideways offset)
        self.start_attack(Attack(self, width=12, height=130, offset=(0, -68), startup=7, active=4, recovery=7,
                                 damage=6, knockbackx=4, knockbacky=12, angle=90, stun=12))

    def sweep_dash(self):     # neutral + light: step forward a little and swing a much shorter sweep
        self.start_attack(Attack(self, width=34, height=34, offset=(26, 0), startup=4, active=4, recovery=8,
                                 damage=4, knockbackx=8, knockbacky=7, angle=35, stun=9))
        self.x_velocity = 6 * self.facing

    def soap(self):           # down + light (grounded): throw soap, very fast but weak
        def fire(owner):
            bar = Hitbox(owner, 12, 12, (0, 0), damage=2, kbx=3, kby=3, angle=20, stun=6)
            Projectile(owner.x + 18 * owner.facing, owner.y, owner.facing, speed=22, lifetime=28, hitbox=bar)
        self.start_attack(Attack(self, 1, 1, (0, 0), startup=8, active=0, recovery=14,
                                 damage=0, knockbackx=0, knockbacky=0, angle=0, stun=0, on_fire=fire))

    def stick_down(self):     # down + light (in the air): a stick thrust straight down
        self.start_attack(Attack(self, width=12, height=90, offset=(0, 57), startup=7, active=6, recovery=12,
                                 damage=6, knockbackx=3, knockbacky=10, angle=-75, stun=12))

#==========================================================
# CHARACTER: CAP'N REX - the barrel, its effects, and special moves
#==========================================================

BARREL_RESPAWN_SECONDS = 5        # how long the barrel takes to fall back in after it leaves the stage


class _NoReflect:
    """Goes in a hitbox's `projectile` slot when a parry should NOT reflect or stun anything (shockwaves)."""
    def reflect(self, parrier):
        pass


class Shockwave:
    """Two flat hitboxes on the ground, one each side of a point. Everything it hits is thrown outwards AND upwards."""
    def __init__(self, owner, x, y, big):
        self.x, self.y = x, y
        if big:
            w, h, damage, kbx, kby, stun, self.life = 170, 56, 14, 13, 15, 24, 8
        else:
            w, h, damage, kbx, kby, stun, self.life = 70, 36, 5, 7, 8, 12, 6
        off_y = 15 - h / 2                                    # sits on the floor, level with the bottom of the barrel
        self.right = Hitbox(owner, w, h, (w / 2 - 10, off_y), damage=damage, kbx=kbx, kby=kby, angle=65, stun=stun)
        self.left = Hitbox(owner, w, h, (-(w / 2 - 10), off_y), damage=damage, kbx=kbx, kby=kby, angle=65, stun=stun)
        self.left.already_hit = self.right.already_hit        # someone standing in the middle is only hit once
        for hb in (self.right, self.left):
            hb.projectile = _NoReflect()
            hb.set_active(True)
        self.done = False
        Particles.burst(x, y + 15, count=28 if big else 10, colour=[(210, 200, 180), (160, 150, 130)], direction=0, spread=150,
                        speed=(2, 7 if big else 4), life=(10, 22), size=(2, 4), gravity=0.2)

    def update(self, targets):
        self.right.place(self.x, self.y, 1)
        self.left.place(self.x, self.y, 1)
        self.right.check(targets, 1)          # facing 1 / -1: each side knocks its victims AWAY from the middle
        self.left.check(targets, -1)
        self.life -= 1
        if self.life <= 0:
            self.delete()

    def delete(self):
        self.right.delete()
        self.left.delete()
        self.done = True


class Barrel:
    """Rex's barrel. Nobody but Rex can touch it: enemy attacks only ever look at players, so they pass straight through.
    mode:  idle | jump | thrown | hop | slam | ship"""
    W, H = 26, 30
    GRAVITY = 0.4

    def __init__(self, owner, x, y):
        self.owner = owner
        self.spawn = (x, y)
        colour = PLAYER_COLOURS[(owner.slot or 0) % len(PLAYER_COLOURS)]          # matches its player's colour
        self.box = Box(self.W, self.H, colour, x, y, border=3, border_colour="black", radius=5, fixed=False)
        self.vx = self.vy = 0
        self.dir = 1
        self.mode = "idle"
        self.grounded = False
        self.held = False
        self.jump_locked = False         # jumped while being carried: can't jump again until it has been thrown
        self.up_locked = False           # caught it with the up special: can't up-special again until it has been thrown
        self.slam_big = False
        self.respawn_timer = 0
        self.timer_text = None
        self.waves = []
        # contact damage while it's flying around. projectile=self means a parry bounces the barrel back instead of stunning Rex
        self.hit_jump = Hitbox(owner, 30, 34, (0, 0), damage=1, kbx=2, kby=3, angle=80, stun=4)
        self.hit_throw = Hitbox(owner, 32, 36, (0, 0), damage=8, kbx=9, kby=7, angle=30, stun=14)
        self.hit_throw.on_hit = self._throw_connected
        for hb in (self.hit_jump, self.hit_throw):
            hb.projectile = self

    #---------------- asking about it ----------------

    def rect(self):
        return self.box._hitbox_rect()

    def can_grab(self):
        return not self.held and self.respawn_timer == 0 and self.mode in ("idle", "jump", "thrown")

    def can_jump(self):
        return not self.held and self.respawn_timer == 0 and self.mode == "idle" and self.grounded

    #---------------- things Rex can make it do ----------------

    def grab(self):
        self.held = True
        self.mode = "idle"
        self.vx = self.vy = 0

    def release(self, vx=0, vy=0, mode="idle", direction=None):
        self.held = False
        self.jump_locked = False         # leaving Rex's hands (thrown, dropped, slammed...) unlocks its jump...
        self.up_locked = False           # ...and his up special
        self.vx, self.vy, self.mode = vx, vy, mode
        if direction is not None:
            self.dir = direction

    def drop(self):
        if self.held:
            self.release()

    def throw(self, direction):
        o = self.owner
        self.box.go_to(o.x + 18 * direction, o.y - 8)
        self.release(13 * direction, -5, "thrown", direction)

    def jump(self):
        self.vy = -12
        self.mode = "jump"
        self.grounded = False

    def slam(self):
        """Airborne: plunge straight down, small shockwave. On the ground: hop up first, then a BIG shockwave."""
        if self.held or self.respawn_timer > 0 or self.mode in ("hop", "slam", "ship"):
            return False
        if self.grounded:
            self.mode, self.vy, self.slam_big = "hop", -9, True
            self.grounded = False
        else:
            self.mode, self.slam_big = "slam", False
        self.vx = 0
        return True

    def make_wave(self, big):
        self.waves.append(Shockwave(self.owner, self.box.x, self.box.y, big))

    def reflect(self, parrier):                   # its hit was parried: it just bounces back, harmless
        self.dir = -self.dir
        self.vx, self.vy, self.mode = 6 * self.dir, -6, "idle"

    def _throw_connected(self, target):           # a thrown barrel stops dead when it hits someone
        self.vx *= 0.2
        self.mode = "idle"

    #---------------- every frame ----------------

    def update(self, targets):
        o = self.owner
        for wave in self.waves[:]:
            wave.update(targets)
            if wave.done:
                self.waves.remove(wave)

        if self.respawn_timer > 0:
            self._tick_respawn()
            return
        if self.mode == "ship":                   # the Ship moves it around (but if that drags it fully into the ground, it's destroyed)
            if self._buried():
                self._fell_off(destroyed=True)
            return
        if self.held:
            self.box.go_to(o.x, o.y - 30)
            self.vx = self.vy = 0
            self.grounded = False
            self.hit_jump.set_active(False)
            self.hit_throw.set_active(False)
            return

        self._physics()
        self.hit_jump.set_active(self.mode == "jump")
        self.hit_throw.set_active(self.mode == "thrown")
        for hb in (self.hit_jump, self.hit_throw):
            hb.place(self.box.x, self.box.y, 1)
        self.hit_jump.check(targets, 1)
        self.hit_throw.check(targets, self.dir)

        if self._buried():
            self._fell_off(destroyed=True)
        elif level.touching(self.box, "Z"):
            self._fell_off()

    def _physics(self):
        b = self.box
        old_x, old_y = b.x, b.y

        if self.mode == "slam":
            self.vy = 22
        else:
            self.vy = min(self.vy + self.GRAVITY, 20)
        if self.mode == "hop" and self.vy >= 0:   # reached the top of the hop: now slam it down
            self.mode = "slam"

        b.x += self.vx
        if level.touching(b):
            b.x = old_x
            self.vx = -self.vx * 0.3
        b.y += self.vy
        landed = False
        if level.touching(b):
            b.y = old_y
            landed = self.vy > 0
            self.vy = 0
            self.grounded = landed
        else:
            self.grounded = False

        friction = 0.9 if self.grounded else 0.05
        if self.vx > 0:
            self.vx = max(0, self.vx - friction)
        elif self.vx < 0:
            self.vx = min(0, self.vx + friction)

        if landed:
            if self.mode == "slam":
                self.make_wave(self.slam_big)
            if self.mode in ("jump", "thrown", "slam", "hop"):
                self.mode = "idle"

    def _buried(self):
        """True if the barrel is completely inside solid terrain (it can't get out of there by itself)."""
        r = self.rect()
        points = [(r.left + 2, r.top + 2), (r.right - 2, r.top + 2), (r.left + 2, r.bottom - 2), (r.right - 2, r.bottom - 2), r.center]
        return all(level.is_solid(x, y) for x, y in points)

    def _fell_off(self, destroyed=False):
        if destroyed:                                  # a little puff of splinters where it was
            Particles.burst(self.box.x, self.box.y, count=14, colour=[(120, 80, 45), (200, 160, 100)],
                            speed=(2, 6), life=(12, 25), size=(2, 4), gravity=0.2)
        self.respawn_timer = BARREL_RESPAWN_SECONDS * Screen.fps
        self.box.visible = False
        self.vx = self.vy = 0
        self.mode = "idle"
        self.grounded = False
        colour = PLAYER_COLOURS[(self.owner.slot or 0) % len(PLAYER_COLOURS)]
        self.timer_text = Text("", 0, 36, 40, colour, outline=3)

    def _tick_respawn(self):
        self.respawn_timer -= 1
        if self.timer_text is None:
            self.timer_text = Text("", 0, 36, 40, PLAYER_COLOURS[(self.owner.slot or 0) % len(PLAYER_COLOURS)], outline=3)
        screen_x = self.spawn[0] - Stage.camera.x + Screen.width / 2          # where on screen it will drop in
        self.timer_text.go_to(max(60, min(Screen.width - 60, screen_x)), 36)
        self.timer_text.text = f"BARREL  {self.respawn_timer / Screen.fps:.1f}"
        if self.respawn_timer <= 0:
            self.timer_text.delete()
            self.timer_text = None
            self.box.go_to(self.spawn[0], max(48, Stage.camera.y - Screen.height / 2 + 10))     # from the top of the screen
            self.box.visible = True
            self.vx = self.vy = 0
            self.mode = "idle"

    def delete(self):
        self.box.delete()
        self.hit_jump.delete()
        self.hit_throw.delete()
        for wave in self.waves:
            wave.delete()
        if self.timer_text is not None:
            self.timer_text.delete()


class Ship:
    """A big projectile that sails across the whole screen at the height Rex launched it from. It can carry the barrel."""
    SPEED = 13

    def __init__(self, owner, y, direction, barrel=None):
        left = Stage.camera.x - Screen.width / 2
        right = Stage.camera.x + Screen.width / 2
        start = left - 120 if direction > 0 else right + 120
        distance = Screen.width + 240
        hull = Hitbox(owner, 170, 64, (0, 0), damage=10, kbx=17, kby=6, angle=20, stun=22)
        self.projectile = Projectile(start, y, direction, speed=self.SPEED, lifetime=int(distance / self.SPEED) + 2,
                                     hitbox=hull, pierce=True, ignore_tiles=True)
        self.vis = Box(170, 56, (120, 80, 45), start, y, border=4,
                       border_colour=PLAYER_COLOURS[(owner.slot or 0) % len(PLAYER_COLOURS)], radius=10, fixed=False)
        self.barrel = barrel
        self.done = False

    def _unload(self, p):
        b = self.barrel
        self.barrel = None
        b.release(3 * p.facing, -4, "thrown", p.facing)       # hops off the ship, carrying a little of its momentum

    def update(self, targets):
        p = self.projectile
        if self.barrel is not None and self.barrel.respawn_timer > 0:      # it was destroyed on the way: nothing left to carry
            self.barrel = None
        if p not in projectiles:                              # sailed off the end of the screen
            if self.barrel is not None:
                self._unload(p)
            self.vis.delete()
            self.done = True
            return
        lead = p.speed * p.facing                              # ships update before projectiles do, so draw it one step ahead to stay lined up
        self.vis.go_to(p.x + lead, p.y)
        if self.barrel is not None:
            self.barrel.box.go_to(p.x + lead, p.y - 45)
            if (p.x - Stage.camera.x) * p.facing >= 0:        # reached the middle of the screen: the barrel gets off
                self._unload(p)

    def delete(self):
        self.vis.delete()


class RexLunge(Move):
    """A small lunge with a weak jab. If the barrel is within reach the lunge stops and Rex picks it up."""
    STARTUP, LUNGE, RECOVERY = 3, 8, 6

    def __init__(self, owner):
        super().__init__(owner)
        self.frame = 0
        self.picked = False
        self.hitbox = self.add_hitbox(Hitbox(owner, 30, 30, (22, 0), damage=4, kbx=7, kby=6, angle=35, stun=9))

    def update(self, targets):
        o, b, f = self.owner, self.owner.barrel, self.frame
        self.frame += 1
        self.hitbox.place(o.x, o.y, self.facing)

        if not self.picked and b.can_grab():
            reach = o._hitbox_rect().inflate(18, 8).union(self.hitbox.zone._rect())
            if b.rect().colliderect(reach):
                b.grab()
                self.picked = True
                o.x_velocity = 0
                self.frame = max(self.frame, self.STARTUP + self.LUNGE)      # skip the rest of the lunge, keep the recovery

        if not self.picked and self.STARTUP <= f < self.STARTUP + self.LUNGE:
            self.hitbox.set_active(True)
            o.x_velocity = 7 * self.facing
            self.hitbox.check(targets, self.facing)
        else:
            self.hitbox.set_active(False)

        if self.frame >= self.STARTUP + self.LUNGE + self.RECOVERY:
            self.end()


class Tentacles(Move):
    """Three tentacles burst up in front of Rex one after another. Long recovery, spikes UP very hard."""
    START, STAGGER, ACTIVE, TOTAL = 10, 4, 10, 60

    def __init__(self, owner):
        super().__init__(owner)
        self.frame = 0
        self.tents = [self.add_hitbox(Hitbox(owner, 18, 20, (34 + 30 * i, 0), damage=7, kbx=2, kby=14, angle=88, stun=24))
                      for i in range(3)]

    def update(self, targets):
        o = self.owner
        for i, tent in enumerate(self.tents):
            age = self.frame - (self.START + i * self.STAGGER)
            if 0 <= age < self.ACTIVE:
                tent.set_active(True)
                height = min(90, 30 + 20 * age)                   # it grows up out of the floor
                tent.zone.height = height
                tent.offset = (tent.offset[0], 12 - height / 2)
            else:
                tent.set_active(False)
            tent.place(o.x, o.y, self.facing)
            tent.check(targets, self.facing)
        self.frame += 1
        if self.frame >= self.TOTAL:
            self.end()


class BarrelDash(Move):
    """Dash hard at the barrel. If Rex is carrying it he throws it straight up first, waits a moment, THEN dashes to it and
    catches it again. Having done that, he can't up-special again until he has thrown the barrel."""
    def __init__(self, owner, throw_first):
        super().__init__(owner)
        self.catch = throw_first         # carrying it = it gets caught again at the end (and the up special is used up until it's thrown)
        self.state, self.timer = ("throw", 6) if throw_first else ("dash", 30)

    def update(self, targets):
        o, b = self.owner, self.owner.barrel
        self.timer -= 1

        if self.state == "throw":
            o.x_velocity = 0
            o.y_velocity = 0
            if self.timer <= 0:
                b.release(0, -17, "idle")
                self.state, self.timer = "wait", 18

        elif self.state == "wait":
            o.x_velocity = 0
            o.y_velocity = 0
            if self.timer <= 0:
                self.state, self.timer = "dash", 30

        elif self.state == "dash":
            dx, dy = b.box.x - o.x, b.box.y - o.y
            dist = math.hypot(dx, dy) or 1
            if dist < 24 or self.timer <= 0 or b.respawn_timer > 0:
                o.x_velocity *= 0.3
                o.y_velocity = 0
                if self.catch and dist < 40 and b.can_grab():     # made it: catch the barrel
                    b.grab()
                    b.up_locked = True
                self.state, self.timer = "recovery", 8
            else:
                o.x_velocity = dx / dist * 18
                o.y_velocity = dy / dist * 18
                o.NoGravTimer = 2

        elif self.state == "recovery":
            if self.timer <= 0:
                self.end()


class BarrelSlamHeld(Move):
    """Slam to the ground WITH the barrel. A big shockwave goes off where you land and the barrel is left there."""
    def __init__(self, owner):
        super().__init__(owner)
        self.fall_frames = 0
        self.timer = 0
        if owner.coyote_time == COYOTE_TIME:                # on the ground: hop up first, same as the barrel does
            self.state = "hop"
            owner.y_velocity = -9
        else:
            self.state = "slam"

    def update(self, targets):
        o, b = self.owner, self.owner.barrel
        if self.state == "hop":
            self.fall_frames += 1
            if o.y_velocity >= 0 or self.fall_frames > 30:
                self.state, self.fall_frames = "slam", 0
        elif self.state == "slam":
            self.fall_frames += 1
            o.x_velocity = 0
            o.y_velocity = 18
            if o.coyote_time == COYOTE_TIME or self.fall_frames > 120:
                b.release()
                b.box.go_to(o.x, o.y - 3)
                b.make_wave(True)
                self.state, self.timer = "recovery", 14
        elif self.state == "recovery":
            self.timer -= 1
            if self.timer <= 0:
                self.end()


#==========================================================
# CHARACTER: CAP'N REX
#==========================================================

class CaptnRex(Player):

    title = "Cap'n Rex"
    blurb = "Cutlass, tentacles, and a trusty barrel he throws, rides and slams."

    def __init__(self, currentLevel, name, x=None, y=None, size=100, spawnIcon="p", controls=None, pad=None, pad_controls=None, slot=None):
        super().__init__(currentLevel, name, x, y, size, spawnIcon, controls, pad, pad_controls, slot)
        spots = currentLevel.find("b")                       # the barrel starts where the stage has a "b"
        bx, by = spots[0] if spots else (self.x, self.y)
        self.barrel = Barrel(self, bx, by)
        self.effects = []                                    # ships in the air

    #---------------- passive: the barrel ----------------

    def update_attack(self, targets):
        super().update_attack(targets)
        self.barrel.update(targets)
        for effect in self.effects[:]:
            effect.update(targets)
            if effect.done:
                self.effects.remove(effect)

    def on_hit(self):
        super().on_hit()
        self.barrel.drop()                                   # knocked out of his hands

    def reset_state(self):
        super().reset_state()
        self.barrel.drop()

    def cleanup(self):
        self.barrel.delete()
        for effect in self.effects:
            effect.delete()
        self.effects = []

    def make_hud(self, x, y):
        self.hud_tick = 0                                    # counts frames, so the THROW warning can blink
        self.hud_icon = Box(16, 18, PLAYER_COLOURS[self.slot], x - 70, y, border=2, border_colour="black", radius=3)
        self.hud_label = Text("BARREL", x, y, 16, (255, 255, 255), outline=2)
        self.hud_sprites = [self.hud_icon, self.hud_label]

    def update_hud(self):
        b = self.barrel
        self.hud_tick += 1
        if b.respawn_timer > 0:
            text, colour = f"BARREL BACK IN {b.respawn_timer / Screen.fps:.1f}s", (255, 170, 60)
        elif b.held:
            jump_ready, up_ready = not b.jump_locked, not b.up_locked
            if jump_ready and up_ready:
                text, colour = "JUMP/UP", (110, 220, 130)                       # green: both
            elif jump_ready:
                text, colour = "JUMP", (255, 210, 70)                           # gold: only the jump
            elif up_ready:
                text, colour = "UP", (170, 90, 255)                             # purple: only the up special
            else:
                text = "THROW"                                                  # nothing left: blink red / dark red
                colour = (240, 60, 60) if (self.hud_tick // 8) % 2 else (120, 0, 0)
        else:
            text, colour = "BARREL", (255, 255, 255)
        self.hud_label.text, self.hud_label.colour = text, colour
        self.hud_icon.x = self.hud_label.x - self.hud_label.width / 2 - 14
        self.hud_icon.alpha = 70 if b.respawn_timer > 0 else 255

    #---------------- input ----------------

    def attackChecks(self, targets=()):
        if not self.actionable:
            return

        heavy = self.pressed("heavy")
        light = self.pressed("light")
        jumpward = (self.barrel.held and self.jump_charges == 0) and (self.jump_buffer == 4)
        if not (heavy or light or jumpward):
            return

        grounded = self.coyote_time == COYOTE_TIME
        down = self.held("down")
        side = self.held("left") or self.held("right")
        up = self.held("up")
        if jumpward:
            self.barrel_jump()
            return
        if heavy:
            if down:
                self.barrel_slam()
            elif up:
                self.barrel_dash()
            elif side:
                self.ship()
            else:
                self.barrel_jump()
        else:
            if down:
                if grounded: self.tentacles()
                else:        self.cutlass_down()
            elif up:
                self.cutlass_up()
            elif side:
                # Side light: a blade wave, unless he's carrying the barrel, then he throws it that way instead
                if self.barrel.held: self.throw_barrel()
                else:                self.blade_wave()
            else:
                # Neutral light: riposte if someone nearby was just parried. Otherwise throw the barrel if he has it, else lunge for it
                if not self.try_riposte(targets):
                    if self.barrel.held: self.throw_barrel()
                    else:                self.lunge_grab()

    #---------------- HEAVY (all about the barrel) ----------------

    def barrel_jump(self):    # neutral + heavy: the barrel jumps. Holding it? Rex jumps WITH it (once, until it's thrown)
        b = self.barrel
        if b.held:
            if b.jump_locked:
                return
            def fire(owner):
                owner.y_velocity = -13
                owner.NoGravTimer = 0
                b.jump_locked = True
        else:
            if not b.can_jump():
                return
            def fire(owner):
                b.jump()
        self.start_attack(Attack(self, 1, 1, (0, 0), startup=3, active=0, recovery=4,
                                 damage=0, knockbackx=0, knockbacky=0, angle=0, stun=0, on_fire=fire))

    def barrel_slam(self):    # down + heavy: slam the barrel (or slam WITH it). Shockwaves always launch upward
        b = self.barrel
        if b.held:
            self.start_attack(BarrelSlamHeld(self))
            return
        if b.respawn_timer > 0 or b.mode in ("hop", "slam", "ship"):
            return
        def fire(owner):
            b.slam()
        self.start_attack(Attack(self, 1, 1, (0, 0), startup=5, active=0, recovery=10,
                                 damage=0, knockbackx=0, knockbacky=0, angle=0, stun=0, on_fire=fire))

    def barrel_dash(self):    # up + heavy: dash to the barrel (carrying it? throw it up, dash after a moment, catch it, up special used until thrown)
        b = self.barrel
        if b.held and b.up_locked:                           # already used it on this barrel
            return
        if not b.held and (b.respawn_timer > 0 or b.mode == "ship"):
            return
        self.start_attack(BarrelDash(self, b.held))

    def ship(self):           # side + heavy: a ship crosses the screen at Rex's height. Holding the barrel? It rides along
        direction, y, b = self.facing, self.y, self.barrel     # y is captured NOW: the height he was at when he started
        def fire(owner):
            aboard = b if b.held else None
            if aboard:
                aboard.release(0, 0, "ship")
            owner.effects.append(Ship(owner, y, direction, aboard))
        self.start_attack(Attack(self, 1, 1, (0, 0), startup=24, active=0, recovery=14,
                                 damage=0, knockbackx=0, knockbacky=0, angle=0, stun=0, on_fire=fire))

    #---------------- LIGHT ----------------

    def lunge_grab(self):     # neutral + light: small lunge that stops (and picks the barrel up) if it's in reach
        self.start_attack(RexLunge(self))

    def throw_barrel(self):   # neutral or side + light while carrying the barrel: throw it the way he's facing (side input turns him that way first)
        def fire(owner):
            if owner.barrel.held:
                owner.barrel.throw(owner.facing)
        self.start_attack(Attack(self, 1, 1, (0, 0), startup=4, active=0, recovery=8,
                                 damage=0, knockbackx=0, knockbacky=0, angle=0, stun=0, on_fire=fire))

    def cutlass_up(self):     # up + light: upward cutlass swing
        self.start_attack(Attack(self, width=56, height=84, offset=(12, -42), startup=5, active=4, recovery=10,
                                 damage=6, knockbackx=7, knockbacky=12, angle=82, stun=12))

    def blade_wave(self):     # side + light (barrel not in hand): a wave of blade energy flies out
        def fire(owner):
            wave = Hitbox(owner, 22, 46, (0, 0), damage=5, kbx=8, kby=6, angle=25, stun=10)
            Projectile(owner.x + 24 * owner.facing, owner.y - 2, owner.facing, speed=14, lifetime=10, hitbox=wave)
        self.start_attack(Attack(self, 1, 1, (0, 0), startup=8, active=0, recovery=16,
                                 damage=0, knockbackx=0, knockbacky=0, angle=0, stun=0, on_fire=fire))

    def tentacles(self):      # down + light (grounded): three tentacles in front, long recovery, big upward spike
        self.start_attack(Tentacles(self))

    def cutlass_down(self):   # down + light (in the air): cutlass swung downward
        self.start_attack(Attack(self, width=46, height=54, offset=(8, 34), startup=5, active=6, recovery=9,
                                 damage=6, knockbackx=5, knockbacky=9, angle=-70, stun=12))

#==========================================================
# CHARACTER: BOMBHEAD - explosions, bombs and special moves
#   Blast      - one explosion: a hitbox that lives for a few frames, plus a see-through fireball so you can see its size
#   Explosive  - base for anything Bombhead throws that goes bang on contact (Bomb, Shell, DroppedBomb)
#   Everything Bombhead makes lives in his `effects` list, which he updates every frame (like Cap'n Rex's ships).
#==========================================================

class Blast:
    """An explosion. Hits everyone except its owner. mode="radial" throws victims away from the centre,
    mode="angle" throws them the way `facing` points (used by the shell, which is a directional shot).
    A parry blocks it for the parrier, but doesn't stun Bombhead or send it back."""
    def __init__(self, owner, x, y, size, damage, kbx, kby, stun, mode="radial", angle=45, facing=1, life=5):
        self.owner, self.x, self.y, self.facing = owner, x, y, facing
        self.life = self.max_life = life
        self.done = False
        self.hitbox = Hitbox(owner, size, size, (0, 0), damage=damage, kbx=kbx, kby=kby, angle=angle, stun=stun, mode=mode)
        self.hitbox.projectile = _NoReflect()
        self.hitbox.set_active(True)
        self.vis = Box(size, size, (255, 160, 50), x, y, alpha=150, radius=size / 2, fixed=False)
        Particles.burst(x, y, count=int(size / 4) + 10, colour=[(255, 210, 70), (255, 130, 30), (110, 110, 110)],
                        speed=(2, 3 + size / 40), life=(12, 28), size=(3, 7), gravity=0.05, drag=0.95)
        Sound.play("BlastBounceFire")

    def update(self, targets):
        victims = [p for p in players if p is not self.owner]      # ignores `targets`: a parried bomb changes owner
        self.hitbox.place(self.x, self.y, self.facing)
        self.hitbox.check(victims, self.facing)
        self.life -= 1
        self.vis.alpha = max(0, 150 * self.life / self.max_life)
        if self.life <= 0:
            self.delete()

    def delete(self):
        if not self.done:
            self.done = True
            self.hitbox.delete()
            self.vis.delete()


class Explosive:
    """A bomb-like object. Subclasses fill in step() (movement) and explode() (what the bang is).
    `home` is the Bombhead who made it (it lives in his effects list), `owner` is whoever it currently hurts people FOR,
    which only changes if someone parries it."""
    MAX_AGE = 600

    def __init__(self, owner, x, y, size, colour, border_colour="black"):
        self.home = self.owner = owner
        self.x, self.y, self.size = x, y, size
        self.vx = self.vy = 0
        self.age = 0
        self.done = False
        self.box = Box(size, size, colour, x, y, border=3, border_colour=border_colour, radius=size / 2, fixed=False)
        self.zone = Zone(x, y, size + 4, size + 4)

    def step(self):
        pass

    def explode(self):
        pass

    def detonate(self):
        self.explode()
        self.delete()

    def fizzle(self):
        Particles.burst(self.x, self.y, count=6, colour=[(120, 120, 120), (200, 200, 200)], speed=(1, 3), life=(8, 16), size=(2, 3), gravity=-0.05)
        self.delete()

    def reflect(self, parrier):
        """Parried: it now belongs to the parrier and heads back the way it came."""
        self.owner = parrier
        self.vx = -self.vx
        self.vy = min(self.vy, 0) - 2
        Particles.burst(self.x, self.y, count=30, colour=(100, 50, 255), speed=(4, 9), life=(20, 40), size=(3, 6), gravity=0, drag=0.98)

    def update(self, targets):
        self.age += 1
        old_x, old_y = self.x, self.y
        self.step()
        if self.done:
            return
        if self.age > self.MAX_AGE:
            self.fizzle()
            return
        portal_transit(self, old_x, old_y, lambda x, y: not level.is_solid(x, y))
        self.box.go_to(self.x, self.y)
        self.zone.x, self.zone.y = self.x, self.y
        for t in [p for p in players if p is not self.owner]:
            if t.touching_zone(self.zone):
                if t.parrying:
                    self.reflect(t)
                    t.on_parry_success()
                else:
                    self.detonate()
                return

    def delete(self):
        if not self.done:
            self.done = True
            self.box.delete()
            self.zone.delete()


class Bomb(Explosive):
    """The thrown bomb: arcs, bounces ONCE, and goes off on the second bounce (floor or wall) or on touching an enemy."""
    def __init__(self, owner, x, y, direction):
        super().__init__(owner, x, y, 16, (45, 45, 55), border_colour=(255, 120, 30))
        self.vx, self.vy = 7 * direction, -4
        self.bounces = 0

    def bounce(self):
        self.bounces += 1
        if self.bounces >= 2:
            self.detonate()

    def step(self):
        half = self.size / 2
        self.vy = min(self.vy + 0.4, 14)
        nx = self.x + self.vx
        if level.is_solid(nx + math.copysign(half, self.vx), self.y):
            self.vx = -self.vx * 0.5                       # bounced off a wall (counts as a bounce)
            self.bounce()
            if self.done:
                return
        else:
            self.x = nx
        ny = self.y + self.vy
        if self.vy > 0 and level.is_solid(self.x, ny + half):
            self.vy = -max(5, self.vy * 0.55)              # bounced off the floor
            self.bounce()
        elif self.vy < 0 and level.is_solid(self.x, ny - half):
            self.vy = 0                                    # bonked its head: just stops rising
        else:
            self.y = ny

    def explode(self):
        # a fairly minor explosion (the centre sits a little low so victims are popped upward)
        self.home.effects.append(Blast(self.owner, self.x, self.y + 8, 90, damage=6, kbx=8, kby=9, stun=12))


class Shell(Explosive):
    """The heavy side shot: really slow, flies straight, ONLY explodes on a person (walls and the floor just stop it)."""
    def __init__(self, owner, x, y, direction):
        super().__init__(owner, x, y, 24, (255, 120, 30), border_colour=(60, 20, 0))
        self.vx = 3.2 * direction
        self.MAX_AGE = 240

    def step(self):
        self.x += self.vx
        if level.is_solid(self.x, self.y):
            self.fizzle()
        elif self.age % 4 == 0:
            Particles.burst(self.x - 8 * math.copysign(1, self.vx), self.y, count=1, colour=[(255, 200, 60), (160, 160, 160)],
                            speed=(0.5, 1.5), life=(8, 14), size=(2, 3), gravity=0)

    def explode(self):
        # major damage + knockback, thrown the way the shell was travelling
        self.home.effects.append(Blast(self.owner, self.x, self.y, 140, damage=22, kbx=20, kby=11, stun=26,
                                       mode="angle", angle=30, facing=1 if self.vx >= 0 else -1))


class DroppedBomb(Explosive):
    """The heavy down bomb: falls from the top of the screen and goes off when it touches the ground or anybody."""
    def __init__(self, owner, x, y):
        super().__init__(owner, x, y, 30, (35, 35, 45), border_colour=(255, 60, 40))
        self.vy = 6
        self.MAX_AGE = 300

    def step(self):
        self.vy = min(self.vy + 0.5, 16)
        self.y += self.vy
        if level.is_solid(self.x, self.y + self.size / 2):
            self.detonate()

    def explode(self):
        self.home.effects.append(Blast(self.owner, self.x, self.y + 10, 190, damage=17, kbx=15, kby=15, stun=22))


class BombDash(Move):
    """side + light: dash a fair distance. Hit someone and they're knocked forward while Bombhead rockets up and away.
    Miss and he has a LONG recovery."""
    def __init__(self, owner):
        super().__init__(owner)
        self.state, self.timer = "startup", 8
        self.connected = False
        self.hitbox = self.add_hitbox(Hitbox(owner, 56, 44, (28, 0), damage=7, kbx=13, kby=5, angle=20, stun=18))
        self.hitbox.on_hit = self._landed

    def _landed(self, target):
        self.connected = True

    def update(self, targets):
        o = self.owner
        self.timer -= 1

        if self.state == "startup":                       # hang for a moment, no gravity
            o.x_velocity = 0
            o.y_velocity = 0
            o.NoGravTimer = 2
            if self.timer <= 0:
                self.state, self.timer = "dash", 18
                self.hitbox.set_active(True)

        elif self.state == "dash":
            o.x_velocity = 14 * self.facing
            o.y_velocity = 0
            o.NoGravTimer = 2
            self.hitbox.place(o.x, o.y, self.facing)
            self.hitbox.check(targets, self.facing)
            if self.cancelled:                            # parried
                return
            if self.connected:                            # victim goes forward, Bombhead goes up and away
                self.hitbox.set_active(False)
                o.x_velocity = -8 * self.facing
                o.y_velocity = -10
                o.NoGravTimer = 0
                self.end(recovery=8)
                return
            if self.timer <= 0:                           # whiffed
                self.state, self.timer = "recovery", 32
                self.hitbox.set_active(False)
                o.x_velocity = 2 * self.facing

        elif self.state == "recovery":
            if self.timer <= 0:
                self.end()


class SlideKick(Move):
    """down + light: a low sliding kick that knocks people upward. aerial=True slams to the floor first, then slides."""
    def __init__(self, owner, aerial=False):
        super().__init__(owner)
        self.fall_frames = 0
        if aerial:
            self.state, self.timer = "slam", 0
            owner.x_velocity = 0
        else:
            self.state, self.timer = "startup", 6
        self.hitbox = self.add_hitbox(Hitbox(owner, 54, 26, (30, 12), damage=8, kbx=4, kby=13, angle=80, stun=16))

    def update(self, targets):
        o = self.owner

        if self.state == "slam":
            self.fall_frames += 1
            o.y_velocity = 16
            if o.coyote_time == COYOTE_TIME or self.fall_frames > 120:   # landed (or safety timeout)
                self.state, self.timer = "startup", 5
            return

        self.timer -= 1
        if self.state == "startup":
            o.x_velocity = 0
            if self.timer <= 0:
                self.state, self.timer = "slide", 16
                self.hitbox.set_active(True)
        elif self.state == "slide":
            o.x_velocity = 11 * self.facing                # the ground's friction takes a little off every frame
            if self.timer <= 0:
                self.state, self.timer = "recovery", 14
                self.hitbox.set_active(False)
                o.x_velocity = 3 * self.facing
        elif self.state == "recovery":
            if self.timer <= 0:
                self.end()
                return

        self.hitbox.place(o.x, o.y, self.facing)
        self.hitbox.check(targets, self.facing)


class BlastLaunch(Move):
    """up + heavy: set off an explosion just in front of Bombhead's feet. It launches HIM up and away from the way he's facing
    (enough height to get back onto the stage), and hurts anyone standing in it. Twice per time on the floor."""
    def __init__(self, owner):
        super().__init__(owner)
        self.state, self.timer = "startup", 7
        owner.up_blasts -= 1

    def update(self, targets):
        o = self.owner
        self.timer -= 1
        if self.state == "startup":
            o.x_velocity = 0
            o.y_velocity = 0
            o.NoGravTimer = 2
            if self.timer <= 0:
                o.effects.append(Blast(o, o.x + 34 * self.facing, o.y + 10, 100, damage=6, kbx=9, kby=9, stun=14))
                o.x_velocity = -8 * self.facing
                o.y_velocity = -15
                o.NoGravTimer = 4
                self.state, self.timer = "recovery", 12
        elif self.state == "recovery":
            if self.timer <= 0:
                self.end()


class Haymaker(Attack):
    """neutral + heavy: an enormous wind-up (you can see the sparks building), then one huge sideways hit.
    Getting hit during the wind-up cancels it, same as any other move."""
    def update(self, targets):
        if self.frame < self.startup and self.frame % 5 == 0:
            o = self.owner
            power = self.frame / self.startup
            Particles.burst(o.x + 14 * self.facing, o.y, count=1 + int(power * 3), colour=[(255, 140, 30), (255, 230, 80)],
                            speed=(1, 2 + 4 * power), life=(8, 14), size=(2, 4), gravity=0)
        super().update(targets)


#==========================================================
# CHARACTER: BOMBHEAD
#==========================================================

class Bombhead(Player):

    title = "Bombhead"
    blurb = "DEADMAN DANNY (30 seconds to live baby)"

    FUSE_SECONDS = 30
    FUSE_FRAMES = FUSE_SECONDS * 60           # (the game runs at 60 fps)
    MAX_UP_BLASTS = 1                         # up + heavy uses between touching the floor
    BAR_WIDTH = 100
    # The fuse bar's colour as it drains: green -> gold -> yellow -> red   (fraction left, colour)
    FUSE_COLOURS = [(1.0, (80, 210, 90)), (0.66, (240, 175, 25)), (0.33, (255, 240, 60)), (0.0, (235, 50, 50))]

    def __init__(self, currentLevel, name, x=None, y=None, size=100, spawnIcon="p", controls=None, pad=None, pad_controls=None, slot=None):
        super().__init__(currentLevel, name, x, y, size, spawnIcon, controls, pad, pad_controls, slot)
        self.fuse = self.FUSE_FRAMES          # frames left to live
        self.exploded = False
        self.up_blasts = self.MAX_UP_BLASTS
        self.effects = []                     # bombs and explosions
        self.hud_tick = 0

    #---------------- passive: the fuse ----------------

    def should_die(self):
        return self.exploded

    def on_enemy_death(self, dead):
        self.fuse = self.FUSE_FRAMES          # someone else died: fuse refilled

    def reset_state(self):
        super().reset_state()
        self.fuse = self.FUSE_FRAMES          # respawning refills it too
        self.exploded = False
        self.up_blasts = self.MAX_UP_BLASTS

    def self_destruct(self):
        # Everyone nearby gets hurt and thrown; Bombhead dies (the match loop sees should_die() and respawns him)
        self.effects.append(Blast(self, self.x, self.y, 320, damage=30, kbx=20, kby=20, stun=30, life=6))
        self.exploded = True

    def handle_movement(self, currentLevel):
        if self.coyote_time == COYOTE_TIME:
            self.up_blasts = self.MAX_UP_BLASTS
        return super().handle_movement(currentLevel)

    def update_attack(self, targets):
        super().update_attack(targets)
        if not self.exploded:
            self.fuse -= 1
            if self.fuse <= 0:
                self.self_destruct()
            elif self.fuse < 600 and self.fuse % 12 == 0:      # the last 10 seconds: smoke
                Particles.burst(self.x, self.y - 14, count=2, colour=[(120, 120, 120), (255, 150, 40)],
                                speed=(1, 3), life=(10, 20), size=(2, 4), gravity=-0.05)
        for effect in self.effects[:]:
            effect.update(targets)
            if effect.done:
                self.effects.remove(effect)

    def cleanup(self):
        for effect in self.effects:
            effect.delete()
        self.effects.clear()

    #---------------- HUD ----------------

    def make_hud(self, x, y):
        self.bar_left = x - self.BAR_WIDTH / 2
        back = Box(self.BAR_WIDTH, 10, "black", x, y, alpha=120, border=2, border_colour="black")
        self.fill = Box(self.BAR_WIDTH, 10, self.FUSE_COLOURS[0][1], x, y)
        self.label = Text("FUSE", x, y - 17, 16, PLAYER_COLOURS[self.slot], outline=2)
        self.pips = [Box(10, 10, (255, 150, 40), x + self.BAR_WIDTH / 2 + 14 + i * 14, y, border=2, border_colour="black", radius=5)
                     for i in range(self.MAX_UP_BLASTS)]               # how many up + heavy blasts are left
        self.hud_sprites = [back, self.fill, self.label] + self.pips

    def fuse_colour(self, fraction):
        stops = self.FUSE_COLOURS
        for (hi_f, hi_c), (lo_f, lo_c) in zip(stops, stops[1:]):
            if fraction >= lo_f:
                t = (fraction - lo_f) / (hi_f - lo_f)
                return tuple(int(lo_c[i] + (hi_c[i] - lo_c[i]) * t) for i in range(3))
        return stops[-1][1]

    def update_hud(self):
        self.hud_tick += 1
        fraction = max(0, self.fuse / self.FUSE_FRAMES)
        width = max(1, self.BAR_WIDTH * fraction)
        self.fill.width = width
        self.fill.x = self.bar_left + width / 2
        self.fill.colour = self.fuse_colour(fraction)
        self.fill.alpha = 255 if self.fuse > 600 or (self.hud_tick // 6) % 2 else 120      # flashes in the last 10 seconds
        self.label.text = f"FUSE  {max(0, math.ceil(self.fuse / 60))}s"
        for i, pip in enumerate(self.pips):
            pip.alpha = 255 if i < self.up_blasts else 40

    #---------------- input ----------------

    def attackChecks(self, targets=()):
        if not self.actionable:
            return

        heavy = self.pressed("heavy")
        light = self.pressed("light")
        if not (heavy or light):
            return

        grounded = self.coyote_time == COYOTE_TIME
        down = self.held("down")
        side = self.held("left") or self.held("right")
        up = self.held("up")

        if heavy:
            if down:
                self.drop_bomb()
            elif up:
                self.blast_launch()
            elif side:
                self.shell()
            else:
                self.haymaker()
        else:
            if down:
                self.slide_kick(aerial=not grounded)
            elif up:
                self.upswing()
            elif side:
                self.bomb_dash()
            else:
                # Neutral light: riposte if someone nearby was just parried, otherwise throw a bomb
                if not self.try_riposte(targets):
                    self.throw_bomb()

    #---------------- HEAVY ----------------

    def blast_launch(self):   # up + heavy: explosion in front that launches him up and away (2 per floor touch)
        if self.up_blasts > 0:
            self.start_attack(BlastLaunch(self))

    def shell(self):          # side + heavy: really slow explosive round, only goes off on a person
        def fire(owner):
            owner.effects.append(Shell(owner, owner.x + 22 * owner.facing, owner.y - 2, owner.facing))
        self.start_attack(Attack(self, 1, 1, (0, 0), startup=16, active=0, recovery=26,
                                 damage=0, knockbackx=0, knockbacky=0, angle=0, stun=0, on_fire=fire))

    def drop_bomb(self):      # down + heavy: a bomb falls in from the top of the screen, in front of him
        def fire(owner):
            x = max(40, min(level.width - 40, owner.x + 80 * owner.facing))
            top = Stage.camera.y - Screen.height / 2 - 20
            owner.effects.append(DroppedBomb(owner, x, top))
        self.start_attack(Attack(self, 1, 1, (0, 0), startup=14, active=0, recovery=16,
                                 damage=0, knockbackx=0, knockbacky=0, angle=0, stun=0, on_fire=fire))

    def haymaker(self):       # neutral + heavy: crazy long wind-up, then a huge sideways hit
        self.start_attack(Haymaker(self, width=76, height=50, offset=(44, 0), startup=70, active=5, recovery=26,
                                   damage=30, knockbackx=24, knockbacky=7, angle=15, stun=24))

    #---------------- LIGHT ----------------

    def upswing(self):        # up + light: simple upward swing (same shape as Ven's)
        self.start_attack(Attack(self, width=70, height=65, offset=(0, -25), startup=4, active=4, recovery=9,
                                 damage=5, knockbackx=5, knockbacky=11, angle=90, stun=12))

    def bomb_dash(self):      # side + light: dash at them (see BombDash)
        self.start_attack(BombDash(self))

    def slide_kick(self, aerial=False):   # down + light: slide kick (in the air: slam down first)
        self.start_attack(SlideKick(self, aerial))

    def throw_bomb(self):     # neutral + light: lob a small bomb that bounces once, then goes off
        def fire(owner):
            owner.effects.append(Bomb(owner, owner.x + 16 * owner.facing, owner.y - 4, owner.facing))
        self.start_attack(Attack(self, 1, 1, (0, 0), startup=8, active=0, recovery=16,
                                 damage=0, knockbackx=0, knockbacky=0, angle=0, stun=0, on_fire=fire))

#==========================================================
# CHARACTER: ANGELLICA - light constructs and special moves
#   GravityField - a big box where everybody falls slower (registered in gravity_fields, which Player.handle_movement reads)
#   LightPillar  - a full-height column of light that lingers and ticks damage
#   Starball     - the three-bar heavy: slides to a stop, charges, then a long growing explosion
#   Orb          - one of the three neutral-light orbs: hovers, tracks, locks on, pauses, fires
#   WingBurst / GrabSlam / AscendSurge - multi-stage moves
#   Everything she summons lives in her `effects` list, which she updates every frame (like Bombhead and Cap'n Rex).
#==========================================================

class GravityField:
    """Inside the box, gravity is multiplied by `scale` for EVERY player (Angellica included)."""
    def __init__(self, owner, x, y, size=380, scale=0.3, life=480):
        self.owner, self.x, self.y, self.size, self.scale, self.life = owner, x, y, size, scale, life
        self.done = False
        self.vis = Box(size, size, (150, 200, 255), x, y, alpha=45, border=3, border_colour=(190, 225, 255), radius=24, fixed=False)
        gravity_fields.append(self)

    def contains(self, player):
        half = self.size / 2
        return abs(player.x - self.x) <= half and abs(player.y - self.y) <= half

    def update(self, targets):
        self.life -= 1
        if self.life < 60:                                    # flickers when it's about to end
            self.vis.alpha = 45 if (self.life // 5) % 2 else 15
        if self.life % 8 == 0:                                # little motes drifting upward
            half = int(self.size / 2)
            Particles.burst(self.x + random_number(-half, half), self.y + random_number(-half, half), count=1,
                            colour=(200, 230, 255), direction=0, spread=20, speed=(0.5, 1.5), life=(30, 50), size=(2, 3), gravity=-0.02)
        if self.life <= 0:
            self.delete()

    def delete(self):
        if not self.done:
            self.done = True
            if self in gravity_fields:
                gravity_fields.remove(self)
            self.vis.delete()


class LightPillar:
    """A column from the top of the stage to the bottom. A thin warning first, then it lingers and hits again every few frames."""
    WIDTH, WARN, ACTIVE, REARM = 90, 18, 56, 14

    def __init__(self, owner, x, facing):
        self.owner, self.x, self.facing = owner, x, facing
        self.y = level.height / 2
        self.t = 0
        self.done = False
        self.hitbox = Hitbox(owner, self.WIDTH, level.height, (0, 0), damage=7, kbx=4, kby=8, angle=80, stun=10, colour=(255, 245, 190))
        self.hitbox.projectile = _NoReflect()                 # a parry blocks it but doesn't stun Angellica
        self.vis = Box(20, level.height, (255, 245, 190), x, self.y, alpha=40, fixed=False)

    def update(self, targets):
        self.t += 1
        if self.t <= self.WARN:
            self.vis.width = 20 + (self.WIDTH - 20) * self.t / self.WARN
            return
        if self.t == self.WARN + 1:
            self.vis.width, self.vis.alpha = self.WIDTH, 110
            Sound.play("BlastBounceFire")
        if (self.t - self.WARN - 1) % self.REARM == 0:        # switch off and on again so it can hit everyone once more
            self.hitbox.set_active(False)
            self.hitbox.set_active(True)
        self.hitbox.place(self.x, self.y, 1)
        self.hitbox.check([p for p in players if p is not self.owner], self.facing)
        if self.t > self.WARN + self.ACTIVE - 10:
            self.vis.alpha = max(0, self.vis.alpha - 8)
        if self.t >= self.WARN + self.ACTIVE:
            self.delete()

    def delete(self):
        if not self.done:
            self.done = True
            self.hitbox.delete()
            self.vis.delete()


class Starball:
    """The three-bar heavy. Slides out, slows to a stop (no gravity), charges for a moment, then explodes in a big
    growing blast that lingers and hits again every few frames, with a harder final pulse."""
    BOOM_FRAMES, CHARGE_FRAMES, REARM = 200, 22, 14

    def __init__(self, owner, x, y, direction):
        self.owner, self.x, self.y = owner, x, y
        self.vx = 11 * direction
        self.state, self.t = "fly", 0
        self.done = False
        self.box = Box(26, 26, (255, 240, 170), x, y, border=3, border_colour="white", radius=13, fixed=False)
        self.hitbox = Hitbox(owner, 10, 10, (0, 0), damage=15, kbx=11, kby=11, angle=45, stun=10, mode="radial", colour=(255, 240, 170))
        self.hitbox.projectile = _NoReflect()
        self.final = False

    def update(self, targets):
        self.t += 1
        if self.state == "fly":
            self.vx *= 0.93
            nx = self.x + self.vx
            if level.is_solid(nx + math.copysign(13, self.vx), self.y):
                self.vx = 0                                   # hit a wall: stops dead
            else:
                self.x = nx
            if abs(self.vx) < 0.4 or self.t > 240:
                self.state, self.t = "charge", 0

        elif self.state == "charge":                          # pulses so you know it's about to go
            self.box.width = self.box.height = 26 + (self.t % 6) * 2
            if self.t >= self.CHARGE_FRAMES:
                self.state, self.t = "boom", 0
                self.hitbox.set_active(True)
                Sound.play("BlastBounceFire")

        elif self.state == "boom":
            progress = self.t / self.BOOM_FRAMES
            size = 40 + 400 * progress
            self.hitbox.zone.width = self.hitbox.zone.height = size
            self.box.width = self.box.height = size
            self.box.radius = size / 2
            self.box.alpha = 160 * (1 - progress * 0.7)
            if self.t % 3 == 0:
                Particles.burst(self.x, self.y, count=3, colour=[(255, 240, 170), (255, 255, 255), (190, 225, 255)],
                                speed=(1, 2 + size / 60), life=(10, 20), size=(2, 5), gravity=0)
            if self.t == self.BOOM_FRAMES - 8 and not self.final:       # the last pulse hits much harder
                self.final = True
                self.hitbox.damage, self.hitbox.kbx, self.hitbox.kby, self.hitbox.stun = 12, 16, 16, 22
                self.hitbox.set_active(False)
                self.hitbox.set_active(True)
            elif self.t % self.REARM == 1:
                self.hitbox.set_active(False)
                self.hitbox.set_active(True)
            self.hitbox.place(self.x, self.y, 1)
            self.hitbox.check([p for p in players if p is not self.owner], 1)
            if self.t >= self.BOOM_FRAMES:
                self.delete()
                return
        self.box.go_to(self.x, self.y)

    def delete(self):
        if not self.done:
            self.done = True
            self.hitbox.delete()
            self.box.delete()


class Orb:
    """Hovers above Angellica and follows her, turning to face the nearest enemy. Then it LOCKS (goes red and stops),
    waits a moment, and shoots quickly along the line it locked. If Angellica is hit before it fires, it pops."""
    TRACK, LOCK = 40, 14

    def __init__(self, owner, ox, oy, extra_delay):
        self.owner, self.ox, self.oy, self.extra = owner, ox, oy, extra_delay
        self.x, self.y = owner.x + ox, owner.y + oy
        self.aim = (owner.facing, 0)
        self.state, self.t = "track", 0
        self.done = False
        self.box = Box(14, 14, (255, 240, 170), self.x, self.y, border=2, border_colour="white", radius=7, fixed=False)

    def nearest_aim(self):
        foes = [p for p in players if p is not self.owner]
        if not foes:
            return self.aim
        t = min(foes, key=lambda p: math.hypot(p.x - self.x, p.y - self.y))
        dx, dy = t.x - self.x, t.y - self.y
        dist = math.hypot(dx, dy) or 1
        return (dx / dist, dy / dist)

    def update(self, targets):
        self.t += 1
        o = self.owner
        if self.state == "track":
            self.x, self.y = o.x + self.ox, o.y + self.oy
            self.aim = self.nearest_aim()
            if self.t % 6 == 0:                               # a little spark shows where it's looking
                Particles.burst(self.x + self.aim[0] * 14, self.y + self.aim[1] * 14, count=1, colour=(255, 255, 255),
                                speed=(0.2, 0.6), life=(4, 8), size=(2, 2), gravity=0)
            if self.t >= self.TRACK:
                self.state, self.t = "lock", 0
                self.box.colour = (255, 90, 90)
        elif self.state == "lock":
            if self.t >= self.LOCK + self.extra:
                self.fire()
                return
        self.box.go_to(self.x, self.y)

    def fire(self):
        o = self.owner
        dx, dy = self.aim
        facing = 1 if dx >= 0 else -1
        angle = math.degrees(math.atan2(-dy, abs(dx)))        # Projectile angles: 0 = straight ahead, 90 = up, negative = down
        hb = Hitbox(o, 14, 14, (0, 0), damage=4, kbx=6, kby=5, angle=20, stun=10, colour=(255, 240, 170))
        def landed(target):
            if hb.owner is o:                                 # (a parried orb that comes back doesn't refill HER bar)
                o.light_hit(target)
        hb.on_hit = landed
        Projectile(self.x, self.y, facing, speed=17, lifetime=45, hitbox=hb, angle=angle)
        self.delete()

    def delete(self):
        if not self.done:
            self.done = True
            self.box.delete()


class WingBurst(Move):
    """down + light: wings shoot out of both sides at once."""
    def __init__(self, owner):
        super().__init__(owner)
        self.frame = 0
        self.right = self.add_hitbox(Hitbox(owner, 80, 36, (50, -6), damage=6, kbx=11, kby=8, angle=30, stun=12, colour=(255, 245, 210)))
        self.left = self.add_hitbox(Hitbox(owner, 80, 36, (-50, -6), damage=6, kbx=11, kby=8, angle=30, stun=12, colour=(255, 245, 210)))
        self.left.already_hit = self.right.already_hit        # someone in the middle is only hit once
        for hb in (self.right, self.left):
            hb.on_hit = owner.light_hit

    def update(self, targets):
        o = self.owner
        self.frame += 1
        on = 6 <= self.frame < 12
        self.right.set_active(on)
        self.left.set_active(on)
        self.right.place(o.x, o.y, 1)                         # facing 1 for both: the offsets already put them on opposite sides...
        self.left.place(o.x, o.y, 1)
        self.right.check(targets, 1)                          # ...and this knocks each victim AWAY from Angellica
        self.left.check(targets, -1)
        if self.cancelled:
            return
        if self.frame >= 22:
            self.end()


class GrabSlam(Move):
    """side + light: dash forward. Catch someone and she hops up (carrying them forward), then slams down:
    the landing sends out a wide hit around her. Miss and she has a long recovery."""
    def __init__(self, owner):
        super().__init__(owner)
        self.state, self.timer = "startup", 8
        self.target = None
        self.fall_frames = 0
        self.grab = self.add_hitbox(Hitbox(owner, 48, 40, (28, 0), damage=3, kbx=0, kby=0, angle=0, stun=0, colour=(255, 245, 210)))
        self.grab.on_hit = self._grabbed
        self.slam = self.add_hitbox(Hitbox(owner, 150, 56, (0, 12), damage=14, kbx=12, kby=14, angle=60, stun=24, mode="radial", colour=(255, 245, 210)))
        self.slam.on_hit = owner.light_hit

    def _grabbed(self, target):
        if self.target is None:
            self.target = target
            self.owner.light_hit(target)

    def hold(self):                                           # keep the caught player pinned to her, helpless
        o, t = self.owner, self.target
        t.actionableTimer = 20
        t.NoGravTimer = 2
        t.x_velocity = t.y_velocity = 0
        tx, ty = o.x + 24 * self.facing, o.y + 4
        if level.is_solid(tx, ty):
            tx, ty = o.x, o.y
        t.x, t.y = tx, ty

    def update(self, targets):
        o = self.owner
        self.timer -= 1

        if self.state == "startup":
            o.x_velocity = 0
            o.y_velocity = 0
            o.NoGravTimer = 2
            if self.timer <= 0:
                self.state, self.timer = "dash", 14
                self.grab.set_active(True)

        elif self.state == "dash":
            o.x_velocity = 13 * self.facing
            o.y_velocity = 0
            o.NoGravTimer = 2
            self.grab.place(o.x, o.y, self.facing)
            self.grab.check(targets, self.facing)
            if self.cancelled:                                # parried
                return
            if self.target is not None:                       # caught someone: hop up and forward
                self.grab.set_active(False)
                self.state, self.timer = "rise", 16
                o.x_velocity = 5 * self.facing
                o.y_velocity = -9
                o.NoGravTimer = 0
                self.hold()
            elif self.timer <= 0:                             # whiffed: long recovery
                self.state, self.timer = "recovery", 26
                self.grab.set_active(False)
                o.x_velocity = 2 * self.facing

        elif self.state == "rise":
            self.hold()
            o.x_velocity = 5 * self.facing
            if self.timer <= 0:
                self.state = "slam"

        elif self.state == "slam":
            self.hold()
            self.fall_frames += 1
            o.y_velocity = 18
            o.x_velocity = 3 * self.facing
            if o.coyote_time == COYOTE_TIME or self.fall_frames > 120:     # landed (or safety timeout)
                t = self.target
                self.target = None                            # let go BEFORE the slam hitbox, so cancel() doesn't undo its stun
                t.actionableTimer = 0
                t.NoGravTimer = 0
                o.x_velocity = 0
                self.state, self.timer = "impact", 5
                self.slam.set_active(True)
                Particles.burst(o.x, o.y + 14, count=24, colour=[(255, 245, 210), (190, 225, 255)], direction=0, spread=160,
                                speed=(2, 6), life=(10, 20), size=(2, 4), gravity=0.2)
                Sound.play("Heavy Hitter")
            else:
                return

        elif self.state == "impact":
            if self.timer <= 0:
                self.state, self.timer = "recovery", 18
                self.slam.set_active(False)

        elif self.state == "recovery":
            if self.timer <= 0:
                self.end()
                return

        if self.state == "impact" and self.slam.active:       # the slam's hits (including the landing frame itself)
            self.slam.place(o.x, o.y, 1)
            self.slam.check(targets, 1)

    def cancel(self):
        t = self.target
        if t is not None:                                     # she got hit mid-carry: drop them
            self.target = None
            t.actionableTimer = 0
            t.NoGravTimer = 0
        super().cancel()


class AscendSurge(Move):
    """up + heavy: a short prepare, then she surges upward with a hitbox around her.
    Hold left or right during the prepare to tilt the surge a little that way."""
    MAX_TILT = 25                 # degrees away from straight up

    def __init__(self, owner):
        super().__init__(owner)
        self.state, self.timer = "startup", 16
        self.tilt = 0
        self.hitbox = self.add_hitbox(Hitbox(owner, 64, 64, (0, 0), damage=9, kbx=8, kby=11, angle=80, stun=16, mode="radial", colour=(255, 245, 210)))
        self.hitbox.on_hit = owner.light_hit
        owner.surges -= 1

    def update(self, targets):
        o = self.owner
        self.timer -= 1

        if self.state == "startup":
            o.x_velocity = 0
            o.y_velocity = 0
            o.NoGravTimer = 2
            steer = (1 if o.held("right") else 0) - (1 if o.held("left") else 0)
            if steer:
                self.tilt = steer * self.MAX_TILT             # the last direction you held wins
            a = math.radians(self.tilt)
            Particles.burst(o.x + 22 * math.sin(a), o.y - 22 * math.cos(a), count=1, colour=(255, 255, 255),
                            direction=self.tilt, spread=10, speed=(1, 2), life=(6, 10), size=(2, 3), gravity=0)
            if self.timer <= 0:
                self.state, self.timer = "surge", 16
                self.hitbox.set_active(True)
                Sound.play("BlastBounceFire")

        elif self.state == "surge":
            a = math.radians(self.tilt)
            o.x_velocity = 14 * math.sin(a)
            o.y_velocity = -14 * math.cos(a)
            o.NoGravTimer = 2
            self.hitbox.place(o.x, o.y, self.facing)
            self.hitbox.check(targets, self.facing)
            if self.cancelled:
                return
            if self.timer <= 0:
                self.state, self.timer = "recovery", 14
                self.hitbox.set_active(False)
                o.x_velocity *= 0.4
                o.y_velocity *= 0.3
                o.NoGravTimer = 0

        elif self.state == "recovery":
            if self.timer <= 0:
                self.end()


#==========================================================
# CHARACTER: ANGELLICA
#==========================================================

class Angellica(Player):

    title = "Angellica"
    blurb = "Low gravity angel that uses light as a resource."

    MAX_LIGHT = 3
    MAX_SURGES = 1                # up + heavy uses between touching the floor
    SEG_W, SEG_GAP = 30, 4

    def __init__(self, currentLevel, name, x=None, y=None, size=100, spawnIcon="p", controls=None, pad=None, pad_controls=None, slot=None):
        super().__init__(currentLevel, name, x, y, size, spawnIcon, controls, pad, pad_controls, slot)
        self.gravity = 0.28                       # passive: reduced gravity...
        self.max_dash_charges = 2                 # ...and two air dashes
        self.light = self.MAX_LIGHT
        self.surges = self.MAX_SURGES
        self.regain_lock = 0                      # frames after a refill where hits can't refill again (so 3 orbs landing together = 1 bar)
        self.deny_timer = 0                       # flashes the bar red when you can't afford a move
        self.field = None                         # her current gravity field (a new one replaces it)
        self.effects = []
        self.hud_tick = 0

    #---------------- passive: the light bar ----------------

    def light_hit(self, target):
        """Called by every hitbox of an attack that does NOT cost light. Hitting someone while she's airborne refills a bar."""
        airborne = self.coyote_time != COYOTE_TIME
        if airborne and self.regain_lock == 0 and self.light < self.MAX_LIGHT:
            self.light += 1
            self.regain_lock = 30
            Particles.burst(self.x, self.y, count=12, colour=[(255, 240, 170), (255, 255, 255)],
                            speed=(2, 5), life=(10, 20), size=(2, 4), gravity=-0.05)

    def spend(self, amount):
        if self.light < amount:
            self.deny_timer = 20
            return False
        self.light -= amount
        return True

    def free(self, move):                         # tags a move as "costs no light", so landing it in the air refills a bar
        for hb in move.hitboxes:
            hb.on_hit = self.light_hit
        return move

    def clear_orbs(self):
        for effect in self.effects:
            if isinstance(effect, Orb):
                effect.delete()

    def on_hit(self):
        super().on_hit()
        self.clear_orbs()                         # orbs that haven't fired yet pop when she's hit

    def reset_state(self):
        super().reset_state()
        self.light = self.MAX_LIGHT
        self.surges = self.MAX_SURGES
        self.regain_lock = 0
        self.clear_orbs()

    def handle_movement(self, currentLevel):
        if self.deny_timer > 0: self.deny_timer -= 1
        if self.coyote_time == COYOTE_TIME:
            self.surges = self.MAX_SURGES
        return super().handle_movement(currentLevel)

    def update_attack(self, targets):
        super().update_attack(targets)
        if self.regain_lock > 0: self.regain_lock -= 1
        for effect in self.effects[:]:
            effect.update(targets)
            if effect.done:
                self.effects.remove(effect)

    def cleanup(self):
        for effect in self.effects:
            effect.delete()
        self.effects.clear()

    #---------------- HUD ----------------

    def make_hud(self, x, y):
        total = self.MAX_LIGHT * self.SEG_W + (self.MAX_LIGHT - 1) * self.SEG_GAP
        left = x - total / 2 + self.SEG_W / 2
        self.segs = [Box(self.SEG_W, 10, (255, 235, 140), left + i * (self.SEG_W + self.SEG_GAP), y, border=2, border_colour="black", radius=3)
                     for i in range(self.MAX_LIGHT)]
        self.label = Text("LIGHT", x, y - 17, 16, PLAYER_COLOURS[self.slot], outline=2)
        self.hud_sprites = self.segs + [self.label]

    def update_hud(self):
        self.hud_tick += 1
        for i, seg in enumerate(self.segs):
            if i < self.light:
                seg.colour, seg.alpha = (255, 235, 140), 255
            elif self.deny_timer > 0:
                seg.colour, seg.alpha = (230, 60, 60), 255            # red flash: "can't afford that!"
            else:
                seg.colour, seg.alpha = (255, 235, 140), 40

    #---------------- input ----------------

    def attackChecks(self, targets=()):
        if not self.actionable:
            return

        heavy = self.pressed("heavy")
        light = self.pressed("light")
        if not (heavy or light):
            return

        down = self.held("down")
        side = self.held("left") or self.held("right")
        up = self.held("up")

        if heavy:
            if down:
                self.light_pillar()
            elif up:
                self.ascend()
            elif side:
                self.starball()
            else:
                self.gravity_zone()
        else:
            if down:
                self.wings()
            elif up:
                self.column()
            elif side:
                self.grab_slam()
            else:
                # Neutral light: riposte if someone nearby was just parried, otherwise summon the orbs
                if not self.try_riposte(targets):
                    self.orbs()

    #---------------- HEAVY ----------------

    def gravity_zone(self):   # neutral + heavy (1 bar): a big area where everyone falls slower
        if not self.spend(1):
            return
        def fire(owner):
            if owner.field is not None:
                owner.field.delete()                      # only one at a time
            owner.field = GravityField(owner, owner.x, owner.y)
            owner.effects.append(owner.field)
        self.start_attack(Attack(self, 1, 1, (0, 0), startup=12, active=0, recovery=14,
                                 damage=0, knockbackx=0, knockbacky=0, angle=0, stun=0, on_fire=fire))

    def light_pillar(self):   # down + heavy (1 bar): a full-height column of light in front of her that lingers
        if not self.spend(1):
            return
        def fire(owner):
            x = max(60, min(level.width - 60, owner.x + 100 * owner.facing))
            owner.effects.append(LightPillar(owner, x, owner.facing))
        self.start_attack(Attack(self, 1, 1, (0, 0), startup=12, active=0, recovery=16,
                                 damage=0, knockbackx=0, knockbacky=0, angle=0, stun=0, on_fire=fire))

    def ascend(self):         # up + heavy (free, but once per floor touch): prepare, then surge up (see AscendSurge)
        if self.surges > 0:
            self.start_attack(AscendSurge(self))

    def starball(self):       # side + heavy (all 3 bars): a ball that coasts to a stop, then a long growing explosion
        if not self.spend(self.MAX_LIGHT):
            return
        def fire(owner):
            owner.effects.append(Starball(owner, owner.x + 20 * owner.facing, owner.y - 2, owner.facing))
        self.start_attack(Attack(self, 1, 1, (0, 0), startup=14, active=0, recovery=24,
                                 damage=0, knockbackx=0, knockbacky=0, angle=0, stun=0, on_fire=fire))

    #---------------- LIGHT ----------------

    def wings(self):          # down + light: wings out on both sides
        self.start_attack(WingBurst(self))

    def column(self):         # up + light: a column straight up
        self.start_attack(self.free(Attack(self, width=34, height=250, offset=(0, -135), startup=8, active=6, recovery=12,
                                           damage=7, knockbackx=3, knockbacky=13, angle=90, stun=14)))

    def grab_slam(self):      # side + light: dash grab into a slam
        self.start_attack(GrabSlam(self))

    def orbs(self):           # neutral + light: three orbs rise, track, lock on, pause, then fire
        def fire(owner):
            for ox, oy, delay in ((-34, -44, 0), (0, -62, 6), (34, -44, 12)):
                owner.effects.append(Orb(owner, ox, oy, delay))
        self.start_attack(Attack(self, 1, 1, (0, 0), startup=8, active=0, recovery=14,
                                 damage=0, knockbackx=0, knockbacky=0, angle=0, stun=0, on_fire=fire))

#==========================================================
# CHARACTER: THE WATCHER - portals, tentacles and special moves
#   (paste this whole block ABOVE the "All character list" / CHARACTERS dict, then add
#    "The Watcher": Watcher   to CHARACTERS. The other edits are listed in the chat message.)
#
#   Portal      - one doorway (a tall thin box standing in the world)
#   PortalSet   - one Watcher's pair of portals (slot 0 = portal 1, slot 1 = portal 2)
#   portal_transit() - moves anything that crosses one portal out of the other
#   portal_slices()  - the bits of a melee hitbox that have poked THROUGH a portal
#   SpikeTentacle / TentacleBarrage / TentacleLift - multi-stage moves
#   TentacleBall - the side-heavy projectile with four tentacles
#==========================================================

PORTAL_COLOURS = [(60, 140, 255), (255, 150, 40)]     # portal 1 = blue, portal 2 = orange
portal_sets = []                                      # every Watcher's PortalSet (only sets with BOTH portals out do anything)


class Portal:
    W, H = 22, 96

    def __init__(self, index, x, y):
        self.index, self.x, self.y = index, x, y
        self.box = Box(self.W, self.H, PORTAL_COLOURS[index], x, y, alpha=170,
                       border=3, border_colour="white", radius=11, fixed=False)

    def delete(self):
        self.box.delete()


class PortalSet:
    def __init__(self, owner):
        self.owner = owner
        self.slots = [None, None]

    def place(self, index, x, y):
        self.slots[index] = Portal(index, x, y)
        Particles.burst(x, y, count=18, colour=PORTAL_COLOURS[index], speed=(2, 5), life=(10, 22), size=(2, 4), gravity=0)

    def remove(self, index):
        portal = self.slots[index]
        if portal is not None:
            Particles.burst(portal.x, portal.y, count=18, colour=PORTAL_COLOURS[index], speed=(2, 5), life=(10, 22), size=(2, 4), gravity=0)
            portal.delete()
            self.slots[index] = None

    def clear(self):
        self.remove(0)
        self.remove(1)

    def ambient(self):                                    # a little shimmer so you can see where they are
        for portal in self.slots:
            if portal is not None:
                Particles.burst(portal.x, portal.y + random_number(-40, 40), count=1, colour=PORTAL_COLOURS[portal.index],
                                speed=(0.3, 1), life=(10, 20), size=(2, 3), gravity=0)


def portal_transit(obj, old_x, old_y, fits):
    """Anything with .x and .y that moved from (old_x, old_y) to where it is now: if that path crossed a portal, it comes out
    of the other one, carrying on in the same direction. `fits(x, y)` says whether the exit is clear (a blocked portal does nothing).
    Checking the whole path (not just the end point) means fast things can't skip over a portal."""
    for pset in portal_sets:
        a, b = pset.slots
        if a is None or b is None:
            continue
        for src, dst in ((a, b), (b, a)):
            before, after = old_x - src.x, obj.x - src.x
            if before == 0 or before * after > 0:         # started on the line, or never crossed it
                continue
            t = before / (before - after)
            cross_y = old_y + (obj.y - old_y) * t
            if abs(cross_y - src.y) > Portal.H / 2:       # went over or under the portal
                continue
            direction = 1 if before < 0 else -1
            new_x = dst.x + direction * max(abs(after), 1)    # however far it had gone past the first portal, it is that far out of the second
            new_y = obj.y + (dst.y - src.y)
            if not fits(new_x, new_y):
                continue
            for portal in (src, dst):
                Particles.burst(portal.x, obj.y, count=8, colour=PORTAL_COLOURS[portal.index], speed=(1, 4), life=(8, 16), size=(2, 3), gravity=0)
            obj.x, obj.y = new_x, new_y
            return True
    return False


def player_fits(player, x, y):
    old = player.x, player.y
    player.x, player.y = x, y
    clear = not level.touching(player)
    player.x, player.y = old
    return clear


def portal_slices(rect, origin_x):
    """For a melee hitbox rect that overlaps a portal: ONLY the part past the portal (away from the attacker, origin_x)
    is copied out of the other portal. Returns a list of (rect, centre)."""
    out = []
    for pset in portal_sets:
        a, b = pset.slots
        if a is None or b is None:
            continue
        for src, dst in ((a, b), (b, a)):
            top = max(rect.top, int(src.y - Portal.H / 2))
            bottom = min(rect.bottom, int(src.y + Portal.H / 2))
            sx = int(src.x)
            if bottom <= top or not (rect.left < sx < rect.right):
                continue
            left, right = (sx, rect.right) if origin_x < src.x else (rect.left, sx)
            piece = rect.copy()
            piece.update(left, top, max(1, right - left), bottom - top)
            piece = piece.move(int(dst.x - src.x), int(dst.y - src.y))
            out.append((piece, piece.center))
    return out


def floor_below(x, y, limit=240):
    """The y of the top of the first solid tile under (x, y), or None if there isn't one close enough."""
    ts = level.tile_size
    yy = y
    while yy < y + limit:
        if level.is_solid(x, yy):
            return int(yy // ts) * ts
        yy += 8
    return None


#---------------- moves ----------------

class SpikeTentacle(Move):
    """A tentacle that bursts out of nowhere in front of the Watcher and grows along one axis.
    up=True : rises out of the FLOOR just in front of him and spikes UP.
    up=False: drops out of THIN AIR above and in front of him and spikes DOWN."""
    def __init__(self, owner, up):
        super().__init__(owner)
        self.up = up
        self.frame = 0
        self.x = owner.x + 70 * self.facing
        if level.is_solid(self.x, owner.y):               # a wall in the way: come up right under him instead
            self.x = owner.x
        if up:
            self.startup, self.active, self.recovery = 12, 12, 16
            floor = floor_below(self.x, owner.y)
            self.anchor = floor if floor is not None else owner.y + 13
            self.hitbox = self.add_hitbox(Hitbox(owner, 22, 20, (0, 0), damage=8, kbx=3, kby=14, angle=88, stun=20))
        else:
            self.startup, self.active, self.recovery = 14, 10, 14
            self.anchor = owner.y - 55
            self.hitbox = self.add_hitbox(Hitbox(owner, 20, 20, (0, 0), damage=7, kbx=3, kby=13, angle=-80, stun=18))
        self.total_frames = self.startup + self.active + self.recovery

    def update(self, targets):
        age = self.frame - self.startup
        if self.frame == 3:                               # a little warning where it will appear
            Particles.burst(self.x, self.anchor, count=8, colour=[(150, 70, 200), (90, 40, 130)], speed=(1, 3), life=(10, 18), size=(2, 3), gravity=0.05)
        if 0 <= age < self.active:
            height = min(100, 30 + 18 * age)              # it grows out
            self.hitbox.set_active(True)
            self.hitbox.zone.height = height
            self.hitbox.zone.x = self.x
            self.hitbox.zone.y = self.anchor - height / 2 if self.up else self.anchor + height / 2
            self.hitbox.check(targets, self.facing)
        else:
            self.hitbox.set_active(False)
        self.frame += 1
        if self.frame >= self.total_frames:
            self.end()


class TentacleBarrage(Move):
    """side + light: after a long wind-up, three tentacles lash out horizontally, one above the other."""
    START, ACTIVE, TOTAL = 18, 8, 42
    ROWS = (-22, 0, 22)

    def __init__(self, owner):
        super().__init__(owner)
        self.total_frames = self.TOTAL
        self.frame = 0
        shared = set()                                    # a victim is only hit by one of the three
        self.tents = []
        for dy in self.ROWS:
            hb = self.add_hitbox(Hitbox(owner, 20, 16, (30, dy), damage=5, kbx=11, kby=6, angle=20, stun=12))
            hb.already_hit = shared
            self.tents.append(hb)

    def update(self, targets):
        o = self.owner
        age = self.frame - self.START
        on = 0 <= age < self.ACTIVE
        length = min(150, 40 + 30 * age) if on else 0
        for hb in self.tents:                             # switch them ALL on before any of them checks (they share one "already hit" set)
            hb.set_active(on)
            if on:
                hb.zone.width = length
                hb.offset = (14 + length / 2, hb.offset[1])
            hb.place(o.x, o.y, self.facing)
        for hb in self.tents:
            hb.check(targets, self.facing)
        self.frame += 1
        if self.frame >= self.TOTAL:
            self.end()


class TentacleLift(Move):
    """up + heavy: a tentacle pushes up from beneath him and shoves him skyward (a recovery move)."""
    STARTUP, ACTIVE, RECOVERY = 5, 12, 8

    def __init__(self, owner):
        super().__init__(owner)
        self.total_frames = self.STARTUP + self.ACTIVE + self.RECOVERY
        self.frame = 0
        self.hitbox = self.add_hitbox(Hitbox(owner, 20, 20, (0, 24), damage=4, kbx=2, kby=8, angle=-80, stun=10))
        owner.lifts -= 1

    def update(self, targets):
        o = self.owner
        age = self.frame - self.STARTUP
        if age < 0:                                       # hang for a moment while it gathers
            o.y_velocity = 0
            o.NoGravTimer = 2
        elif age == 0:
            o.y_velocity = -13
            o.NoGravTimer = 6
        if 0 <= age < self.ACTIVE:
            height = min(80, 24 + 14 * age)
            self.hitbox.set_active(True)
            self.hitbox.zone.height = height
            self.hitbox.offset = (0, 14 + height / 2)     # hangs below his feet, growing downward
            self.hitbox.place(o.x, o.y, self.facing)
            self.hitbox.check(targets, self.facing)
        else:
            self.hitbox.set_active(False)
        self.frame += 1
        if self.frame >= self.total_frames:
            self.end()


class TentacleBall:
    """side + heavy: a ball that sails out; shortly after it's thrown, four tentacles strike out of it (up, down, left, right),
    hold for a moment, and retract. It goes through portals like any other projectile."""
    STRIKE_AT, EXTEND, HOLD, RETRACT = 14, 6, 8, 8
    LENGTH, THICK = 95, 14

    def __init__(self, owner, x, y, direction):
        self.owner, self.x, self.y, self.facing = owner, x, y, direction
        self.vx, self.vy = 11 * direction, -1
        self.t = 0
        self.done = False
        self.box = Box(18, 18, (150, 70, 200), x, y, border=3, border_colour="black", radius=9, fixed=False)
        self.body = Hitbox(owner, 18, 18, (0, 0), damage=3, kbx=5, kby=4, angle=25, stun=8)
        self.body.projectile = _NoReflect()               # a parry blocks it, but doesn't stun the Watcher
        self.body.set_active(True)
        shared = set()                                    # one victim, one tentacle hit
        self.arms = []                                    # (hitbox, direction x, direction y, facing used for knockback)
        for (dx, dy), face, angle, kbx, kby in [((1, 0), 1, 25, 9, 7), ((-1, 0), -1, 25, 9, 7), ((0, -1), 1, 90, 3, 11), ((0, 1), 1, -80, 3, 10)]:
            hb = Hitbox(owner, self.THICK, self.THICK, (0, 0), damage=6, kbx=kbx, kby=kby, angle=angle, stun=12)
            hb.projectile = _NoReflect()
            hb.already_hit = shared
            self.arms.append((hb, dx, dy, face))

    def reach(self):
        age = self.t - self.STRIKE_AT
        if age < 0:
            return 0
        if age < self.EXTEND:
            return self.LENGTH * (age + 1) / self.EXTEND
        if age < self.EXTEND + self.HOLD:
            return self.LENGTH
        return self.LENGTH * (1 - (age - self.EXTEND - self.HOLD + 1) / self.RETRACT)

    def update(self, targets):
        self.t += 1
        old_x, old_y = self.x, self.y
        self.vy = min(self.vy + 0.15, 8)
        self.vx *= 0.97
        nx = self.x + self.vx
        if level.is_solid(nx + math.copysign(9, self.vx), self.y):
            self.vx = 0
        else:
            self.x = nx
        ny = self.y + self.vy
        if level.is_solid(self.x, ny + (9 if self.vy > 0 else -9)):
            self.vy = 0
        else:
            self.y = ny
        portal_transit(self, old_x, old_y, lambda x, y: not level.is_solid(x, y))
        self.box.go_to(self.x, self.y)

        victims = [p for p in players if p is not self.owner]
        self.body.place(self.x, self.y, 1)
        self.body.check(victims, self.facing)

        reach = max(0, self.reach())
        for hb, dx, dy, face in self.arms:                # on first, THEN check (they share a hit set)
            hb.set_active(reach > 0)
            if reach > 0:
                hb.zone.width, hb.zone.height = (reach, self.THICK) if dx else (self.THICK, reach)
                hb.zone.x = self.x + dx * (9 + reach / 2)
                hb.zone.y = self.y + dy * (9 + reach / 2)
        for hb, dx, dy, face in self.arms:
            hb.check(victims, face)

        if self.t - self.STRIKE_AT >= self.EXTEND + self.HOLD + self.RETRACT:
            self.delete()

    def delete(self):
        if not self.done:
            self.done = True
            self.body.delete()
            for hb, _, _, _ in self.arms:
                hb.delete()
            self.box.delete()


#==========================================================
# CHARACTER: THE WATCHER
#==========================================================

class Watcher(Player):

    title = "The Watcher"
    blurb = "Portal magician. also fuck doorman"

    PORTAL_COOLDOWN = 45            # frames before a portal that was just retrieved can be placed again
    MAX_LIFTS = 1                   # up + heavy uses between touching the floor
    SEG_W, SEG_GAP = 40, 6

    def __init__(self, currentLevel, name, x=None, y=None, size=100, spawnIcon="p", controls=None, pad=None, pad_controls=None, slot=None):
        super().__init__(currentLevel, name, x, y, size, spawnIcon, controls, pad, pad_controls, slot)
        self.portals = PortalSet(self)
        portal_sets.append(self.portals)
        self.portal_cd = [0, 0]
        self.deny_timer = 0
        self.lifts = self.MAX_LIFTS
        self.effects = []
        self.tick = 0

    #---------------- portals ----------------

    def portal_spot(self):
        """Where a portal goes: in front of him, standing on the floor level of his feet, pulled back if a wall is in the way."""
        y = self.y + 13 - Portal.H / 2
        for dist in (90, 70, 50, 30, 0):
            x = self.x + dist * self.facing
            blocked = any(level.is_solid(x + dx, y + dy)
                          for dx in (-Portal.W / 2, 0, Portal.W / 2)
                          for dy in (-Portal.H / 2 + 2, 0, Portal.H / 2 - 2))
            if not blocked:
                return x, y
        return self.x, y

    def toggle_portal(self, index):
        if self.portals.slots[index] is not None:         # already out: retrieve it
            self.portals.remove(index)
            self.portal_cd[index] = self.PORTAL_COOLDOWN
        elif self.portal_cd[index] == 0:
            x, y = self.portal_spot()
            self.portals.place(index, x, y)
        else:
            self.deny_timer = 20

    def handle_movement(self, currentLevel):
        for i in range(2):
            if self.portal_cd[i] > 0: self.portal_cd[i] -= 1
        if self.deny_timer > 0: self.deny_timer -= 1
        if self.coyote_time == COYOTE_TIME:
            self.lifts = self.MAX_LIFTS
        return super().handle_movement(currentLevel)

    def update_attack(self, targets):
        super().update_attack(targets)
        self.tick += 1
        if self.tick % 10 == 0:
            self.portals.ambient()
        for effect in self.effects[:]:
            effect.update(targets)
            if effect.done:
                self.effects.remove(effect)

    def reset_state(self):
        super().reset_state()
        self.portals.clear()
        self.portal_cd = [0, 0]
        self.lifts = self.MAX_LIFTS

    def cleanup(self):
        for effect in self.effects:
            effect.delete()
        self.effects.clear()
        self.portals.clear()
        if self.portals in portal_sets:
            portal_sets.remove(self.portals)

    #---------------- HUD ----------------

    def make_hud(self, x, y):             # two boxes: portal 1 (blue) and portal 2 (orange)
        total = 2 * self.SEG_W + self.SEG_GAP
        left = x - total / 2 + self.SEG_W / 2
        self.segs = [Box(self.SEG_W, 10, PORTAL_COLOURS[i], left + i * (self.SEG_W + self.SEG_GAP), y, border=2, border_colour="black", radius=3)
                     for i in range(2)]
        self.label = Text("PORTALS", x, y - 17, 16, PLAYER_COLOURS[self.slot], outline=2)
        self.hud_sprites = self.segs + [self.label]

    def update_hud(self):
        for i, seg in enumerate(self.segs):
            if self.portals.slots[i] is not None:         # solid: this portal is out
                seg.colour, seg.alpha = PORTAL_COLOURS[i], 255
            elif self.portal_cd[i] > 0:                   # grey: just retrieved, recharging
                seg.colour, seg.alpha = (120, 120, 120), 160
            elif self.deny_timer > 0:
                seg.colour, seg.alpha = (230, 60, 60), 255
            else:                                         # faded: ready to place
                seg.colour, seg.alpha = PORTAL_COLOURS[i], 40

    #---------------- input ----------------

    def attackChecks(self, targets=()):
        if not self.actionable:
            return

        heavy = self.pressed("heavy")
        light = self.pressed("light")
        if not (heavy or light):
            return

        down = self.held("down")
        side = self.held("left") or self.held("right")
        up = self.held("up")

        if heavy:
            if down:
                self.portal_two()
            elif up:
                self.tentacle_lift()
            elif side:
                self.tentacle_ball()
            else:
                self.portal_one()
        else:
            if down:
                self.sky_tentacle()
            elif up:
                self.big_swipe()
            elif side:
                self.tentacle_barrage()
            else:
                # Neutral light: riposte if someone nearby was just parried, otherwise a tentacle out of the floor
                if not self.try_riposte(targets):
                    self.floor_tentacle()

    #---------------- HEAVY ----------------

    def _portal_move(self, index):
        if self.portals.slots[index] is None and self.portal_cd[index] > 0:
            self.deny_timer = 20                          # still recharging
            return
        def fire(owner):
            owner.toggle_portal(index)
        self.start_attack(Attack(self, 1, 1, (0, 0), startup=6, active=0, recovery=8,
                                 damage=0, knockbackx=0, knockbacky=0, angle=0, stun=0, on_fire=fire))

    def portal_one(self):     # neutral + heavy: place portal 1, or retrieve it if it's already out
        self._portal_move(0)

    def portal_two(self):     # down + heavy: place portal 2, or retrieve it if it's already out
        self._portal_move(1)

    def tentacle_lift(self):  # up + heavy: a tentacle under him shoves him upward (once per floor touch)
        if self.lifts > 0:
            self.start_attack(TentacleLift(self))

    def tentacle_ball(self):  # side + heavy: throw a ball that sprouts four tentacles shortly after
        def fire(owner):
            owner.effects.append(TentacleBall(owner, owner.x + 20 * owner.facing, owner.y - 4, owner.facing))
        self.start_attack(Attack(self, 1, 1, (0, 0), startup=12, active=0, recovery=16,
                                 damage=0, knockbackx=0, knockbacky=0, angle=0, stun=0, on_fire=fire))

    #---------------- LIGHT ----------------

    def big_swipe(self):      # up + light: a big box a little in front of and above him, launches upward
        self.start_attack(Attack(self, width=90, height=110, offset=(25, -55), startup=8, active=5, recovery=12,
                                 damage=7, knockbackx=4, knockbacky=13, angle=90, stun=14))

    def tentacle_barrage(self):   # side + light: three tentacles lash out sideways after a long startup
        self.start_attack(TentacleBarrage(self))

    def floor_tentacle(self):     # neutral + light: a tentacle bursts out of the floor just ahead, spikes upward
        self.start_attack(SpikeTentacle(self, up=True))

    def sky_tentacle(self):       # down + light: a tentacle from thin air above and ahead, spikes downward
        self.start_attack(SpikeTentacle(self, up=False))

#==========================================================
# CHARACTER: SION - special moves (multi-stage, so they get their own classes)
#==========================================================

#---------------- Sion tuning ----------------
SION_MAX_PAIN = 200          # the most "Pain Trade" damage bonus he can hold. A full bar = the bat jumps
SION_HEAL_BUDGET = 50        # the most damage he can heal away per stock (stops infinite healing)
SION_POWER_PER_PAIN = 0.02   # each point of bonus = +1% damage on everything he hits (full bar = x2)
SION_BAT_JUMPS = 4           # air jumps he has while the bar is full
SION_MAX_RISES = 1           # up + heavy uses between touching the floor
SION_BLOOD = (170, 0, 50)    # the colour of his hitboxes


def pain_colour(amount):
    """White at 0 (and for healing), getting redder the more damage is being traded for."""
    if amount <= 0:
        return (255, 255, 255)
    fade = 1 - min(1, amount / SION_MAX_PAIN)
    return (255, int(255 * fade), int(255 * fade))


class PainTrade(Move):
    """Neutral + heavy. A number floats above him: left / right changes it (hold to go faster), heavy again locks it in,
    parry cancels. Positive = he takes that much damage and gains attack power. Negative = he heals (limited).
    Being hit while choosing cancels it with nothing applied."""
    TIMEOUT = 360             # frames before it cancels itself

    def __init__(self, owner):
        super().__init__(owner)
        self.age = 0
        self.amount = 0
        self.hold = 0
        self.number = Text("0", owner.x, owner.y - 66, 30, "white", outline=3, fixed=False)

    def update(self, targets):
        o = self.owner
        self.age += 1
        o.x_velocity = 0
        if o.coyote_time != COYOTE_TIME:          # in the air he hangs still while he decides
            o.y_velocity = 0
            o.NoGravTimer = 2

        direction = (1 if o.held("right") else 0) - (1 if o.held("left") else 0)
        step = 0
        if direction == 0:
            self.hold = 0
        else:
            self.hold += 1
            if self.hold == 1:
                step = 1                                          # a tap = 1
            elif self.hold > 30 and self.hold % 3 == 0:
                step = 5                                          # held a while = fast
            elif self.hold > 10 and self.hold % 3 == 0:
                step = 1                                          # held = steady
        low, high = o.pain_limits()
        self.amount = max(low, min(high, self.amount + direction * step))

        self.number.text = f"+{self.amount}" if self.amount > 0 else str(self.amount)
        self.number.colour = pain_colour(self.amount)
        self.number.go_to(o.x, o.y - 66)

        if self.age > 1 and o.pressed("heavy"):       # (age > 1 so the press that started the move doesn't also lock it)
            o.apply_pain(self.amount)
            self.end(recovery=14)
        elif o.pressed("parry") or self.age >= self.TIMEOUT:
            self.end(recovery=8)                      # cancelled, nothing applied

    def cancel(self):
        if self.number is not None:
            self.number.delete()
            self.number = None
            self.owner.NoGravTimer = 0
        super().cancel()


class BatTeleport(Move):
    """Side + heavy. He vanishes, three bats appear on the path ahead, then he reappears at the end of it."""
    STARTUP = 8
    VANISHED = 10
    DISTANCE = 230
    BATS = 3

    def __init__(self, owner):
        super().__init__(owner)
        self.frame = 0
        self.start = (owner.x, owner.y)
        self.distance = 0
        shared = set()                    # the same set for all three, so one victim is only hit once
        self.bats = []
        for i in range(self.BATS):
            bat = self.add_hitbox(Hitbox(owner, 44, 36, (0, 0), damage=4, kbx=5, kby=6, angle=45, stun=12, colour=SION_BLOOD))
            bat.already_hit = shared
            self.bats.append(bat)

    def update(self, targets):
        o = self.owner
        self.frame += 1
        o.hold_still()

        if self.frame == self.STARTUP:                # vanish, and the bats appear along the route
            o.vanished = True
            self.distance = self.find_distance()
            for i, bat in enumerate(self.bats):
                bat.offset = (self.distance * (i + 1) / (self.BATS + 1), -4 if i % 2 else 4)
                bat.set_active(True)
                bat.place(self.start[0], self.start[1], self.facing)
                Particles.burst(bat.zone.x, bat.zone.y, count=10, colour=[(60, 0, 20), SION_BLOOD, (20, 20, 20)],
                                speed=(1, 4), life=(10, 20), size=(2, 4), gravity=0, drag=0.95)
        elif self.frame > self.STARTUP:
            for bat in self.bats:
                bat.check(targets, self.facing)

        if self.frame >= self.STARTUP + self.VANISHED:   # reappear at the end of the path
            o.go_to(self.start[0] + self.distance * self.facing, self.start[1])
            o.vanished = False
            Particles.burst(o.x, o.y, count=14, colour=[(60, 0, 20), SION_BLOOD], speed=(2, 6),
                            life=(10, 22), size=(2, 4), gravity=0, drag=0.94)
            self.end(recovery=16)

    def find_distance(self):
        """The furthest he can go (up to DISTANCE) without ending up inside a wall."""
        o = self.owner
        for dist in range(self.DISTANCE, 0, -10):
            if player_fits(o, o.x + dist * self.facing, o.y):
                return dist
        return 0

    def cancel(self):
        self.owner.vanished = False                   # hit while vanished: he's back, where he started
        self.owner.NoGravTimer = 0
        super().cancel()


class ShadowRise(Move):
    """Up + heavy. A hitbox forms above him and gravity stops pulling on him. A moment later he teleports into it."""
    HEIGHT = 300
    DELAY = 20

    def __init__(self, owner):
        super().__init__(owner)
        self.frame = 0
        self.spot = (owner.x, owner.y - self.HEIGHT)
        self.box = self.add_hitbox(Hitbox(owner, 70, 70, (0, 0), damage=7, kbx=4, kby=12, angle=90, stun=16, colour=SION_BLOOD))
        self.box.place(self.spot[0], self.spot[1], 1)
        self.box.set_active(True)
        owner.rises -= 1
        owner.hold_still()

    def update(self, targets):
        o = self.owner
        self.frame += 1
        o.hold_still()
        self.box.check(targets, self.facing)

        if self.frame >= self.DELAY:
            for rise in range(self.HEIGHT, 0, -10):       # as high as he fits (a ceiling can stop him short)
                if player_fits(o, o.x, o.y - rise):
                    o.go_to(o.x, o.y - rise)
                    break
            Particles.burst(o.x, o.y, count=14, colour=[(60, 0, 20), SION_BLOOD], speed=(2, 6),
                            life=(10, 22), size=(2, 4), gravity=0, drag=0.94)
            self.end(recovery=10)

    def cancel(self):
        self.owner.NoGravTimer = 0
        super().cancel()


class SlashLine:
    """What his down light leaves behind: a moment after the hit, a big thin sideways hitbox appears where the victim is.
    Lives in Sion.effects, so it still goes off even though the move that made it has finished."""
    DELAY = 14
    ACTIVE = 6

    def __init__(self, owner, victim):
        self.owner, self.victim = owner, victim
        self.facing = owner.facing
        self.timer = self.DELAY
        self.life = self.ACTIVE
        self.hitbox = None
        self.done = False

    def update(self, targets):
        if self.hitbox is None:
            self.timer -= 1
            if self.timer > 0:
                return
            self.hitbox = Hitbox(self.owner, 420, 14, (0, 0), damage=7, kbx=5, kby=11, angle=75, stun=20, colour=SION_BLOOD)
            self.hitbox.place(self.victim.x, self.victim.y, self.facing)
            self.hitbox.set_active(True)
            Particles.burst(self.victim.x, self.victim.y, count=16, colour=[SION_BLOOD, (255, 255, 255)],
                            direction=90, spread=10, speed=(6, 12), life=(6, 12), size=(2, 3), gravity=0, drag=0.9)
            return
        self.hitbox.check(targets, self.facing)
        self.life -= 1
        if self.life <= 0:
            self.delete()

    def delete(self):
        if self.hitbox is not None:
            self.hitbox.delete()
            self.hitbox = None
        self.done = True


class Sion(Player):

    title = "Sion"
    blurb = "Vampire. Pays in blood for power."

    BAR_WIDTH = 100

    # Lets the match hide him while he's vanished (the match code shows every player again each frame, so this overrides that)
    vanished = False
    _shown = True

    @property
    def visible(self):
        return self._shown and not self.vanished

    @visible.setter
    def visible(self, value):
        self._shown = value

    def __init__(self, currentLevel, name, x=None, y=None, size=100, spawnIcon="p", controls=None, pad=None, pad_controls=None, slot=None):
        super().__init__(currentLevel, name, x, y, size, spawnIcon, controls, pad, pad_controls, slot)
        self.pain = 0                         # the Pain Trade damage bonus he currently holds (0 - SION_MAX_PAIN)
        self.heal_left = SION_HEAL_BUDGET     # how much more he is allowed to heal this stock
        self.rises = SION_MAX_RISES
        self.effects = []

    #---------------- Pain Trade ----------------

    @property
    def power(self):                          # read by Hitbox.hit: multiplies everything he deals
        return 1 + self.pain * SION_POWER_PER_PAIN

    def pain_limits(self):
        """(lowest, highest) number he can pick: he can't heal more than he has damage / budget, or add more than fits in the bar."""
        return -int(min(self.heal_left, self.health)), int(SION_MAX_PAIN - self.pain)

    def apply_pain(self, amount):
        if amount > 0:
            self.health += amount
            self.pain = min(SION_MAX_PAIN, self.pain + amount)
            Particles.burst(self.x, self.y, count=10 + amount // 3, colour=BLOOD, speed=(2, 7),
                            life=(15, 30), size=(2, 4), gravity=0.1)
            if self.pain >= SION_MAX_PAIN:    # full bar: bat form, extra jumps
                self.max_jump_charges = SION_BAT_JUMPS
                self.jump_charges = SION_BAT_JUMPS
        elif amount < 0:
            healed = min(-amount, self.health, self.heal_left)
            self.health -= healed
            self.heal_left -= healed
            Particles.burst(self.x, self.y, count=10 + int(healed) // 3, colour=[(255, 255, 255), (255, 190, 190)],
                            speed=(1, 4), life=(15, 30), size=(2, 4), gravity=-0.05)

    def hold_still(self):
        self.x_velocity = 0
        self.y_velocity = 0
        self.NoGravTimer = 2

    #---------------- housekeeping ----------------

    def handle_movement(self, currentLevel):
        if self.coyote_time == COYOTE_TIME:
            self.rises = SION_MAX_RISES
        return super().handle_movement(currentLevel)

    def update_attack(self, targets):
        super().update_attack(targets)
        for effect in self.effects[:]:
            effect.update(targets)
            if effect.done:
                self.effects.remove(effect)

    def clear_effects(self):
        for effect in self.effects:
            effect.delete()
        self.effects.clear()

    def reset_state(self):
        self.vanished = False
        self.pain = 0
        self.heal_left = SION_HEAL_BUDGET
        self.rises = SION_MAX_RISES
        self.max_jump_charges = 1                 # before super(), which refills jumps up to this
        self.clear_effects()
        super().reset_state()

    def cleanup(self):
        self.clear_effects()
        self.vanished = False

    #---------------- HUD ----------------

    def make_hud(self, x, y):             # a bar of the damage bonus, with a lighter section previewing the number he's choosing
        self.bar_left = x - self.BAR_WIDTH / 2
        back = Box(self.BAR_WIDTH, 10, "black", x, y, alpha=120, border=2, border_colour="black")
        self.fill = Box(1, 10, SION_BLOOD, self.bar_left, y)
        self.preview = Box(1, 10, "white", self.bar_left, y, alpha=0)
        self.label = Text("PAIN", x, y - 17, 16, PLAYER_COLOURS[self.slot], outline=2)
        self.hud_sprites = [back, self.fill, self.preview, self.label]

    def _set_bar(self, box, start, end):  # start / end are 0-1 fractions of the bar; sprites sit by their centre
        width = self.BAR_WIDTH * (end - start)
        if width < 1:
            box.alpha = 0
            return
        box.width = width
        box.x = self.bar_left + self.BAR_WIDTH * start + width / 2

    def update_hud(self):
        frac = self.pain / SION_MAX_PAIN
        self.fill.alpha = 255
        self.fill.colour = (int(130 + 125 * frac), int(20 * (1 - frac)), int(40 * (1 - frac)))
        self._set_bar(self.fill, 0, frac)
        move = self.current_attack
        pending = move.amount if isinstance(move, PainTrade) and move.amount > 0 else 0
        self.preview.alpha = 150
        self._set_bar(self.preview, frac, frac + pending / SION_MAX_PAIN)
        self.label.text = "PAIN  MAX" if self.pain >= SION_MAX_PAIN else f"PAIN  +{int(self.pain)}%"

    #---------------- input ----------------

    def attackChecks(self, targets=()):
        if not self.actionable:
            return

        heavy = self.pressed("heavy")
        light = self.pressed("light")
        if not (heavy or light):
            return

        grounded = self.coyote_time == COYOTE_TIME
        down = self.held("down")
        side = self.held("left") or self.held("right")
        up = self.held("up")

        if heavy:
            if down:
                self.blood_fountain()
            elif up:
                if self.rises > 0 or grounded:
                    self.shadow_rise()
            elif side:
                self.bat_teleport()
            else:
                self.pain_trade()
        else:
            if down:
                self.low_slice()
            elif up:
                self.upper_slice()
            elif side:
                self.slash()
            else:
                # Neutral light: riposte if someone nearby was just parried, otherwise the pulling slash
                if not self.try_riposte(targets):
                    self.hook_slash()

    #---------------- HEAVY ----------------

    def pain_trade(self):     # neutral + heavy: pick a number, press heavy again to lock it in
        self.start_attack(PainTrade(self))

    def bat_teleport(self):   # side + heavy: vanish, three bats on the path, reappear ahead
        self.start_attack(BatTeleport(self))

    def blood_fountain(self): # down + heavy: six blood drops spurt up and out, then rain down. Long recovery
        def fire(owner):
            for side in (1, -1):
                for angle, speed in ((50, 8), (68, 9), (84, 9)):
                    drop = Hitbox(owner, 16, 16, (0, 0), damage=4, kbx=5, kby=5, angle=20, stun=10, colour=SION_BLOOD)
                    Projectile(owner.x, owner.y - 10, owner.facing * side, speed=speed, lifetime=90,
                               hitbox=drop, angle=angle, gravity=0.35)
            Particles.burst(owner.x, owner.y - 10, count=18, colour=BLOOD, direction=0, spread=70,
                            speed=(4, 9), life=(15, 30), size=(2, 4), gravity=0.3)
        self.start_attack(Attack(self, 1, 1, (0, 0), startup=10, active=0, recovery=45,
                                 damage=0, knockbackx=0, knockbacky=0, angle=0, stun=0, on_fire=fire))

    def shadow_rise(self):    # up + heavy: hitbox above him, no gravity, then he teleports into it
        self.start_attack(ShadowRise(self))

    #---------------- LIGHT ----------------

    def hook_slash(self):     # neutral + light: a slash out in front of him that drags the victim in towards him
        self.start_attack(Attack(self, width=50, height=45, offset=(62, 0), startup=6, active=4, recovery=10,
                                 damage=4, knockbackx=7, knockbacky=4, angle=30, stun=12, mode="pull"))

    def slash(self):          # side + light: a normal side slash
        self.start_attack(Attack(self, width=60, height=40, offset=(40, 0), startup=4, active=4, recovery=9,
                                 damage=6, knockbackx=11, knockbacky=6, angle=25, stun=10))

    def low_slice(self):      # down + light: a low slice ahead. If it connects, a wide thin hitbox appears on the victim a moment later
        attack = Attack(self, width=50, height=34, offset=(48, 8), startup=7, active=4, recovery=12,
                        damage=4, knockbackx=2, knockbacky=2, angle=20, stun=22)
        attack.hitbox.on_hit = lambda victim: self.effects.append(SlashLine(self, victim))
        self.start_attack(attack)

    def upper_slice(self):    # up + light: a simple slice upward
        self.start_attack(Attack(self, width=55, height=70, offset=(15, -35), startup=4, active=4, recovery=9,
                                 damage=6, knockbackx=5, knockbacky=11, angle=90, stun=12))


#All character list

CHARACTERS = {
    "Ven": Ven,
    "Rend": Rend,
    "Cleaning Lady": CleaningLady,
    "Cap'n Rex": CaptnRex,
    "Bombhead": Bombhead,
    "Angellica": Angellica,
    "The Watcher" : Watcher,
    "Sion": Sion
}

#==========================================================
# RESPAWNING + CAMERA
#==========================================================


def death_effects(player):
    # Added a fix cas particales wouldnt be visible if u died off the bottom
    death_x = min(player.x, Stage.camera.x + Screen.width / 2)
    death_y = min(player.y, Stage.camera.y + Screen.height / 2)

    print(f"Death particles triggered at ({death_x}, {death_y})")

    # Main Purple burst.
    Particles.burst(
        death_x, death_y,
        count=70,
        colour=(100, 50, 255),
        speed=(3, 12),
        life=(30, 60),
        size=(3, 7),
        gravity=0.15,
        drag=0.98
    )

    # Bright Pink sparks.
    Particles.burst(
        death_x, death_y,
        count=35,
        colour=(255, 230, 230),
        speed=(4, 10),
        life=(20, 45),
        size=(2, 5),
        gravity=0.1,
        drag=0.98
    )

    # Smaller Purple particles.
    Particles.burst(
        death_x, death_y,
        count=20,
        colour=(255, 0, 255),
        speed=(2, 7),
        life=(25, 50),
        size=(2, 4),
        gravity=0.2,
        drag=0.97
    )

    Sound.play("Death Booble")
    Sound.play("Death sfx")


def respawn(player):
    death_effects(player)
    # Respawn the player.
    px, py = level.find(player.spawnIcon)[0]
    print(f"Respawn at spawn '{player.spawnIcon}', damage was {player.health}")

    player.reset_state()
    player.go_to(px, py)

    player.health = 0

    if getattr(player, "stats", None) is not None:
        player.stats.invuln = match.rules.shield_frames      # respawn shield
        player.stats.last_attacker = None

    for other in players:                   # lets characters react to a death (Bombhead's fuse refills)
        if other is not player:
            other.on_enemy_death(player)



class CameraFocus:
    #Camera in the middle of all players
    def __init__(self):
        self.x = 0
        self.y = 0

    def track(self, players):
        if not players:
            return
        self.x = sum(p.x for p in players) / len(players)
        self.y = sum(p.y for p in players) / len(players)

#================================================================================================================================#
#                                                           ACTUAL GAME                                                          #
#================================================================================================================================#
#SETUP
MATCH_BG = Screen.background            # the colour fights are played on (the menus use their own)

players = []                            # fighters still IN the match (eliminated ones are removed)
hud = {}                                # slot -> damage counter, along the bottom of the screen
stock_hud = {}                          # slot -> "STOCKS 3" / "SCORE 2" under the damage counter
tags = {}                               # slot -> the little "P(whatever)" floating above each player's head
crowns = {}                             # slot -> the crown above whoever won the last match
all_stats = []                          # every fighter's stats, including eliminated ones
camera_zone = None
focus = None
ui = SimpleNamespace(feed=None, banner=None, clock=None)
match = SimpleNamespace(rules=ms.Rules(), sd=False, out_counter=0, finishing=0, winners=[])
training = SimpleNamespace(active=False, dummy=None, hud=[],
                           behaviour=DUMMY_BEHAVIOURS[0], reset_damage=0, auto_reset=True,      # (these three are remembered between sessions)
                           combo=0, combo_damage=0.0, last_hit=0.0, best=0, since_hit=999)

def others(player):                     # everyone a player's attacks can hit
    return [p for p in players if p is not player]

def start_match(entries, rules, map_index=0, online=None):
    """entries comes straight from character_select(). online = None for a local match, or {'seed':..., 'names': {slot: name}}"""
    global players, hud, stock_hud, tags, crowns, all_stats, camera_zone, focus
    Screen.background = MATCH_BG
    Particles.clear()
    load_level(map_index + 1, allLevels, allLegends)
    match.rules, match.sd, match.out_counter, match.finishing, match.winners = rules, False, 0, 0, []
    ms.State.frame = 0
    sim_rng.seed(online["seed"] if online else None)
    names = online["names"] if online else {}

    players, hud, stock_hud, tags, crowns, all_stats = [], {}, {}, {}, {}, []
    for entry in entries:
        slot, device = entry["slot"], entry.get("device")
        if entry.get("dummy"):                          # training: the practice partner
            player = Dummy(level, "player", 0, 0, spawnIcon=str(slot + 1), slot=slot)
            training.dummy = player
        else:
            if online:
                controls, pad = None, None                  # buttons come from the network instead
            else:
                controls, pad = (settings.keyboard[slot], None) if device[0] == "profile" else (None, device[1])
            player = CHARACTERS[entry["character"]](
                level, "player", 0, 0,
                spawnIcon=str(slot + 1),
                controls=controls,
                pad=pad,
                pad_controls=settings.pad[slot],
                slot=slot
            )
        if online:
            player.net = NetInput()
        player.facing = 1 if player.x < level.width / 2 else -1        # everyone starts looking towards the middle
        player.health = rules.start_damage
        player.stats = ms.PlayerStats(slot, str(entry["character"]), PLAYER_COLOURS[slot], rules.stocks if rules.is_stock else 0)
        player.stats.invuln = 0
        players.append(player)
        all_stats.append(player.stats)

    for i, player in enumerate(players):
        slot = player.slot
        colour = PLAYER_COLOURS[slot]
        hud_x = Screen.width * (i + 1) / (len(players) + 1)
        hud[slot] = Text("", hud_x, Screen.height - 40, 44, colour, outline=3)
        stock_hud[slot] = Text("", hud_x, Screen.height - 12, 22, colour, outline=2)
        player.make_hud(hud_x, Screen.height - 85)          # the character's own extra UI, just above the damage counter
        tags[slot] = Text(names.get(slot, "DUMMY" if isinstance(player, Dummy) else f"P{slot + 1}"), player.x, player.y - 28, 22, colour, outline=2, fixed=False)
        if not online and ms.records.crown_slot == slot and not isinstance(player, Dummy):    # last match's winner wears the crown
            crowns[slot] = ms.Crown(player.x, player.y - 56, 30, fixed=False)

    ui.feed, ui.banner, ui.clock = ms.KillFeed(), ms.Banner(), ms.MatchClock()
    focus = CameraFocus()
    focus.track(players)
    camera_zone = level.zone()
    Stage.camera.go_to(focus.x, focus.y)
    Stage.camera.follow(focus, 100)
    Stage.camera.limit_to(camera_zone)
    Screen.update()                     # one frame to let the button that started the match pass, otherwise it would also pause / jump

def end_match():
    """Throws the whole fight away so the menus (and the next fight) start clean."""
    global level, players, hud, stock_hud, tags, crowns, camera_zone
    for player in players:
        player.cancel_attack()
        player.cleanup()
        player.delete_hud()
        player.delete()
    for proj in projectiles[:]:
        proj.hitbox.delete()
    projectiles.clear()
    for sprite in list(hud.values()) + list(stock_hud.values()) + list(tags.values()) + list(crowns.values()):
        sprite.delete()
    for helper in (ui.feed, ui.banner, ui.clock):
        if helper is not None:
            helper.delete()
    ui.feed = ui.banner = ui.clock = None
    for sprite in training.hud:
        sprite.delete()
    training.hud, training.active, training.dummy = [], False, None
    players, hud, stock_hud, tags, crowns = [], {}, {}, {}, {}
    Stage.camera.reset()
    camera_zone.delete()
    level.delete()
    del level                           # so load_level knows there is no old level to delete next time
    Particles.clear()
    Screen.fps = 60

def pause_requested():
    if Keyboard.pressed("escape"):
        return True
    return any(p.pad is not None and Gamepad.pressed(p.pad, "start") for p in players)

#---------------- lives / knockouts ----------------

def stock_rules():
    """Stocks matter in Stock mode, and in Sudden Death (which is always one life each)."""
    return match.rules.is_stock or match.sd

def eliminate(player):
    """Out of lives: the fighter leaves the match (their stats stay for the results screen)."""
    player.stats.final_health = player.health
    player.stats.out_order = match.out_counter
    death_effects(player)
    player.cancel_attack()
    player.cleanup()
    player.delete_hud()
    player.delete()
    players.remove(player)
    for other in players:
        other.on_enemy_death(player)
    slot = player.slot
    hud[slot].text = f"P{slot + 1}  OUT"
    hud[slot].colour = (120, 120, 120)
    stock_hud[slot].text = ""
    tags[slot].hide()
    if slot in crowns:
        crowns[slot].hide()

def begin_sudden_death(contenders):
    match.sd = True
    for p in contenders:
        p.stats.stocks = 1
        p.health = 300
        respawn(p)
    ui.banner.show("SUDDEN DEATH!", 150, (255, 70, 70))
    ui.feed.add("SUDDEN DEATH - one life each, 300% damage", (255, 90, 90))

def finish_match(winner_slots):
    match.finishing = 100               # a short slow motion "GAME!" before the results
    match.winners = winner_slots
    Screen.fps = 30
    if len(winner_slots) == 1:
        ui.banner.show("GAME!", 100, ms.GOLD)
    else:
        ui.banner.show("DRAW!", 100, "white")

def process_kos(ko_list):
    if training.active:                                 # training: no stocks, no stats, no results. Just come back.
        for p in ko_list:
            respawn(p)
            p.health = training.reset_damage if p is training.dummy else 0
        return
    doomed = []
    for p in ko_list:
        for message, colour in ms.credit_ko(p.stats, stock_rules(), all_stats):
            ui.feed.add(message, colour)
        if stock_rules() and p.stats.stocks <= 0:
            doomed.append(p)
        else:
            respawn(p)
    if not doomed:
        return
    survivors = [p for p in players if p not in doomed]
    if not survivors:                                   # everybody went out on the same frame
        if match.rules.sudden_death:
            begin_sudden_death(doomed)
        else:
            for p in doomed:
                eliminate(p)
            finish_match([p.stats.slot for p in doomed])
        return
    for p in doomed:
        eliminate(p)
    match.out_counter += 1
    if len(players) == 1:
        finish_match([players[0].stats.slot])

def check_time_up(frame):
    limit = match.rules.time_limit_frames
    if not limit or match.sd or frame < limit:
        return
    front = ms.leaders(players, stock_rules())
    if len(front) == 1:
        finish_match([front[0].stats.slot])
    elif match.rules.sudden_death:
        for p in [p for p in players if p not in front]:
            eliminate(p)
        match.out_counter += 1
        begin_sudden_death(front)
    else:
        finish_match([p.stats.slot for p in front])

def build_result(frame):
    for p in players:
        p.stats.final_health = p.health
    ordered = ms.rank(all_stats, match.winners, match.rules.is_stock or match.sd)
    return ms.MatchResult(ordered, match.winners, match.rules, frame, match.sd)

#---------------- the match ----------------

def step_game(frame, fighting):
    """One frame of the actual fight."""
    for p in players:
        before = (p.x, p.y)
        p.handle_movement(level)
        portal_transit(p, before[0], before[1], lambda x, y, p=p: player_fits(p, x, y))

    for p in players:                   # everyone decides their attack first
        p.attackChecks(others(p))
    for p in players:                   # then every move advances, so its fair (looking at you tristan)
        p.update_attack(others(p))

    for proj in projectiles[:]:         # copy, since update() removes finished projectiles
        proj.update([p for p in players if p is not proj.owner], level)

    ko_list = [p for p in players if p.should_die() or level.touching(p, "Z") or level.touching(p, "Q")]  #TODO: Death Code #ALSO "Q" is used so that the Capt'n barrel isnt killed by the top blastzone
    if match.finishing:                 # the match is already decided: just put people back, no stats
        for p in ko_list:
            respawn(p)
    elif ko_list:
        process_kos(ko_list)

def update_ui(frame):
    for p in players:
        s = p.stats
        if s.invuln > 0:                # respawn shield: blink, count down
            s.invuln -= 1
            p.visible = s.invuln == 0 or (s.invuln // 4) % 2 == 0
        else:
            p.visible = True
        hud[p.slot].text = f"P{p.slot + 1}  {int(p.health)}%"
        if stock_rules():
            stock_hud[p.slot].text = f"STOCKS  {s.stocks}"
            stock_hud[p.slot].colour = (255, 70, 70) if s.stocks == 1 else PLAYER_COLOURS[p.slot]
        else:
            stock_hud[p.slot].text = f"SCORE  {s.score}"
        p.update_hud()
        tags[p.slot].go_to(p.x, p.y - 28)
        if p.slot in crowns:
            crowns[p.slot].go_to(p.x, p.y - 58)
    ui.feed.update()
    ui.banner.update()
    ui.clock.update(frame, match.rules.time_limit_frames, match.sd)
    if players:
        focus.track(players)

def run_match():
    """Plays one match. Returns a MatchResult, or None if the players quit from the pause menu (or closed the window)."""
    frame = 0
    ms.State.frame = 0
    update_ui(0)
    ms.countdown(lambda: update_ui(0))          # 3 - 2 - 1 - FIGHT!
    try:
        while Screen.running:
            if pause_requested():
                if pause_menu() == "quit":
                    return None
                Screen.update()         # same again: the button that closed the pause menu mustn't also jump or attack

            step_game(frame, not match.finishing)
            frame += 1
            ms.State.frame = frame
            if not match.finishing:
                check_time_up(frame)
            update_ui(frame)
            Screen.update()

            if match.finishing:
                match.finishing -= 1
                if match.finishing == 0:
                    return build_result(frame)
        return None
    finally:
        Screen.fps = 60
        for p in players:
            p.visible = True


#==========================================================
# ONLINE PLAY
#   Lockstep: every computer runs this whole simulation, and only the BUTTONS cross the internet (see Network.py).
#   For that to work the simulation must do exactly the same thing everywhere, so:
#     - anything random that affects the fight uses sim_rng (seeded the same for everyone), never random_float()
#     - every player reads buttons through player.net (a NetInput) instead of the keyboard
#   A fingerprint of the fight is compared every half second; if two computers ever disagree, the match is stopped.
#==========================================================

class NetInput:
    """One player's buttons for the current frame, as bit masks (bit i = ACTIONS[i])."""
    def __init__(self):
        self.h = 0              # held
        self.p = 0              # pressed this frame

    def held(self, action):
        return bool(self.h >> ACTIONS.index(action) & 1)

    def pressed(self, action):
        return bool(self.p >> ACTIONS.index(action) & 1)

def sample_local_input():
    """This computer's buttons right now. Online you always use your Player 1 keyboard layout + your first controller."""
    held = pressed = 0
    keys, layout = settings.keyboard[0], settings.pad[0]
    pad = 0 if Gamepad.count > 0 else None
    for bit, action in enumerate(ACTIONS):
        key = keys.get(action)
        if key:
            if Keyboard.held(key): held |= 1 << bit
            if Keyboard.pressed(key): pressed |= 1 << bit
        button = layout.get(action)
        if pad is not None and button is not None:
            if Gamepad.held(pad, button): held |= 1 << bit
            if Gamepad.pressed(pad, button): pressed |= 1 << bit
    return held, pressed

def state_hash():
    rows = [(p.slot, round(p.x, 2), round(p.y, 2), round(p.health, 2), p.stats.stocks) for p in players]
    return zlib.crc32(repr(rows).encode())

def forfeit(slot, name):
    """Somebody left the match: they are out, and if only one fighter is left that fighter wins."""
    player = next((p for p in players if p.slot == slot), None)
    if player is None or match.finishing:
        return
    player.stats.stocks = 0
    ui.feed.add(f"{name} left the match", (255, 110, 110))
    eliminate(player)
    match.out_counter += 1
    if len(players) == 1:
        finish_match([players[0].stats.slot])

def wait_for_bundle(client, frame, waiting):
    """Blocks until everybody's buttons for this frame have arrived. Returns None if the connection died / timed out."""
    started = time.time()
    while Screen.running:
        bundle = client.take_bundle(frame)
        if bundle is not None:
            waiting.hide()
            return bundle
        if not client.connected or client.desync_frame is not None:
            return None
        waited = time.time() - started
        if waited > Network.WAIT_TIMEOUT:
            return None
        Screen._read_events()                   # keep the window alive (and keep any button presses) without advancing the game
        if waited > 0.3:
            waiting.show()
            Screen._show_frame(False)
        else:
            time.sleep(0.001)
    return None

def run_online_match(client, delay, names):
    """Plays one online match. Returns (outcome, MatchResult or None). Outcome: done / left / lost / desync / quit."""
    frame = 0
    ms.State.frame = 0
    client.clear_match_state()
    for f in range(delay):                      # nobody can have pressed anything yet: the first frames are neutral
        client.send_input(f, 0, 0)
    update_ui(0)
    ms.countdown(lambda: update_ui(0))
    waiting = Text("Waiting for other players...", Screen.width / 2, 110, 34, "white", outline=3)
    waiting.hide()
    leave_armed = 0
    try:
        while Screen.running:
            held, pressed = sample_local_input()
            client.send_input(frame + delay, held, pressed)

            if Keyboard.pressed("escape") or Gamepad.pressed(0, "start"):     # no pausing online, so Esc twice leaves instead
                if leave_armed:
                    client.send({"t": "leave_match"})
                    return "left", None
                leave_armed = 240
                ui.banner.show("Press ESC again to leave the match", 150, (255, 120, 120))
            if leave_armed:
                leave_armed -= 1

            bundle = wait_for_bundle(client, frame, waiting)
            if bundle is None:
                if client.desync_frame is not None:
                    return "desync", None
                return ("lost" if not client.connected or Screen.running else "quit"), None
            for p in players:
                row = bundle["i"].get(str(p.slot), (0, 0))
                p.net.h, p.net.p = row[0], row[1]
            for slot in bundle.get("left", []):
                forfeit(slot, names.get(slot, f"P{slot + 1}"))

            step_game(frame, not match.finishing)
            frame += 1
            ms.State.frame = frame
            if not match.finishing:
                check_time_up(frame)
            if frame % 30 == 0:
                client.send({"t": "hash", "f": frame, "h": state_hash()})
            update_ui(frame)
            Screen.update()

            if match.finishing:
                match.finishing -= 1
                if match.finishing == 0:
                    return "done", build_result(frame)
        return "quit", None
    finally:
        Screen.fps = 60
        waiting.delete()
        for p in players:
            p.visible = True

def play_online_match(client, payload):
    """Called by the online lobby when the host starts a match. Returns True if this player wants a rematch."""
    online_rules = ms.Rules()
    online_rules.load(payload["rules"])
    entries = [{"slot": e["slot"], "character": e["character"]} for e in payload["entries"]]
    names = {e["slot"]: e["name"] for e in payload["entries"]}
    map_index = payload["map"] if 0 <= payload["map"] < len(MAPS) else 0
    start_match(entries, online_rules, map_index, online={"seed": payload["seed"], "names": names})
    outcome, result = run_online_match(client, payload["delay"], names)
    end_match()
    Screen.background = MENU_BG
    if outcome == "done":
        client.send({"t": "match_done"})
        result.map_name = MAPS[map_index]["name"]
        return ms.results_screen(result, PLAYER_COLOURS) == "rematch"      # (no lifetime wins / crown online: seats aren't people)
    if outcome in ("desync", "lost"):
        client.send({"t": "leave_match"})
        why = ("The two games stopped agreeing with each other. Make sure everyone has the same files (and OS)."
               if outcome == "desync" else "The connection to the server was lost.")
        Menu("Match ended", [Item("OK", result="ok")], subtitle=why, spacing=68, width=420, back_result="ok").run()
    return False

#==========================================================
# TRAINING MODE
#   Same fight code as a normal match (start_match / step_game), but: nobody loses stocks, there is no clock or results
#   screen, nothing is saved, and a Dummy stands in for the opponent. The combo counter hooks in through training_on_hit().
#==========================================================

TRAINING_COMBO_GAP = 60         # frames between hits before it counts as a NEW combo
TRAINING_AUTO_RESET = 120       # frames without being hit before the dummy's damage goes back to the preset
TRAINING_DAMAGES = [0, 25, 50, 100, 150, 200, 300]

def training_on_hit(attacker, target, dealt):
    """Called from Hitbox.hit every time damage lands."""
    if not training.active or target is not training.dummy or attacker is training.dummy:
        return
    if training.since_hit > TRAINING_COMBO_GAP:
        training.combo, training.combo_damage = 0, 0.0
    training.combo += 1
    training.combo_damage += dealt
    training.last_hit = dealt
    training.since_hit = 0
    training.best = max(training.best, training.combo)

def training_reset():
    """Everyone back to their spawn point, projectiles gone, dummy back to its preset damage."""
    for proj in projectiles[:]:
        proj.hitbox.delete()
        projectiles.remove(proj)
    for p in players:
        px, py = level.find(p.spawnIcon)[0]
        p.reset_state()
        p.go_to(px, py)
        p.facing = 1 if p.x < level.width / 2 else -1
        p.health = training.reset_damage if p is training.dummy else 0
    Particles.clear()
    training.combo, training.combo_damage, training.since_hit = 0, 0.0, 999

def training_reset_requested():
    return Keyboard.pressed("r") or any(p.pad is not None and Gamepad.pressed(p.pad, "back") for p in players)

def training_pause_menu():
    """Returns resume / reset / select / map / quit."""
    dim = Box(Screen.width, Screen.height, "black", Screen.width / 2, Screen.height / 2, alpha=170)

    def cycle(options, current, step):
        return options[(options.index(current) + step) % len(options)] if current in options else options[0]

    def set_behaviour(step):
        training.behaviour = cycle(DUMMY_BEHAVIOURS, training.behaviour, step)
        training.dummy.behaviour = training.behaviour

    def set_damage(step):
        training.reset_damage = cycle(TRAINING_DAMAGES, training.reset_damage, step)
        training.dummy.health = training.reset_damage

    def toggle_auto(step):
        training.auto_reset = not training.auto_reset

    items = [Item("Resume", result="resume"), Item("Reset Positions", result="reset")]
    if training.dummy is not None:
        for label, value, change in (("Dummy Behaviour", lambda: training.behaviour, set_behaviour),
                                     ("Dummy Damage", lambda: f"{training.reset_damage}%", set_damage),
                                     ("Auto-Reset Damage", lambda: "On" if training.auto_reset else "Off", toggle_auto)):
            items.append(Item(label, value=value, on_left=lambda c=change: c(-1), on_right=lambda c=change: c(1)))
    items += [Item("Change Fighter", result="select"), Item("Change Map", result="map"), Item("Quit to Menu", result="quit")]
    result = Menu("Training", items, hint="Left / Right: change     Esc to resume", spacing=56, width=620, back_result="resume").run()
    dim.delete()
    return result or "quit"

def start_training(entries, map_index):
    rules = ms.Rules()
    rules.mode, rules.stocks, rules.minutes, rules.shield, rules.sudden_death = "Stock", 10, 0, 0, False
    entries = list(entries)
    free = next((s for s in range(MAX_PLAYERS) if s not in {e["slot"] for e in entries}), None)
    training.active, training.dummy = True, None
    training.combo, training.combo_damage, training.last_hit, training.best, training.since_hit = 0, 0.0, 0.0, 0, 999
    if free is not None:                                            # (with four humans there's no seat left for the dummy)
        entries.append({"slot": free, "character": "Dummy", "dummy": True})
    start_match(entries, rules, map_index)
    training.hud = [Text("", 0, 0, 28, "white", outline=3) for _ in range(4)]
    training.hud.append(Text("R / Back: reset     Esc / Start: training menu", Screen.width / 2, 66, 20, (140, 140, 170), outline=1))
    if training.dummy is not None:
        training.dummy.behaviour = training.behaviour
        training.dummy.health = training.reset_damage

def training_update_ui(frame):
    update_ui(frame)
    d = training.dummy
    for p in players:
        stock_hud[p.slot].text = d.behaviour.upper() if p is d else ""
    if d is not None:
        hud[d.slot].text = f"DUMMY  {int(d.health)}%"
    ui.clock.text.text = "TRAINING"
    combo_on = training.since_hit <= TRAINING_COMBO_GAP and training.combo > 1
    lines = (f"HITS  {training.combo}", f"COMBO DAMAGE  {int(training.combo_damage)}",
             f"LAST HIT  {int(training.last_hit)}", f"BEST COMBO  {training.best} HITS")
    for i, (t, line) in enumerate(zip(training.hud, lines)):
        t.text = line
        t.colour = ms.GOLD if combo_on and i < 2 else "white"
        t.x, t.y = 18 + t.width / 2, 30 + i * 32

def run_training():
    """Plays until the player picks something that leaves training. Returns 'select', 'map' or 'quit'."""
    frame = 0
    ms.State.frame = 0
    training_update_ui(0)
    try:
        while Screen.running:
            if pause_requested():
                choice = training_pause_menu()
                if choice in ("select", "map", "quit"):
                    return choice
                if choice == "reset":
                    training_reset()
                Screen.update()         # the button that closed the menu mustn't also jump or attack
            if training_reset_requested():
                training_reset()
            if training.dummy is not None:
                training.dummy.think(others(training.dummy))
            step_game(frame, True)
            frame += 1
            ms.State.frame = frame
            training.since_hit += 1
            if training.auto_reset and training.since_hit == TRAINING_AUTO_RESET and training.dummy is not None:
                training.dummy.health = training.reset_damage
            training_update_ui(frame)
            Screen.update()
        return "quit"
    finally:
        Screen.fps = 60
        for p in players:
            p.visible = True

def training_mode():
    """Fighter -> map -> practice. Returns to the main menu when the player quits."""
    pick = lambda: character_select(settings, CHARACTERS, min_players=1, title="Training - Choose Your Fighter")
    entries = pick()
    step = "map"
    while entries and Screen.running:
        if step == "map":
            picked = ms.map_select(MAPS, ms.records.map_choice)
            if picked is None:                                      # backed out: pick fighters again
                entries = pick()
                continue
            ms.records.set_map_choice(picked[0])
            map_index, step = picked[1], "play"
        start_training(entries, map_index)
        outcome = run_training()
        end_match()
        Screen.background = MENU_BG
        if outcome == "select":
            entries, step = pick(), "map"
        elif outcome == "map":
            step = "map"
        else:
            break

#GAMELOOP
Screen.background = MENU_BG
rules = ms.load_rules()
while Screen.running:
    choice = main_menu(settings)
    if choice == "online":
        online_menu(settings, CHARACTERS, MAPS, rules, ONLINE_BUILD, play_online_match)
        Screen.background = MENU_BG
        continue
    if choice == "training":
        training_mode()
        Screen.background = MENU_BG
        continue
    if choice != "play":
        break
    entries = character_select(settings, CHARACTERS)
    step = "map"                                                    # which screen comes next: "map" -> "rules" -> fight
    while entries and Screen.running:
        if step == "map":
            picked = ms.map_select(MAPS, ms.records.map_choice)
            if picked is None:                                      # backed out: pick fighters again
                entries = character_select(settings, CHARACTERS)
                continue
            ms.records.set_map_choice(picked[0])
            map_index = picked[1]
            step = "rules"
        if not ms.rules_menu(rules, entries, PLAYER_COLOURS, MAPS[map_index]["name"]):
            step = "map"                                            # backed out of the rules: pick the map again
            continue
        while Screen.running:                                       # one pass = one match (so "Rematch" is just another pass)
            start_match(entries, rules, map_index)
            result = run_match()
            end_match()
            Screen.background = MENU_BG
            if result is None:                                      # quit from the pause menu
                entries = None
                break
            result.map_name = MAPS[map_index]["name"]
            ms.records.award(result)                                # wins + the crown
            action = ms.results_screen(result, PLAYER_COLOURS)
            if action == "rematch":
                continue
            if action == "select":
                entries = character_select(settings, CHARACTERS)
                step = "map"
            elif action == "menu":
                entries = None
            elif action == "map":
                step = "map"
            break                                                   # "rules" falls out to the rules menu again