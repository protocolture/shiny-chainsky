import os, time, random, vlc
from itertools import cycle
from PiicoDev_Potentiometer import PiicoDev_Potentiometer
from PiicoDev_RGB import PiicoDev_RGB
from PiicoDev_Unified import sleep_ms

# If you must force ALSA device, uncomment:
# os.environ['SDL_AUDIODRIVER'] = 'alsa'
# os.environ['AUDIODEV'] = 'plughw:3,0'

# ---------- TRACKS ----------
signal_tracks = [
    "ch1.ogg","ch2.ogg","ch3.ogg","ch4.ogg",
    "ch5.ogg","ch6.ogg","ch7.ogg","ch8.ogg",
    "ch9.ogg","ch10.ogg","ch11.ogg","ch12.ogg",
]
static_tracks = ["AM-Static.mp3","Radio-Static.mp3","AllStaticChatterPlanet.ogg"]
effect_tracks = ["roar.mp3","Scream1.mp3","scream2.mp3","zombscream.mp3"]
blend_tracks  = static_tracks + ["Nasa.mp3"]  # per your spec

# ---------- BUILD 16-SLOT DIAL (alternating signal/static) ----------
dial_slots = 16
sig_iter  = cycle(signal_tracks)
stat_iter = cycle(static_tracks)
playlist  = [next(sig_iter) if i % 2 == 0 else next(stat_iter) for i in range(dial_slots)]

# ---------- HARDWARE ----------
tune_pot   = PiicoDev_Potentiometer(suppress_warnings=True)
volume_pot = PiicoDev_Potentiometer(id=[1,0,0,0], suppress_warnings=True)
leds       = PiicoDev_RGB()

# ---------- VLC PLAYERS ----------
# Two base decks (left/right) + two overlays (effect + blend)
Instance = vlc.Instance("--quiet --no-video --intf dummy --no-xlib")
deckL = Instance.media_player_new()
deckR = Instance.media_player_new()
fx1   = Instance.media_player_new()
fx2   = Instance.media_player_new()

def load_and_play(player, path, loop=True):
    m = Instance.media_new_path(os.path.abspath(path))
    player.set_media(m)
    player.play()
    # crude wait until start
    time.sleep(0.1)
    # emulate looping by callback restart (works for very long files too)
    if loop:
        def _requeue(event):
            # Restart same media
            player.stop()
            player.play()
        em = player.event_manager()
        em.event_detach(vlc.EventType.MediaPlayerEndReached)  # avoid doubles
        em.event_attach(vlc.EventType.MediaPlayerEndReached, _requeue)

def set_vol(player, vol_0_1):
    v = max(0, min(100, int(vol_0_1 * 100)))
    player.audio_set_volume(v)

# ---------- COLOR UTILS ----------
def blend_rgb(c1, c2, t):
    t = 0.0 if t < 0 else (1.0 if t > 1.0 else t)
    return [int(c1[i] + (c2[i]-c1[i])*t) for i in range(3)]

green, red, purple = [0,255,0], [255,0,0], [128,0,128]
def is_signal(name): return name not in static_tracks

# ---------- STATE ----------
left_idx = right_idx = None
override_active = False
override_start  = 0.0
override_duration = 5.0
override_fade_speed = 0.05
override_effect = None
override_blend  = None
last_trigger_time = time.time()

print("[INFO] Ready. Streaming mode engaged.")

try:
    while True:
        now = time.time()
        # Master volume (0..1)
        mv = max(0.0, min(1.0, volume_pot.value / 100.0))
        # Optional perceptual curve:
        # mv = mv ** 1.5

        # ---- Trigger overlay every ~60s ----
        if not override_active and (now - last_trigger_time) > 60:
            last_trigger_time = now
            override_active = True
            override_start  = now
            override_effect = random.choice(effect_tracks)
            override_blend  = random.choice(blend_tracks)
            load_and_play(fx1, override_effect, loop=True)
            load_and_play(fx2, override_blend,  loop=True)
            set_vol(fx1, 0.0); set_vol(fx2, 0.0)
            print(f"[EVENT] {override_effect} + {override_blend}")

        # ---- Overlay fade logic ----
        if override_active:
            elapsed = now - override_start
            # LEDs purple during event
            for i in range(3): leds.setPixel(i, purple)
            leds.show()
            if elapsed < override_duration:
                # fade up to 0.5 * master
                cur = (elapsed / override_duration)
                tgt = 0.5 * mv * cur
                set_vol(fx1, tgt); set_vol(fx2, tgt)
            else:
                # fade down
                cur = max(0.0, 1.0 - (elapsed - override_duration) / override_duration)
                tgt = 0.5 * mv * cur
                set_vol(fx1, tgt); set_vol(fx2, tgt)
                if tgt <= 0.01:
                    fx1.stop(); fx2.stop()
                    override_active = False
                    print("[EVENT] Cleared")

        # ---- Normal tuning (no event) ----
        if not override_active:
            val = tune_pot.value             # 0..100
            pos = (val / 100.0) * (dial_slots - 1)  # 0..15
            i   = int(pos)
            t   = pos - i
            j   = min(i + 1, dial_slots - 1)

            if left_idx != i:
                left_idx = i
                left_path = playlist[i]
                load_and_play(deckL, left_path, loop=True)
                print(f"[LOAD] L <- {left_path}")

            if right_idx != j:
                right_idx = j
                right_path = playlist[j]
                load_and_play(deckR, right_path, loop=True)
                print(f"[LOAD] R <- {right_path}")

            # Crossfade via volumes
            set_vol(deckL, (1.0 - t) * mv)
            set_vol(deckR, t * mv)

            # LED signal vs static
            sig = 0.0
            if is_signal(playlist[i]): sig += (1.0 - t)
            if is_signal(playlist[j]): sig += t
            color = blend_rgb(red, green, sig)
            for k in range(3): leds.setPixel(k, color)
            leds.show()

        sleep_ms(50)

except KeyboardInterrupt:
    pass
finally:
    for p in (deckL, deckR, fx1, fx2):
        try: p.stop()
        except: pass
    leds.clear()
    print("Radio off.")
