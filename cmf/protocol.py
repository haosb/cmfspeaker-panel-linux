"""Nothing/CMF 0x55 framing, CRCs and payload codecs for Speaker S (E494).

Frame: 55 | control u16LE | cmd u16LE | len u16LE | seq | payload | crc16LE
CRC-16/MODBUS over everything before the CRC. Replies clear bit 15 of the command.
"""

import struct
from dataclasses import dataclass

# Reads carry endpoint 0x07 except GET_PROTOCOL_VERSION, which has an empty payload.
READ_ENDPOINT = b"\x07"

GET_PROTOCOL_VERSION = 0xC001
GET_BATTERY = 0xC007
GET_MODEL = 0xC01C
GET_FIRMWARE = 0xC042
GET_EQ = 0xC01F
SET_EQ = 0xF010
GET_CUSTOM_EQ = 0xC044
SET_CUSTOM_EQ = 0xF041
GET_BASS = 0xC04E
SET_BASS = 0xF051
GET_SPATIAL = 0xC04F
SET_SPATIAL = 0xF052
GET_NIGHT = 0xC072
SET_NIGHT = 0xF076
GET_FIND = 0xC002
FIND = 0xF002
GET_STEREO = 0xC045
SET_STEREO = 0xF047
EVENT_STEREO = 0x6026

EQ_PRESETS = {0: "balanced", 1: "voice", 2: "more treble", 3: "more bass", 5: "custom"}

# Device wire order (matches the captured C044 reply): peak, high shelf, low shelf.
BANDS = (
    ("mid", 1, 980.0, 0.7),
    ("high", 2, 3400.0, 1.0),
    ("low", 0, 140.0, 0.8),
)


def crc16(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


@dataclass
class Frame:
    cmd: int
    seq: int
    payload: bytes


def encode(cmd, payload=b"", seq=1):
    body = struct.pack("<BHHHB", 0x55, 0x0160, cmd, len(payload), seq) + payload
    return body + struct.pack("<H", crc16(body))


class Decoder:
    """Accumulates notifications; ATT may split or coalesce frames."""

    def __init__(self):
        self.buf = bytearray()

    def feed(self, data):
        self.buf += data
        frames = []
        while True:
            start = self.buf.find(0x55)
            if start < 0:
                self.buf.clear()
                break
            del self.buf[:start]
            if len(self.buf) < 8:
                break
            _, cmd, length = struct.unpack_from("<HHH", self.buf, 1)
            if length > 512:  # corrupt length: resync on the next 0x55
                del self.buf[:1]
                continue
            total = 8 + length + 2
            if len(self.buf) < total:
                break
            raw = bytes(self.buf[:total])
            if crc16(raw[:-2]) != int.from_bytes(raw[-2:], "little"):
                del self.buf[:1]
                continue
            frames.append(Frame(cmd, raw[7], raw[8 : 8 + length]))
            del self.buf[:total]
        return frames


def mac_bytes(mac):
    parts = mac.split(":")
    if len(parts) != 6:
        raise ValueError(f"bad MAC: {mac}")
    return bytes(int(part, 16) for part in parts)


def mac_from_le(raw):
    return ":".join(f"{byte:02X}" for byte in reversed(raw[-6:]))


def decode_battery(payload):
    return payload[2] if payload and len(payload) >= 3 else None


def decode_model(payload):
    return f"{int.from_bytes(payload[:2], 'little'):04X}" if payload and len(payload) >= 2 else None


def encode_eq_preset(preset):
    return bytes([preset, 0])


def decode_eq(payload):
    return payload[0] if payload else None


def encode_custom_eq(gains):
    payload = bytes([len(BANDS)]) + struct.pack("<f", -0.0)  # device's own reply encoding
    for name, filt, freq, q in BANDS:
        payload += struct.pack("<Bfff", filt, float(gains[name]), freq, q)
    return payload


def decode_custom_eq(payload):
    if not payload or len(payload) < 5:
        return None
    count = payload[0]
    if len(payload) < 5 + count * 13:
        return None
    gains = {}
    for index in range(count):
        filt, gain, _freq, _q = struct.unpack_from("<Bfff", payload, 5 + index * 13)
        name = next((n for n, f, _, _ in BANDS if f == filt), None)
        if name:
            gains[name] = gain
    return gains


def encode_bass(level):
    return bytes([1 if level else 0, level * 2])


def decode_bass(payload):
    if not payload or len(payload) < 2:
        return None
    return bool(payload[0]), payload[1] // 2


def encode_spatial(enabled):
    return bytes([1 if enabled else 0])


def decode_spatial(payload):
    return bool(payload[0]) if payload else None


def encode_night(enabled, minutes=300):
    return bytes([1 if enabled else 0]) + struct.pack("<H", minutes if enabled else 0)


def decode_night(payload):
    if not payload or len(payload) < 3:
        return None
    return bool(payload[0]), struct.unpack_from("<H", payload, 1)[0]


def encode_stereo(mode, role, peer_mac):
    return bytes([mode, role]) + mac_bytes(peer_mac)[::-1]


UNGROUP_PAYLOAD = bytes([0, 1]) + b"\xff" * 6


def decode_stereo(payload):
    if not payload:
        return None
    # Peer MAC is payload[3:9]; some firmware appends a 3-byte trailer (model/role).
    peer = mac_from_le(payload[3:9]) if len(payload) >= 9 and payload[0] == 1 else None
    return payload[0], peer
