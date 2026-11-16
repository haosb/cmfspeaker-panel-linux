# CMF Speaker S protocol notes

Verified on model E494, firmware `1.0.1.39` and `1.0.1.55` (2026-11-16). Interoperability notes from a legally owned device. Not affiliated with Nothing/CMF.

## Link

- BLE GATT service `0000fd90-0000-1000-8000-00805f9b34fb`
- Write `68745353-1810-4b13-83a2-c1b21b652c9b`
- Notify `ca235943-1810-45e6-8326-fc8ca3bc45ce`
- Coexists with A2DP/AVRCP. No bonding needed.
- Never write OTA `e49a25f8-…` / `00006666-…` or Fast Pair `0000fe2c-…`.

Advertisement: manufacturer `0x0CCB`. Payload: `state, 01, model u16BE (E494), classic MAC 6B little-endian`. Bind the LE device to its A2DP unit by the classic MAC; the LE address rotates. An idle peer advertises state `00`; the official app filters others.

## Framing

```
55 | control u16LE | cmd u16LE | len u16LE | seq | payload | crc16LE
control = 0x0160
CRC-16/MODBUS over header+payload, low byte first
reply cmd = request cmd with bit 15 cleared
seq 1..250, one outstanding request
```

Reads carry payload `07` (endpoint "speaker"), except `C001` (empty). Unanswered read = unsupported command.

## Commands

| Function | Read | Write | Write payload |
|---|---|---|---|
| Protocol version | `C001` | — | empty |
| Battery | `C007` | — | `07` → `01 07 37` = 55 % (byte 2) |
| Model | `C01C` | — | `07` → `94 E4` = E494 |
| Firmware | `C042` | — | `07` |
| Config/serial | `C006` | — | `07` |
| EQ preset | `C01F` | `F010` | `preset 00` |
| Custom EQ | `C044` | `F041` | see below |
| Ultra Bass | `C04E` | `F051` | `enabled level*2` |
| Spatial | `C04F` | `F052` | `00` off / `01` fixed |
| Night mode | `C072` | `F076` | `mode, minutes u16LE` |
| Find | `C002` | `F002` | `07 01` |
| Stereo | `C045` | `F047` | see below |

EQ presets: `0` balanced, `1` voice, `2` more treble, `3` more bass, `5` custom. `F041` only stores the bands; select Custom with `F010` payload `05 00`.

Custom EQ: `count:u8, totalGain:f32LE, count × [filter:u8, gain:f32LE, freq:f32LE, Q:f32LE]`. Device order: peak 980 Hz Q0.7, high shelf 3400 Hz Q1.0, low shelf 140 Hz Q0.8. Gain −6…+6 dB.

Ultra Bass: UI level 1–5 → wire `level*2`. `C04E` can report a stored level while disabled (e.g. `00 02` = off, level 1). UI keys off the enabled byte.

Night: `F076 00 00 00` normal; `01 2C 01` night, auto-off 300 min.

Stereo `F047` payload: `mode, role, peer MAC 6B reversed`. Stereo: mode `01`; role `01` master, `00` slave; payload carries the *other* unit's classic MAC. Ungroup: `00 01 FF FF FF FF FF FF`.

Verified sequence:

1. Connect this host's A2DP to the intended master.
2. Open FD90 links to both units.
3. Write `F047` to master (`01 01 <slave MAC rev>`), then slave (`01 00 <master MAC rev>`).
4. Both ack `0x7047`; master emits event `0x6026` (`E026`) payload `01`; `C045` confirms.
5. Ungroup from the master; `E026` goes `01 → 00`.

`C045` payload: `mode, role, 0x3C|0x37, peer MAC 6B reversed (bytes 3–8)`. Firmware `1.0.1.55` appends `94 E4 01` after the peer MAC; do not take the payload tail as the MAC.

Interlocks are silent on the device: always read back. Night conflicts with Voice / More treble / More bass and fixed spatial; Balanced and Custom do not. Spatial conflicts with Ultra Bass. A sound write to the slave only does not sync to the master; write the A2DP master and let the pair propagate.

## Safety

- Control channel is unauthenticated. Keep it local.
- Never write OTA/Fast Pair; bricking risk.
- Firmware behavior can change. The app shows read-back, not requested state.
