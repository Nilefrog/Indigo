import os,math,random,time,pygame,sys,textwrap

__all__ = ["random_number","random_float","Screen","color","colour","Keyboard","Mouse","Sprite","Stage","Sound","Zone","TileMap"]


#All Of This Code is Based off of the pygame library!, You Can Read About it Here: https://www.pygame.org/docs/
#Pygame allows python to draw to the screen, and read inputs!

#This Is Useful for a Variety of Things, especially, making games!


# ======Intialisation======

#Typically, we have to ask pygame to intialise (or set itself up) before we can do anything in our script
#This is Done For You
pygame.init()

#We also setup the clock internally, Which will be used in later scripts
_clock = pygame.time.Clock()

#The font used for zone labels
_font = pygame.font.Font(None, 20)

#General Other Constants
_ROTATE_MODES = ("all", "flip", "none")
_EDGE_MODES = ("free", "onscreen", "bounce")

#More Setup Can Be Found Later in the Script, But We Need to Intialise Pygame First, as a variety of Functions Depend On It!

# ======TYPES======

#Types are kinds of variables, For example Strings, or Integers
#Pygame also adds some Extra Types of Variables You Can use in Your code.

#This Function Allows You To Create a New Colour Variable!
#You Can Use Names of Colours, Which You Can Find Here: https://www.pygame.org/docs/ref/color_list.html
#Or, you can input an R,G,B Value as an Iterable, For Example a list using [r,g,b] or a Tuple as (r,g,b),
#For Example: (255,55,77) 

def color(c):
    if isinstance(c, str):
        try:
            return pygame.Color(c)
        except ValueError: #If You Input Something Invalid, A Reminder is Sent as an Error Message
            raise ValueError(f"Error!: Unknown Colour '{c}', Try Using a Valid Colour Found at https://www.pygame.org/docs/ref/color_list.html, or a (r,g,b) value!")
    try:
        return pygame.Color(*c)
    except (TypeError,ValueError):
        raise ValueError(f"Error!: Incorrect RGB Value, it should be in the form (r,g,b), with brackets around it! eg. (255,0,0)")
    
colour = color #Incase The Spirit Of The British Takes You Over

#This Function Is Acctually Used Internally, But It Uses the key_code Function of pygame.
#You Can Find Valid Keycodes Here: https://www.pygame.org/docs/ref/key.html
def _key_code(name):
    try:
        return pygame.key.key_code(name.lower().replace(" arrow", ""))
    except ValueError:
        raise ValueError(f"Error!: Invalid Key {name}, Find Valid Keys Here!: https://www.pygame.org/docs/ref/key.html")

# ======SCREEN======

class _Screen():
    def __init__(self,width=480,height =360,resizable=False):

        #You Can Read Any Screen Variables Using screen.(variable)
        #For Example, You can Get the screen width using
        #Screen.width
         
        self.width = width
        self.height = height
        self.resizable = resizable
        self.is_fullscreen = False
        self.surface = None
        self.fps = 30
        self.running = True
        self.background = "white"
        self._screen_set()

    def _screen_set(self): # This is called internally, to apply your changes after you set them
        flags = pygame.SCALED
        if self.resizable:
            flags |= pygame.RESIZABLE
        if self.is_fullscreen:
            flags |= pygame.FULLSCREEN
        self.surface = pygame.display.set_mode((self.width,self.height), flags)
        self.surface.fill(self.background)    # Fixes a Bug Where the Screen would be black for exactly 1 frame after running


    #The Update function is Very Important!
    #Your Screen Doesnt Visually Change, Unless you do Screen.update() at the end of your code!
    #The Example Script Has This Implemented for you, but if you start from a fresh file, remember that!

    #Remember to do Screen.update() At The End of Your Gameloop!

    #This is probably the most important function in the code
    def update(self):
        Keyboard._new_frame()
        Mouse._new_frame()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            Keyboard._handle(event)
            Mouse._handle(event)

        Stage._draw_frame()          #Draw order -> camera, backdrop, tiles, sprites, then zones
        pygame.display.flip()
        self.surface.fill(self.background)
        _clock.tick(self.fps)

    #Using Pygame, We can Modify the Size of The Screen, to Enlarge it, and go beyond the typical size!
    def size(self,width,height): # Simply input your desired width and height in pixels!
        self.width = width
        self.height = height
        self._screen_set()

    #We Can Also Set Whether or Not The Window Can Be Resized By Users, By Clicking and Dragging on the Edge
    def set_resizable(self, on=True): # Simply input True, or False
        self.resizable = on
        self._screen_set()

    #We Can Also, Toggle Fullscreen For the User!
    def fullscreen(self, on=True): # Simply input True or False
        self.is_fullscreen = on
        self._screen_set()

    def toggle_fullscreen(self): # This Does The Same Thing as Fullscreen, but it will toggle it for you
        self.is_fullscreen = not self.is_fullscreen # This Flips Fullscreen from off to on, and on to off!
        self._screen_set()
    

