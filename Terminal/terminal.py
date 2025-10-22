#!/usr/bin/env python3
# weyland_terminal.py
# CRT-green recovery console with BIOS-y boot sequence and Webdis-backed status.

# Immediate clear so nothing flashes before the logo/boot text
import os
os.system("cls" if os.name == "nt" else "clear")

import sys
import time
import json
import signal
from urllib import request, parse

try:
    import requests
except Exception:
    requests = None

# === ANSI COLORS ===
GREEN = "\033[32m"
YELLOW = "\033[33m"
RESET = "\033[0m"

# === CONFIG ===
WEBDIS_BASE = "http://192.168.30.114:7379"
TIMEOUT = 5

# === CONSTANTS ===
SYSTEM_ERROR_MSG = (
    "ERROR: Subsystem Malfunction. Please see your authorised Weyland Yutani ship maintenance representative."
)
SENSOR_ERROR_MSG = (
    "ERROR: Internal Sensors Offline. Please see your authorised Weyland Yutani ship maintenance representative."
)

# === ROOMS & STATES (canonical variables; not HA entity IDs) ===
ROOMS = [
    "Command_Deck_Room",
    "Recreation_Lounge_Room",
    "Cargo_Bay_Room",
    "Computer_Core_Room",
    "Medical_Room",
    "Crew_Qtrs_Room",
    "Briefing_Room",
    "Armoury_Brig_Room",
    "Primary_Comms_Room",
    "Cryo_Storage_Room",
    "Engineering_Room",
    "Reactor_Core_Room",
]
ROOM_STATES = ["ok", "fire", "breach"]

# Phases defined but intentionally unused for now
PHASE_KEYS = ["Phase1", "Phase2", "Phase3", "Phase4"]

# Atmospheric layers, shallow → deep
LAYER_KEYS = ["CloudDeck", "Stratosheath", "RedZone", "Crushdepth"]

# --- Storage keys ---
STORAGE_KEYS = [
    "STORAGE:HE3_KG",
    "STORAGE:HE6_KG",
    "STORAGE:D2_KG",
    "STORAGE:N2_KG",
    "STORAGE:O2_KG",
    "STORAGE:LITHIUM_KG",
]
LOW_STORAGE_THRESHOLD = 100.0  # kg

# === ASCII LOGO (yellow) ===
LOGO_ASCII = r"""
     @@@@@@@@@@@@       @@@@@@@@@@@@        @@@@@@@@        @@@@@@@@@@@@       @@@@@@@@@@@@         
      @@@@@@@@@@@@@      @@@@@@@@@@@      @@@@@@@@@@@@     @@@@@@@@@@@@      @@@@@@@@@@@@@          
       @@@@@@@@@@@@@@     @@@@@@@@      @@@@@@@@@@@@@@@@     @@@@@@@@      @@@@@@@@@@@@@            
         @@@@@@@@@@@@@@     @@@@      @@@@@@@@@@@@@@@@@@@@     @@@@      @@@@@@@@@@@@@@             
           @@@@@@@@@@@@@@     @     @@@@@@@@@@@@@@@@@@@@@@@@     @     @@@@@@@@@@@@@@               
             @@@@@@@@@@@@@@       @@@@@@@@@@@@    @@@@@@@@@@@@       @@@@@@@@@@@@@@                 
               @@@@@@@@@@@@@@   @@@@@@@@@@@@        @@@@@@@@@@@@   @@@@@@@@@@@@@@                   
                 @@@@@@@@@@@@@@@@@@@@@@@@@            @@@@@@@@@@@@@@@@@@@@@@@@@                     
                   @@@@@@@@@@@@@@@@@@@@@      @@@@      @@@@@@@@@@@@@@@@@@@@@                       
                     @@@@@@@@@@@@@@@@@      @@@@@@@@      @@@@@@@@@@@@@@@@@                         
                       @@@@@@@@@@@@@@     @@@@@@@@@@@@     @@@@@@@@@@@@@@                           
                         @@@@@@@@@       @@@@@@@@@@@@@@      @@@@@@@@@@                             
"""

