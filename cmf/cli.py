"""Command line app: python3 -m cmf <command>."""

import argparse

from . import protocol as p
from .bluez import is_classic_connected, scan
from .speaker import Speaker, pair_stereo, ungroup

PRESETS = {"balanced": 0, "voice": 1, "treble": 2, "bass": 3, "custom": 5}


def _gain(value):
    gain = float(value)
    if not -6.0 <= gain <= 6.0:
        raise argparse.ArgumentTypeError("gain must be between -6 and +6 dB")
    return gain


def _parse(argv):
    parser = argparse.ArgumentParser(
        prog="cmf", description="Control a CMF Speaker S (E494) over BLE GATT."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("scan", help="list nearby units")

    target = argparse.ArgumentParser(add_help=False)
    target.add_argument("--mac", help="classic MAC of the unit; default: the only unit found")
    sub.add_parser("status", parents=[target], help="read all settings")
    eq = sub.add_parser("eq", parents=[target], help="set an EQ preset")
    eq.add_argument("preset", choices=sorted(PRESETS))
    custom = sub.add_parser("custom-eq", parents=[target], help="set 3-band custom EQ")
    custom.add_argument("low", type=_gain, help="low shelf 140 Hz, dB")
    custom.add_argument("mid", type=_gain, help="peak 980 Hz, dB")
    custom.add_argument("high", type=_gain, help="high shelf 3400 Hz, dB")
    bass = sub.add_parser("bass", parents=[target], help="Ultra Bass level (0 = off)")
    bass.add_argument("level", type=int, choices=range(6))
    spatial = sub.add_parser("spatial", parents=[target], help="spatial audio")
    spatial.add_argument("state", choices=["on", "off"])
    night = sub.add_parser("night", parents=[target], help="night mode")
    night.add_argument("state", choices=["on", "off"])
    night.add_argument("--minutes", type=int, default=300, help="auto-off minutes (default 300)")
    sub.add_parser("find", parents=[target], help="make the speaker play a locating sound")
    sub.add_parser("ungroup", parents=[target], help="leave the stereo pair")

    pair = sub.add_parser("pair", help="stereo-pair two units")
    pair.add_argument("--master", help="classic MAC of the A2DP master")
    pair.add_argument("--slave", help="classic MAC of the idle second unit")
    return parser.parse_args(argv)


def _pick(units, mac):
    if mac:
        for unit in units:
            if unit.classic_mac.upper() == mac.upper():
                return unit
        raise SystemExit(f"{mac} is not advertising; run `cmf scan`")
    if len(units) == 1:
        return units[0]
    raise SystemExit("several units found; pass --mac (see `cmf scan`)")


def _eq_name(value):
    return "?" if value is None else p.EQ_PRESETS.get(value, f"id {value}")


def _bass_text(value):
    if value is None:
        return "?"
    enabled, level = value
    return f"level {level}" if enabled else "off"


def _bool_text(value):
    return "?" if value is None else ("on" if value else "off")


def _night_text(value):
    if value is None:
        return "?"
    enabled, minutes = value
    return f"on ({minutes} min)" if enabled else "off"


def _stereo_text(value):
    if value is None:
        return "?"
    mode, peer = value
    return {0: "single", 1: f"stereo with {peer}", 2: "party"}.get(mode, f"mode {mode}")


def _print_status(status):
    unit = status["unit"]
    print(f'{unit.name}  model {status["model"] or unit.model}  classic {unit.classic_mac}')
    print(f'  protocol {status["protocol"] or "?"}  firmware {status["firmware"] or "?"}')
    battery = "?" if status["battery"] is None else status["battery"]
    print(f"  battery {battery}%")
    print(f'  eq {_eq_name(status["eq"])}')
    print(f'  bass {_bass_text(status["bass"])}')
    print(f'  spatial {_bool_text(status["spatial"])}')
    print(f'  night {_night_text(status["night"])}')
    print(f'  stereo {_stereo_text(status["stereo"])}')


def _pair(args, units):
    master = _pick(units, args.master) if args.master else None
    if master is None:
        connected = [u for u in units if is_classic_connected(u.classic_mac)]
        if len(connected) == 1:
            master = connected[0]
    if master is None:
        raise SystemExit("cannot tell which unit is the A2DP master; pass --master MAC")

    if args.slave:
        slave = _pick(units, args.slave)
    else:
        others = [u for u in units if u.classic_mac != master.classic_mac]
        slave = next((u for u in others if u.state == 0), others[0] if len(others) == 1 else None)
    if slave is None or slave.classic_mac == master.classic_mac:
        raise SystemExit("second unit not found; power it on and pass --slave if two are visible")

    with Speaker(master) as master_speaker, Speaker(slave) as slave_speaker:
        state = pair_stereo(master_speaker, slave_speaker)
    print(f"stereo {_stereo_text(state)}")
    return 0


def main(argv=None):
    args = _parse(argv)
    units = scan()
    if not units:
        raise SystemExit("no CMF Speaker S advertising nearby (power it on)")
    if args.cmd == "scan":
        for unit in units:
            flag = "idle" if unit.state == 0 else f"state {unit.state}"
            print(f"{unit.classic_mac}  {unit.model}  {unit.name}  LE {unit.le_address}  {flag}")
        return 0
    if args.cmd == "pair":
        return _pair(args, units)

    with Speaker(_pick(units, args.mac)) as speaker:
        if args.cmd == "status":
            _print_status(speaker.summary())
        elif args.cmd == "eq":
            print(f"eq {_eq_name(speaker.set_eq(PRESETS[args.preset]))}")
        elif args.cmd == "custom-eq":
            gains = speaker.set_custom_eq(
                {"low": args.low, "mid": args.mid, "high": args.high}
            )
            if gains is None:
                raise SystemExit("device did not confirm custom EQ")
            print("custom eq  " + "  ".join(f"{k} {v:+.1f} dB" for k, v in gains.items()))
        elif args.cmd == "bass":
            print(f"bass {_bass_text(speaker.set_bass(args.level))}")
        elif args.cmd == "spatial":
            print(f"spatial {_bool_text(speaker.set_spatial(args.state == 'on'))}")
        elif args.cmd == "night":
            print(f"night {_night_text(speaker.set_night(args.state == 'on', args.minutes))}")
        elif args.cmd == "find":
            speaker.find()
            print("find requested")
        elif args.cmd == "ungroup":
            print(f"stereo {_stereo_text(ungroup(speaker))}")
    return 0
