"""CMF Speaker S model: settings with read-back, and stereo pairing."""

import time

from . import protocol as p
from .bluez import Link

# Unsupported reads answer nothing; short probe keeps status fast.
TIMEOUT = 0.4


class Speaker:
    def __init__(self, unit):
        self.unit = unit
        self.link = None

    def open(self):
        self.link = Link(self.unit)
        return self

    def close(self):
        if self.link:
            self.link.close()
            self.link = None

    def __enter__(self):
        return self.open()

    def __exit__(self, *exc):
        self.close()

    def _read(self, cmd, payload=p.READ_ENDPOINT):
        reply = self.link.request(cmd, payload, timeout=TIMEOUT)
        if reply is None:  # transient miss; unsupported commands simply miss twice
            reply = self.link.request(cmd, payload, timeout=TIMEOUT)
        return reply

    def protocol_version(self):
        raw = self._read(p.GET_PROTOCOL_VERSION, b"")
        return raw.decode(errors="replace") if raw else None

    def firmware(self):
        raw = self._read(p.GET_FIRMWARE)
        return raw.decode(errors="replace") if raw else None

    def model(self):
        raw = self._read(p.GET_MODEL)
        return p.decode_model(raw)

    def battery(self):
        return p.decode_battery(self._read(p.GET_BATTERY))

    def eq(self):
        return p.decode_eq(self._read(p.GET_EQ))

    def set_eq(self, preset):
        self.link.request(p.SET_EQ, p.encode_eq_preset(preset))
        return self.eq()  # the device silently enforces interlocks

    def custom_eq(self):
        return p.decode_custom_eq(self._read(p.GET_CUSTOM_EQ))

    def set_custom_eq(self, gains):
        self.link.request(p.SET_CUSTOM_EQ, p.encode_custom_eq(gains))
        # F041 only stores the bands; preset 5 is what actually selects Custom.
        self.link.request(p.SET_EQ, p.encode_eq_preset(5))
        return self.custom_eq()

    def bass(self):
        return p.decode_bass(self._read(p.GET_BASS))

    def set_bass(self, level):
        self.link.request(p.SET_BASS, p.encode_bass(level))
        return self.bass()

    def spatial(self):
        return p.decode_spatial(self._read(p.GET_SPATIAL))

    def set_spatial(self, enabled):
        self.link.request(p.SET_SPATIAL, p.encode_spatial(enabled))
        return self.spatial()

    def night(self):
        return p.decode_night(self._read(p.GET_NIGHT))

    def set_night(self, enabled, minutes=300):
        self.link.request(p.SET_NIGHT, p.encode_night(enabled, minutes))
        return self.night()

    def find(self):
        self.link.request(p.FIND, b"\x07\x01")

    def stereo(self):
        return p.decode_stereo(self._read(p.GET_STEREO))

    def summary(self):
        return {
            "unit": self.unit,
            "protocol": self.protocol_version(),
            "model": self.model(),
            "firmware": self.firmware(),
            "battery": self.battery(),
            "eq": self.eq(),
            "custom_eq": self.custom_eq(),
            "bass": self.bass(),
            "spatial": self.spatial(),
            "night": self.night(),
            "stereo": self.stereo(),
        }


def pair_stereo(master, slave):
    """Master must already be the host's A2DP sink; the peer should be idle."""
    if master.link.request(
        p.SET_STEREO, p.encode_stereo(1, 1, slave.unit.classic_mac), timeout=1.0
    ) is None:
        raise RuntimeError(f"no ack from master {master.unit.classic_mac}")
    if slave.link.request(
        p.SET_STEREO, p.encode_stereo(1, 0, master.unit.classic_mac), timeout=1.0
    ) is None:
        raise RuntimeError(f"no ack from slave {slave.unit.classic_mac}")
    master.link.wait_event(p.EVENT_STEREO, timeout=3.0)
    # The units can report single for a moment after the ack; poll until they link.
    deadline = time.monotonic() + 4.0
    state = master.stereo()
    while (not state or state[0] != 1) and time.monotonic() < deadline:
        time.sleep(0.2)
        state = master.stereo()
    return state


def ungroup(speaker):
    speaker.link.request(p.SET_STEREO, p.UNGROUP_PAYLOAD, timeout=1.0)
    return speaker.stereo()