# === LOCKDOWN (no exit) ===
def disable_exit():
    sys.exit = lambda *_, **__: print(f"\n{GREEN}[system] Exit disabled. Weyland protocol active.{RESET}\n")

def ignore_signals():
    def handler(signum, frame):
        print(f"\n{GREEN}[system] Signal {signum} ignored. Corporate policy forbids termination.{RESET}")
    for sig in ("SIGINT", "SIGTERM", "SIGHUP", "SIGQUIT"):
        if hasattr(signal, sig):
            signal.signal(getattr(signal, sig), handler)

# === UTILS: slow typing, progress bars, etc. ===
def type_out(s: str, cps: int = 80, end: str = "\n", color: str = GREEN):
    """Typewriter output at roughly cps chars/sec."""
    delay = 1.0 / max(10, cps)
    for ch in s:
        sys.stdout.write((color or "") + ch + (RESET if color else ""))
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write(end)
    sys.stdout.flush()

def bar_task(label: str, steps: int = 8, step_delay: float = 0.6):
    sys.stdout.write(f"{GREEN}{label}{RESET}\r")
    sys.stdout.flush()
    time.sleep(step_delay)
    sys.stdout.write(f"{GREEN}{label} [........]{RESET}\r")
    sys.stdout.flush()
    time.sleep(step_delay)
    for i in range(steps):
        filled = "X" * (i + 1)
        rest = "." * (8 - (i + 1))
        sys.stdout.write(f"{GREEN}{label} [{filled}{rest}]{RESET}\r")
        sys.stdout.flush()
        time.sleep(step_delay)
    sys.stdout.write(f"{GREEN}{label} [XXXXXXXX]{RESET}\r")
    sys.stdout.flush()
    time.sleep(2)
    sys.stdout.write(f"{GREEN}{label} Complete     {RESET}\n")
    sys.stdout.flush()

def fake_progress(task, seconds=2.5):
    steps = 25
    delay = max(0.02, seconds / steps)
    sys.stdout.write(f"{GREEN}{task}: [")
    sys.stdout.flush()
    for _ in range(steps):
        time.sleep(delay)
        sys.stdout.write("#")
        sys.stdout.flush()
    sys.stdout.write(f"] done{RESET}\n")

