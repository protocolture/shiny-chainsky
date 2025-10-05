import os, time, random, vlc
from PiicoDev_Potentiometer import PiicoDev_Potentiometer
from PiicoDev_RGB import PiicoDev_RGB
from PiicoDev_Unified import sleep_ms

# --- Tracks ---
signal_tracks = [f"ch{i}.ogg" for i in range(1, 13)]
static_tracks = ["AllStaticChatterPlanet.ogg"]  # one static is enough to test

playlist = []
for i in range(16):
    if i % 2 == 0:
        playlist.append(signal_tracks[i % len(signal_tracks)])
    else:
        playlist.append(static_tracks[0])

# --- Hardware ---
tune_pot = PiicoDev_Potentiometer(suppress_warnings=True)
leds = PiicoDev_RGB()

# --- VLC Setup ---
Instance = vlc.Instance("--quiet --no-video --intf dummy")
deckL = Instance.media_player_new()
deckR = Instance.media_player_new()

def load_and_play(player, path):
    m = Instance.media_new_path(os.path.abspath(path))
    player.set_media(m)
    player.play()
    time.sleep(0.2)

def force_alive(player, path):
    if player.get_state() not in (vlc.State.Playing, vlc.State.Buffering):
        load_and_play(player, path)

print("[INFO] Starting VLC base test")

left_idx = right_idx = None

try:
    while True:
        val = tune_pot.value
        pos = (val / 100.0) * 15
        i = int(pos)
        t = pos - i
        j = min(i + 1, 15)

        # Load if new station
        if i != left_idx:
            load_and_play(deckL, playlist[i])
            left_idx = i
            print(f"[LOAD] L <- {playlist[i]}")
        if j != right_idx:
            load_and_play(deckR, playlist[j])
            right_idx = j
            print(f"[LOAD] R <- {playlist[j]}")

        # Keep them alive
        force_alive(deckL, playlist[left_idx])
        force_alive(deckR, playlist[right_idx])

        # Mix volumes
        deckL.audio_set_volume(int((1.0 - t) * 100))
        deckR.audio_set_volume(int(t * 100))

        sleep_ms(100)

except KeyboardInterrupt:
    deckL.stop()
    deckR.stop()
    leds.clear()
    print("Radio off")
