#!/usr/bin/env python3
import sys, subprocess
from pathlib import Path
from PiicoDev_RFID import PiicoDev_RFID
from PiicoDev_Unified import sleep_ms

# -------- CONFIG --------
TEXT_DIR  = Path("text")
AUDIO_DIR = Path("audio")

RAW_PRINTER_PATH = "/dev/usb/lp0"  # ESC/POS direct
DO_RAW_PRINT     = True            # set False to suppress physical printing
USE_MPG123       = True            # True = mpg123 CLI, False = pygame

PRESENT_SLEEP_MS = 200             # matches your working inventory loop
ABSENT_SLEEP_MS  = 100
# ------------------------

def normalize_uid(uid):
    # Same behavior as your inventory script
    if isinstance(uid, (bytes, bytearray)):
        return "".join(f"{b:02X}" for b in uid)
    if isinstance(uid, (list, tuple)):
        return "".join(f"{int(b):02X}" for b in uid)
    if isinstance(uid, str):
        return "".join(c for c in uid.upper() if c.isalnum())
    return str(uid).upper()

def raw_print_text_file(txt_path: Path):
    dev = Path(RAW_PRINTER_PATH)
    print(f"[DEBUG] RAW print device: {dev}")
    if not dev.exists():
        print(f"[PRINT ERROR] Device {dev} does not exist.", file=sys.stderr)
        return
    try:
        content = txt_path.read_bytes()
    except Exception as e:
        print(f"[TEXT ERROR] Failed to read {txt_path}: {e}", file=sys.stderr)
        return

    # ESC/POS: init, content, feed 3 lines, full cut
    payload = b"\x1b@" + content + b"\n\n\n" + b"\x1dV\x00"
    try:
        with open(dev, "wb", buffering=0) as p:
            p.write(payload)
        print("[DEBUG] RAW print job written to device")
    except PermissionError as e:
        print(f"[PRINT ERROR] Permission denied on {dev}: {e}", file=sys.stderr)
    except Exception as e:
        print(f"[PRINT ERROR] Write to {dev} failed: {e}", file=sys.stderr)

def maybe_print_text(uid: str):
    txt = TEXT_DIR / f"{uid}.txt"
    print(f"[DEBUG] Checking text: {txt}")
    if not txt.exists():
        print("[DEBUG] No matching text file")
        return
    try:
        content = txt.read_text(encoding="utf-8", errors="replace").rstrip()
        print(f"--- TEXT OUTPUT ({uid}) ---\n{content}\n---------------------------")
    except Exception as e:
        print(f"[TEXT ERROR] {e}", file=sys.stderr)
        return
    if DO_RAW_PRINT:
        raw_print_text_file(txt)

def play_mp3_mpg123(path: Path):
    print(f"[DEBUG] Playing audio via mpg123: {path}")
    subprocess.run(["mpg123", "-q", str(path)], check=False)
    print("[DEBUG] Playback complete")

def play_mp3_pygame(path: Path):
    import pygame
    if not pygame.mixer.get_init():
        pygame.mixer.init()
    pygame.mixer.music.load(str(path))
    print(f"[DEBUG] Playing audio via pygame: {path}")
    pygame.mixer.music.play()
    get_busy = getattr(pygame.mixer.music, "get_busy", None) or getattr(pygame.mixer.music, "getBusy", None)
    while get_busy():
        sleep_ms(100)
    print("[DEBUG] Playback complete")

def maybe_play_audio(uid: str):
    mp3 = AUDIO_DIR / f"{uid}.mp3"
    print(f"[DEBUG] Checking audio: {mp3}")
    if not mp3.exists():
        print("[DEBUG] No matching audio file")
        return
    try:
        if USE_MPG123:
            play_mp3_mpg123(mp3)
        else:
            play_mp3_pygame(mp3)
    except Exception as e:
        print(f"[AUDIO ERROR] {e}", file=sys.stderr)

def main():
    rfid = PiicoDev_RFID()
    inventory_seen = set()  # optional: not used for storage, just debugging
    last_uid = None

    print("Ready. Present a tag.")

    try:
        while True:
            if rfid.tagPresent():
                raw = rfid.readID()  # your working reader call
                if raw:
                    uid = normalize_uid(raw)
                    if uid != last_uid:
                        print(f"[DEBUG] Detected UID: {uid}")
                        inventory_seen.add(uid)
                        maybe_print_text(uid)
                        maybe_play_audio(uid)
                        last_uid = uid
                    sleep_ms(PRESENT_SLEEP_MS)
                else:
                    # No UID returned despite presence; short backoff
                    sleep_ms(50)
            else:
                if last_uid is not None:
                    print("[DEBUG] Tag removed")
                last_uid = None
                sleep_ms(ABSENT_SLEEP_MS)
    except KeyboardInterrupt:
        print("\n[DEBUG] Exiting.")

if __name__ == "__main__":
    main()
