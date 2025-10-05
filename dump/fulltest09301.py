import os
import pygame
import time
import random
from itertools import cycle
# Defer PiicoDev imports until AFTER audio load to avoid I2C noise blocking early prints

# --- TRACKS ---
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
effect_tracks = ["roar.mp3","Scream1.mp3","scream2.mp3","zombscream.mp3"]
blend_tracks  = static_tracks + ["Nasa.mp3"]

# --- AUDIO INIT (keep it like the working build) ---
# If you need to force device, uncomment:
# os.environ['SDL_AUDIODRIVER'] = 'alsa'
# os.environ['AUDIODEV'] = 'plughw:3,0'

try:
    pygame.mixer.init(buffer=4096)  # match the earlier working behavior
except Exception as e:
    print(f"[AUDIO][WARN] mixer.init failed with {e}; retrying with bigger buffer")
    pygame.mixer.quit()
    pygame.mixer.init(buffer=8192)

# Channels plan:
# 0..15  : base “dial” (16 slots)
# 20..27 : overlay FX + blends (8 total)
upper_base = 20
upper_count = len(effect_tracks) + len(blend_tracks)  # 8
highest_index = upper_base + upper_count - 1
total_channels = max(28, highest_index + 1)  # give a little headroom
pygame.mixer.set_num_channels(total_channels)

# --- BUILD 16-SLOT DIAL (alternate signal/static, cycle through lists) ---
dial_slots = 16
sig_iter   = cycle(signal_tracks)
stat_iter  = cycle(static_tracks)

playlist = []
for n in range(dial_slots):
    playlist.append(next(sig_iter) if n % 2 == 0 else next(stat_iter))

# --- LOAD BASE CHANNELS (0..15) ---
base_channels = []
track_names   = []
for ch_idx, filename in enumerate(playlist):
    try:
        snd = pygame.mixer.Sound(filename)
    except Exception as e:
        # Don’t die here; substitute a known-good static so we still print progress
        print(f"[LOAD][WARN] {filename}: {e} — substituting {static_tracks[0]}")
        snd = pygame.mixer.Sound(static_tracks[0])

    ch = pygame.mixer.Channel(ch_idx)
    ch.play(snd, loops=-1)
    ch.set_volume(0.0)
    base_channels.append(ch)
    track_names.append(filename)
    print(f"[LOAD] Base ch {ch_idx:02d}: {filename}")

# --- PRELOAD OVERLAY CHANNELS (20..27), LOOPED & MUTED ---
upper_channels = {}
upper_list = effect_tracks + blend_tracks
for i, filename in enumerate(upper_list):
    ch_num = upper_base + i
    try:
        snd = pygame.mixer.Sound(filename)
    except Exception as e:
        print(f"[LOAD][WARN] {filename}: {e} — substituting {static_tracks[0]}")
        filename = static_tracks[0]
        snd = pygame.mixer.Sound(filename)

    ch = pygame.mixer.Channel(ch_num)
    ch.play(snd, loops=-1)
    ch.set_volume(0.0)
    upper_channels[filename] = ch
    print(f"[LOAD] FX  ch {ch_num:02d}: {filename}")

print(f"[INFO] Mixer channels ready: total={total_channels}, highest_used={highest_index}")

# --- NOW bring in PiicoDev (avoid early I2C flak) ---
from PiicoDev_Potentiometer import PiicoDev_Potentiometer
from PiicoDev_RGB import PiicoDev_RGB
from PiicoDev_Unified import sleep_ms

# If your PiicoDev lib supports it, suppress warnings to reduce console spam/latency
tune_pot   = PiicoDev_Potentiometer(suppress_warnings=True)            # main tuner (0..100)
volume_pot = PiicoDev_Potentiometer(id=[1,0,0,0], suppress_warnings=True)  # master volume (0..100)
leds = PiicoDev_RGB()

# --- HELPERS ---
def blend_rgb(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return [
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    ]

green  = [0,255,0]
red    = [255,0,0]
purple = [128,0,128]

def is_signal(name): return name not in static_tracks

def fade_channel(channel, target_vol, step=0.05):
    current = channel.get_volume()
    target_vol = max(0.0, min(1.0, target_vol))
    if abs(current - target_vol) < step:
        channel.set_volume(target_vol)
    elif current < target_vol:
        channel.set_volume(min(current + step, 1.0))
    else:
        channel.set_volume(max(current - step, 0.0))

# --- STATE ---
override_active = False
override_duration = 5.0
override_fade_speed = 0.05
override_effect = None
override_blend  = None
last_trigger_time = time.time()

# --- MAIN LOOP ---
try:
    while True:
        now = time.time()
        master_volume = max(0.0, min(1.0, volume_pot.value / 100.0))

        # Trigger event every ~60s
        if not override_active and (now - last_trigger_time) > 60:
            last_trigger_time = now
            override_active = True
            override_start = now
            override_effect = random.choice(effect_tracks)
            override_blend  = random.choice(blend_tracks)
            print(f"[EVENT] Triggered: {override_effect} + {override_blend}")

        # Overlay event handling
        if override_active:
            elapsed = now - override_start
            for _ in range(3): leds.setPixel(_, purple)
            leds.show()

            if elapsed < override_duration:
                fade_channel(upper_channels[override_effect], 0.5 * master_volume, override_fade_speed)
                fade_channel(upper_channels[override_blend],  0.5 * master_volume, override_fade_speed)
            else:
                fade_channel(upper_channels[override_effect], 0.0, override_fade_speed)
                fade_channel(upper_channels[override_blend],  0.0, override_fade_speed)
                if (upper_channels[override_effect].get_volume() == 0.0 and
                    upper_channels[override_blend].get_volume()  == 0.0):
                    print("[EVENT] Cleared.")
                    override_active = False

        # Normal tuning (no event)
        if not override_active:
            val = tune_pot.value            # 0..100
            pos = (val / 100.0) * 15.0      # dial 0..15
            i   = int(pos)
            t   = pos - i
            j   = min(i + 1, 15)

            for idx in range(16):
                base = (1.0 - t) if idx == i else (t if idx == j else 0.0)
                base_channels[idx].set_volume(base * master_volume)

            left_file  = track_names[i]
            right_file = track_names[j]
            signal_strength = 0.0
            if is_signal(left_file):  signal_strength += (1.0 - t)
            if is_signal(right_file): signal_strength += t
            led_color = blend_rgb(red, green, signal_strength)
            for _ in range(3): leds.setPixel(_, led_color)
            leds.show()

        sleep_ms(50)

except KeyboardInterrupt:
    pass
finally:
    for ch in base_channels: ch.stop()
    for ch in upper_channels.values(): ch.stop()
    leds.clear()
    print("Radio off.")

