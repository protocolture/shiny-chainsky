# This will be a large code block, so let's organize and display it clearly.
from pathlib import Path

code = """
# full_radio_system.py
# Comprehensive script for fake-radio system with PiicoDev integration and scream override events

import pygame
from PiicoDev_RPot import PiicoDev_RPot
from PiicoDev_SlidePot import PiicoDev_SlidePot
from PiicoDev_RGB import PiicoDev_RGB
from PiicoDev_Unified import sleep_ms
import random
import time
import os

# ==== Configuration ====
STATION_FILES = [
    "AllPlanet.mp3",
    "AM-Static.mp3",
    "journal1.mp3",
    "Radio-Static.mp3",
    "Jupiter.mp3",
    "AM-Static.mp3",
    "Mercury.mp3",
    "Radio-Static.mp3",
    "Nasa.mp3",
    "twilightyzone.mp3",
    "Neptune.mp3",
    "AM-Static.mp3",
    "Vintage.mp3",
    "Radio-Static.mp3",
    "journal1.mp3",
    "AM-Static.mp3"
]

SCREAM_EFFECTS = [
    "Scream1.mp3",
    "scream2.mp3",
    "roar.mp3",
    "zombscream.mp3"
]

STATIC_TRACKS = ["Radio-Static.mp3", "AM-Static.mp3", "Nasa.mp3"]

LED_GREEN = [0, 255, 0]
LED_RED = [255, 0, 0]
LED_PURPLE = [128, 0, 128]

# ==== Init ====
pygame.mixer.init()
pot = PiicoDev_RPot()
volume_pot = PiicoDev_SlidePot()
led = PiicoDev_RGB()

# Load 16 channels for stations
channels = [pygame.mixer.Channel(i) for i in range(16)]
tracks = []

for i, filename in enumerate(STATION_FILES):
    sound = pygame.mixer.Sound(filename)
    sound.set_volume(1.0)
    channels[i].play(sound, loops=-1)
    tracks.append(sound)
    print(f"Loaded channel {i}: {filename}")

# Load scream tracks to upper channels
scream_channels = []
for i in range(len(SCREAM_EFFECTS)):
    ch = pygame.mixer.Channel(40 + i)
    sound = pygame.mixer.Sound(SCREAM_EFFECTS[i])
    sound.set_volume(0.0)
    ch.play(sound, loops=-1)
    scream_channels.append((ch, sound))

# Load static tracks for override (reuse channels above 40)
static_sounds = [pygame.mixer.Sound(f) for f in STATIC_TRACKS]

last_event = time.time()

# ==== Main Loop ====
while True:
    try:
        # Set master volume
        vol = max(0, min(1, volume_pot.value))
        pygame.mixer.music.set_volume(vol)
        for s in tracks:
            s.set_volume(vol)

        # Get current tuning position
        tune_val = pot.value * 15  # 0-15
        left = int(tune_val)
        right = min(15, left + 1)
        mix = tune_val - left
        left_gain = 1.0 - mix
        right_gain = mix

        for i, ch in enumerate(channels):
            if i == left:
                ch.set_volume(left_gain * vol)
            elif i == right:
                ch.set_volume(right_gain * vol)
            else:
                ch.set_volume(0.0)

        # LED blending between red and green
        green_ratio = (left_gain if STATION_FILES[left] not in STATIC_TRACKS else 0) + \
                      (right_gain if STATION_FILES[right] not in STATIC_TRACKS else 0)
        red_ratio = 1.0 - green_ratio
        r = int(LED_RED[0] * red_ratio + LED_GREEN[0] * green_ratio)
        g = int(LED_RED[1] * red_ratio + LED_GREEN[1] * green_ratio)
        b = int(LED_RED[2] * red_ratio + LED_GREEN[2] * green_ratio)
        led.fill([r, g, b])
        led.show()

        # Every 60 seconds trigger a scream + static override
        if time.time() - last_event > 60:
            last_event = time.time()
            print("[EVENT] Triggering scream event")

            scream_index = random.randint(0, len(SCREAM_EFFECTS) - 1)
            static = random.choice(static_sounds)
            scream_channel, scream_sound = scream_channels[scream_index]
            scream_channel.set_volume(0.5 * vol)
            ch_static = pygame.mixer.Channel(50)
            ch_static.play(static, loops=0)
            ch_static.set_volume(0.5 * vol)

            led.fill(LED_PURPLE)
            led.show()

            # Wait for scream sound length, then fade both
            length = scream_sound.get_length()
            end_time = time.time() + length
            while time.time() < end_time:
                sleep_ms(100)

            scream_channel.set_volume(0.0)
            ch_static.stop()

        sleep_ms(100)
    except KeyboardInterrupt:
        break
"""

output_path = Path("/mnt/data/full_radio_system.py")
output_path.write_text(code)
output_path
