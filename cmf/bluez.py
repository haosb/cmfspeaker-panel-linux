"""BlueZ D-Bus transport: LE discovery, the FD90 control link, request/response."""

import re
import time
from dataclasses import dataclass

import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

from .protocol import Decoder, encode, mac_from_le

DBusGMainLoop(set_as_default=True)

BLUEZ = "org.bluez"
ADAPTER_IFACE = "org.bluez.Adapter1"
DEVICE_IFACE = "org.bluez.Device1"
SERVICE_IFACE = "org.bluez.GattService1"
CHAR_IFACE = "org.bluez.GattCharacteristic1"
PROPS_IFACE = "org.freedesktop.DBus.Properties"
OM_IFACE = "org.freedesktop.DBus.ObjectManager"

FD90 = "0000fd90-0000-1000-8000-00805f9b34fb"
WRITE_CHAR = "68745353-1810-4b13-83a2-c1b21b652c9b"
NOTIFY_CHAR = "ca235943-1810-45e6-8326-fc8ca3bc45ce"
NOTHING_MANUF = 0x0CCB
ADDRESS_RE = re.compile(r"^[0-9a-f]{2}([-:][0-9a-f]{2}){5}$", re.I)


@dataclass
class Unit:
    path: str
    le_address: str
    classic_mac: str
    model: str
    state: int
    name: str


def _objects(bus):
    manager = dbus.Interface(bus.get_object(BLUEZ, "/"), OM_IFACE)
    return manager.GetManagedObjects()


def _adapter(bus):
    for path, props in _objects(bus).items():
        if ADAPTER_IFACE in props:
            return dbus.Interface(bus.get_object(BLUEZ, path), ADAPTER_IFACE)
    raise RuntimeError("no Bluetooth adapter")


def _name(device):
    name = str(device.get("Name") or "")
    return name if name and not ADDRESS_RE.match(name) else ""


def parse_units(objects):
    names = {}
    for props in objects.values():
        device = props.get(DEVICE_IFACE)
        if device and _name(device):
            names[str(device.get("Address", "")).upper()] = _name(device)

    units = []
    for path, props in objects.items():
        device = props.get(DEVICE_IFACE)
        if not device:
            continue
        for key, value in (device.get("ManufacturerData") or {}).items():
            if int(key) != NOTHING_MANUF:
                continue
            # BlueZ strips the company id; live payload: state, 01, model u16BE, MAC LE.
            raw = bytes(bytearray(value))
            if len(raw) < 10:
                continue
            classic_mac = mac_from_le(raw)
            units.append(
                Unit(
                    path=path,
                    le_address=str(device.get("Address", "")),
                    classic_mac=classic_mac,
                    model=f"{int.from_bytes(raw[2:4], 'big'):04X}",
                    state=raw[0],
                    name=_name(device) or names.get(classic_mac, "") or "CMF Speaker S",
                )
            )
    return units


def scan(timeout=6.0):
    bus = dbus.SystemBus()
    adapter = _adapter(bus)
    started = False
    try:
        adapter.SetDiscoveryFilter({"Transport": "le", "DuplicateData": dbus.Boolean(True)})
        adapter.StartDiscovery()
        started = True
    except dbus.DBusException as exc:
        if "InProgress" not in (exc.get_dbus_name() or ""):
            raise
    loop = GLib.MainLoop()
    GLib.timeout_add(int(timeout * 1000), loop.quit)
    try:
        loop.run()
    finally:
        if started:
            adapter.StopDiscovery()
    return parse_units(_objects(bus))


def is_classic_connected(mac):
    for props in _objects(dbus.SystemBus()).values():
        device = props.get(DEVICE_IFACE)
        if (
            device
            and str(device.get("Address", "")).upper() == mac.upper()
            and bool(device.get("Connected"))
        ):
            return True
    return False


