import unittest

from cmf import protocol as p
from cmf.bluez import parse_units

# Verified frames with CRC already computed; seq byte is 1 unless noted.
FRAMES = [
    (0xC001, b"", 1, "55 60 01 01 c0 00 00 01 24 df"),
    (0xC007, b"\x07", 1, "55 60 01 07 c0 01 00 01 07 9f 43"),
    (0xF010, b"\x03\x00", 1, "55 60 01 10 f0 02 00 01 03 00 27 59"),
    (0xF051, b"\x01\x06", 1, "55 60 01 51 f0 02 00 01 01 06 f7 3f"),
    (0xF052, b"\x01", 1, "55 60 01 52 f0 01 00 01 01 53 40"),
    (0xF052, b"\x00", 1, "55 60 01 52 f0 01 00 01 00 92 80"),
    (0xF076, b"\x01\x2c\x01", 1, "55 60 01 76 f0 03 00 01 01 2c 01 e2 09"),
    (0xF076, b"\x00\x00\x00", 1, "55 60 01 76 f0 03 00 01 00 00 00 6e c9"),
    (0xF002, b"\x07\x01", 1, "55 60 01 02 f0 02 00 01 07 01 d6 58"),
]

VERSION_REPLY = "55 60 01 01 40 05 00 01 31 2e 30 2e 31 42 bd"

CUSTOM_EQ_REPLY = (
    "03 00 00 00 80 01 00 00 00 00 00 00 75 44 33 33 33 3f "
    "02 00 00 00 00 00 80 54 45 00 00 80 3f "
    "00 00 00 00 00 00 00 0c 43 cd cc 4c 3f"
)


def hexbytes(text):
    return bytes.fromhex(text)


class FrameTests(unittest.TestCase):
    def test_encode_matches_verified_frames(self):
        for cmd, payload, seq, expected in FRAMES:
            with self.subTest(cmd=hex(cmd)):
                self.assertEqual(p.encode(cmd, payload, seq), hexbytes(expected))

    def test_stereo_frames_match_layout(self):
        # Synthetic MACs; the role bytes and frame layout were verified on hardware.
        self.assertEqual(
            p.encode(p.SET_STEREO, p.encode_stereo(1, 1, "AA:BB:CC:DD:EE:02"), 2),
            hexbytes("55 60 01 47 f0 08 00 02 01 01 02 ee dd cc bb aa 94 d5"),
        )
        self.assertEqual(
            p.encode(p.SET_STEREO, p.encode_stereo(1, 0, "AA:BB:CC:DD:EE:01"), 2),
            hexbytes("55 60 01 47 f0 08 00 02 01 00 01 ee dd cc bb aa 84 26"),
        )

    def test_decode_reply(self):
        frames = p.Decoder().feed(hexbytes(VERSION_REPLY))
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].cmd, 0x4001)
        self.assertEqual(frames[0].seq, 1)
        self.assertEqual(frames[0].payload, b"1.0.1")

    def test_decoder_handles_split_and_coalesced_frames(self):
        decoder = p.Decoder()
        data = hexbytes(VERSION_REPLY) + hexbytes(FRAMES[0][3])
        frames = []
        for byte in data:
            frames += decoder.feed(bytes([byte]))
        self.assertEqual([f.cmd for f in frames], [0x4001, 0xC001])

    def test_bad_crc_is_skipped(self):
        bad = bytearray(hexbytes(VERSION_REPLY))
        bad[-1] ^= 0xFF
        frames = p.Decoder().feed(bytes(bad) + hexbytes(VERSION_REPLY))
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].cmd, 0x4001)

    def test_crc(self):
        self.assertEqual(p.crc16(b"123456789"), 0x4B37)  # standard check value


