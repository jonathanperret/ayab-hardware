# KH-910 right-hand sensor board (BP-111025-7 / PCB-E-144)

Reverse-engineering workspace for the Brother KH-910 right sensor board
(3 optical encoders via photo-interrupters PI1/PI2, hall-sensor amplifier
IC303 + comparator, mylar-reader signal conditioning).

- `tracer/` — local interactive tracing tool. Run `python3 tracer/server.py`
  and open http://localhost:8765/. All work is in `tracer/state.json`
  (pads with positions on both photos, traces with side + corners, parts);
  every save keeps a copy in `tracer/backups/`.
- `photos/` — original photos: both sides, crack close-ups, repairs, S-5 connector.
- `images/` — annotated photos, crack/repair maps; `tests/` = continuity-test probe maps.
- `kicad/` — KiCad 10 project. The schematic is the same drawing as `schematic/` (converted element by element by `kicad/build/svg_to_kicad_sch.py`) and its connectivity is checked against the tracer netlist on every build; the PCB uses the tracer's pad positions and tracks (rounded corners), with nets named as in the schematic. `kicad/build/build.sh` regenerates both (needs a python with numpy, scipy and schemdraw: `PYTHON=... kicad/build/build.sh`) and writes `erc_report.txt` / `drc_report.txt`.
- `schematic/` — schematic sheets drawn from the tracer netlist (`draw_schematic.py`), `netlist.txt` at the top level.

## Measured so far (multimeter)
- Harness pad I = +5V, H = GND; D = IC302 p13, E = IC301 p14, F = IC301 p7, G = IC301 p8.
- Bottom harness, two bundles: optical (mylar reader) board on J signal, K GND, L +5V;
  hall sensor board on M +5V, N and P outputs (difference amplifier IC303 via R335/R334), O GND.
- Open solder jumpers (solder side): JP1 between R325.1 and R326.1, JP2 between R323.1 and R324.1.
- Flex cracks repaired 2026-11-15: R1 solder-side GND bus (top edge), R2 +5V
  trace under IC302, R3a/b right-edge +5V trace (both sides), R4 solder jumper.

## To beep when the board is back
- R305.1 ↔ IC301.11 (expect beep: component-side right-edge trace = GND, drawn on that assumption)
- R305.1 ↔ IC301.4 (expect open)
- pad I ↔ IC302.2 (expect open; +5V should be on IC302.3)
- IC301 (324) pins 1, 2, 3, 6, 13 have no solder-side copper; their connections run under the IC body (component side). Beep:
  IC301.6 ↔ IC301.9, IC301.13 ↔ IC301.9 (shared comparator reference?), IC301.1 ↔ IC301.2 (follower?),
  (section 1, pins 1-3, treated as unused).
- Interrupter outputs to comparators: PI1.5 and PI1.6 ↔ IC301.5 / IC301.10 / IC301.12.
- PI1.3 and PI1.7: no copper found, assumed NC; confirm with diode test.
- Hall amplifier (IC303 section 2): IC303.7 ↔ CH301 net (expect beep, via152?). IC303.5 (IN2+) ↔ VR301.3 / R333.2-R335.1 node / pad J (via148):
  tells whether VR301 sets an offset (wiper reaches IN2+) or the hall sensor drive (wiper only feeds pad N).
  Powered test: no magnet near the sensor, turn VR301 and watch CH301 (large smooth change = offset).
- Hall/optical mixing at IC302.11 (IN4+): traces say hall out → R322 → IC302.11 and R321 links IC302.11 to the optical divider (R320/R319).
  Hall and optical must not mix, so something is off. Measure ohms: IC302.11 ↔ pad J (expect open or very high),
  R321.1 ↔ R320.1, R321.2 ↔ R322.2, and confirm which two pads each of R319–R322 actually spans.
- PI1/PI2 LED chain: R303.2, R304.2 ↔ +5V (expect beep); diode test PI1.1→PI1.3 and PI1.2→PI1.4 (~1.1 V), PI1.3 ↔ PI1.4 (beep if tied); PI1.8 ↔ +5V.
- R303.2 / R304.2 supply is not visible on either photo (likely under the resistor bodies, component side): beep R303.2 ↔ R304.2, R304.2 ↔ pad I, R305.2 ↔ R304.2 and ↔ pad I.
  (Repair R4 = jumper bridging the cracked R310.2 → via137 trace.)
- R309.1 ↔ R310.2 (expect 0 Ω: shared reference ladder +5V–R306–R307–R309–R310–GND).
- Links drawn on inference (hidden copper), confirm by beeping: IC302.10 ↔ via152 (hall amp out); R322.1 ↔ IC302.13;
  R318.2 / R320.2 ↔ +5V; via148 (pad J) ↔ IC302.4 and IC302.6; via089 ↔ IC301.4; D301 cathode side ↔ PI1.3/PI1.4/PI2.4;
  R303.2 ↔ IC301.5; R304.2 ↔ IC301.10; D301 band toward PI1.8.