# ======ASSETS======

#Sprites and Backdrops can be placed into the folders Next to Your Script!
#Tiles (for TileMap) go in a folder called "tiles"
_IMAGE_TYPES = (".png", ".jpg", ".jpeg", ".gif", ".bmp")
_SOUND_TYPES = (".wav", ".ogg", ".mp3")

def _find_project_folder():
    main = sys.modules.get("__main__")
    path = getattr(main, "__file__", None)
    return os.path.dirname(os.path.abspath(path)) if path else os.getcwd()

_project_dir = _find_project_folder()

#This is Used Internally, to Load Images from disk, once!, 

#Why would we only load them once?, well say your using a list to create alot of sprites at once, loading the images alot of times is
#Really, Really Slow.
#To Fix this, were going to create an _image_cache, and store the images there.

#Images are loaded from the disk ONCE, then remembered.
_image_cache = {}

def _load_images_from_disk(kind, name):
    folder = os.path.join(_project_dir, kind)
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"Error!: No Folder Named '{kind}'. It Should Be Next to Your Script, Here: {_project_dir}")

    for ext in _IMAGE_TYPES: #Single Sprites
        path = os.path.join(folder, name + ext)
        if os.path.isfile(path):
            return [(name, pygame.image.load(path).convert_alpha())]

    sub = os.path.join(folder, name)  #Folders of Costumes
    if os.path.isdir(sub):
        files = sorted(f for f in os.listdir(sub) if f.lower().endswith(_IMAGE_TYPES))
        if files:
            return [(os.path.splitext(f)[0], pygame.image.load(os.path.join(sub, f)).convert_alpha()) for f in files]

    found = sorted({os.path.splitext(f)[0] for f in os.listdir(folder)})
    raise FileNotFoundError(f"Error!: Could Not Find '{name}' in your '{kind}' folder. Found: {', '.join(found) or 'Nothing'}")

#This Loads the images directly out of the cache.
def _load_images(kind, name):
    if (kind, name) not in _image_cache:
        _image_cache[(kind, name)] = _load_images_from_disk(kind, name)
    return _image_cache[(kind, name)]

def _find_sound(name):
    folder = os.path.join(_project_dir, "sounds")
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"Error!: No Folder Named 'sounds'. It Should Be Next to Your Script, Here: {_project_dir}")
    for ext in _SOUND_TYPES:
        path = os.path.join(folder, name + ext)
        if os.path.isfile(path):
            return path
    found = sorted({os.path.splitext(f)[0] for f in os.listdir(folder)})
    raise FileNotFoundError(f"Error!: Could Not Find '{name}' in your 'sounds' folder. Found: {', '.join(found) or 'Nothing'}")

# ======SPRITES======

#Pygame Doesnt Really Support Sprites, But They Have Been Created as a Custom Class For You!, Think of a Class as a collection of variables and functions.

