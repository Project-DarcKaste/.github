'''main.py
---
Mostly cosists of the actual raycaster.
Also has some other stuff
<hr/>
<code>Coded by: Github Copilot, Jayden Mays</code>'''
import pygame
import math
import json
import os
import random
import tkinter as tk
from tkinter import *
import debug_menu
from debug_menu import DevTools
import music as mus
from music import *

'''#################################################
Labels are placed in the code for navigation purposes
#labels are:
initpyg
sounds
vars1
CLASSGameState
kbdin
'''#################################################


# Initialize Pygame
#initpyg
pygame.init()
pygame.font.init()
ico = pygame.image.load("Assets\\_Backups\\Raycaster_20.ico" if not os.path.exists("Assets\\Icons\\darckaste_ico2_16x16.ico") else "Assets\\Icons\\darckaste_ico2_16x16.ico")
pygame.display.set_icon(ico)

#sounds
sfx_chan = pygame.mixer.Channel(1)
footstep = pygame.mixer.Sound("Assets/Audio/footstep.wav")
footstep_hard = pygame.mixer.Sound("Assets/Audio/footstep_hard.wav")
menu_sel = pygame.mixer.Sound("Assets/Audio/menu_select.wav")
menu_back = pygame.mixer.Sound("Assets/Audio/menu_back.wav")

#cursors
CUR_CROSS = pygame.cursors.Cursor((27,27),pygame.image.load("Assets\\Cursors\\cur_cross.png"))
CUR_POINTER = pygame.cursors.Cursor((0,0),pygame.image.load("Assets\\Cursors\\cur_pointer_large.png"))
CUR_SELECT = pygame.cursors.Cursor((3,3),pygame.image.load("Assets\\Cursors\\cur_select_large.png"))


FONT = "Poor Richard"
ACCENT_COLOR = "#DC143C"
A_ALIAS = False

# Constants
#vars1
SCREEN_WIDTH = pygame.display.get_desktop_sizes()[0][0]
SCREEN_HEIGHT = pygame.display.get_desktop_sizes()[0][1]
FOV = math.pi / 3  # 60 degrees field of view
HALF_FOV = FOV / 2
RAYS = pygame.display.get_desktop_sizes()[0][0] # Further reduced rays for performance
STEP_ANGLE = FOV / RAYS
MAX_DEPTH = 1920
print("Variables:")
print("Max Depth set to:", MAX_DEPTH)
print("Rays set to:", RAYS)
print("Step Angle set to:", STEP_ANGLE)
print("Half FOV set to:", HALF_FOV)
print("FOV set to (degrees):", math.degrees(FOV))
print("Screen Width:", SCREEN_WIDTH)
print("Screen Height:", SCREEN_HEIGHT)
print("Screen Aspect Ratio:", SCREEN_WIDTH / SCREEN_HEIGHT)
print()

# Menu and game settings
MIN_WALL_HEIGHT = 20  # Don't render very small wall slices
print("Min Wall Height set to:", MIN_WALL_HEIGHT)
print()