# === BIOS-STYLE BOOT (ported from your bash script’s “boot” function) ===
def bios_boot_sequence():
    type_out("Initializing BIOS", cps=80)
    time.sleep(0.4)
    type_out("WARNING: BIOS DOES NOT MATCH CALLISTO II BIOS HASH", cps=80)
    time.sleep(0.6)
    type_out("CONTINUE BOOT AT OWN RISK", cps=80)
    time.sleep(0.6)
    type_out("USE OF NON STANDARD BIOS VIOLATES SOFTWARE AGREEMENT", cps=80)
    time.sleep(0.6)
    type_out("SOLAR HARDWARE NOT RESPONSIBLE FOR DAMAGE OR DEATH", cps=80)
    time.sleep(0.8)

    glitch_lines = [
        r"\e[4AW#RNING: BI@S DOES NOT MATCH C@LL1STO II BOIS HASH",
        "CONTIP*E BONT AT O5N RISK",
        "URE 1F N*N STA*DARD B8OS VIOL(TES SOFTWARE AGR3EME^T",
        "SOKAR H@RD#ARE NOT RESPO7SIBLE FOR DEMAGE OR D%ATH",
        r"\e[4AW#R.ING= B*@S D*eS N%T M@TqH C@Ll1!TO %& B.IS H+SH",
        "CO*T+P*E BO!T AT O5N R*SK",
        "U!E 1F N*N STA*D+RD B8OS V*OL(T$S SOFTWARE AGR3EME^T",
        "S0*AR H@$D#!RE NOT RE+PO7SI*LE F+R DEM!GE @R D%ATH",
        r"\e[4AW#R.ING= B*@? D*eS N%T }@TqH C@Ll1!T+ %& B.I< H+SH",
        ":o*?+P*E BO!T AT O5N R*SK",
        "U!E 1F N*N S>A*}+RD B8OS V*OL(T$S S<FT?AR< {GR3EME^T",
        "S0*AR H@$D#!RE N{T RE+PO7SI*L? F+R DEM!GE @R D%ATH",
        "****************************************************************",
        "********************BIOS SECURITY OVERWRITTEN*******************",
        "****************************************************************",
        "****************************************************************",
    ]
    for line in glitch_lines:
        type_out(line, cps=80)
        time.sleep(0.4 if "BIOS SECURITY" not in line and "*" not in line else 0.8)

    os.system("cls" if os.name == "nt" else "clear")
    for dots in ["Initializing boot.", "Initializing boot..", "Initializing boot..."]:
        sys.stdout.write(f"{GREEN}{dots}{RESET}\r")
        sys.stdout.flush()
        time.sleep(0.4)
    sys.stdout.write(" " * 60 + "\r")
    sys.stdout.flush()

    type_out("Version Detect", cps=80)
    time.sleep(0.4)
    type_out("Drake Industries DRAKOS 4.1 beta...", cps=80)
    time.sleep(0.4)
    type_out("Hardware Detect", cps=80)
    time.sleep(0.6)
    type_out("Solar Hardware Callisto II", cps=80)
    time.sleep(0.4)

    bar_task("MEMTEST", steps=8, step_delay=0.6)
    type_out("64K RAM detected", cps=80)
    time.sleep(1.2)

    os.system("cls" if os.name == "nt" else "clear")
    print(f"{YELLOW}{LOGO_ASCII}{RESET}")
    time.sleep(3)

# === WEBDIS HELPERS ===
def safe_get(url):
    """HTTP GET with graceful failure; returns text or None."""
    if requests:
        try:
            r = requests.get(url, timeout=TIMEOUT)
            r.raise_for_status()
            return r.text
        except Exception:
            return None
    else:
        try:
            with request.urlopen(url, timeout=TIMEOUT) as resp:
                return resp.read().decode("utf-8")
        except Exception:
            return None

def webdis_get(key):
    """GET key via Webdis; returns parsed JSON dict or None if unreachable."""
    u = WEBDIS_BASE.rstrip("/") + f"/GET/{parse.quote(key, safe='')}.json"
    raw = safe_get(u)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None

def webdis_set(key, value):
    """SET key via Webdis; returns parsed JSON dict or None if unreachable."""
    u = WEBDIS_BASE.rstrip("/") + f"/SET/{parse.quote(key, safe='')}/{parse.quote(str(value), safe='')}.json"
    raw = safe_get(u)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None

def _extract_scalar(v):
    """Normalize scalars to lowercase strings."""
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float)):
        return str(v).lower()
    if isinstance(v, str):
        return v.strip().lower()
    return None

def _val_from_webdis_get(payload):
    """
    Handle Webdis GET variants:
      {"GET":["OK","1"]}, {"GET":["1"]}, {"GET":"1"}, {"GET":[1]}, {"GET":[true]}
    Returns a lowercase string scalar or 'nil'.
    """
    if payload is None or not isinstance(payload, dict) or "GET" not in payload:
        return "nil"
    data = payload["GET"]
    if isinstance(data, list):
        for item in reversed(data):
            s = _extract_scalar(item)
            if s and s != "ok":
                return s
        return "nil"
    s = _extract_scalar(data)
    return s if s is not None else "nil"

def _truthy(x):
    return str(x).strip().lower() in ("1", "true", "on", "yes")