class Sprite:
    def __init__(self, name, x=None, y=None, size=100):
        self._costumes = _load_images("sprites", name)
        self.name = name                   # Current Sprite Name
        self.costume = 0                   # The Current Costume
        self.x = Screen.width / 2 if x is None else x    # Sprite Centre
        self.y = Screen.height / 2 if y is None else y
        self.direction = 90                # 90 = right, 0 = up, 180 = down, 270 = left
        self.size = size                   # a percentage, like Scratch
        self.visible = True
        self.fixed = False                 # True = stuck to the screen, ignores the camera (for scores etc.)
        self.show_hitbox = False           # set True to draw the hitbox for debugging
        self._rotate_mode = "all"          # "all", "flip" or "none"
        self._edge_mode = "free"           # "free", "onscreen" or "bounce"
        self._hitbox = None                # None = use the whole image, Otherwise use the specified Hitbox
        self._x_limits = None              # see clamping below
        self._y_limits = None
        self._zone = None                  # a Zone the sprite is locked inside
        Stage._sprites.append(self)        # the Stage will now draw it for us

    #rotate_mpde lets you alter whether the sprite flips or rotates freely, or doesnt rotate at all
    @property
    def rotate_mode(self):
        return self._rotate_mode

    @rotate_mode.setter
    def rotate_mode(self, mode):
        mode = str(mode).lower()
        if mode not in _ROTATE_MODES:
            raise ValueError(f"Error!: '{mode}' is not a rotate mode. Choose from: {', '.join(_ROTATE_MODES)}")
        self._rotate_mode = mode

    #edge_mode lets you choose from being allowed of screen, capped at the edge of the screen, or rotating at the edge of the screen.
    @property
    def edge_mode(self):
        return self._edge_mode

    @edge_mode.setter
    def edge_mode(self, mode):
        mode = str(mode).lower()
        if mode not in _EDGE_MODES:
            raise ValueError(f"Error!: '{mode}' is not an edge mode. Choose from: {', '.join(_EDGE_MODES)}")
        self._edge_mode = mode

    # --- motion ---

    #Move Or Step Moves You in Your Current Forward Direction, Like Steps in Scratch
    def move(self, steps):
        rad = math.radians(self.direction)
        self.x += steps * math.sin(rad)
        self.y -= steps * math.cos(rad)    #IMPORTANT NOTE!, Pygame Puts 0,0 as the top left corner of the screen, so increasing y would normally cause you to go down!, its been inverted for you here.
        self._apply_edge_mode()
        self._apply_limits()

    def turn_right(self, degrees):
        self.direction = (self.direction + degrees) % 360

    def turn_left(self, degrees):
        self.direction = (self.direction - degrees) % 360

    #Teleports You To The Specified Co-ordinates
    def go_to(self, x, y):
        self.x, self.y = x, y

    #Makes Your Sprite Face a Point
    def point_towards(self, x, y):
        self.direction = math.degrees(math.atan2(x - self.x, self.y - y)) % 360

    # --- looks ---

    #Moves to The Next Costume
    def next_costume(self):
        self.costume = (self.costume + 1) % len(self._costumes)

    #Moves to The Previous Costume
    def previous_costume(self):
        self.costume = (self.costume - 1) % len(self._costumes)

    #Switches to a specfic costume
    def switch_costume(self, which):       
        names = [n for n, _ in self._costumes]
        if isinstance(which, int):
            self.costume = which % len(names)
        elif which in names:
            self.costume = names.index(which)
        else:
            raise ValueError(f"Error!: '{self.name}' has no costume called '{which}'. It has: {', '.join(names)}")

    def show(self):
        self.visible = True

    def hide(self):
        self.visible = False

    def delete(self):                      # Deletes the Current Sprite 
        Stage._sprites.remove(self)

    # --- hitboxes ---

    #Sets a custom collision box. width/height are in pixels (at size 100), and the
    #offsets move the box away from the sprite's centre. Y points down, due to pygame!
    #The hitbox scales with size, but does not rotate!
    #Example: player.set_hitbox(20, 40, 0, 5)
    #Turn on player.show_hitbox = True to see it as a red outline!
    def set_hitbox(self, width, height, offset_x=0, offset_y=0):
        self._hitbox = (width, height, offset_x, offset_y)

    #Goes back to using the Sprite as a hitbox reference.
    def reset_hitbox(self):
        self._hitbox = None

    # --- clamping ---

    #Locks the sprite's x between low and high. Use None for "no limit" on a side.
    #Example: paddle.clamp_x(50, 430)  or  paddle.clamp_y(200, 200) to pin it to a line!
    def clamp_x(self, low=None, high=None):
        self._x_limits = (low, high)
        self._apply_limits()

    def clamp_y(self, low=None, high=None):
        self._y_limits = (low, high)
        self._apply_limits()

    #Keeps the sprite's hitbox inside a Zone
    def limit_to(self, zone):
        self._zone = zone
        self._apply_limits()

    #Removes every clamp and zone limit
    def unclamp(self):
        self._x_limits = None
        self._y_limits = None
        self._zone = None

    # --- sensing ---

    #Pygame Uses Rects - Short For Rectangle, In Order to Detect Colision, via rect().colliderect()
    def touching(self, other):
        return self.visible and other.visible and self._hitbox_rect().colliderect(other._hitbox_rect())

    def touching_mouse(self):
        if self.fixed:
            return self._hitbox_rect().collidepoint(Mouse.x, Mouse.y)
        return self._hitbox_rect().collidepoint(Mouse.world_x, Mouse.world_y)

    def touching_edge(self):
        return not self._view().contains(self._hitbox_rect())

    def touching_zone(self, zone):
        return self._hitbox_rect().colliderect(zone._rect())

    def inside_zone(self, zone):
        return zone._rect().contains(self._hitbox_rect())

    def touching_solid(self, tilemap):
        return tilemap.touching(self)

    # --- Cloning ---

    #To Create Copies of a Sprite, use (newspritename) = (sprite name).clone()
    def clone(self):
        twin = Sprite(self.name, self.x, self.y, self.size)
        twin.costume = self.costume
        twin.direction = self.direction
        twin.visible = self.visible
        twin.fixed = self.fixed
        twin.show_hitbox = self.show_hitbox
        twin.rotate_mode = self.rotate_mode
        twin.edge_mode = self.edge_mode
        twin._hitbox = self._hitbox
        twin._x_limits = self._x_limits
        twin._y_limits = self._y_limits
        twin._zone = self._zone
        return twin

    # --- internal ---

    #What "the edge" means: the screen for fixed sprites, the part of the world the camera can see otherwise
    def _view(self):
        return Screen.surface.get_rect() if self.fixed else Stage._view_rect()

    #Keeps the sprite on the screen if its edge_mode says so.
    #"onscreen" pushes it back in, and "bounce" pushes it back in AND turns it around
    def _apply_edge_mode(self):
        if self._edge_mode == "free":
            return
        screen = self._view()
        rect = self._hitbox_rect()
        if screen.contains(rect):          # completely on screen, so nothing to do
            return

        fixed = rect.clamp(screen)         # the same rectangle, moved to the nearest spot fully on screen
        shift_x = fixed.x - rect.x         # positive = it was off the LEFT edge, negative = off the RIGHT
        shift_y = fixed.y - rect.y         # positive = it was off the TOP edge, negative = off the BOTTOM
        self.x += shift_x
        self.y += shift_y

        if self._edge_mode == "bounce":
            rad = math.radians(self.direction)
            heading_x = math.sin(rad)      # positive = heading right
            heading_y = -math.cos(rad)     # positive = heading down (the minus, because pygame's y points down)
            #Only bounce if it is heading INTO the wall, otherwise it could flip back and forth
            if (shift_x > 0 and heading_x < 0) or (shift_x < 0 and heading_x > 0):
                self.direction = (360 - self.direction) % 360    # mirror left-right
            if (shift_y > 0 and heading_y < 0) or (shift_y < 0 and heading_y > 0):
                self.direction = (180 - self.direction) % 360    # mirror top-bottom

    #Pushes the sprite back inside any clamps or zone it has
    def _apply_limits(self):
        if self._x_limits:
            low, high = self._x_limits
            if low is not None and self.x < low:
                self.x = low
            if high is not None and self.x > high:
                self.x = high
        if self._y_limits:
            low, high = self._y_limits
            if low is not None and self.y < low:
                self.y = low
            if high is not None and self.y > high:
                self.y = high
        if self._zone is not None:
            rect = self._hitbox_rect()
            fixed = rect.clamp(self._zone._rect())
            self.x += fixed.x - rect.x
            self.y += fixed.y - rect.y

    def _image(self):
        image = self._costumes[self.costume][1]
        if self.size != 100:
            w = max(1, int(image.get_width() * self.size / 100))
            h = max(1, int(image.get_height() * self.size / 100))
            image = pygame.transform.smoothscale(image, (w, h))

        direction = self.direction % 360
        if self._rotate_mode == "all":
            if direction != 90:
                image = pygame.transform.rotate(image, 90 - direction)
        elif self._rotate_mode == "flip":
            if 180 < direction < 360:
                image = pygame.transform.flip(image, True, False)   # (flip sideways, don't flip upside down)
        return image

    def _rect(self): 
        return self._image().get_rect(center=(self.x, self.y))

    def _hitbox_rect(self):
        if self._hitbox is None:
            return self._rect()
        w, h, off_x, off_y = self._hitbox
        scale = self.size / 100
        box = pygame.Rect(0, 0, max(1, int(w * scale)), max(1, int(h * scale)))
        box.center = (round(self.x + off_x * scale), round(self.y + off_y * scale))
        return box

    def _draw(self):
        if self.visible:
            ox, oy = (0, 0) if self.fixed else Stage._offset()
            image = self._image()
            Screen.surface.blit(image, image.get_rect(center=(self.x - ox, self.y - oy)))
            if self.show_hitbox:
                pygame.draw.rect(Screen.surface, (255, 0, 0), self._hitbox_rect().move(-ox, -oy), 1)