class Link:
    def __init__(self, unit, timeout=15.0):
        self.unit = unit
        self.bus = dbus.SystemBus()
        self.seq = 1
        self.decoder = Decoder()
        self.events = []
        self._response = None
        self._expect = None
        self._loop = None
        self._timer = None

        self._device = dbus.Interface(self.bus.get_object(BLUEZ, unit.path), DEVICE_IFACE)
        try:
            self._device.Connect()
        except dbus.DBusException as exc:
            if "AlreadyConnected" not in (exc.get_dbus_name() or ""):
                raise
        self._wait_services(timeout)
        self._resolve_gatt()

        self.bus.add_signal_receiver(
            self._on_props, "PropertiesChanged", PROPS_IFACE, BLUEZ, self._notify_path
        )
        self._notify.StartNotify()

    def _wait_services(self, timeout):
        props = dbus.Interface(self.bus.get_object(BLUEZ, self.unit.path), PROPS_IFACE)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if bool(props.Get(DEVICE_IFACE, "ServicesResolved")):
                return
            time.sleep(0.1)
        raise RuntimeError(f"services did not resolve on {self.unit.classic_mac}")

    def _resolve_gatt(self):
        objects = _objects(self.bus)
        service = next(
            path
            for path, props in objects.items()
            if SERVICE_IFACE in props
            and path.startswith(self.unit.path + "/")
            and str(props[SERVICE_IFACE]["UUID"]).lower() == FD90
        )
        chars = {
            str(props[CHAR_IFACE]["UUID"]).lower(): path
            for path, props in objects.items()
            if CHAR_IFACE in props and path.startswith(service + "/")
        }
        self._notify_path = chars[NOTIFY_CHAR]
        self._notify = dbus.Interface(
            self.bus.get_object(BLUEZ, self._notify_path), CHAR_IFACE
        )
        self._write = dbus.Interface(self.bus.get_object(BLUEZ, chars[WRITE_CHAR]), CHAR_IFACE)

    def _on_props(self, interface, changed, invalidated):
        if interface != CHAR_IFACE:
            return
        value = changed.get("Value")
        if value is None:
            return
        for frame in self.decoder.feed(bytes(bytearray(value))):
            if self._expect is not None and frame.cmd == self._expect:
                self._response = frame
                self._expect = None
                if self._loop:
                    self._loop.quit()
            else:
                self.events.append(frame)

    def _on_timeout(self):
        self._timer = None
        if self._loop:
            self._loop.quit()
        return False

    def request(self, cmd, payload=b"", timeout=1.0):
        """Write one frame and wait for its reply; None means no reply (unsupported)."""
        seq, self.seq = self.seq, 1 if self.seq >= 250 else self.seq + 1
        self._expect = cmd & 0x7FFF
        self._response = None
        self._loop = GLib.MainLoop()
        self._timer = GLib.timeout_add(int(timeout * 1000), self._on_timeout)
        try:
            self._write.WriteValue(encode(cmd, payload, seq), {"type": dbus.String("command")})
            if self._response is None:
                self._loop.run()
        finally:
            if self._timer is not None:
                GLib.source_remove(self._timer)
                self._timer = None
            self._loop = None
        response, self._response = self._response, None
        return None if response is None else response.payload

    def wait_event(self, cmd, timeout=3.0):
        deadline = time.monotonic() + timeout
        while True:
            for index, frame in enumerate(self.events):
                if frame.cmd == cmd:
                    return self.events.pop(index)
            if time.monotonic() >= deadline:
                return None
            loop = GLib.MainLoop()
            self._loop = loop
            GLib.timeout_add(100, loop.quit)
            loop.run()
            self._loop = None

    def close(self):
        try:
            self._notify.StopNotify()
        except dbus.DBusException:
            pass
        self.bus.remove_signal_receiver(self._on_props, "PropertiesChanged", PROPS_IFACE)
        try:
            self._device.Disconnect()
        except dbus.DBusException:
            pass
