import os
import pygame
import time

# Optional: force ALSA + USB card explicitly
# os.environ['SDL_AUDIODRIVER'] = 'alsa'
# os.environ['AUDIODEV'] = 'plughw:3,0'

print("[INFO] Initializing pygame…")
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
print("[INFO] Mixer initialized")

# Show driver info
print("[INFO] Using audio driver:", pygame.mixer.get_init())
print("[INFO] Number of channels available:", pygame.mixer.get_num_channels())

filename = "ch1-test.ogg"

try:
    print(f"[INFO] Loading {filename} …")
    sound = pygame.mixer.Sound(filename)
    print("[INFO] Loaded successfully")
except Exception as e:
    print(f"[ERROR] Could not load {filename}: {e}")
    raise SystemExit(1)

print("[INFO] Starting playback…")
channel = sound.play()

if not channel:
    print("[ERROR] Failed to play sound")
    raise SystemExit(1)

# Wait until finished
while channel.get_busy():
    print(f"[DEBUG] Playing {filename} … vol={channel.get_volume()}")
    time.sleep(0.5)

print("[INFO] Playback finished, exiting.")