# ======CAMERA======

#The camera is the point in the world that sits in the middle of the screen.
#Sprites keep their world co-ordinates, and we just shift everything when drawing.
class _Camera:
    def __init__(self):
        self._x = None                 # None = centre of the screen, so nothing moves
        self._y = None
        self.target = None
        self.smooth = 0
        self._zone = None

    @property
    def x(self):
        return Screen.width / 2 if self._x is None else self._x
    @x.setter
    def x(self, value):
        self._x = value

    @property
    def y(self):
        return Screen.height / 2 if self._y is None else self._y
    @y.setter
    def y(self, value):
        self._y = value

    def go_to(self, x, y):
        self.x, self.y = x, y

    #Follow a sprite! smooth is 0-99: 0 snaps to it, higher numbers lag behind more.
    def follow(self, sprite, smooth=0):
        self.target = sprite
        self.smooth = max(0, min(99, smooth))

    def stop_following(self):
        self.target = None

    #The camera will never show anything outside the zone (the screen edge stays inside it)
    def limit_to(self, zone):
        self._zone = zone

    def unlimit(self):
        self._zone = None

    def _update(self):
        if self.target is not None:
            if self.smooth == 0:
                self.x, self.y = self.target.x, self.target.y
            else:
                k = 1 - self.smooth / 100
                self.x += (self.target.x - self.x) * k
                self.y += (self.target.y - self.y) * k
        if self._zone is not None:
            w, h = Screen.surface.get_size()
            z = self._zone._rect()
            self.x = _limit(self.x, z.left + w / 2, z.right - w / 2)
            self.y = _limit(self.y, z.top + h / 2, z.bottom - h / 2)

