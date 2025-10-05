import os, time, random, vlc
from itertools import cycle
from PiicoDev_Potentiometer import PiicoDev_Potentiometer
from PiicoDev_RGB import PiicoDev_RGB
from PiicoDev_Unified import sleep_ms

# ---------- TRACKS ----------
signal_tracks = [
    "ch1.ogg","ch2.ogg","ch3.ogg","ch4.ogg",
    "ch5.ogg","ch6.ogg","ch7.ogg","ch8.ogg",
    "ch9.ogg","ch10.ogg","ch11.ogg","ch12.ogg",
]
static_tracks = ["AM-Static.mp3","Radio-Static.mp3","AllStaticChatterPlanet.ogg"]
effect_tracks = ["roar.mp3","Scream1.mp3","scream2.mp3","zombscream.mp3"]
blend_tracks  = static_tracks + ["Nasa.mp3"]  # keep NASA in blends

# ---------- BUILD 16-SLOT DIAL (alternate signal/static) ----------
dial_slots = 16
sig_iter  = cycle(signal_tracks)
stat_iter = cycle(static_tracks)
playlist  = [next(sig_iter) if i % 2 == 0 else next(stat_iter) for i in range(dial_slots)]

# ---------- HARDWARE ----------
tune_pot   = PiicoDev_Potentiometer(suppress_warnings=True)
volume_pot = PiicoDev_Potentiometer(id=[1,0,0,0], suppress_warnings=True)
leds       = PiicoDev_RGB()

# ---------- VLC SETUP ----------
Instance = vlc.Instance("--quiet --no-video --intf dummy --no-xlib")
deckL = Instance.media_player_new()
deckR = Instance.media_player_new()
fx1   = Instance.media_player_new()
fx2   = Instance.media_player_new()

def load_and_play_loop(player, path):
    m = Instance.media_new_path(os.path.abspath(path))
    player.set_media(m)
    player.play()
    time.sleep(0.1)  # allow start

    def _requeue(event):
        # restart same media when it ends
        try:
            player.stop()
            player.play()
        except Exception:
            pass

    em = player.event_manager()
    # ensure only one handler bound
    try: em.event_detach(vlc.EventType.MediaPlayerEndReached)
    except Exception: pass
    em.event_attach(vlc.EventType.MediaPlayerEndReached, _requeue)

def set_vol(player, vol_0_1):
    v = max(0, min(100, int(vol_0_1 * 100)))
    player.audio_set_volume(v)

def ensure_playing(player):
    st = player.get_state()
    # If ended/stopped/error, kick it
    if st in (vlc.State.Ended, vlc.State.Stopped, vlc.State.Error, vlc.State.NothingSpecial):
        try:
            player.play()
        except Exception:
            pass

# ---------- COLOR UTILS ----------
def blend_rgb(c1, c2, t):
    t = 0.0 if t < 0 else (1.0 if t > 1.0 else t)
    return [int(c1[i] + (c2[i]-c1[i])*t) for i in range(3)]

green, red, purple = [0,255,0], [255,0,0], [128,0,128]
def is_signal(name): return name not in static_tracks

# ---------- STATE ----------
left_idx = right_idx = None
override_active = False
override_t = 0.0         # 0..1 fade progress
override_dir = +1        # +1 fade-in, -1 fade-out
override_effect = None
override_blend  = None
last_trigger_time = time.time()

# hysteresis to avoid thrashing deck loads
last_pos_idx_pair = None

print("[INFO] VLC streaming with live tuning during events.")

try:
    while True:
        now = time.time()

        # ---- Read controls ----
        mv = max(0.0, min(1.0, volume_pot.value / 100.0))
        val = tune_pot.value                      # 0..100
        pos = (val / 100.0) * (dial_slots - 1)    # 0..15 float
        i   = int(pos)
        t   = pos - i
        j   = min(i + 1, dial_slots - 1)

        # ---- Load decks on index change (ALWAYS, even during events) ----
        pair = (i, j)
        if pair != last_pos_idx_pair:
            # left deck
            if left_idx != i:
                left_idx = i
                load_and_play_loop(deckL, playlist[i])
                print(f"[LOAD] L <- {playlist[i]}")
            # right deck
            if right_idx != j:
                right_idx = j
                load_and_play_loop(deckR, playlist[j])
                print(f"[LOAD] R <- {playlist[j]}")
            last_pos_idx_pair = pair

        # ---- Keep decks alive (guard unexpected stops) ----
        ensure_playing(deckL)
        ensure_playing(deckR)

        # ---- Trigger overlay every ~60s (non-blocking) ----
        if not override_active and (now - last_trigger_time) > 60:
            last_trigger_time = now
            override_active = True
            override_t = 0.0
            override_dir = +1
            override_effect = random.choice(effect_tracks)
            override_blend  = random.choice(blend_tracks)
            load_and_play_loop(fx1, override_effect)
            load_and_play_loop(fx2, override_blend)
            set_vol(fx1, 0.0); set_vol(fx2, 0.0)
            print(f"[EVENT] {override_effect} + {override_blend}")

        # ---- Overlay fade (non-blocking) ----
        if override_active:
            # progress
            step = 0.05   # fade speed per loop (adjust with sleep_ms below)
            override_t += step * override_dir
            if override_t >= 1.0:
                override_t = 1.0
                override_dir = -1
            elif override_t <= 0.0:
                override_t = 0.0
                override_active = False
                fx1.stop(); fx2.stop()
                print("[EVENT] Cleared")

            # overlays at up to 0.8 of master
            overlay_gain = 0.8 * mv * override_t if override_dir == +1 else 0.8 * mv * override_t
            set_vol(fx1, overlay_gain)
            set_vol(fx2, overlay_gain)

            # LEDs purple during event
            for k in range(3): leds.setPixel(k, purple)
            leds.show()
        else:
            # Normal LED based on signal weighting
            sig = 0.0
            if is_signal(playlist[i]): sig += (1.0 - t)
            if is_signal(playlist[j]): sig += t
            color = blend_rgb(red, green, sig)
            for k in range(3): leds.setPixel(k, color)
            leds.show()

        # ---- Base deck volumes ALWAYS follow pot (even during events) ----
        set_vol(deckL, (1.0 - t) * mv)  # bases at full master
        set_vol(deckR, t * mv)

        sleep_ms(50)

except KeyboardInterrupt:
    pass
finally:
    for p in (deckL, deckR, fx1, fx2):
        try: p.stop()
        except: pass
    leds.clear()
    print("Radio off.")
