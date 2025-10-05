import pygame
import time
from PiicoDev_Potentiometer import PiicoDev_Potentiometer
from PiicoDev_Unified import sleep_ms

# Initialize potentiometer
pot = PiicoDev_Potentiometer()

# Initialize mixer
pygame.mixer.init()

# Define station files
station_files = [
    "AM-Static.mp3",     # 0
    "Mercury.mp3",       # 1
    "Nasa.mp3",          # 2
    "Radio-Static.mp3",  # 3
    "Vintage.mp3"        # 4
]

# Preload sounds and channels
stations = []
channels = []

for i, file in enumerate(station_files):
    try:
        sound = pygame.mixer.Sound(file)
        channel = pygame.mixer.Channel(i)
        channel.play(sound, loops=-1)
        channel.set_volume(0.0)
        stations.append(sound)
        channels.append(channel)
        print(f"Loaded station {i}: {file}")
    except Exception as e:
        print(f"Failed to load {file}: {e}")
        exit(1)

# Main loop
try:
    while True:
        val = pot.value             # 0.0 to 100.0
        scaled = val / 100 * 4      # Map to 0–4 float
        index = int(scaled)         # Zone A
        t = scaled - index          # Blend amount
        index_next = min(index + 1, 4)

        for i in range(5):
            if i == index:
                volume = 1.0 - t
            elif i == index_next:
                volume = t
            else:
                volume = 0.0
            channels[i].set_volume(volume)

        print(f"Zone: {scaled:.2f} | Volumes: {[round(c.get_volume(),2) for c in channels]}")
        sleep_ms(50)

except KeyboardInterrupt:
    for ch in channels:
        ch.stop()
    print("Stopped.")