#Keeps value between low and high. If the zone is smaller than the screen, we centre on it instead
def _limit(value, low, high):
    if low > high:
        return (low + high) / 2
    return max(low, min(high, value))


# ======STAGE======

#Whilst Not An Offical element of pygame, backdrops or stages are supported in this scrpit
class _Stage:
    def __init__(self):
        self._sprites = [] #A List of all the Sprites on the stage
        self._zones = []
        self._tilemaps = []
        self._backdrop = None
        self._stretch = True
        self._cache = None                 # the backdrop stretched to fit the screen
        self._cache_size = None
        self.camera = _Camera()

    #We can use backdrop to Select The Current Image the Stage Displays
    #For Example Stage.backdrop("forest"), or Stage.backdrop(None) to remove
    #stretch=True fits the image to the screen. stretch=False draws it at full size
    #starting at world (0,0), so a big image becomes a big room the camera can explore!
    def backdrop(self, name, stretch=True):
        self._backdrop = None if name is None else _load_images("backdrops", name)[0][1]
        self._stretch = stretch
        self._cache_size = None

    #How far the world is shifted on screen, and the part of the world currently visible
    def _offset(self):
        w, h = Screen.surface.get_size()
        return round(self.camera.x - w / 2), round(self.camera.y - h / 2)

    def _view_rect(self):
        w, h = Screen.surface.get_size()
        ox, oy = self._offset()
        return pygame.Rect(ox, oy, w, h)

    def _draw_backdrop(self):
        if self._backdrop is None:
            return
        if self._stretch:
            size = Screen.surface.get_size()
            if self._cache_size != size:       # only re-stretch if the screen size changed
                self._cache = pygame.transform.smoothscale(self._backdrop, size)
                self._cache_size = size
            Screen.surface.blit(self._cache, (0, 0))
        else:
            ox, oy = self._offset()
            Screen.surface.blit(self._backdrop, (-ox, -oy))

    def _draw_frame(self):
        for sprite in self._sprites:
            sprite._apply_edge_mode()
            sprite._apply_limits()
        self.camera._update()          # after sprites are limited, so it follows where they really are
        self._draw_backdrop()
        for tilemap in self._tilemaps:
            tilemap._draw()
        for sprite in self._sprites:
            sprite._draw()
        for zone in self._zones:
            zone._draw()


