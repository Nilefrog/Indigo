from GameSnake import *

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
ZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxpxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxZ
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

#CLASSES
class Player(Sprite):

    def __init__(self,currentLevel, name, x=None, y=None, size=100):
        super().__init__(name, x, y, size)
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

        px, py = currentLevel.find("p")[0]
        self.go_to(px,py)

    def handle_movement(self,currentLevel: TileMap):
        old_y = self.y
        old_x = self.x

        #Decrementing Movement Related Timers 
        if self.jump_buffer > 0: self.jump_buffer -= 1
        if self.coyote_time > 0: self.coyote_time -= 1
        if self.actionableTimer > 0: self.actionableTimer -= 1
        if self.NoGravTimer > 0: self.NoGravTimer -= 1

        if self.actionableTimer == 0: #actionability check
            self.actionable = True
        else:
            self.actionable = False

        if self.NoGravTimer == 0: #account for gravity
            self.y_velocity += self.gravity
        if Keyboard.pressed("space"):
                self.jump_buffer = 5    
        if self.actionable:

            #Jump Logic
            if self.jump_buffer != 0 and self.jump_charges > 0 and self.coyote_time == 0:
                self.jump_charges -= 1
                self.y_velocity = -self.jump_velocity
                self.jump_buffer = 0
            elif self.jump_buffer != 0 and self.coyote_time != 0:
                self.y_velocity = -self.jump_velocity
                self.jump_buffer = 0

            #Walk Logic
            if self.coyote_time == 4: #A Grounded Check

                #Calculate Friction
                if self.x_velocity > 0:
                    self.x_velocity -= self.walk_decceleration
                    if self.x_velocity < 0:
                        self.x_velocity = 0
                if self.x_velocity < 0:
                    self.x_velocity += self.walk_decceleration
                    if self.x_velocity > 0:
                        self.x_velocity = 0

                if Keyboard.held("a"):
                    if self.x_velocity > -self.max_speed:
                        self.x_velocity -= self.walk_acceleration
                        if self.x_velocity < -self.max_speed:
                            self.x_velocity = -self.max_speed

                if Keyboard.held("d"):
                    if self.x_velocity < self.max_speed:
                        self.x_velocity += self.walk_acceleration
                        if self.x_velocity > self.max_speed:
                            self.x_velocity = self.max_speed
            else: # Arial Movement Options
                
                #Calculate Friction
                if self.x_velocity > 0:
                    self.x_velocity -= self.air_decceleration
                    if self.x_velocity < 0:
                        self.x_velocity = 0
                if self.x_velocity < 0:
                    self.x_velocity += self.air_decceleration
                    if self.x_velocity > 0:
                        self.x_velocity = 0

                if Keyboard.held("a"):
                    if self.x_velocity > -self.max_speed:
                        self.x_velocity -= self.air_acceleration
                        if self.x_velocity < -self.max_speed:
                            self.x_velocity = -self.max_speed

                if Keyboard.held("d"):
                    if self.x_velocity < self.max_speed:
                        self.x_velocity += self.air_acceleration
                        if self.x_velocity > self.max_speed:
                            self.x_velocity = self.max_speed

                if Keyboard.pressed("left shift") and self.dash_charges > 0:
                    self.dash_charges -= 1
                    currentInputDir = 0
                    if Keyboard.held("a"): currentInputDir -= 1
                    if Keyboard.held("d"): currentInputDir += 1
                    if currentInputDir == 0:
                        if self.x_velocity > 0:
                            currentInputDir = 1
                        elif self.x_velocity < 0:
                            currentInputDir = -1
                        else:
                            currentInputDir = 1    #Fallback failsafe for if you just dash without moving
                    self.x_velocity = self.dash_speed * currentInputDir
                    self.actionableTimer = 10
                    self.NoGravTimer = 10
                    self.y_velocity = 0

        self.x += self.x_velocity
        if level.touching(self):
            self.x = old_x
            self.x_velocity = 0

        self.y += self.y_velocity
        if currentLevel.touching(self):
            self.coyote_time = 5
            self.y = old_y
            if not self.y_velocity < 0:
                self.dash_charges = self.max_dash_charges
                self.jump_charges = self.max_jump_charges
            self.y_velocity = 0
        

            
#SETUP
load_level(1,allLevels,allLegends)
player1 = Player(level, "player", 0, 0)
player1.set_hitbox(20, 25, 0, 0)
Stage.camera.go_to(player1.x,player1.y)

#GAMELOOP
while Screen.running:
    player1.handle_movement(level)

    if level.touching(player1,"Z"):
        print(player1.y)
        px, py = level.find("p")[0]
        player1.go_to(px,py)        
    Screen.update()