def _read_flag_by_patterns(base_key):
    """
    Try common key shapes for a single boolean flag.
    base_key: e.g., 'Command_Deck_Room:fire' or 'Command_Deck_Room_fire' (we construct both).
    Returns tuple (found, is_true).
    """
    candidates = [base_key, base_key.lower()]
    if ":" in base_key:
        room, state = base_key.split(":", 1)
        candidates += [f"{room}_{state}", f"{room}_{state}".lower()]
    else:
        if "_" in base_key:
            room, state = base_key.rsplit("_", 1)
            candidates += [f"{room}:{state}", f"{room}:{state}".lower()]

    for k in candidates:
        payload = webdis_get(k)
        if payload is None:
            continue
        val = _val_from_webdis_get(payload)
        if val != "nil":
            return True, _truthy(val)
    return False, False

def _room_state(room, state):
    found, truth = _read_flag_by_patterns(f"{room}:{state}")
    if found:
        return truth
    _, truth = _read_flag_by_patterns(f"{room}_{state}")
    return truth

def _get_any_truthy(*keys):
    for k in keys:
        v = _val_from_webdis_get(webdis_get(k))
        if _truthy(v):
            return True
    return False

def _get_float(key):
    """Fetch a Webdis key and parse it as float; return (ok, value) where ok=False if not present/unparseable."""
    payload = webdis_get(key)
    if payload is None:
        return False, None
    val = _val_from_webdis_get(payload)
    if val == "nil":
        return False, None
    try:
        return True, float(val)
    except Exception:
        # Try stripping non-numeric cruft just in case
        try:
            cleaned = "".join(ch for ch in val if (ch.isdigit() or ch in ".-"))
            return True, float(cleaned)
        except Exception:
            return False, None

# === UI: help and status ===
def print_help():
    print(
        f"{GREEN}"
        "SYSTEMS RECOVERY TERMINAL HELP\n"
        "---------------------------------\n"
        "Limited operational capacity. Full flight data unavailable.\n"
        f"{RESET}"
    )
    print(f"{GREEN}status{RESET}            - Report subsystem alerts and environmental warnings")
    print(f"{GREEN}storage{RESET}           - Query propellant and life-support storage levels")
    print(f"{GREEN}nav_lights{RESET}        - Toggle navigation lights (if functional)")
    print(f"{GREEN}distress_beacon{RESET}   - Manage Lockmart 9000 Distress Beacon")
    print(f"{GREEN}help{RESET}              - Display this message")
    print(f"{GREEN}exit{RESET}              - Attempt to exit (disabled)\n")

def print_status():
    warnings = []

    # Sensor/Webdis availability
    if safe_get(WEBDIS_BASE.rstrip('/') + "/PING") is None:
        print(f"{GREEN}{SENSOR_ERROR_MSG}{RESET}")
        return

    # Per-room warnings (fire/breach only)
    for room in ROOMS:
        if _room_state(room, "fire"):
            warnings.append(f"WARNING: FIRE detected in {room.replace('_', ' ')}.")
        if _room_state(room, "breach"):
            warnings.append(f"WARNING: HULL BREACH detected in {room.replace('_', ' ')}.")

    # Layer detection: prefer deepest active by list order
    active_layers = []
    for lk in LAYER_KEYS:
        v = _val_from_webdis_get(webdis_get(lk))
        if _truthy(v):
            active_layers.append(lk)
    layer = active_layers[-1] if active_layers else "<UNKNOWN LAYER>"

    # Global warnings
    warnings.append(
        f"WARNING: SHIP IN UNCONTROLLED DESCENT THROUGH {layer} of unexplored gas giant. Critical failure imminent."
    )
    warnings.append(
        "WARNING: Primary Crew unreachable. Backup Crew woken up per Weyland Yutani Emergency Guidelines."
    )

    print(f"{GREEN}\n--- SYSTEM WARNINGS ---{RESET}")
    for w in warnings:
        print(f"{GREEN}{w}{RESET}")

