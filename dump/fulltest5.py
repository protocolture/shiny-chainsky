import pygame
import time
import random
from PiicoDev_Potentiometer import PiicoDev_Potentiometer
from PiicoDev_RGB import PiicoDev_RGB
from PiicoDev_Unified import sleep_ms

# === TRACK SETUP ===
signal_tracks = [
    "AllPlanet.mp3", "journal1.mp3", "Jupiter.mp3", "Mercury.mp3",
    "Nasa.mp3", "Neptune.mp3", "twilightyzone.mp3", "Vintage.mp3"
]
static_tracks = ["AM-Static.mp3", "Radio-Static.mp3"]
effect_tracks = ["roar.mp3", "Scream1.mp3", "scream2.mp3", "zombscream.mp3"]

# === INIT ===
pot = PiicoDev_Potentiometer()
leds = PiicoDev_RGB()

pygame.mixer.init(buffer=4096)
pygame.mixer.set_num_channels(18)  # 16 + 2 for override

channels = []
track_names = []

# Interleaved radio playlist
playlist = []
for i in range(8):
    playlist.append(signal_tracks[i])
    playlist.append(static_tracks[i % 2])

# Load base channels
for i, filename in enumerate(playlist):
    sound = pygame.mixer.Sound(filename)
    channel = pygame.mixer.Channel(i)
    channel.play(sound, loops=-1)
    channel.set_volume(0.0)
    channels.append(channel)
    track_names.append(filename)
    print(f"Loaded channel {i}: {filename}")

# Load effect and blend channels (channels 16 + 17)
effect_channel = pygame.mixer.Channel(16)
blend_channel = pygame.mixer.Channel(17)

# === LED HELPERS ===
def blend_rgb(c1, c2, t):
    return [
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t)
    ]

green = [0, 255, 0]
red   = [255, 0, 0]
purple = [128, 0, 128]

def is_signal(filename):
    return filename not in static_tracks

# === STATE ===
override_active = False
override_end_time = 0
last_trigger_time = time.time()

# === MAIN LOOP ===
try:
    while True:
        now = time.time()

        # === EVENT TRIGGER ===
        if not override_active and now - last_trigger_time > 60:
            last_trigger_time = now
            override_active = True

            # Stop all radio channels
            for ch in channels:
                ch.set_volume(0.0)

            # Select effect + blend track
            effect_file = random.choice(effect_tracks)
            blend_file = random.choice(static_tracks + ["Nasa.mp3"])
            print(f"[EVENT] Playing: {effect_file} + {blend_file}")

            # Load & play
            effect_sound = pygame.mixer.Sound(effect_file)
            blend_sound = pygame.mixer.Sound(blend_file)

            effect_channel.play(effect_sound)
            blend_channel.play(blend_sound)

            effect_channel.set_volume(0.5)
            blend_channel.set_volume(0.5)

            override_end_time = now + max(effect_sound.get_length(), blend_sound.get_length())

        # === EVENT MODE ===
        if override_active:
            # LEDs stay purple
            for led in range(3):
                leds.setPixel(led, purple)
            leds.show()

            if now >= override_end_time:
                override_active = False
                effect_channel.stop()
                blend_channel.stop()
                print("[EVENT] Ending override — resuming normal tuning.")

        # === NORMAL TUNING ===
        if not override_active:
            val = pot.value
            pos = val / 100 * 15
            i = min(int(pos), 15)
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

            # LED signal vs static blend
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
    effect_channel.stop()
    blend_channel.stop()
    leds.clear()
    print("Radio off.")