#CLASSGameState
class GameState:
    def __init__(self):
        # Game state
        self.paused = False
        self.selected_option = 0
        self.last_tab = False
        
        # Menu animation state
        self.menu_offset = SCREEN_HEIGHT  # Start offscreen
        self.target_offset = SCREEN_HEIGHT
        self.menu_alpha = 0  # For fade effect
        self.target_alpha = 0
        self.settings_offset = SCREEN_WIDTH  # For settings slide
        self.target_settings_offset = SCREEN_WIDTH
        self.last_time = pygame.time.get_ticks()
        
        # Settings (with min/max values)
        self.settings = {
            'Quality': {
                'value': 0,
                'min': 0,
                'max': 2,
                'options': ['Low', 'Medium', 'High']
            },
            'FOV': {
                'value': 70,
                'min': 45,
                'max': 90,
                'step': 5
            },
            'Mouse Sensitivity': {
                'value': 40,
                'min': 10,
                'max': 100,
                'step': 1
            },
            'Max Fps': {
                'value': 60,
                'min': 10,
                'max': 240,
                'step': 1
            },
            'Detail': {
                'value': 0,
                'min': 0,
                'max': 1,
                'options': ['Performance','Quality']
            }
            }
        print("Default Settings:", self.settings,"\n")

        # Menu options
        self.menu_options = ['Resume', 'Settings', 'New Map', 'Exit']
        self.in_settings = False
        self.selected_setting = 0
        self.transitioning_map = True  # For map transition effect
        
        # Load saved settings if they exist
        self.load_settings()

    @property
    def quick_mode(self):
        return self.settings['Quality']['value'] == 0
        
    def get_detail_reduction(self):
        quality = self.settings['Quality']['value']
        if quality == 0:  # Low
            return 0.015  # Keep low quality the same for weak hardware
        elif quality == 1:  # Medium
            return 0.15  # Better balance between quality and performance
        else:  # High
            return 0.035  # Optimized high quality - still detailed but more efficient
            
    def get_fov(self):
        return math.radians(self.settings['FOV']['value'])
        
    def get_mouse_sensitivity(self):
        return self.settings['Mouse Sensitivity']['value']

    def warn(self,msg="Message",font_size=18,btn="Ok",btn_font_size=12,title="Title",wid=200,hei=100,x=100,y=100,icon="Assets\\_Backups\\Raycaster_20.ico"):
        '''Messenger Function
        ---
        Handles the messaging system that I made. Like that "Restart to apply changes." thing that appears every time you exit the settings.'''
        pygame.mouse.set_visible(True)
        message = tk.Tk()
        Tk.title(message,title)
        Tk.iconbitmap(message,bitmap=icon)

        message.geometry(f"{wid}x{hei}+{x}+{y}")
        message.overrideredirect(True)

        frame = tk.Frame(
            message,
            relief=FLAT,
            borderwidth=0,
            bg="#000000"
            ) 
        frame.pack(
            fill=BOTH,
            expand=1
            )

        label = tk.Label(
            frame,
            text=msg,
            font=(FONT,font_size),
            fg=ACCENT_COLOR,
            bg="#000000"
            ) 
        label.pack(fill="none", expand=1) 

        button = tk.Button(
            frame,
            text=btn,
            relief=FLAT,
            borderwidth=2,
            command=lambda: (message.destroy(),pygame.mouse.set_visible(False) if state.paused == 0 else pygame.mouse.set_visible(True)),
            font=(FONT,btn_font_size),
            fg=ACCENT_COLOR,
            bg="#000000",
            activebackground="#000000",
            activeforeground="Alice Blue",
            takefocus=True
            ) 
        button.pack(side="right",padx=5,pady=5)

        tk.mainloop()

    def get_max_fps(self):
        '''Get the max FPS, presumably from settings.json'''
        return self.settings['Max Fps']['value']
    
    def get_detail(self):
        '''Get the detail level.'''
        return self.settings['Detail']['value']

    def next_menu_item(self):
        if self.in_settings:
            self.selected_setting = (self.selected_setting + 1) % len(self.settings)
        else:
            self.selected_option = (self.selected_option + 1) % len(self.menu_options)
            
    def prev_menu_item(self):
        if self.in_settings:
            self.selected_setting = (self.selected_setting - 1) % len(self.settings)
        else:
            self.selected_option = (self.selected_option - 1) % len(self.menu_options)
            
    def adjust_setting(self,direction):
        if not self.in_settings:
            return
            
        setting_name = list(self.settings.keys())[self.selected_setting]
        setting = self.settings[setting_name]
        
        if 'options' in setting:  # Discrete options
            current = setting['value']
            if direction > 0:
                setting['value'] = min(setting['max'], current + 1)
            else:
                setting['value'] = max(setting['min'], current - 1)
        else:  # Continuous value
            current = setting['value']
            if direction > 0:
                setting['value'] = min(setting['max'], current + setting['step'])
            else:
                setting['value'] = max(setting['min'], current - setting['step'])
        
        # Save settings whenever they are changed
        self.save_settings()

    def detect_exit_settings(self):
        '''Not necessary'''
        self.settings_open = False
        print("Detecting...")

        if state.in_settings == True and self.settings_open == False:
            print("in settings")
            self.settings_open = True

        elif self.settings_open == True and state.in_settings == False:
            print("not in settings")
            self.settings_open = False

    def save_settings(self):
        """Save current settings to a JSON file"""

        state.detect_exit_settings()
        settings_data = {}
        for name, setting in self.settings.items():
            settings_data[name] = {'value': setting['value']}

        settings_path = os.path.join(os.path.dirname(__file__), 'settings.json')

        try:
            with open(settings_path, 'w') as f:
                json.dump(settings_data, f, indent=4)
        except Exception as e:
            print(f"Failed to save settings: {e}")
    
    def load_settings(self):
        """Load settings from JSON file if it exists"""
        settings_path = os.path.join(os.path.dirname(__file__), 'settings.json')
        try:
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    settings_data = json.load(f)
                    for name, data in settings_data.items():
                        if name in self.settings:
                            # Ensure value is within bounds
                            value = data['value']
                            setting = self.settings[name]
                            value = max(setting['min'], min(setting['max'], value))
                            setting['value'] = value
        except Exception as e:
            print(f"Failed to load settings: {e}")



# Create game state
state = GameState()
print("Game State initialized.\n")

# Menu colors and font settings
MENU_BG = (0, 0, 0, 180)
MENU_FG = (240, 248, 255)
MENU_SELECTED = ACCENT_COLOR
menu_font = None  # Will be initialized with Pygame
print(f"MENU_FG = Alice Blue\nMENU_BG = Black\nMENU_SELECTED = {ACCENT_COLOR}\n")

# Initialize Pygame
pygame.init()
pygame.font.init()
print("Pygame initialized.\n")

# Constants
SCREEN_WIDTH = int(pygame.display.get_desktop_sizes()[0][0])
SCREEN_HEIGHT = int(pygame.display.get_desktop_sizes()[0][1])
MAX_DEPTH = SCREEN_WIDTH*2
print("Aspect Ratio: 16:9\n")
print(pygame.display.get_desktop_sizes(),"\n",pygame.display.Info(),"\n")

# Initialize fonts
font = pygame.font.SysFont(FONT, 16)
menu_font = pygame.font.SysFont(FONT, 32)
setting_font = pygame.font.SysFont(FONT, 24)
show_fps = True

def get_menu_item_rect(i, text, is_settings=False):
    """Get the rectangle for a menu item for mouse detection"""
    if is_settings:
        x = SCREEN_WIDTH // 4
        y = SCREEN_HEIGHT // 4 + i * 50
        width = SCREEN_WIDTH // 2
        height = 40
    else:
        x = SCREEN_WIDTH // 4
        y = SCREEN_HEIGHT // 2 - len(state.menu_options) * 30 + i * 60
        width = SCREEN_WIDTH // 2
        height = 40
    return pygame.Rect(x, y, width, height)

