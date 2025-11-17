'''Music
---
Handles the music for Project DarcKaste
<hr/>
<code>Coded by: Jayden Mays</code>'''
import pygame

pygame.mixer.init()

#Vars
CHASE = "Assets\\Audio\\Music\\chase_drums.mp3"
CHASE_HELL = "Assets\\Audio\\Music\\chase.mp3"
ROAM = "Assets\\Audio\\Music\\explorer.mp3"

class MusicPlayer:
    def __init__(self):
        pass

    def play_music(self,sound=ROAM):
        try:
            if sound == ROAM:
                pygame.mixer.music.load(ROAM)
                pygame.mixer.music.play(start=10.0)
            else:
                pygame.mixer.music.load(sound)
                pygame.mixer.music.play()
        except pygame.error:
            print(f"Could not find {sound}. Files might be named incorrectly. Check Assets/Audio/Music")
