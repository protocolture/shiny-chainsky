import pygame
import time
from PiicoDev_Potentiometer import PiicoDev_Potentiometer
from PiicoDev_RGB import PiicoDev_RGB
from PiicoDev_Unified import sleep_ms

# === CONFIG ===
signal_tracks = [
    "AllPlanet.mp3", "journal1.mp3", "Jupiter.mp3", "Mercury.mp3",
    "Nasa.mp3", "Neptune.mp3", "twilightyzone.mp3", "Vintage.mp3"
]
static_tracks = ["AM-Static.mp3", "Radio-Static.mp3"]  # Alternates

# === SETUP ===
pot = PiicoDev_Potentiometer()
leds = PiicoDev_RGB()

pygame.mixer.init(buffer=4096)
pygame.mixer.set_num_channels(16)

channels = []
track_names = []

# Build interleaved playlist: [signal, static, signal, static, ...]
playlist = []
for i in range(8):
    playlist.append(signal_tracks[i])
    playlist.append(static_tracks[i % 2])  # Alternate static type

# Load sounds + assign channels
for i, filename in enumerate(playlist):
    try:
        sound = pygame.mixer.Sound(filename)
        channel = pygame.mixer.Channel(i)
        channel.play(sound, loops=-1)
        channel.set_volume(0.0)
        channels.append(channel)
        track_names.append(filename)
        print(f"Loaded channel {i}: {filename}")
    except Exception as e:
        print(f"Failed to load {filename}: {e}")
        exit(1)

# === COLOR UTILITY ===
def blend_rgb(c1, c2, t):
    return [
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t)
    ]

green = [0, 255, 0]
red   = [255, 0, 0]

def is_signal(filename):
    return filename not in static_tracks

# === MAIN LOOP ===
try:
    while True:
        val = pot.value                  # 0.0 to 100.0
        pos = val / 100 * 15             # 0.0 to 15.0
        i = int(pos)
        t = pos - i
        j = min(i + 1, 15)

        # Set volumes
        for idx in range(16):
            if idx == i:
                vol = 1.0 - t
            elif idx == j:
                vol = t
            else:
                vol = 0.0
            channels[idx].set_volume(vol)

        # LED blending logic
        left_file = track_names[i]
        right_file = track_names[j]
        left_type = is_signal(left_file)
        right_type = is_signal(right_file)

        left_weight = 1.0 - t
        right_weight = t

        signal_strength = 0.0
        if left_type: signal_strength += left_weight
        if right_type: signal_strength += right_weight

        led_color = blend_rgb(red, green, signal_strength)
        for led in range(3):
            leds.setPixel(led, led_color)
        leds.show()

        print(f"Tuned: {pos:.2f} → {track_names[i]} ({1-t:.2f}), {track_names[j]} ({t:.2f}) | LED: {led_color}")
        sleep_ms(50)

except KeyboardInterrupt:
    for ch in channels:
        ch.stop()
    leds.clear()
    print("Radio off.")