# ======ZONES======

#A Zone is a rectangle in the world that you can See. Use it to limit the camera or sprites.
#Zones allow limiting Player movement easily, and can generarlly make debugging slightly easier.
#x,y is the centre, like a sprite. 
class Zone:
    def __init__(self, x, y, width, height, colour="red", name=""):
        self.x, self.y = x, y
        self.width, self.height = width, height
        self.colour = color(colour)
        self.name = name
        self.visible = False
        Stage._zones.append(self)

    #Show the Zone as a Coloured Square, for debugging
    #Change The Zone Colour with Zone.colour
    def show(self):
        if self.visible == True:
            print("Warning!: This Zone was Already Shown!")
        self.visible = True

    def hide(self):
        if self.visible == False:
            print("Warning!: This Zone was Already Hidden!")
        self.visible = False

    def delete(self):
        Stage._zones.remove(self)

    def contains_point(self, x, y):
        return self._rect().collidepoint(x, y)

    def _rect(self):
        rect = pygame.Rect(0, 0, max(1, int(self.width)), max(1, int(self.height)))
        rect.center = (round(self.x), round(self.y))
        return rect

    def _draw(self):
        if not self.visible:
            return
        ox, oy = Stage._offset()
        rect = self._rect().move(-ox, -oy)
        shade = pygame.Surface(rect.size, pygame.SRCALPHA)
        shade.fill((*tuple(self.colour)[:3], 70))
        Screen.surface.blit(shade, rect)
        pygame.draw.rect(Screen.surface, self.colour, rect, 2)
        if self.name:
            Screen.surface.blit(_font.render(self.name, True, self.colour), (rect.x + 4, rect.y + 4))


# ======TILEMAP======