def update_menu_animation():
    """Update menu animation states"""
    current_time = pygame.time.get_ticks()
    delta_time = (current_time - state.last_time) / 1000.0  # Convert to seconds
    state.last_time = current_time
    
    # Animation speeds
    SLIDE_SPEED = 500000  # pixels per second
    FADE_SPEED = 400  # alpha per second
    
    # Update target positions based on menu state
    state.target_offset = 0 if state.paused else SCREEN_HEIGHT
    state.target_alpha = 120 if state.paused else 0
    state.target_settings_offset = 0 if state.in_settings else SCREEN_WIDTH
    
    # Smoothly animate menu position
    if state.menu_offset < state.target_offset:
        state.menu_offset = min(state.target_offset, 
                              state.menu_offset + SLIDE_SPEED * delta_time)
    elif state.menu_offset > state.target_offset:
        state.menu_offset = max(state.target_offset, 
                              state.menu_offset - SLIDE_SPEED * delta_time)
    
    # Smoothly animate settings slide
    if state.settings_offset < state.target_settings_offset:
        state.settings_offset = min(state.target_settings_offset, 
                                  state.settings_offset + SLIDE_SPEED * delta_time)
    elif state.settings_offset > state.target_settings_offset:
        state.settings_offset = max(state.target_settings_offset, 
                                  state.settings_offset - SLIDE_SPEED * delta_time)
    
    # Smoothly animate overlay alpha
    if state.menu_alpha < state.target_alpha:
        state.menu_alpha = min(state.target_alpha, 
                             state.menu_alpha + FADE_SPEED * delta_time)
    elif state.menu_alpha > state.target_alpha:
        state.menu_alpha = max(state.target_alpha, 
                             state.menu_alpha - FADE_SPEED * delta_time)

def get_cursor():
    '''Detects if mouse is pressed, and changes the cursor accordingly'''
    if pygame.mouse.get_pressed()[0] == 1 and state.paused == 1:
        pygame.mouse.set_cursor(CUR_SELECT)
    elif state.paused == 1:
        pygame.mouse.set_cursor(CUR_POINTER)
    else:
        pygame.mouse.set_cursor(CUR_CROSS)

