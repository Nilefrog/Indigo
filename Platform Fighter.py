from GameSnake import *
from Controls import *      # per-player key / button layouts + saved settings
from Menus import *         # main menu, settings, character select, pause
import math

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
default_legend = {
    "0": "ground",
    "#": "wall",
}

allLevels = {
    1: default_stage
}

allLegends = {
    1: default_legend
}

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
        self._deleted = False

    def set_active(self, on):
        if on and not self.active:
            self.already_hit.clear()      # a re-activated box can hit again
        self.active = on
        self.zone.visible = on

    def place(self, x, y, facing):
        self.zone.x = x + self.offset[0] * facing
        self.zone.y = y + self.offset[1]

    def check(self, targets, facing):
        """Returns True if this call landed at least one hit."""
        if not self.active:
            return False
        landed = False
        for t in targets:
            if self._deleted:             # a parry can cancel the whole move mid-loop
                break
            if t not in self.already_hit and t.touching_zone(self.zone):
                self.already_hit.add(t)
                if self.hit(t, facing):
                    landed = True
        return landed

    def hit(self, target, facing):
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
        target.health += self.damage
        scale = (target.health / 200) + 1
        a = math.radians(self.angle)
        if not self.projectile:
            self.owner.dash_charges = 1
            self.owner.jump_charges = 1

        if self.mode == "radial":
            dx = target.x - self.zone.x
            dy = target.y - self.zone.y
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

class Projectile: #Player Attack Projectiles
    def __init__(self, x, y, facing, speed, lifetime, hitbox, pierce=False, angle=0, gravity=0, ignore_tiles=False):
        self.x, self.y, self.facing = x, y, facing
        self.speed, self.lifetime = speed, lifetime
        self.angle = angle            # degrees away from straight ahead: 0 = forward, 90 = straight up, negative = down
        self.gravity = gravity        # pulls it down a bit more every frame, so shots can arc
        self.fall = 0
        self.ignore_tiles = ignore_tiles   # True = flies straight through walls and the floor
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
        a = math.radians(self.angle)
        self.fall += self.gravity
        self.x += self.speed * math.cos(a) * self.facing
        self.y += -self.speed * math.sin(a) + self.fall
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
        key = self.controls.get(action) if self.controls is not None else None
        if key and Keyboard.held(key):
            return True
        button = self.pad_controls.get(action)
        return self.pad is not None and button is not None and Gamepad.held(self.pad, button)

    def pressed(self, action):
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
            self.y_velocity += self.gravity
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

    def on_parry_success(self):
        """You parried something: skip the rest of the parry's endlag so you can punish straight away."""
        self.actionableTimer = 0
        self.dash_charges = self.max_dash_charges
        self.jump_charges = self.max_jump_charges
        self.NoGravTimer = 0
        print("Parried!")

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

class Dummy(Player):
    """A punching bag: no controls, so it never does anything on its own."""
    def __init__(self, currentLevel, name, x=None, y=None, size=100, spawnIcon="e"):
        super().__init__(currentLevel, name, x, y, size, spawnIcon, controls=None)

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
    TRASH_PER_DAMAGE = 1.5       # every point of damage she deals adds this much trash (so a full bag takes a while)
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
                       speed=speed[0] + random_float() * (speed[1] - speed[0]), lifetime=lifetime,
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

#All character list

CHARACTERS = {
    "Ven": Ven,
    "Rend": Rend,
    "Cleaning Lady": CleaningLady,
    "Cap'n Rex": CaptnRex
}

#==========================================================
# RESPAWNING + CAMERA
#==========================================================


def respawn(player):
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
    # Respawn the player.
    px, py = level.find(player.spawnIcon)[0]
    print(f"Respawn at spawn '{player.spawnIcon}', damage was {player.health}")

    player.reset_state()
    player.go_to(px, py)

    player.health = 0



class CameraFocus:
    #Camera in the middle of all players
    def __init__(self):
        self.x = 0
        self.y = 0

    def track(self, players):
        self.x = sum(p.x for p in players) / len(players)
        self.y = sum(p.y for p in players) / len(players)