#Draw your level as text! Every character is one tile.
#legend says which image (from the 'tiles' folder) each character uses.
#Any character not in the legend is empty space, '.' is a good one to use.
#solid is a string of the characters that sprites can't walk through.
#
#    level = TileMap("""
#    ##########
#    #....P...#
#    #...##...#
#    ##########
#    """, {"#": "wall"}, tile_size=32, solid="#")
class TileMap:

    def __init__(self, layout, legend, tile_size=32, solid=""):
        rows = textwrap.dedent(layout).split("\n")   # dedent means you can indent the map in your code
        while rows and not rows[0].strip():
            rows.pop(0)
        while rows and not rows[-1].strip():
            rows.pop()
        if not rows:
            raise ValueError("Error!: the TileMap layout is empty!")
        self.tile_size = tile_size
        self.cols = max(len(r) for r in rows)
        self.rows = len(rows)
        self._grid = [r.ljust(self.cols, ".") for r in rows]
        self._solid = set(solid)
        self._images = {}
        for char, name in legend.items():
            image = _load_images("tiles", name)[0][1]
            self._images[char] = pygame.transform.scale(image, (tile_size, tile_size))
        Stage._tilemaps.append(self)

    @property
    def width(self):                       # whole map width in pixels
        return self.cols * self.tile_size

    @property  
    def height(self):
        return self.rows * self.tile_size

    #Creates A Zone covering the whole map, handy for Stage.camera.limit_to(level.zone())
    def zone(self, colour="blue", name="map"):
        return Zone(self.width / 2, self.height / 2, self.width, self.height, colour, name)

    #Finds every tile with that character, and returns a list of (x, y) centres.
    #Great for start positions: x, y = level.find("P")[0]
    def find(self, char):
        ts = self.tile_size
        return [(c * ts + ts / 2, r * ts + ts / 2)
                for r in range(self.rows) for c in range(self.cols) if self._grid[r][c] == char]
    
    #Checks if Co-ordinates x,y contain a solid block
    def is_solid(self, x, y):
        return self._cell(int(x // self.tile_size), int(y // self.tile_size)) in self._solid

    #Checks if a Sprite is touching a specific character, if no character is provided, checks if theyre touching solid ground.
    def touching(self, sprite, char=None):
            rect = sprite._hitbox_rect()
            ts = self.tile_size
            # If a specific character is passed, check for that. Otherwise, use solid tiles.
            target_chars = set(char) if char is not None else self._solid
            for row in range(rect.top // ts, (rect.bottom - 1) // ts + 1):
                for col in range(rect.left // ts, (rect.right - 1) // ts + 1):
                    if self._cell(col, row) in target_chars:
                        return True
            return False

    def delete(self):
        Stage._tilemaps.remove(self)

    def _cell(self, col, row):
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return self._grid[row][col]
        return " "

    def _draw(self):                       # only draws the tiles the camera can see
        ts = self.tile_size
        ox, oy = Stage._offset()
        w, h = Screen.surface.get_size()
        for row in range(max(0, oy // ts), min(self.rows, (oy + h) // ts + 1)):
            for col in range(max(0, ox // ts), min(self.cols, (ox + w) // ts + 1)):
                image = self._images.get(self._grid[row][col])
                if image:
                    Screen.surface.blit(image, (col * ts - ox, row * ts - oy))


# ===== INPUT =====

#We Can Use Pygame To Detect What Keys are Being Pressed!
#Alot of this is used Internally However, in the Screen.update()
#However You Can Still Access These Via Keyboard.(function), For Example, Keyboard.held()

class _Keyboard:
    def __init__(self):
        self._pressed = set() # Note That a Set, is a Type of Iterable (List) that uses the {} Curly Brackets
        self._released = set()

    #This Function Returns Either True, or False Based on Whether the Inputed Key Is Held Down or Not.
    #Note That it uses the _key_code function, Which Converts a String Into A key code
    def held(self,key):
        return bool(pygame.key.get_pressed()[_key_code(key)])

    #This Function Simply Checks If A Key Was Pressed Last Frame

    def pressed(self, key):
        return _key_code(key) in self._pressed

    #This Function Simply Checks If A Key Was Released Last Frame

    def released(self, key):
        return _key_code(key) in self._released

    #These Clear The Sets Which Contain All Keys Pressed And Released Last Frame
    #This Is Automatically Called for You inside of Screen.update(), and is used internally
    def _new_frame(self):
        self._pressed.clear()
        self._released.clear()

    #This Function is also used internally, and makes ensures pressed or released contains the keyboard keys pressed/ released this frame
    def _handle(self, event):
        if event.type == pygame.KEYDOWN:
            self._pressed.add(event.key)
        elif event.type == pygame.KEYUP:
            self._released.add(event.key)

#Pygame Also Allows Us To Get Input From the Mouse
#Similarly, You Can Access this with Mouse.(function), e.g Mouse.down

class _Mouse():
    def __init__(self):
        self._clicked = False
        self._right_clicked = False
        self._middle_clicked = False

    #This Returns The Mouse's X Co-Ordinate (on the screen)
    @property
    def x(self):
        return pygame.mouse.get_pos()[0]

    #This Returns The Mouse's Y Co-Ordinate (on the screen)
    @property
    def y(self):
        return pygame.mouse.get_pos()[1]

    #Mouse position in the WORLD, rather than on the screen. They differ when the camera has moved!
    @property
    def world_x(self):
        return self.x + Stage._offset()[0]

    @property
    def world_y(self):
        return self.y + Stage._offset()[1]

    #This Checks If the Mouse's Left Click is Currently Being Held Down
    @property
    def left_down(self):
        return pygame.mouse.get_pressed()[0]

    down = left_down #down is Kept as a Shortcut for left_down

    #This Checks If the Mouse's Right Click is Currently Being Held Down
    @property
    def right_down(self):
        return pygame.mouse.get_pressed()[2]

    #This Checks If the Mouse's Middle Click is Currently Being Held Down
    @property
    def middle_down(self):
        return pygame.mouse.get_pressed()[1]

    #This Returns The Mouse has just been clicked.
    @property
    def clicked(self):
        return self._clicked

    #This Returns if Right Click Has Just Been Pressed
    @property
    def right_clicked(self):
        return self._right_clicked

    #This returns if Middle Click has Just Been Pressed
    @property
    def middle_clicked(self):
        return self._middle_clicked

    #The Rest of This Does Similar Things to self._pressed in Keyboard, by simply reseting every frame to False
    #and Showing True if it was clicked this Frame
    def _new_frame(self):
        self._clicked = False
        self._middle_clicked = False
        self._right_clicked = False

    def _handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self._clicked = True
            elif event.button == 2:
                self._middle_clicked = True
            elif event.button == 3:
                self._right_clicked = True


# ======SOUND======
class _Sound:
    def __init__(self):
        self._cache = {}               # sounds are stored here
        self._volume = 100             # a percentage, like Scratch
        self._works = pygame.mixer.get_init() is not None    # did pygame find the speakers?
        if not self._works:
            try:
                pygame.mixer.init()
                self._works = True
            except pygame.error:
                print("Warning!: Speakers not found, so sounds are switched off.")

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, percent):
        self._volume = max(0, min(100, percent))     # keeps it between 0 and 100
        if self._works:
            pygame.mixer.music.set_volume(self._volume / 100)


    #Play Sounds can Overlap Themselves!
    def play(self, name): 
        if name not in self._cache:
            path = _find_sound(name)   # runs even with no speakers, so typos are still caught
            try:
                self._cache[name] = pygame.mixer.Sound(path) if self._works else None
            except pygame.error as e:
                raise ValueError(f"Error!: Could not load '{name}' ({e}). Try a .wav or .ogg file!")
        sound = self._cache[name]
        if sound:
            sound.set_volume(self._volume / 100)
            sound.play()

    #play_music comes with an explicit number of loops to be played, using -1 will repeat the music infintely.
    def play_music(self, name, loops=-1):    # -1 means repeat forever
        path = _find_sound(name)
        if not self._works:
            return
        try:
            pygame.mixer.music.load(path)
        except pygame.error as e:
            raise ValueError(f"Error!: Could not load '{name}' ({e}). Try a .wav or .ogg file!")
        pygame.mixer.music.set_volume(self._volume / 100)
        pygame.mixer.music.play(loops)
    
    def stop_music(self):
        if self._works:
            pygame.mixer.music.stop()

    def stop_all(self):                # like Scratch's "stop all sounds"
        if self._works:
            pygame.mixer.stop()
            pygame.mixer.music.stop()


# ======RANDOM======

#This Code Uses The Random Module to generate a random number!
#To Use this Module, it must be imported at the top of the script, which is done automatically for you with this script.
#random_number, takes 2  numbers, a Min and a Max Number and generates a number between them.
def random_number(x,y):
    if not isinstance(x, int) or not isinstance(y, int):
        raise ValueError("Error!: random_number takes two integers as inputs, a min and a max!")

    return random.randint(x, y)

#random float also generates a random number, but this time its a decimal between 0 and 1
#Note That it Can generate the number 0, but not the number one, think of it as 0 <= x < 1
def random_float():
        return random.random()


# ====== SETUP ======

#There are a Few Final Things to Setup, Which we do at The End of This Script.
Screen = _Screen() # This Creates a New Screen, called "Screen". We call this Instantiating, Which is Creating a new Object out of a Class!
Keyboard = _Keyboard() # This Allows You To Uses Keyboard to Detect Keyboard input!
Mouse = _Mouse()
Stage = _Stage()
Sound = _Sound()