# === STORAGE QUERY ===
def print_storage():
    # Sensor/Webdis availability
    if safe_get(WEBDIS_BASE.rstrip('/') + "/PING") is None:
        print(f"{GREEN}{SENSOR_ERROR_MSG}{RESET}")
        return

    print(f"{GREEN}--- STORAGE LEVELS (kg) ---{RESET}")
    low_warnings = []
    for key in STORAGE_KEYS:
        ok, val = _get_float(key)
        label = key.split(":")[-1]
        if not ok or val is None:
            print(f"{GREEN}{label:16} : N/A{RESET}")
            continue
        print(f"{GREEN}{label:16} : {val:,.2f}{RESET}")
        if val < LOW_STORAGE_THRESHOLD:
            low_warnings.append(f"WARNING: LOW CAPACITY for {label} ({val:,.2f} kg)")

    if low_warnings:
        print(f"{GREEN}\n--- STORAGE WARNINGS ---{RESET}")
        for w in low_warnings:
            print(f"{GREEN}{w}{RESET}")

# === DISTRESS BEACON HANDLER ===
LOCKMART_BOILERPLATE = (
    "The Lockmart 9000 Distress Beacon broadcasts on all intergalactic long-range frequencies at the highest "
    "possible power. Lockmart is not responsible for misuse, damage, tumours, or death associated with long-term "
    "Distress Beacon exposure.\n"
    "Would you like to enable the Distress Beacon?"
)

def handle_distress_beacon():
    if safe_get(WEBDIS_BASE.rstrip('/') + "/PING") is None:
        print(f"{GREEN}{SENSOR_ERROR_MSG}{RESET}")
        return

    available = _truthy(_val_from_webdis_get(webdis_get("distress_beacon_available")))
    already_on = _get_any_truthy("distress_beacon_on", "distress_beacon")

    if not available and not already_on:
        print(f"{GREEN}{SYSTEM_ERROR_MSG}{RESET}")
        return

    if already_on:
        print(f"{GREEN}[OK] Distress Beacon is already enabled.{RESET}")
        return

    print(f"{GREEN}{LOCKMART_BOILERPLATE}{RESET}")
    ans = input(f"{GREEN}Enable Distress Beacon? (y/N): {RESET}").strip().lower()
    if ans not in ("y", "yes"):
        print(f"{GREEN}Operation cancelled.{RESET}")
        return

    res = webdis_set("distress_beacon_on", 1)
    if res is None:
        print(f"{GREEN}{SENSOR_ERROR_MSG}{RESET}")
        return

    print(f"{GREEN}[OK] Distress Beacon enabled.{RESET}")

# === REPL ===
def repl():
    while True:
        try:
            cmd = input(f"{GREEN}WY>{RESET} ").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{GREEN}Exit disabled.{RESET}")
            continue

        if cmd == "help":
            print_help()
        elif cmd == "status":
            print_status()
        elif cmd in ("storage", "query_storage", "query storage"):
            print_storage()
        elif cmd == "nav_lights":
            print(f"{GREEN}{SYSTEM_ERROR_MSG}{RESET}")
        elif cmd == "distress_beacon":
            handle_distress_beacon()
        elif cmd == "exit":
            print(f"{GREEN}Exit disabled.{RESET}")
        else:
            print(f"{GREEN}Unknown command. Type 'help'.{RESET}")

# === MAIN ===
def main():
    disable_exit()
    ignore_signals()

    # BIOS-like boot sequence adapted from your bash script
    bios_boot_sequence()

    # Recovery banner
    print(f"{GREEN}Weyland-Yutani Corporation — Proprietary Systems Loader{RESET}\n")
    fake_progress("Authenticating corporate seals", 2.0)
    fake_progress("Mounting restricted volumes", 1.6)
    fake_progress("Decrypting mission data", 1.4)
    print(
        f"\n{GREEN}"
        "SYSTEMS RECOVERY TERMINAL v3.4\n"
        "---------------------------------\n"
        "NOTICE: This interface provides partial access to shipboard systems.\n"
        "Full flight data and mission logs are unavailable.\n"
        "Unauthorized interference with Weyland-Yutani property is a breach of contract.\n"
        f"{RESET}\n"
    )
    print(f"{GREEN}Type 'help' for available commands.{RESET}\n")
    repl()

if __name__ == "__main__":
    main()
