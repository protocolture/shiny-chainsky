import os
import pygame
import time
import random
from itertools import cycle, islice
from PiicoDev_Potentiometer import PiicoDev_Potentiometer
from PiicoDev_RGB import PiicoDev_RGB
from PiicoDev_Unified import sleep_ms

# Optional: force ALSA device if needed
# os.environ['SDL_AUDIODRIVER'] = 'alsa'
# os.environ['AUDIODEV'] = 'plughw:3,0'

# === TRACKS ===
signal_tracks = [
    "ch1.ogg","ch2.ogg","ch3.ogg","ch4.ogg",
    "ch5.ogg","ch6.ogg","ch7.ogg","ch8.ogg",
    "ch9.ogg","ch10.ogg","ch11.ogg","ch12.ogg"
]

static_tracks = [
    "AM-Static.mp3",
    "Radio-Static.mp3",
    "AllStaticChatterPlanet.ogg",
]

effect_tracks = [
    "roar.mp3",
    "Scream1.mp3",
    "scream2.mp3",
    "zombscream.mp3",
]

# Keep NASA in blends as requested
blend_tracks = static_tracks + ["Nasa.mp3"]

# === SETUP ===
# If the PiicoDev lib supports it, you can pass suppress_warnings=True
tune_pot   = PiicoDev_Potentiometer()               # Main tuner (0–100)
volume_pot = PiicoDev_Potentiometer(id=[1,0,0,0])   # Master volume (0–100)
leds = PiicoDev_RGB()

# Mixer: larger buffer to avoid underruns, stereo 44.1k
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=8192)

# Channels:
#  - 0..15  : base radio (16-slot dial)
#  - 30..37 : overlay FX+blend (8 tracks total)
upper_base_index = 30
upper_count = len(effect_tracks) + len(blend_tracks)  # 4 + 4 = 8
highest_channel = upper_base_index + upper_count - 1  # 37
total_channels = max(40, highest_channel + 1)         # be generous
pygame.mixer.set_num_channels(total_channels)

# === Build a 16-slot dial: alternate signal / static, cycling through lists ===
dial_slots = 16
signal_iter = cycle(signal_tracks)
static_iter = cycle(static_tracks)

playlist = []
for n in range(dial_slots):
    if n % 2 == 0:
        playlist.append(next(signal_iter))
    else:
        playlist.append(next(static_iter))

# === Load base radio channels (0–15) ===
base_channels = []
track_names   = []
for ch_idx, filename in enumerate(playlist):
    try:
        snd = pygame.mixer.Sound(filename)
    except Exception as e:
        print(f"[LOAD][WARN] {filename}: {e} — substituting first static")
        snd = pygame.mixer.Sound(static_tracks[0])

    ch = pygame.mixer.Channel(ch_idx)
    ch.play(snd, loops=-1)
    ch.set_volume(0.0)
    base_channels.append(ch)
    track_names.append(filename)
    print(f"[LOAD] Base ch {ch_idx:02d}: {filename}")

# === Preload overlay FX/static/NASA (channels 30–37), looped & muted ===
upper_channels = {}
upper_list = effect_tracks + blend_tracks  # order defines channel mapping
for i, filename in enumerate(upper_list):
    ch_num = upper_base_index + i
    try:
        snd = pygame.mixer.Sound(filename)
    except Exception as e:
        print(f"[LOAD][WARN] {filename}: {e} — substituting first static")
        # safe fallback to a static
        fallback = static_tracks[0]
        snd = pygame.mixer.Sound(fallback)
        filename = fallback

    ch = pygame.mixer.Channel(ch_num)
    ch.play(snd, loops=-1)
    ch.set_volume(0.0)
    upper_channels[filename] = ch
    print(f"[LOAD] FX ch {ch_num:02d}: {filename}")

# === HELPERS ===
def blend_rgb(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return [
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    ]

green  = [0, 255, 0]
red    = [255, 0, 0]
purple = [128, 0, 128]

def is_signal(name):
    return name not in static_tracks

def fade_channel(channel, target_vol, step=0.05):
    current = channel.get_volume()
    # clamp
    target_vol = max(0.0, min(1.0, target_vol))
    if abs(current - target_vol) < step:
        channel.set_volume(target_vol)
        return
    if current < target_vol:
        channel.set_volume(min(current + step, 1.0))
    else:
        channel.set_volume(max(current - step, 0.0))

# === State ===
override_active = False
override_duration = 5.0
override_fade_speed = 0.05
override_effect = None
override_blend = None
last_trigger_time = time.time()

print(f"[INFO] Mixer channels: {total_channels}, highest used: {highest_channel}")

# === MAIN LOOP ===
try:
    while True:
        now = time.time()

        # Master volume (0..1), with clamp and optional curve
        mv = max(0.0, min(1.0, volume_pot.value / 100.0))
        # Optional perceptual curve:
        # mv = mv ** 1.5

        # Trigger event every ~60s
        if not override_active and (now - last_trigger_time) > 60:
            last_trigger_time = now
            override_active = True
            override_start = now
            override_effect = random.choice(effect_tracks)
            override_blend  = random.choice(blend_tracks)
            print(f"[EVENT] Triggered: {override_effect} + {override_blend}")

        # Event mode: fade in then out two overlay channels
        if override_active:
            elapsed = now - override_start

            # LEDs purple during event
            for _ in range(3):
                leds.setPixel(_, purple)
            leds.show()

            if elapsed < override_duration:
                fade_channel(upper_channels[override_effect], 0.5 * mv, override_fade_speed)
                fade_channel(upper_channels[override_blend],  0.5 * mv, override_fade_speed)
            else:
                fade_channel(upper_channels[override_effect], 0.0, override_fade_speed)
                fade_channel(upper_channels[override_blend],  0.0, override_fade_speed)
                v1 = upper_channels[override_effect].get_volume()
                v2 = upper_channels[override_blend].get_volume()
                if v1 == 0.0 and v2 == 0.0:
                    print("[EVENT] Cleared.")
                    override_active = False

        # Normal tuning (when no event)
        if not override_active:
            val = tune_pot.value              # 0..100
            pos = (val / 100.0) * (dial_slots - 1)  # 0..15
            i   = int(pos)
            t   = pos - i
            j   = min(i + 1, dial_slots - 1)

            # Crossfade volumes on base channels
            for idx in range(dial_slots):
                base = (1.0 - t) if idx == i else (t if idx == j else 0.0)
                base_channels[idx].set_volume(base * mv)

            # LED color: green for signal, red for static, blended
            left_file  = track_names[i]
            right_file = track_names[j]
            signal_strength = 0.0
            if is_signal(left_file):  signal_strength += (1.0 - t)
            if is_signal(right_file): signal_strength += t
            led_color = blend_rgb(red, green, signal_strength)
            for _ in range(3):
                leds.setPixel(_, led_color)
            leds.show()

        sleep_ms(50)

except KeyboardInterrupt:
    for ch in base_channels:
        ch.stop()
    for ch in upper_channels.values():
        ch.stop()
    leds.clear()
    print("Radio off.")