#================================================================================================================================#
#                                                           ACTUAL GAME                                                          #
#================================================================================================================================#
#SETUP
MATCH_BG = Screen.background            # the colour fights are played on (the menus use their own)

players = []
hud = []                                # one damage counter per player, along the bottom of the screen
tags = []                               # the little "P(whatever)" floating above each player's head
camera_zone = None
focus = None

def others(player):                     # everyone a player's attacks can hit
    return [p for p in players if p is not player]

def start_match(entries):
    """entries comes straight from character_select()"""
    global players, hud, tags, camera_zone, focus
    Screen.background = MATCH_BG
    Particles.clear()
    load_level(1, allLevels, allLegends)

    players, hud, tags = [], [], []
    for entry in entries:
        slot, device = entry["slot"], entry["device"]
        controls, pad = (settings.keyboard[slot], None) if device[0] == "profile" else (None, device[1])
        player = CHARACTERS[entry["character"]](
            level, "player", 0, 0,
            spawnIcon=str(slot + 1),
            controls=controls,
            pad=pad,
            pad_controls=settings.pad[slot],
            slot=slot
        )
        player.facing = 1 if player.x < level.width / 2 else -1        # everyone starts looking towards the middle
        players.append(player)

    for i, player in enumerate(players):
        colour = PLAYER_COLOURS[player.slot]
        hud_x = Screen.width * (i + 1) / (len(players) + 1)
        hud.append(Text("", hud_x, Screen.height - 40, 44, colour, outline=3))
        player.make_hud(hud_x, Screen.height - 85)          # the character's own extra UI, just above the damage counter
        tags.append(Text(f"P{player.slot + 1}", player.x, player.y - 28, 22, colour, outline=2, fixed=False))

    focus = CameraFocus()
    focus.track(players)
    camera_zone = level.zone()
    Stage.camera.go_to(focus.x, focus.y)
    Stage.camera.follow(focus, 100)
    Stage.camera.limit_to(camera_zone)
    Screen.update()                     # one frame to let the button that started the match pass, otherwise it would also pause / jump

def end_match():
    """Throws the whole fight away so the menus (and the next fight) start clean."""
    global level, players, hud, tags, camera_zone
    for player in players:
        player.cancel_attack()
        player.cleanup()
        player.delete_hud()
        player.delete()
    for proj in projectiles[:]:
        proj.hitbox.delete()
    projectiles.clear()
    for sprite in hud + tags:
        sprite.delete()
    players, hud, tags = [], [], []
    Stage.camera.reset()
    camera_zone.delete()
    level.delete()
    del level                           # so load_level knows there is no old level to delete next time
    Particles.clear()

def pause_requested():
    if Keyboard.pressed("escape"):
        return True
    return any(p.pad is not None and Gamepad.pressed(p.pad, "start") for p in players)

def run_match():
    """Plays until the players quit from the pause menu (or close the window)."""
    while Screen.running:
        if pause_requested():
            if pause_menu() == "quit":
                return
            Screen.update()             # same again: the button that closed the pause menu mustn't also jump or attack

        for p in players:
            p.handle_movement(level)

        for p in players:                   # everyone decides their attack first
            p.attackChecks(others(p))
        for p in players:                   # then every move advances, so its fair (looking at you tristan)
            p.update_attack(others(p))

        for proj in projectiles[:]:         # copy, since update() removes finished projectiles
            proj.update([p for p in players if p is not proj.owner], level)

        for p in players:
            if level.touching(p, "Z") or level.touching(p, "Q"): #TODO: Death Code #ALSO "Q" is used so that the Capt'n barrel isnt killed by the top blastzone
                respawn(p)

        for i, p in enumerate(players):
            hud[i].text = f"P{p.slot + 1}  {int(p.health)}%"
            p.update_hud()
            tags[i].go_to(p.x, p.y - 28)

        focus.track(players)
        Screen.update()

#GAMELOOP
Screen.background = MENU_BG
while Screen.running:
    choice = main_menu(settings)
    if choice != "play":
        break
    entries = character_select(settings, CHARACTERS)
    if entries:
        start_match(entries)
        run_match()
        end_match()
        Screen.background = MENU_BG

settings.save()