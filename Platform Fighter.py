from GameSnake import *
import math

#Set the Screen Size and FPS
Screen.size(1280, 720)
Screen.fps = 60

#Allows the Screen to be Moved and Altered
Screen.set_resizable(True)

#LEVEL LAYOUTS AND LOADING
default_stage = """
ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ
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
Zxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx2xxxxxxx1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
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
    def __init__(self, x, y, facing, speed, lifetime, hitbox, pierce=False):
        self.x, self.y, self.facing = x, y, facing
        self.speed, self.lifetime = speed, lifetime
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
        self.x += self.speed * self.facing
        self.lifetime -= 1
        self.hitbox.place(self.x, self.y, self.facing)
        landed = self.hitbox.check(targets, self.facing)
        if self.lifetime <= 0 or tilemap.is_solid(self.x, self.y) or (landed and not self.pierce):
            self.hitbox.delete()
            projectiles.remove(self)


#==========================================================
# PLAYER
#==========================================================

class Player(Sprite): #Generalised Player, Superclass for each Character

    def __init__(self,currentLevel, name, x=None, y=None, size=100, spawnIcon = "p", controls=None, pad=None):
        super().__init__(name, x, y, size)
        self.controls = controls          # a keyboard controls dictionary, or None for no keyboard input
        self.pad = pad                    # which controller slot drives this player (0 = first), or None
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

    def held(self, action):
        if self.controls is not None and Keyboard.held(self.controls[action]):
            return True
        return self.pad is not None and Gamepad.held(self.pad, PAD_CONTROLS[action])

    def pressed(self, action):
        if self.controls is not None and Keyboard.pressed(self.controls[action]):
            return True
        return self.pad is not None and Gamepad.pressed(self.pad, PAD_CONTROLS[action])

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
                self.coyote_time = 0          # the jump uses up the grace window, so you can't jump from it again

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

#==========================================================
# CHARACTER: VEN
#==========================================================

class Ven(Player):

    def __init__(self, currentLevel, name, x=None, y=None, size=100, spawnIcon="p", controls=None, pad=None):
        super().__init__(currentLevel, name, x, y, size, spawnIcon, controls, pad)
        self.special_ammo = 2

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
            if down and self.special_ammo >0:
                self.rifle_shot()
            elif up and self.special_ammo > 0:
                self.blast_bouncer()
            elif side and self.special_ammo > 0:
                self.throw_stone()
            else:
                pass
        else:
            if down:
                if grounded: self.Breaker()
                else:        pass
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

    def throw_stone(self):
        # Inverse knockback: victims are dragged TOWARDS Rend instead of away
        def fire(owner):
            stone = Hitbox(owner, 14, 14, (0, 0), damage=3, kbx=6, kby=4, angle=15, stun=8, mode="pull")
            Projectile(owner.x + 20 * owner.facing, owner.y, owner.facing, speed=12, lifetime=45, hitbox=stone)
        # active=0 means the move itself never hits, it only spawns the stone
        self.start_attack(Attack(self, 1, 1, (0, 0), startup=6, active=0, recovery=12,
                                 damage=0, knockbackx=0, knockbacky=0, angle=0, stun=0, on_fire=fire))

    #---------------- LIGHT ----------------

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
    MAX_CHARGE = 90               # frames (1.5 seconds at 60fps)

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

    def __init__(self, currentLevel, name, x=None, y=None, size=100, spawnIcon="p", controls=None, pad=None):
        super().__init__(currentLevel, name, x, y, size, spawnIcon, controls, pad)
        self.stored_charge = 0        # Consume charge waiting to be released (in frames)

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
#All character list

CHARACTERS = {
    "Ven": Ven,
    "Rend": Rend
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

    if player.health > 100:
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
load_level(1,allLevels,allLegends)

# Character choices
player1_character = "Ven"
player2_character = "Rend"

# Create players using their selected characters
player1 = CHARACTERS[player1_character](
    level, "player", 0, 0,
    spawnIcon="1",
    controls=P1_CONTROLS,
    pad=1
)

player2 = CHARACTERS[player2_character](
    level, "player", 0, 0,
    spawnIcon="2",
    controls=P2_CONTROLS,
    pad=0
)

player2.facing = -1

players = [player1, player2]

def others(player):                     # everyone a player's attacks can hit
    return [p for p in players if p is not player]

focus = CameraFocus()
focus.track(players)
Stage.camera.go_to(focus.x, focus.y)
Stage.camera.follow(focus, 100)
Stage.camera.limit_to(level.zone())

#GAMELOOP
while Screen.running:
    for p in players:
        p.handle_movement(level)

    for p in players:                   # everyone decides their attack first...
        p.attackChecks(others(p))
    for p in players:                   # ...then every move advances, so its fair (looking at you tristan)
        p.update_attack(others(p))

    for proj in projectiles[:]:         # copy, since update() removes finished projectiles
        proj.update([p for p in players if p is not proj.owner], level)

    for p in players:
        if level.touching(p, "Z"): #TODO: Death Code
            respawn(p)

    focus.track(players)
    Screen.update()