import time
from urllib.parse import quote
import appdaemon.plugins.hass.hassapi as hass
import requests


class RPG2025RoomKeys(hass.Hass):
    """
    Existing:
      - Aggregate room OK/FIRE/BREACH booleans from HA -> write per-room key to Webdis
      - Optional publish to pubsub channel

    New (every tick, unconditional):
      - HA Phase booleans -> Webdis keys Phase1..Phase4 (strings "true"/"false")
      - Webdis Layer keys -> HA booleans (CloudDeck/Stratosheath/RedZone/Crushdepth)
    """

    # ---------- Existing room map (unchanged) ----------
    ENTITY_MAP = {
        "input_boolean.commanddeck_ok":     ("Command_Deck_Room", "ok"),
        "input_boolean.commanddeck_fire":   ("Command_Deck_Room", "fire"),
        "input_boolean.commanddeck_breach": ("Command_Deck_Room", "breach"),

        "input_boolean.recreation_ok":      ("Recreation_Lounge_Room", "ok"),
        "input_boolean.recreation_fire":    ("Recreation_Lounge_Room", "fire"),
        "input_boolean.recreation_breach":  ("Recreation_Lounge_Room", "breach"),

        "input_boolean.cargobay_ok":        ("Cargo_Bay_Room", "ok"),
        "input_boolean.cargobay_fire":      ("Cargo_Bay_Room", "fire"),
        "input_boolean.cargobay_breach":    ("Cargo_Bay_Room", "breach"),

        "input_boolean.computercore_ok":    ("Computer_Core_Room", "ok"),
        "input_boolean.computercore_fire":  ("Computer_Core_Room", "fire"),
        "input_boolean.computercore_breach":("Computer_Core_Room", "breach"),

        "input_boolean.medical_ok":         ("Medical_Room", "ok"),
        "input_boolean.medical_fire":       ("Medical_Room", "fire"),
        "input_boolean.medical_breach":     ("Medical_Room", "breach"),

        "input_boolean.crewqtrs_ok":        ("Crew_Qtrs_Room", "ok"),
        "input_boolean.crewqtrs_fire":      ("Crew_Qtrs_Room", "fire"),
        "input_boolean.crewqtrs_breach":    ("Crew_Qtrs_Room", "breach"),

        "input_boolean.briefing_ok":        ("Briefing_Room", "ok"),
        "input_boolean.briefing_fire":      ("Briefing_Room", "fire"),
        "input_boolean.briefing_breach":    ("Briefing_Room", "breach"),

        "input_boolean.armoury_ok":         ("Armoury_Brig_Room", "ok"),
        "input_boolean.armoury_fire":       ("Armoury_Brig_Room", "fire"),
        "input_boolean.armoury_breach":     ("Armoury_Brig_Room", "breach"),

        "input_boolean.comms_ok":           ("Primary_Comms_Room", "ok"),
        "input_boolean.comms_fire":         ("Primary_Comms_Room", "fire"),
        "input_boolean.comms_breach":       ("Primary_Comms_Room", "breach"),

        "input_boolean.cryostore_ok":       ("Cryo_Storage_Room", "ok"),
        "input_boolean.cryostore_fire":     ("Cryo_Storage_Room", "fire"),
        "input_boolean.cryostore_breach":   ("Cryo_Storage_Room", "breach"),

        "input_boolean.engineering_ok":     ("Engineering_Room", "ok"),
        "input_boolean.engineering_fire":   ("Engineering_Room", "fire"),
        "input_boolean.engineering_breach": ("Engineering_Room", "breach"),

        "input_boolean.reactor_ok":         ("Reactor_Core_Room", "ok"),
        "input_boolean.reactor_fire":       ("Reactor_Core_Room", "fire"),
        "input_boolean.reactor_breach":     ("Reactor_Core_Room", "breach"),
    }

    # Webdis layer keys to *read* and reflect into HA booleans
    LAYER_KEYS = ["CloudDeck", "Stratosheath", "RedZone", "Crushdepth"]

    def initialize(self):
        # Config
        self.webdis_url   = self.args.get("webdis_url", "http://192.168.30.114:7379").rstrip("/")
        self.key_prefix   = self.args.get("key_prefix", "rpg2025_room_")
        self.pub_channel  = self.args.get("pub_channel", "rpg2025_room_updates")
        self.phase_pub_channel = self.args.get("phase_pub_channel", "orbit_phase_updates")
        self.layer_pub_channel = self.args.get("layer_pub_channel", "orbit_layer_updates")
        self.interval     = int(self.args.get("interval_sec", 2))
        self.timeout      = float(self.args.get("timeout", 4.0))
        self.publish_on_change = bool(self.args.get("publish_on_change", True))
        self.verbose      = bool(self.args.get("verbose", True))

        # HA entity ids for layer flags (override in apps.yaml if different)
        self.layer_to_ha = {
            "CloudDeck":    self.args.get("ha_cloud_deck",   "input_boolean.cloud_deck"),
            "Stratosheath": self.args.get("ha_stratosheath", "input_boolean.stratosheath"),
            "RedZone":      self.args.get("ha_red_zone",     "input_boolean.red_zone"),
            "Crushdepth":   self.args.get("ha_crushdepth",   "input_boolean.crushdepth"),
        }

        # HA entity ids for PHASE booleans (override if needed)
        self.phase_ha = {
            "Phase1": self.args.get("ha_phase1", "input_boolean.phase1"),
            "Phase2": self.args.get("ha_phase2", "input_boolean.phase2"),
            "Phase3": self.args.get("ha_phase3", "input_boolean.phase3"),
            "Phase4": self.args.get("ha_phase4", "input_boolean.phase4"),
        }

        self._sess = requests.Session()
        self._last = {}  # room_id -> last state string we wrote

        self.log(f"[init] Webdis={self.webdis_url} prefix={self.key_prefix} interval={self.interval}s")
        self.run_every(self._tick, "now", self.interval)

    # ---------- Periodic tick ----------
    def _tick(self, _kwargs):
        # 1) Existing: gather HA booleans, resolve per-room, write to Webdis on change
        raw = {eid: (self.get_state(eid) or "unknown") for eid in self.ENTITY_MAP}
        rooms = self._resolve_rooms(raw)
        changed = 0
        for room_id, state in rooms.items():
            if self._last.get(room_id) != state:
                self._write_room(room_id, state)
                self._last[room_id] = state
                changed += 1

        # 2) NEW: push HA phase booleans -> Webdis keys (unconditional)
        self._sync_phases_ha_to_webdis()

        # 3) NEW: read Webdis layer keys -> force HA booleans (unconditional)
        self._sync_layers_webdis_to_ha()

        if self.verbose:
            fires   = sum(1 for v in rooms.values() if v == "fire")
            breaches= sum(1 for v in rooms.values() if v == "breach")
            self.log(f"[tick] rooms={len(rooms)} changed={changed} fire={fires} breach={breaches}")

    # ---------- Resolve room precedence (unchanged) ----------
    def _resolve_rooms(self, raw_states):
        agg = {}
        for eid, (room, kind) in self.ENTITY_MAP.items():
            is_on = (raw_states.get(eid) == "on")
            agg.setdefault(room, {"ok": False, "breach": False, "fire": False})
            agg[room][kind] = is_on

        out = {}
        for room, f in agg.items():
            if f["ok"]:
                out[room] = "ok"
            elif f["breach"]:
                out[room] = "breach"
            elif f["fire"]:
                out[room] = "fire"
            else:
                out[room] = "ok"
        return out

    # ---------- Webdis helpers ----------
    def _webdis_get_json(self, path):
        url = f"{self.webdis_url}/{path}"
        try:
            r = self._sess.get(url, timeout=self.timeout)
            if r.status_code != 200:
                self.log(f"[webdis] GET {url} -> HTTP {r.status_code}")
                return None
            return r.json()
        except Exception as e:
            self.log(f"[webdis] GET {url} failed: {e}")
            return None

    def _webdis_get_values(self, keys):
        """Return list aligned with keys using MGET JSON; fallback to individual GETs."""
        path = "MGET/" + "/".join(quote(k, safe="") for k in keys) + ".json"
        data = self._webdis_get_json(path)
        if data and "MGET" in data:
            vals = data["MGET"]
            out = []
            for v in vals:
                if isinstance(v, dict) and "value" in v:
                    out.append(str(v["value"]))
                else:
                    out.append(None if v is None else str(v))
            return out

        out = []
        for k in keys:
            g = self._webdis_get_json(f"GET/{quote(k, safe='')}.json")
            if g and "GET" in g:
                gv = g["GET"]
                if isinstance(gv, list) and gv:
                    out.append(str(gv[0]))
                elif isinstance(gv, dict) and "value" in gv:
                    out.append(str(gv["value"]))
                else:
                    out.append(None)
            else:
                out.append(None)
        return out

    def _webdis_set(self, key, value):
        """SET key to value (string), no JSON post body."""
        url_set = f"{self.webdis_url}/SET/{quote(key, safe='')}/{quote(value, safe='')}"
        try:
            r = self._sess.get(url_set, timeout=self.timeout)
            if self.verbose:
                self.log(f"[webdis] SET {key}={value} -> HTTP {r.status_code} RESP={r.text[:160]!r}")
        except Exception as e:
            self.log(f"[webdis] SET failed for {key}: {e}")

    def _webdis_publish(self, channel, message):
        url_pub = f"{self.webdis_url}/PUBLISH/{quote(channel, safe='')}/{quote(message, safe='')}"
        try:
            r = self._sess.get(url_pub, timeout=self.timeout)
            if self.verbose:
                self.log(f"[webdis] PUB {channel} {message!r} -> HTTP {r.status_code} RESP={r.text[:160]!r}")
        except Exception as e:
            self.log(f"[webdis] PUB failed for {channel}: {e}")

    # ---------- Existing: write per-room state to Webdis ----------
    def _write_room(self, room_id, state_str):
        key = f"{self.key_prefix}{room_id}"
        self._webdis_set(key, state_str)
        if self.publish_on_change and self.pub_channel:
            self._webdis_publish(self.pub_channel, f"{room_id}:{state_str}")

    # ---------- NEW: HA phase booleans -> Webdis (unconditional) ----------
    def _sync_phases_ha_to_webdis(self):
        for phase_key, entity in self.phase_ha.items():
            # If entity is missing in HA, skip gracefully
            try:
                st = self.get_state(entity)
            except Exception as e:
                self.log(f"[phase] get_state failed for {entity}: {e}")
                st = None

            truthy = (st == "on")
            val = "true" if truthy else "false"

            self._webdis_set(phase_key, val)
            if self.phase_pub_channel:
                self._webdis_publish(self.phase_pub_channel, f"{phase_key}:{val}")

            if self.verbose:
                self.log(f"[phase] HA {entity}={st!r} -> Webdis {phase_key}={val}")

    # ---------- NEW: Webdis layer flags -> HA (unconditional) ----------
    def _sync_layers_webdis_to_ha(self):
        vals = self._webdis_get_values(self.LAYER_KEYS)
        if self.verbose:
            self.log(f"[layers] Webdis MGET {self.LAYER_KEYS} -> {vals}")

        for key, val in zip(self.LAYER_KEYS, vals):
            entity = self.layer_to_ha.get(key)
            if not entity:
                continue

            truthy = False
            if val is not None:
                s = str(val).strip().lower()
                truthy = s in ("1", "true", "yes", "on")

            try:
                if truthy:
                    self.turn_on(entity)
                else:
                    self.turn_off(entity)
                if self.verbose:
                    self.log(f"[layers] {'turn_on' if truthy else 'turn_off'}({entity}) (from {key}={val!r})")
            except Exception as e:
                self.log(f"[layers] Failed to set {entity} from {key}: {e}")