class CodecTests(unittest.TestCase):
    def test_read_codecs(self):
        self.assertEqual(p.decode_battery(b"\x01\x07\x37"), 55)
        self.assertEqual(p.decode_model(b"\x94\xe4"), "E494")
        self.assertEqual(p.decode_eq(b"\x00"), 0)
        self.assertEqual(p.decode_spatial(b"\x01"), True)
        self.assertEqual(p.decode_night(b"\x01\x2c\x01"), (True, 300))
        self.assertEqual(p.decode_bass(b"\x01\x00"), (True, 0))
        self.assertIsNone(p.decode_battery(b"\x01"))

    def test_write_codecs(self):
        self.assertEqual(p.encode_eq_preset(3), b"\x03\x00")
        self.assertEqual(p.encode_bass(3), b"\x01\x06")
        self.assertEqual(p.encode_spatial(False), b"\x00")
        self.assertEqual(p.encode_night(True, 300), b"\x01\x2c\x01")
        self.assertEqual(p.encode_night(False), b"\x00\x00\x00")
        self.assertEqual(p.UNGROUP_PAYLOAD, b"\x00\x01\xff\xff\xff\xff\xff\xff")

    def test_custom_eq_fixture(self):
        payload = hexbytes(CUSTOM_EQ_REPLY)
        gains = p.decode_custom_eq(payload)
        self.assertEqual(gains, {"mid": 0.0, "high": 0.0, "low": 0.0})
        # Encode is canonical: same band order and constants as the captured reply.
        self.assertEqual(p.encode_custom_eq(gains), payload)

    def test_custom_eq_validates_length(self):
        self.assertIsNone(p.decode_custom_eq(b"\x03\x00"))
        self.assertIsNone(p.decode_custom_eq(b""))

    def test_stereo_state(self):
        self.assertEqual(
            p.decode_stereo(hexbytes("01 01 3c 02 ee dd cc bb aa")),
            (1, "AA:BB:CC:DD:EE:02"),
        )
        # Some firmware appends model and role after the peer MAC.
        self.assertEqual(
            p.decode_stereo(hexbytes("01 01 37 02 ee dd cc bb aa 94 e4 01")),
            (1, "AA:BB:CC:DD:EE:02"),
        )
        self.assertEqual(p.decode_stereo(b"\x00"), (0, None))

    def test_mac_conversion(self):
        self.assertEqual(p.mac_from_le(hexbytes("01 ee dd cc bb aa")), "AA:BB:CC:DD:EE:01")
        self.assertEqual(p.mac_bytes("AA:BB:CC:DD:EE:02")[::-1], hexbytes("02 ee dd cc bb aa"))
        with self.assertRaises(ValueError):
            p.mac_bytes("AA:BB")


class AdvertisementTests(unittest.TestCase):
    def test_live_advertisement_layout(self):
        # Synthetic LE address and classic MAC; the payload layout was verified live.
        objects = {
            "/org/bluez/hci0/dev_11_22_33_44_55_66": {
                "org.bluez.Device1": {
                    "Address": "11:22:33:44:55:66",
                    "AddressType": "random",
                    "Name": "CMF Speaker S",
                    "ManufacturerData": {
                        0x0CCB: hexbytes("02 01 e4 94 01 ee dd cc bb aa")
                    },
                }
            }
        }
        units = parse_units(objects)
        self.assertEqual(len(units), 1)
        self.assertEqual(units[0].classic_mac, "AA:BB:CC:DD:EE:01")
        self.assertEqual(units[0].model, "E494")
        self.assertEqual(units[0].state, 2)

    def test_address_alias_falls_back_to_the_product_name(self):
        objects = {
            "/dev/le": {
                "org.bluez.Device1": {
                    "Address": "11:22:33:44:55:66",
                    "Alias": "7C-A4-25-0D-78-B0",
                    "ManufacturerData": {
                        0x0CCB: hexbytes("02 01 e4 94 01 ee dd cc bb aa")
                    },
                }
            },
            "/dev/classic": {
                "org.bluez.Device1": {
                    "Address": "AA:BB:CC:DD:EE:01",
                    "Name": "CMF Speaker S",
                }
            },
        }
        units = parse_units(objects)
        self.assertEqual(units[0].name, "CMF Speaker S")

    def test_ignores_other_manufacturers_and_short_payloads(self):
        objects = {
            "/dev/a": {"org.bluez.Device1": {"ManufacturerData": {0xFDDF: b"\x03\x0f"}}},
            "/dev/b": {"org.bluez.Device1": {"ManufacturerData": {0x0CCB: b"\x00\x01"}}},
        }
        self.assertEqual(parse_units(objects), [])


if __name__ == "__main__":
    unittest.main()
