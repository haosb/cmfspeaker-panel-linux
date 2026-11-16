import unittest
from unittest.mock import patch

from cmf import protocol as p
from cmf.speaker import Speaker
from cmf.ui import apply_setting


class FakeLink:
    def __init__(self):
        self.calls = []

    def request(self, cmd, payload=b"", timeout=1.0):
        self.calls.append((cmd, payload))
        if cmd == p.GET_CUSTOM_EQ:
            return p.encode_custom_eq({"low": 0.0, "mid": 0.0, "high": 0.0})
        return b""


class FakeUnit:
    def __init__(self, mac):
        self.classic_mac = mac


class FakeSpeaker:
    def __init__(self, mac="AA:BB:CC:DD:EE:FF", stereo=None):
        self.unit = FakeUnit(mac)
        self.stereo_state = stereo
        self.calls = []

    def stereo(self):
        return self.stereo_state

    def set_eq(self, preset):
        self.calls.append(("eq", preset))

    def set_custom_eq(self, gains):
        self.calls.append(("custom_eq", gains))

    def set_bass(self, level):
        self.calls.append(("bass", level))

    def set_spatial(self, enabled):
        self.calls.append(("spatial", enabled))

    def set_night(self, enabled, minutes):
        self.calls.append(("night", enabled, minutes))

    def find(self):
        self.calls.append(("find",))


class FakeSession:
    def __init__(self, *speakers):
        self.speakers = {speaker.unit.classic_mac: speaker for speaker in speakers}

    def states(self):
        return ["state"]


class FlakyLink:
    def __init__(self):
        self.calls = 0

    def request(self, cmd, payload=b"", timeout=1.0):
        self.calls += 1
        return None if self.calls == 1 else b"\x00"


class SpeakerReadTests(unittest.TestCase):
    def test_read_retries_once(self):
        speaker = Speaker(unit=None)
        speaker.link = FlakyLink()
        self.assertEqual(speaker.eq(), 0)
        self.assertEqual(speaker.link.calls, 2)


class SpeakerCustomEqTests(unittest.TestCase):
    def test_stores_bands_then_selects_custom(self):
        speaker = Speaker(unit=None)
        speaker.link = FakeLink()
        gains = {"low": 1.0, "mid": 0.0, "high": 0.0}
        result = speaker.set_custom_eq(gains)
        commands = speaker.link.calls
        self.assertEqual(commands[0][0], p.SET_CUSTOM_EQ)
        self.assertEqual(commands[1], (p.SET_EQ, b"\x05\x00"))
        self.assertEqual(result, {"low": 0.0, "mid": 0.0, "high": 0.0})


class ApplySettingTests(unittest.TestCase):
    def setUp(self):
        self.speaker = FakeSpeaker()
        self.session = FakeSession(self.speaker)

    def test_custom_preset_selects_five(self):
        apply_setting(self.session, {"action": "eq", "preset": "custom"})
        self.assertEqual(self.speaker.calls, [("eq", 5)])

    def test_unknown_preset_rejected(self):
        with self.assertRaises(ValueError):
            apply_setting(self.session, {"action": "eq", "preset": "loud"})
        self.assertEqual(self.speaker.calls, [])

    def test_custom_gains_validated(self):
        apply_setting(
            self.session,
            {"action": "custom_eq", "gains": {"low": 3, "mid": -2, "high": 0}},
        )
        self.assertEqual(self.speaker.calls[0][0], "custom_eq")
        with self.assertRaises(ValueError):
            apply_setting(
                self.session,
                {"action": "custom_eq", "gains": {"low": 7, "mid": 0, "high": 0}},
            )

    def test_bass_level_validated(self):
        apply_setting(self.session, {"action": "bass", "level": 3})
        self.assertEqual(self.speaker.calls, [("bass", 3)])
        with self.assertRaises(ValueError):
            apply_setting(self.session, {"action": "bass", "level": 6})

    def test_switches_and_find(self):
        apply_setting(self.session, {"action": "spatial", "on": True})
        apply_setting(self.session, {"action": "night", "on": False, "minutes": 0})
        apply_setting(self.session, {"action": "find"})
        self.assertEqual(
            self.speaker.calls,
            [("spatial", True), ("night", False, 0), ("find",)],
        )

    def test_switches_require_boolean(self):
        with self.assertRaises(ValueError):
            apply_setting(self.session, {"action": "spatial", "on": "true"})
        with self.assertRaises(ValueError):
            apply_setting(self.session, {"action": "night", "on": 1, "minutes": 30})
        self.assertEqual(self.speaker.calls, [])

    def test_unknown_unit_rejected(self):
        with self.assertRaises(ValueError):
            apply_setting(self.session, {"action": "find", "macs": ["00:00:00:00:00:00"]})

    @patch("cmf.ui.is_classic_connected", side_effect=lambda mac: mac == "AA:BB:CC:DD:EE:01")
    def test_stereo_slave_write_also_reaches_master(self, _connected):
        master = FakeSpeaker("AA:BB:CC:DD:EE:01", stereo=(1, "AA:BB:CC:DD:EE:02"))
        slave = FakeSpeaker("AA:BB:CC:DD:EE:02", stereo=(1, None))
        session = FakeSession(master, slave)
        apply_setting(
            session,
            {"action": "bass", "level": 3, "macs": ["AA:BB:CC:DD:EE:02"]},
        )
        self.assertEqual(slave.calls, [("bass", 3)])
        self.assertEqual(master.calls, [("bass", 3)])

    @patch("cmf.ui.is_classic_connected", side_effect=lambda mac: mac == "AA:BB:CC:DD:EE:01")
    def test_find_stays_on_the_selected_unit(self, _connected):
        master = FakeSpeaker("AA:BB:CC:DD:EE:01", stereo=(1, "AA:BB:CC:DD:EE:02"))
        slave = FakeSpeaker("AA:BB:CC:DD:EE:02", stereo=(1, None))
        session = FakeSession(master, slave)
        apply_setting(session, {"action": "find", "macs": ["AA:BB:CC:DD:EE:02"]})
        self.assertEqual(slave.calls, [("find",)])
        self.assertEqual(master.calls, [])

    @patch("cmf.ui.is_classic_connected", return_value=False)
    def test_unpaired_units_are_not_expanded(self, _connected):
        left = FakeSpeaker("AA:BB:CC:DD:EE:01", stereo=(0, None))
        right = FakeSpeaker("AA:BB:CC:DD:EE:02", stereo=(0, None))
        session = FakeSession(left, right)
        apply_setting(
            session,
            {"action": "bass", "level": 2, "macs": ["AA:BB:CC:DD:EE:02"]},
        )
        self.assertEqual(right.calls, [("bass", 2)])
        self.assertEqual(left.calls, [])


if __name__ == "__main__":
    unittest.main()
