"""Local web console: python3 -m cmf.ui (127.0.0.1 only)."""

import json
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from .bluez import is_classic_connected, scan
from .speaker import Speaker, pair_stereo, ungroup

PORT = 8747
UI_DIR = Path(__file__).parent / "ui"

STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/fonts/archivo.woff2": ("fonts/archivo.woff2", "font/woff2"),
    "/fonts/doto.woff2": ("fonts/doto.woff2", "font/woff2"),
}

PRESETS = {"balanced": 0, "voice": 1, "treble": 2, "bass": 3, "custom": 5}
EQ_NAMES = {0: "Balanced", 1: "Voice", 2: "More treble", 3: "More bass", 5: "Custom"}
BANDS = ("low", "mid", "high")
# These settings propagate across a stereo pair from the master; find stays per-unit.
SYNCED = {"eq", "custom_eq", "bass", "spatial", "night"}


class Session:
    def __init__(self):
        self.speakers = {}

    def close(self):
        for speaker in self.speakers.values():
            try:
                speaker.close()
            except Exception:
                pass
        self.speakers.clear()

    def connect(self):
        self.close()
        units = scan()
        errors = []
        for unit in units[:2]:
            speaker = Speaker(unit)
            try:
                speaker.open()
            except Exception as exc:
                errors.append(f"{unit.classic_mac}: {exc}")
                continue
            self.speakers[unit.classic_mac] = speaker
        return errors

    def states(self):
        states = []
        for mac, speaker in self.speakers.items():
            try:
                states.append(_state(speaker))
            except Exception as exc:
                states.append({"mac": mac, "error": str(exc)})
        return states


def _state(speaker):
    summary = speaker.summary()
    unit = summary["unit"]
    custom = summary["custom_eq"] or {}
    bass = summary["bass"]
    night = summary["night"]
    stereo = summary["stereo"]
    peer = stereo[1] if stereo and stereo[0] == 1 else None
    if peer == "00:00:00:00:00:00":
        peer = None
    eq = summary["eq"]
    return {
        "mac": unit.classic_mac,
        "name": unit.name,
        "model": summary["model"] or unit.model,
        "a2dp": is_classic_connected(unit.classic_mac),
        "protocol": summary["protocol"],
        "firmware": summary["firmware"],
        "battery": summary["battery"],
        "eq": {"id": eq, "name": EQ_NAMES.get(eq, f"Preset {eq}") if eq is not None else None},
        "custom": {name: custom.get(name) for name in BANDS},
        "bass": None if bass is None else {"on": bass[0], "level": bass[1]},
        "spatial": summary["spatial"],
        "night": None if night is None else {"on": night[0], "minutes": night[1]},
        "stereo": None if stereo is None else {"mode": stereo[0], "peer": peer},
    }


def _number(value, low, high, label):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be a number")
    if not low <= number <= high:
        raise ValueError(f"{label} must be between {low} and {high}")
    return number


def _boolean(value, label):
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be true or false")
    return value


def _targets(session, payload):
    macs = payload.get("macs") or list(session.speakers)
    targets = [session.speakers[mac] for mac in macs if mac in session.speakers]
    if not targets:
        raise ValueError("no connected unit selected; rescan")
    return targets


def _stereo_master(session):
    if len(session.speakers) < 2:
        return None
    states = {speaker: speaker.stereo() for speaker in session.speakers.values()}
    paired = [speaker for speaker, state in states.items() if state and state[0] == 1]
    if not paired:
        return None
    for speaker in paired:
        if is_classic_connected(speaker.unit.classic_mac):
            return speaker
    return next((speaker for speaker in paired if states[speaker][1]), paired[0])


def apply_setting(session, payload):
    action = payload.get("action")
    targets = _targets(session, payload)
    # In stereo the pair syncs from the master; a slave-only write would desync it.
    if action in SYNCED and len(session.speakers) > 1:
        master = _stereo_master(session)
        if master is not None and master not in targets:
            targets.append(master)
    for speaker in targets:
        if action == "eq":
            preset = payload.get("preset")
            if preset not in PRESETS:
                raise ValueError("unknown EQ preset")
            speaker.set_eq(PRESETS[preset])
        elif action == "custom_eq":
            gains = payload.get("gains") or {}
            speaker.set_custom_eq(
                {name: _number(gains.get(name), -6, 6, f"{name} gain") for name in BANDS}
            )
        elif action == "bass":
            level = int(_number(payload.get("level"), 0, 5, "bass level"))
            speaker.set_bass(level)
        elif action == "spatial":
            speaker.set_spatial(_boolean(payload.get("on"), "spatial"))
        elif action == "night":
            minutes = int(_number(payload.get("minutes", 300), 0, 1440, "night minutes"))
            speaker.set_night(_boolean(payload.get("on"), "night mode"), minutes)
        elif action == "find":
            speaker.find()
        else:
            raise ValueError("unknown action")
    return session.states()


def apply_pair(session, payload):
    master, slave = payload.get("master"), payload.get("slave")
    if not master or not slave or master == slave:
        raise ValueError("master and slave must be two different units")
    if master not in session.speakers or slave not in session.speakers:
        raise ValueError("both units must be connected; rescan")
    if not is_classic_connected(master):
        raise ValueError("connect this laptop's audio to the master unit first, then pair")
    pair_stereo(session.speakers[master], session.speakers[slave])
    return session.states()


def apply_ungroup(session, payload):
    mac = payload.get("master")
    if mac not in session.speakers:
        raise ValueError("unit is not connected; rescan")
    ungroup(session.speakers[mac])
    return session.states()


SESSION = Session()


class Handler(BaseHTTPRequestHandler):
    server_version = "cmf-ui"

    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path.split("?", 1)[0] == "/api/state":
            self._json({"states": SESSION.states()})
        else:
            self._static()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length > 65536:
                raise ValueError("request too large")
            payload = json.loads(self.rfile.read(length) or b"{}")
            path = self.path.split("?", 1)[0]
            if path == "/api/session":
                errors = [] if SESSION.speakers else SESSION.connect()
                self._json({"states": SESSION.states(), "errors": errors})
            elif path == "/api/scan":
                errors = SESSION.connect()
                self._json({"states": SESSION.states(), "errors": errors})
            elif path == "/api/set":
                self._json({"states": apply_setting(SESSION, payload)})
            elif path == "/api/pair":
                self._json({"states": apply_pair(SESSION, payload)})
            elif path == "/api/ungroup":
                self._json({"states": apply_ungroup(SESSION, payload)})
            else:
                self.send_error(404)
        except Exception as exc:
            self._json({"error": str(exc)}, 400)

    def _static(self):
        entry = STATIC.get(self.path.split("?", 1)[0])
        if entry is None:
            self.send_error(404)
            return
        name, content_type = entry
        body = (UI_DIR / name).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "font-src 'self'; connect-src 'self'; img-src 'self'; frame-ancestors 'none'; "
            "base-uri 'none'; form-action 'none'",
        )
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def main():
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}/"
    print(f"cmf UI: {url}  (Ctrl+C to stop)")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        SESSION.close()
        server.server_close()


if __name__ == "__main__":
    main()