def draw_menu():
    update_menu_animation()
    
    # Create semi-transparent overlay with animated alpha
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, int(state.menu_alpha)))
    screen.blit(overlay, (0, 0))
    
    # Get mouse position
    mouse_pos = pygame.mouse.get_pos()
    
    # Create menu surface for sliding animation
    menu_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    
    if not state.in_settings:
        # Draw main menu
        for i, option in enumerate(state.menu_options):
            # Check if mouse is hovering over this option
            item_rect = get_menu_item_rect(i, option)
            hover = item_rect.collidepoint(mouse_pos)
            
            # Update selection if mouse is hovering
            if hover and state.selected_option != i:
                state.selected_option = i
            
            color = MENU_SELECTED if i == state.selected_option else MENU_FG
            text = menu_font.render(option, A_ALIAS, color)
            x = SCREEN_WIDTH // 2 - text.get_width() // 2
            y = item_rect.y + (item_rect.height - text.get_height()) // 2
            menu_surf.blit(text, (x, y - state.menu_offset))
            
            # Draw subtle highlight box when selected
            if i == state.selected_option:
                pygame.draw.rect(menu_surf, color, 
                               (item_rect.x, item_rect.y - state.menu_offset,
                                item_rect.width, item_rect.height), 2, 10)
    
    # Apply main menu surface
    screen.blit(menu_surf, (0, 0))
    
    if state.in_settings:
        # Create settings surface for slide animation
        settings_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        
        # Draw settings menu
        title = menu_font.render("Settings", A_ALIAS, MENU_FG)
        settings_surf.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 50))
        
        for i, (setting_name, setting) in enumerate(state.settings.items()):
            # Check if mouse is hovering over this setting
            item_rect = get_menu_item_rect(i, setting_name, True)
            hover = item_rect.collidepoint(mouse_pos)
            
            # Update selection if mouse is hovering
            if hover and state.selected_setting != i:
                state.selected_setting = i
            
            color = MENU_SELECTED if i == state.selected_setting else MENU_FG
            
            # Render setting name
            name_text = setting_font.render(setting_name, A_ALIAS, color)
            x = SCREEN_WIDTH // 4
            y = item_rect.y + (item_rect.height - name_text.get_height()) // 2
            settings_surf.blit(name_text, (x, y))
            
            # Render setting value and controls
            # Draw slider track
            slider_width = SCREEN_WIDTH // 4
            slider_x = SCREEN_WIDTH * 3 // 4 - slider_width
            pygame.draw.rect(settings_surf, GRAY, (slider_x, y + item_rect.height//2 - 2, slider_width, 4))
            
            if 'options' in setting:  # Discrete slider (Quality)
                # Draw slider segments
                segment_width = slider_width // len(setting['options'])
                for j in range(len(setting['options'])):
                    segment_x = slider_x + j * segment_width
                    pygame.draw.circle(settings_surf, GRAY, (segment_x, y + item_rect.height//2), 4)
                
                # Draw slider handle
                handle_x = slider_x + (setting['value'] * segment_width)
                pygame.draw.circle(settings_surf, color, (handle_x, y + item_rect.height//2), 8)
                
                # Handle mouse interaction
                if hover and pygame.mouse.get_pressed()[0]:
                    pygame.mixer.Sound.play(menu_sel,loops=1)  # If mouse is held down
                    mouse_x = mouse_pos[0]
                    if slider_x <= mouse_x <= slider_x + slider_width:
                        # Calculate nearest segment
                        segment = int((mouse_x - slider_x) / segment_width + 0.5)
                        segment = max(0, min(len(setting['options'])-1, segment))
                        if setting['value'] != segment:
                            setting['value'] = segment
                            state.save_settings()
                
                # Display current value text
                value_text = setting['options'][setting['value']]
                
            else:  # Continuous slider (FOV and Sensitivity)
                # Calculate value range
                value_range = setting['max'] - setting['min']
                value_pos = (setting['value'] - setting['min']) / value_range
                
                # Draw slider handle
                handle_x = slider_x + (value_pos * slider_width)
                pygame.draw.circle(settings_surf, color, (handle_x, y + item_rect.height//2), 8)
                
                # Handle mouse interaction
                if hover and pygame.mouse.get_pressed()[0]:
                    pygame.mixer.Sound.play(menu_sel,loops=1)  # If mouse is held down
                    mouse_x = mouse_pos[0]
                    if slider_x <= mouse_x <= slider_x + slider_width:
                        # Calculate new value
                        value_pos = (mouse_x - slider_x) / slider_width
                        new_value = setting['min'] + (value_pos * value_range)
                        # Round to nearest step if step is defined
                        if 'step' in setting:
                            new_value = round(new_value / setting['step']) * setting['step']
                        new_value = max(setting['min'], min(setting['max'], new_value))
                        if setting['value'] != new_value:
                            setting['value'] = new_value
                            state.save_settings()
                
                # Display current value text
                if setting['value'] < 1:
                    value_text = f"{setting['value']:.3f}"
                else:
                    value_text = f"{int(setting['value'])}"
                    if setting_name == 'FOV':
                        value_text += "°"
            
            # Display value text for all settings
            value_surface = setting_font.render(value_text, A_ALIAS, color)
            settings_surf.blit(value_surface, (slider_x - value_surface.get_width() - 10, y))
            
            # Draw subtle highlight box when selected
            if i == state.selected_setting:
                pygame.draw.rect(settings_surf, color, item_rect, 2,10)
        
        # Apply settings surface with slide animation
        screen.blit(settings_surf, (state.settings_offset, 0))

# Create surfaces for floor and ceiling
floor_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT // 2), pygame.SRCALPHA)
ceil_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT // 2), pygame.SRCALPHA)

# Performance monitoring
font = pygame.font.SysFont(FONT, 16)
show_fps = True

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GRAY = (128, 128, 128)
FLOOR_DARK = (40, 40, 40)
FLOOR_LIGHT = (60, 60, 60)
CEIL_DARK = (80, 80, 100)
CEIL_LIGHT = (100, 100, 120)

# Texture settings
TEXTURE_SIZE = 64  # Size of texture tiles
textures = {}  # Dictionary to store loaded textures

def load_textures():
    """Load and prepare wall textures"""
    global textures
    
    # Create a brick texture
    brick = pygame.Surface((TEXTURE_SIZE, TEXTURE_SIZE))
    brick.fill((120, 60, 60))  # Base brick color
    
    # Draw brick pattern
    brick_height = 16
    brick_width = 32
    mortar_color = (80, 40, 40)
    for y in range(0, TEXTURE_SIZE, brick_height):
        offset = (y // brick_height % 2) * (brick_width // 2)
        for x in range(-brick_width // 2, TEXTURE_SIZE + brick_width // 2, brick_width):
            # Draw brick
            brick_x = x + offset
            if brick_x < TEXTURE_SIZE and brick_x + brick_width > 0:
                # Actual brick
                pygame.draw.rect(brick, (140, 70, 70), 
                               (max(0, brick_x), y, 
                                min(brick_width, TEXTURE_SIZE - brick_x), brick_height-2))
                # Mortar lines
                pygame.draw.rect(brick, mortar_color,
                               (max(0, brick_x), y+brick_height-2, 
                                min(brick_width, TEXTURE_SIZE - brick_x), 2))
                if brick_x >= 0:
                    pygame.draw.rect(brick, mortar_color, (brick_x, y, 2, brick_height))
    textures['brick'] = brick
    
    # Create a stone texture
    stone = pygame.Surface((TEXTURE_SIZE, TEXTURE_SIZE))
    stone.fill((90, 90, 95))  # Base stone color
    
    # Draw stone pattern
    stone_sizes = [(20, 20), (30, 15), (15, 30), (25, 25)]
    for y in range(0, TEXTURE_SIZE, 15):
        for x in range(0, TEXTURE_SIZE, 20):
            # Stone block
            w, h = stone_sizes[(x + y) % len(stone_sizes)]
            if x + w > TEXTURE_SIZE: w = TEXTURE_SIZE - x
            if y + h > TEXTURE_SIZE: h = TEXTURE_SIZE - y
            
            # Random stone variation
            value = random.randint(-20, 20)
            color = (90 + value, 90 + value, 95 + value)
            pygame.draw.rect(stone, color, (x, y, w-2, h-2))
            # Mortar
            pygame.draw.rect(stone, (60, 60, 65), (x+w-2, y, 2, h))
            pygame.draw.rect(stone, (60, 60, 65), (x, y+h-2, w, 2))
    textures['stone'] = stone
    
    # Create a metal texture
    metal = pygame.Surface((TEXTURE_SIZE, TEXTURE_SIZE))
    metal.fill((60, 65, 70))  # Base metal color
    
    # Draw metal panel pattern
    panel_width = 16
    for x in range(0, TEXTURE_SIZE, panel_width):
        # Panel with slight color variation
        panel_color = (60 + random.randint(-5, 5), 
                      65 + random.randint(-5, 5), 
                      70 + random.randint(-5, 5))
        pygame.draw.rect(metal, panel_color, (x, 0, panel_width-1, TEXTURE_SIZE))
        # Vertical seam
        pygame.draw.rect(metal, (40, 45, 50), (x+panel_width-1, 0, 1, TEXTURE_SIZE))
        # Rivets
        for y in range(8, TEXTURE_SIZE-8, 16):
            pygame.draw.circle(metal, (80, 85, 90), (x + panel_width//2, y), 2)
            pygame.draw.circle(metal, (40, 45, 50), (x + panel_width//2, y), 2, 1)
    textures['metal'] = metal

# Mode 7 settings
SCREEN_DIST = SCREEN_HEIGHT / 2  # Distance to projection plane
FLOOR_STEP = 1  # Ray step size for floor casting
CHECKER_SIZE = 32  # Size of floor/ceiling checkerboard tiles

def get_floor_color(x, y):
    """Get checkerboard pattern color for floor coordinates."""
    checker_x = (x // CHECKER_SIZE) % 2
    checker_y = (y // CHECKER_SIZE) % 2
    return FLOOR_LIGHT if (checker_x + checker_y) % 2 else FLOOR_DARK

def get_ceil_color(x, y):
    """Get checkerboard pattern color for ceiling coordinates."""
    checker_x = (x // CHECKER_SIZE) % 2
    checker_y = (y // CHECKER_SIZE) % 2
    return CEIL_LIGHT if (checker_x + checker_y) % 2 else CEIL_DARK

# Player settings
player_x = random.randrange(16,256,1)
player_y = random.randrange(16,256,1)
player_angle = 0
PLAYER_SPEED = 2  # slower walking speed
TURN_SPEED = 0.1
PLAYER_RADIUS = 16  # collision radius in pixels
MOUSE_SENSITIVITY = 0.003  # radians per pixel of mouse movement
CAMERA_PITCH = 0  # vertical camera offset in pixels
MAX_PITCH = SCREEN_HEIGHT // 4  # limit how far up/down you can look
KEY_PITCH_SPEED = 4  # pixels per frame when using keys

# Map generation settings
MAP_TILES_WIDTH = random.randrange(16,256,1)
MAP_TILES_HEIGHT = random.randrange(16,256,1)
TILE_SIZE = random.randrange(16,64,1)
MIN_ROOM_SIZE = random.randrange(1,3,1)
MAX_ROOM_SIZE = random.randrange(4,16,1)
MIN_ROOMS = random.randrange(2,4,1)
MAX_ROOMS = random.randrange(16,128,1)

def generate_empty_map():
    """Generate an empty map with walls around the edges"""
    return [[1 if i == 0 or i == MAP_TILES_WIDTH-1 or j == 0 or j == MAP_TILES_HEIGHT-1 
             else 1 for i in range(MAP_TILES_WIDTH)] for j in range(MAP_TILES_HEIGHT)]

def create_room(map_data, x, y, width, height):
    """Create a rectangular room"""
    for i in range(max(1, y), min(MAP_TILES_HEIGHT-1, y + height)):
        for j in range(max(1, x), min(MAP_TILES_WIDTH-1, x + width)):
            map_data[i][j] = 0

def create_corridor(map_data, x1, y1, x2, y2):
    """Create a corridor between two points"""
    # Horizontal then vertical
    for x in range(min(x1, x2), max(x1, x2) + 1):
        if 0 < x < MAP_TILES_WIDTH-1 and 0 < y1 < MAP_TILES_HEIGHT-1:
            map_data[y1][x] = 0
    for y in range(min(y1, y2), max(y1, y2) + 1):
        if 0 < x2 < MAP_TILES_WIDTH-1 and 0 < y < MAP_TILES_HEIGHT-1:
            map_data[y][x2] = 0

def generate_random_map():
    """Generate a random dungeon-like map"""
    import random
    
    # Start with solid walls
    global map_data
    map_data = generate_empty_map()
    rooms = []
    # Generate random rooms
    num_rooms = random.randint(MIN_ROOMS, MAX_ROOMS)
    attempts = 0
    max_attempts = 100
    
    while len(rooms) < num_rooms and attempts < max_attempts:
        width = random.randint(MIN_ROOM_SIZE, MAX_ROOM_SIZE)
        height = random.randint(MIN_ROOM_SIZE, MAX_ROOM_SIZE)
        x = random.randint(1, MAP_TILES_WIDTH - width - 1)
        y = random.randint(1, MAP_TILES_HEIGHT - height - 1)
        
        # Check if room overlaps with existing rooms
        overlaps = False
        room = {"x": x, "y": y, "width": width, "height": height}
        
        for other in rooms:
            if (x < other["x"] + other["width"] + 1 and x + width + 1 > other["x"] and
                y < other["y"] + other["height"] + 1 and y + height + 1 > other["y"]):
                overlaps = True
                break
        
        if not overlaps:
            create_room(map_data, x, y, width, height)
            if rooms:  # Connect to previous room
                prev_room = rooms[-1]
                px = prev_room["x"] + prev_room["width"]//2
                py = prev_room["y"] + prev_room["height"]//2
                cx = x + width//2
                cy = y + height//2
                create_corridor(map_data, px, py, cx, cy)
            rooms.append(room)
        
        attempts += 1


    # Ensure player spawn point is clear
    map_data[1][1] = 0
    map_data[1][2] = 0
    map_data[1][3] = 0
    map_data[1][4] = 0
    map_data[1][5] = 0
    map_data[2][1] = 0
    map_data[2][2] = 0
    map_data[2][3] = 0
    map_data[2][4] = 0
    map_data[2][5] = 0

    for row in map_data:
        for col in row:
            if col == 1:
                print("█", end="█")
            elif col == 0:
                print(" ", end=" ")
        print()
    print()


    return map_data

def insta_quit():
    pygame.quit()


def reset_to_new_map():
    """Generate a new map and reset player position"""
    global MAP, MAP_WIDTH, MAP_HEIGHT, player_x, player_y, player_angle
    MAP = generate_random_map()
    MAP_WIDTH = len(MAP[0]) * TILE_SIZE
    MAP_HEIGHT = len(MAP) * TILE_SIZE
    player_x = TILE_SIZE * 1.5
    player_y = TILE_SIZE * 1.5
    player_angle = 0

# Create initial map
reset_to_new_map()

# Load textures
load_textures()

# Set up the display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT),pygame.NOFRAME,0,0,1)
pygame.display.set_caption("DarcKaste")



#get new screen info
print(pygame.display.get_window_size(), "\n", pygame.display.Info(),"\n")

# Hide cursor and capture mouse for mouselook
pygame.mouse.set_visible(False)
pygame.event.set_grab(True)
pygame.mouse.get_rel()  # flush any pending motion

def cast_ray(angle):
    # Find distance to wall
    x, y = player_x, player_y
    sin_a = math.sin(angle)
    cos_a = math.cos(angle)
    
    # Ray increments
    ray_x = cos_a * 2
    ray_y = sin_a * 2
    
    # Distance
    dist = 0
    
    while dist < MAX_DEPTH:
        dist += 2
        
        # New position
        x += ray_x
        y += ray_y
        
        # Check map bounds
        map_x = int(x / TILE_SIZE)
        map_y = int(y / TILE_SIZE)
        
        # Check if ray hits wall
        if map_x < 0 or map_x >= len(MAP[0]) or map_y < 0 or map_y >= len(MAP):
            break
            
        if MAP[map_y][map_x] == 1:
            # Calculate texture coordinate
            hit_x = x % TILE_SIZE
            hit_y = y % TILE_SIZE
            
            # Determine which side of the wall was hit
            if abs(x - map_x * TILE_SIZE) < 2:  # Vertical wall hit
                tex_x = hit_y
            else:  # Horizontal wall hit
                tex_x = hit_x
                
            tex_x = int((tex_x * TEXTURE_SIZE) / TILE_SIZE)
            return dist, tex_x
            
    return MAX_DEPTH, 0


def is_wall(x, y):
    """Return True if the (x,y) world coordinate is inside a wall tile."""
    map_x = int(x / TILE_SIZE)
    map_y = int(y / TILE_SIZE)
    if map_x < 0 or map_x >= len(MAP[0]) or map_y < 0 or map_y >= len(MAP):
        return True
    return MAP[map_y][map_x] == 1


def move_player(dx, dy):
    """Move player by dx,dy with simple collision: move on X then Y, checking radius."""
    global player_x, player_y

    # Attempt X movement
    new_x = player_x + dx
    check_x = new_x + (PLAYER_RADIUS if dx > 0 else -PLAYER_RADIUS)
    if not is_wall(check_x, player_y):
        player_x = new_x

    # Attempt Y movement
    new_y = player_y + dy
    check_y = new_y + (PLAYER_RADIUS if dy > 0 else -PLAYER_RADIUS)
    if not is_wall(player_x, check_y):
        player_y = new_y

# Game loop
running = True
global max_fps
max_fps = state.get_max_fps()
clock = pygame.time.Clock()

mus.MusicPlayer.play_music(ROAM)

while running:
    #display_pos_in_console()
    # Handle events first
    get_cursor()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.mixer.Sound.play(menu_back)
                if state.in_settings:
                    state.warn("Restart to fully apply changes...",72, "Ok",32,"DarcKaste", wid=SCREEN_WIDTH,hei=SCREEN_HEIGHT,x=0,y=0,icon="Assets\\Icons\\darckaste_ico2_16x16.ico")
                    state.in_settings = False
                    state.target_settings_offset = SCREEN_WIDTH
                else:
                    state.paused = not state.paused
                    if not state.paused:  # Resuming game
                        state.target_offset = SCREEN_HEIGHT
                        state.target_alpha = 0
                        pygame.mouse.set_visible(False)
                        pygame.event.set_grab(True)
                    else:  # Entering pause menu
                        state.target_offset = 0
                        state.target_alpha = 120
                        pygame.mouse.set_visible(True)
                        pygame.event.set_grab(False)
            
            # Menu navigation
            elif state.paused:
                if event.key == pygame.K_UP:
                    state.prev_menu_item()
                elif event.key == pygame.K_DOWN:
                    state.next_menu_item()
                elif event.key == pygame.K_RETURN:
                    if not state.in_settings:
                        if state.menu_options[state.selected_option] == 'Resume':
                            state.paused = False
                            pygame.mouse.set_visible(False)
                            pygame.event.set_grab(True)
                        elif state.menu_options[state.selected_option] == 'Settings':
                            state.in_settings = True
                            state.selected_setting = 0
                            state.settings_offset = SCREEN_WIDTH
                            state.target_settings_offset = 0
                        elif state.menu_options[state.selected_option] == 'New Map':
                            # Generate new map and reset position
                            reset_to_new_map()
                            # Resume game
                            state.paused = False
                            pygame.mouse.set_visible(False)
                            pygame.event.set_grab(True)
                        elif state.menu_options[state.selected_option] == 'Exit':
                            running = False
                            print("exiting...")
                elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    if state.in_settings:
                        state.adjust_setting(-1 if event.key == pygame.K_LEFT else 1)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                if state.paused:
                    mouse_pos = pygame.mouse.get_pos()
                    if not state.in_settings:
                        # Check main menu items
                        for i, option in enumerate(state.menu_options):
                            if get_menu_item_rect(i, option).collidepoint(mouse_pos):
                                state.selected_option = i
                                if option == 'Resume':
                                    state.paused = False
                                    pygame.mouse.set_visible(False)
                                    pygame.event.set_grab(True)
                                elif option == 'Settings':
                                    state.in_settings = True
                                    state.selected_setting = 0
                                elif option == 'New Map':
                                    reset_to_new_map()
                                    state.paused = False
                                    pygame.mouse.set_visible(False)
                                    pygame.event.set_grab(True)
                                elif option == 'Exit':
                                    running = False
                                    print("exiting...")
                                break
                    else:
                        # Check settings items
                        for i, (setting_name, setting) in enumerate(state.settings.items()):
                            if get_menu_item_rect(i, setting_name, True).collidepoint(mouse_pos):
                                state.selected_setting = i
                                break

    
    # Clear screen
    screen.fill(BLACK)
    
    # Update game state if not paused
    if not state.paused:
        # Mouse look with dynamic sensitivity
        mx, my = pygame.mouse.get_rel()
        sensitivity = state.get_mouse_sensitivity()
        player_angle += (mx * sensitivity) / 10000
        # In pygame positive y is down; moving mouse up gives negative my, so invert for pitch
        CAMERA_PITCH += (-my * sensitivity * 100) / 10000
        # Clamp pitch
        CAMERA_PITCH = max(-MAX_PITCH, min(MAX_PITCH, CAMERA_PITCH))
        
        # Get keyboard state
        keys = pygame.key.get_pressed()
        
        # Keyboard controls
        #kbdin
        if keys[pygame.K_LEFT]:
            player_angle -= TURN_SPEED

        if keys[pygame.K_RIGHT]:
            player_angle += TURN_SPEED

        #sounds
        if keys[pygame.K_UP] or keys[pygame.K_DOWN] or keys[pygame.K_a] or keys[pygame.K_d] or keys[pygame.K_s] or keys[pygame.K_w]:
            if not sfx_chan.get_busy():
                if not (keys[pygame.K_LSHIFT] and keys[pygame.K_w] or keys[pygame.K_UP]) or (keys[pygame.K_RSHIFT] and keys[pygame.K_w] or keys[pygame.K_UP]):
                    pygame.mixer.Sound.play(footstep,1,random.randrange(375,425))

                elif (keys[pygame.K_LSHIFT] and keys[pygame.K_w] or keys[pygame.K_UP]) or (keys[pygame.K_RSHIFT] and keys[pygame.K_w] or keys[pygame.K_UP]):
                    pygame.mixer.Sound.play(footstep_hard,1,random.randrange(275,325))

                else:
                    sfx_chan.stop()
     
        if keys[pygame.K_SEMICOLON]:
            state.warn("Message text...",18,"Button label",12,"Title",wid=200,hei=100,icon="Assets/_Debug/test_favicon.bmp")

        # Movement
        move_dx = math.cos(player_angle) * PLAYER_SPEED
        move_dy = math.sin(player_angle) * PLAYER_SPEED

        if keys[pygame.K_UP] or keys[pygame.K_w]:
            move_player(move_dx, move_dy)
            if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
                move_player(move_dx*2, move_dy*2)  # Sprinting doubles speed
 
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            move_player(-move_dx, -move_dy)
        
        # Strafing
        strafe_dx = math.cos(player_angle - math.pi/2) * PLAYER_SPEED
        strafe_dy = math.sin(player_angle - math.pi/2) * PLAYER_SPEED

        if keys[pygame.K_a]:
            move_player(strafe_dx, strafe_dy)

        if keys[pygame.K_d]:
            move_player(-strafe_dx, -strafe_dy)
        
        # Look up/down
        #basically useless rn

        if keys[pygame.K_q]:
            CAMERA_PITCH -= KEY_PITCH_SPEED
 
        if keys[pygame.K_e]:
            CAMERA_PITCH += KEY_PITCH_SPEED

        CAMERA_PITCH = max(-MAX_PITCH, min(MAX_PITCH, CAMERA_PITCH))

        #quickly exit (throws error)
        if keys[pygame.K_DELETE]:
            insta_quit()



        # Calculate dynamic FOV and ray settings
        fov = state.get_fov()
        half_fov = fov / 2
        #fill screen with window; black bar on right that shouldnt be there
        ################
        ## IMPORTANT! ##
        ################
        rays = ((80 if state.settings['Detail']['value'] == 0 else 723) - (20 * (2 - state.settings['Quality']['value'])))  # Adjust ray count based on quality
        step_angle = fov / rays
        
        # Clear surfaces
        floor_surf.fill((0,0,0,0))
        ceil_surf.fill((0,0,0,0))
        
        # Render floor/ceiling if not in quick mode
        if not state.quick_mode:
            # Start from bottom of screen, increase step size with distance
            y = SCREEN_HEIGHT//2 - 1
            row = 0
            while row < SCREEN_HEIGHT//2:
                ray_y = SCREEN_HEIGHT - row + CAMERA_PITCH
                if ray_y < SCREEN_HEIGHT // 2:
                    row += 1
                    continue
                
                row_distance = SCREEN_DIST / (ray_y - SCREEN_HEIGHT/2 + 0.0001)
                detail_reduction = state.get_detail_reduction()
                adaptive_step = max(1, int(row_distance * detail_reduction))
                x_step = max(2, int(row_distance * detail_reduction))
                
                if row_distance > MAX_DEPTH:
                    row += adaptive_step
                    continue
                
                angle = player_angle - half_fov
                floor_x = player_x + row_distance * math.cos(angle)
                floor_y = player_y + row_distance * math.sin(angle)
                
                step_x = row_distance * (math.cos(angle + fov) - math.cos(angle)) / SCREEN_WIDTH
                step_y = row_distance * (math.sin(angle + fov) - math.sin(angle)) / SCREEN_WIDTH
                
                for x in range(0, SCREEN_WIDTH, x_step):
                    f_color = get_floor_color(int(floor_x), int(floor_y))
                    c_color = get_ceil_color(int(floor_x), int(floor_y))
                    
                    pygame.draw.rect(floor_surf, f_color, (x, row, x_step, adaptive_step))
                    pygame.draw.rect(ceil_surf, c_color, (x, SCREEN_HEIGHT//2 - row - adaptive_step, x_step, adaptive_step))
                    
                    floor_x += step_x * x_step
                    floor_y += step_y * x_step
                
                row += adaptive_step
        
        # Draw floor/ceiling surfaces
        screen.blit(floor_surf, (0, SCREEN_HEIGHT//2))
        screen.blit(ceil_surf, (0, 0))
        
        # Raycasting with dynamic FOV and quality
        ray_angle = player_angle - half_fov
        wall_width = SCREEN_WIDTH // int(rays)

        for ray in range(int(rays)):
            distance, tex_x = cast_ray(ray_angle)
            
            if distance >= MAX_DEPTH:
                ray_angle += step_angle
                continue
            
            distance *= math.cos(player_angle - ray_angle)
            wall_height = (TILE_SIZE * SCREEN_HEIGHT) / (distance + 0.0001)
            
            if wall_height < MIN_WALL_HEIGHT and state.quick_mode:
                ray_angle += step_angle
                continue
            
            wall_top = int((SCREEN_HEIGHT - wall_height) // 2 + CAMERA_PITCH)
            wall_bottom = int(wall_top + wall_height)
            
            wall_pos = ray * wall_width
            
            if wall_bottom > wall_top:
                wall_height = wall_bottom - wall_top
                
                if not state.quick_mode:
                    # Select texture based on wall orientation and position
                    map_x = int((player_x + math.cos(ray_angle) * distance) / TILE_SIZE)
                    map_y = int((player_y + math.sin(ray_angle) * distance) / TILE_SIZE)
                    
                    # Use different textures based on wall orientation
                    is_vertical = abs(int(x) - map_x * TILE_SIZE) < 2
                    if is_vertical:
                        texture = textures['brick']  # Vertical walls use brick
                    else:
                        texture = textures['stone' if (map_x + map_y) % 2 == 0 else 'metal']
                    
                    # Create wall slice surface
                    slice_surface = pygame.Surface((1, wall_height))
                    
                    # Enhanced shading with distance
                    shade = min(1.0, max(0.3, 1.0 - distance / (MAX_DEPTH * 0.8)))
                    
                    # Draw textured slice with mipmap-style scaling
                    for y in range(wall_height):
                        # Improved texture coordinate calculation
                        tex_y = int((y * TEXTURE_SIZE) / wall_height)
                        tex_y = min(TEXTURE_SIZE - 1, max(0, tex_y))  # Clamp texture coordinate
                        
                        # Get texture color and apply shading
                        color = texture.get_at((tex_x, tex_y))
                        shaded_color = tuple(int(c * shade) for c in color[:3])
                        slice_surface.set_at((0, y), shaded_color)
                    
                    # Scale and draw the slice
                    if wall_width > 1:
                        slice_surface = pygame.transform.scale(slice_surface, (wall_width, wall_height))
                    screen.blit(slice_surface, (wall_pos, wall_top))
                else:
                    # Quick mode with shading
                    color_intensity = int(min(255, max(10, 255 - distance/3)))
                    wall_color = (color_intensity, color_intensity, color_intensity)
                    pygame.draw.rect(screen, wall_color, (wall_pos, wall_top, wall_width, wall_height))
            
            ray_angle += step_angle
        pygame.Surface.blit(screen,pygame.image.load("Assets\\Cursors\\cur_cross.png"),dest=(pygame.display.get_desktop_sizes()[0][0]/2,pygame.display.get_desktop_sizes()[0][1]/2))


    
    # Draw pause menu if paused
    if state.paused:
        if map := 1:
            draw_menu()
    
    # Draw FPS counter (and more!)
    if show_fps:
        fps = clock.get_fps()
        fps_text = font.render(
            f'FPS: {int(fps)} | FOV: {int(state.settings["FOV"]["value"])}° | Quality: {state.settings["Quality"]["options"][state.settings["Quality"]["value"]]} | Coords: ({int(player_x)}, {int(player_y)}) | Rays: {rays} | wall_width: {wall_width}',
            A_ALIAS,"Alice Blue" ,BLACK
        )
        screen.blit(fps_text, (0, 0))

    # Update display
    pygame.display.flip()

    clock.tick(max_fps) #if you can get more than like 2 fps on high graphics you got a good pc cuz i dont think its optimized at all

# Cleanup
pygame.quit()
