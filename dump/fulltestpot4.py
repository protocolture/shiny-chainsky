import pygame
import time
import random
from PiicoDev_Potentiometer import PiicoDev_Potentiometer
from PiicoDev_RGB import PiicoDev_RGB
from PiicoDev_Unified import sleep_ms

# === TRACKS ===
signal_tracks = [
    "ch1.mp3", "ch2.mp3", "ch3.mp3", "ch4.mp3",
    "ch5.mp3", "ch6.mp3", "ch7.mp3", "ch8.mp3",
    "ch9.mp3", "ch10.mp3", "ch11.mp3", "ch12.mp3"
]

static_tracks = [
    "AM-Static.mp3",
    "Radio-Static.mp3",
    "AllStaticChatterPlanet.mp3"
]

effect_tracks = [
    "roar.mp3",
    "Scream1.mp3",
    "scream2.mp3",
    "zombscream.mp3"
]

blend_tracks = static_tracks + ["Nasa.mp3"]  # Retain Nasa.mp3 in blends

# === SETUP ===
tune_pot = PiicoDev_Potentiometer()                     # Main tuner
volume_pot = PiicoDev_Potentiometer(id=[1,0,0,0])       # Volume controller (slide pot)
leds = PiicoDev_RGB()

total_channels = 48  # 0–15 = base radio, 40+ = overlay FX
pygame.mixer.init(buffer=4096)
pygame.mixer.set_num_channels(total_channels)

channels = []
track_names = []

# === Load base radio channels (0–15) ===
playlist = []
for i in range(8):
    playlist.append(signal_tracks[i])
    playlist.append(static_tracks[i % 2])

for i, filename in enumerate(playlist):
    sound = pygame.mixer.Sound(filename)
    ch = pygame.mixer.Channel(i)
    ch.play(sound, loops=-1)
    ch.set_volume(0.0)
    channels.append(ch)
    track_names.append(filename)
    print(f"[LOAD] Base channel {i}: {filename}")

# === Load upper FX/static channels (40–47) ===
upper_tracks = effect_tracks + blend_tracks
upper_channels = {}
for i, filename in enumerate(upper_tracks):
    ch_num = 40 + i
    sound = pygame.mixer.Sound(filename)
    ch = pygame.mixer.Channel(ch_num)
    ch.play(sound, loops=-1)
    ch.set_volume(0.0)
    upper_channels[filename] = ch
    print(f"[LOAD] FX channel {ch_num}: {filename}")

# === Helpers ===
def blend_rgb(c1, c2, t):
    return [
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t)
    ]

green = [0, 255, 0]
red = [255, 0, 0]
purple = [128, 0, 128]

def is_signal(name): return name not in static_tracks

def fade_channel(channel, target_vol, step=0.05):
    current = channel.get_volume()
    if abs(current - target_vol) < step:
        channel.set_volume(target_vol)
    elif current < target_vol:
        channel.set_volume(min(current + step, 1.0))
    else:
        channel.set_volume(max(current - step, 0.0))

# === State ===
override_active = False
override_duration = 5
override_fade_speed = 0.05
override_effect = None
override_blend = None
last_trigger_time = time.time()

# === MAIN LOOP ===
try:
    while True:
        now = time.time()

        # === Volume control
        master_volume = volume_pot.value / 100

        # === Trigger event every 60s
        if not override_active and now - last_trigger_time > 60:
            last_trigger_time = now
            override_active = True
            override_start = now
            override_effect = random.choice(effect_tracks)
            override_blend = random.choice(blend_tracks)
            print(f"[EVENT] Triggered: {override_effect} + {override_blend}")

        # === FX mode
        if override_active:
            elapsed = now - override_start
            for i in range(3): leds.setPixel(i, purple)
            leds.show()

            if elapsed < override_duration:
                fade_channel(upper_channels[override_effect], 0.5 * master_volume, override_fade_speed)
                fade_channel(upper_channels[override_blend], 0.5 * master_volume, override_fade_speed)
            else:
                fade_channel(upper_channels[override_effect], 0.0, override_fade_speed)
                fade_channel(upper_channels[override_blend], 0.0, override_fade_speed)
                if (
                    upper_channels[override_effect].get_volume() == 0.0 and
                    upper_channels[override_blend].get_volume() == 0.0
                ):
                    print("[EVENT] Cleared.")
                    override_active = False

        # === Normal tuning mode
        if not override_active:
            val = tune_pot.value
            pos = val / 100 * 15
            i = min(int(pos), 15)
            t = pos - i
            j = min(i + 1, 15)

            for idx in range(16):
                vol = (1.0 - t if idx == i else t if idx == j else 0.0) * master_volume
                channels[idx].set_volume(vol)

            # LED signal strength feedback
            left_file = track_names[i]
            right_file = track_names[j]
            signal_strength = 0.0
            if is_signal(left_file): signal_strength += 1.0 - t
            if is_signal(right_file): signal_strength += t

            led_color = blend_rgb(red, green, signal_strength)
            for i in range(3):
                leds.setPixel(i, led_color)
            leds.show()

        sleep_ms(50)

except KeyboardInterrupt:
    for ch in channels:
        ch.stop()
    for ch in upper_channels.values():
        ch.stop()
    leds.clear()
    print("Radio off.")
