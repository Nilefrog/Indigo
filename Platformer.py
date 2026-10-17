from GameSnake import *

Screen.size(640, 360)
Screen.fps = 60

# --- Level Layouts ---
layout_1 = """
################################################
#xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx#
#xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx#
#xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx#
#xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx#
#xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx#
#xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx#
#xxxxxxxxxxxx00000xxxxxxxxxxxxxxxxxxxxxxxxxxxxx#
#xxxxxxxxxxxxxxxxxxxxx00000xxxxxxxxxxxxxxxxxxxx#
#xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx#
#xxxxxxxxxxx00000xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx#
#xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx#
#xxxxxxx00000xxxxxxxxxxxxxxx00000xxxxxxxxx^xxxx#
#xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxdxxxx#
#xxp000xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx000000000#
#0000000000000000000000000000000000000000000000#
################################################
"""

layout_2 = """
################################################
#xxxxxxxxxxxxx^xxxxxxxxxxxx00000xxxxxxxxxxxxxxx#
#xxxxxxxxxxxxxdxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx#
#xxxxxxxxxxx00000xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx#
#xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx#
#xxxxxxx00000xxxxxxxxxxxxxxx00000xxxxxxxxxxxxxx#
#xxxxxxxxxxxxxxxxx000xxxxxxxxxxxxxxxxxxxxxxxxxx#
#xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx#
#xxxxxx00000xxxxxxxxxxxx00000xxxxxxxxxxxxxxxxxx#
#xxxxxxxxxxxxxxxxxxxxxx0xxxxxxxxxxxxxxxxxxxxxxx#
#xxxxxxxxxxxxxxxxxxxx0xxxxxxxxxxxxxxxxxxxxxxxxx#
#xxxxxxxxxxxxxxxxx0xxxxxxxxxxxxxxxxxxxxxxxxxxxx#
#xxxxxxxxxxxx0xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx#
#xxxxxxxx0xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx#
#xxp000xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx#
#0000000000000000000000000000000000000000000000#
################################################
"""

legend = {
    "0": "ground",
    "#": "wall",
    "d": "door_bottom",
    "^": "door_top"
}

# --- Game State ---
current_level_num = 1

def load_level(level_num):
    global level, camera_zone, player_x, player_y
    
    if 'level' in globals():
        level.delete()
        camera_zone.delete()
        
    layout = layout_1 if level_num == 1 else layout_2
    level = TileMap(layout, legend, tile_size=32, solid="0#")
    
    camera_zone = level.zone()
    Stage.camera.limit_to(camera_zone)
    
    px, py = level.find("p")[0]
    player.go_to(px, py)

# Initialize Player, Overlay, and First Level
player = Sprite("player", 0, 0)
player.set_hitbox(20, 25, 0, 0)

# Screen overlay sprite for the transition effect (make sure you have a folder named 'transition' inside your 'sprites' folder with multiple costume images!)
overlay = Sprite("transition", Screen.width / 2, Screen.height / 2)
overlay.fixed = True
overlay.visible = False
transition_backward = False

load_level(1)
Screen.set_resizable(True)
Stage.camera.follow(player)

speed = 5
jump_strength = 12
gravity = 0.6

velocity_y = 0
on_ground = False

# Transition Control Variables
transitioning = False
transition_timer = 0
transition_duration = 30  # Total frames for the transition animation

while Screen.running:
    # --- Door Detection & Trigger ---
    ts = level.tile_size
    rect = player._hitbox_rect()
    

    if level.touching(player,"d") and (Keyboard.pressed("up") or Keyboard.pressed("w")) and not transitioning:
        transitioning = True
        transition_backward = False
        transition_timer = 0
        overlay.show()

    # --- Transition Animation & Level Swap ---
    if transitioning:
        transition_timer += 1
        if transition_timer % 15 == 0 and not transition_backward:
            transition_backward = True
        # Cycle through costumes every 5 frames
        if transition_timer % 5 == 0 and transition_backward == False:
            overlay.switch_costume(f"Transition-{int(transition_timer / 5 )}")
        elif transition_timer % 5 == 0:
            overlay.switch_costume(f"Transition-{6-int(transition_timer / 5 )}")
            
        # Swap level halfway through the animation
        if transition_timer == transition_duration // 2:
            if current_level_num == 1:
                current_level_num = 2
                load_level(2)
            else:
                current_level_num = 1
                load_level(1)
                
        # End transition
        if transition_timer >= transition_duration:
            transition_backward = False
            transitioning = False
            overlay.hide()
            
    else:
        # --- Normal Gameplay & Movement Logic (Frozen during transition) ---
        old_x = player.x
        old_y = player.y

        if Keyboard.held("left") or Keyboard.held("a"):
            player.x -= speed

        if Keyboard.held("right") or Keyboard.held("d"):
            player.x += speed

        if level.touching(player):
            player.x = old_x

        if Keyboard.pressed("space") and on_ground:
            velocity_y = -jump_strength
            on_ground = False

        velocity_y += gravity
        player.y += velocity_y

        if level.touching(player):
            player.y = old_y

            if velocity_y > 0:
                on_ground = True

            velocity_y = 0
        else:
            on_ground = False

    Screen.update()