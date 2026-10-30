# AYAB-SR-ESP32

ESP32-S3 interface board for Silver Reed knitting machines (successor of the
`ayab-silver-reed-shield` in `silverreed-firmware`). KiCad 10 project.
AYAB talks to it over Wi-Fi in normal use; USB (J2) is the fallback for users
who prefer a cable, and for flashing.

![Board, 3D view](renders/iso_front.png)

Status: schematic complete, board placed and routed (DRC: 0 unconnected, no
clearance errors). Not built yet — see *Open points* before ordering.

The schematic is a single A2 sheet split into titled sections: power input,
5 V buck, 3.3 V supply, USB (programming), user interface, solenoid buck,
current sense and limiter, mechanical, MCU, level shifting and machine
connector. Sections connect through net labels.

## Power

| Rail | Source | Notes |
|---|---|---|
| `+15V` | J1 USB-C PD, CH224A (U1) asks for 15 V (R1 = 56k) | Feeds both bucks |
| `Vout` / `Vsol` | U6 TPS54202, adjustable 4.6–13.3 V with RV1 | Solenoid supply, through shunt R6 (50 mΩ); `Vsol` goes to the DIN socket |
| `+5V` | U9 TPS54202, R12/R13 = 75k/10k → 5.07 V | Machine logic (DIN pin 7), U4, pull-ups R15–R18 |
| `+3.3V` | U10 AP2112K from `+5V` (D2) or J2 VBUS (D1) | ESP32, OLED, U7, U8 |

- U6 (solenoids) is enabled by the ESP32 (`SOL_EN`, 100k pull-down: off until
  the firmware turns it on). U9 is always on.
- Current limiter: U7 INA381A1 senses R6 (Kelvin connection), compares with
  the threshold set by RV2, and its `ALERT` output switches Q1, which pulls
  U6's FB to ground. `Vsense` (U7 VOUT, 1 V/A) is read by the ESP32.
  Threshold: R9 82k / RV2 50k / R23 27k on 3.3 V gives CMPREF 0.56–1.60 V,
  i.e. 0.56–1.60 A (0.60–1.48 A to 0.53–1.70 A with a ±20 % trimmer).
  Hysteresis 4 µA × (12.5k + R10 82k) ≈ 0.38 V, i.e. ~0.4 A; CMPREF stays
  above it over the whole range, so `ALERT` always releases (RESET is tied
  to GND).

## ESP32-S3-WROOM-1 pin map

| GPIO | Module pin | Signal | Direction / notes |
|---|---|---|---|
| IO0 | 27 | `BTN_C` | S1 push (centre); also the BOOT strap: held at reset → download mode |
| IO1 | 39 | `Vsense` | ADC1_CH0, U7 output, 1 V per amp of solenoid current |
| IO2 | 38 | `Vsol_div` | ADC1_CH1, `Vsol` × 10/57 (R7 47k / R8 10k): 15 V → 2.63 V |
| IO8 | 12 | `SDA` | I²C: OLED (U5) and CH224A (U1), 4.7k pull-ups |
| IO18 | 11 | `SCL` | I²C |
| IO9 | 17 | `ND1_3V` | Machine ND1 via U8 |
| IO10 | 18 | `CCP_3V` | Machine CCP (carriage clock) via U8 |
| IO11 | 19 | `HOK_3V` | Machine HOK (direction) via U8 |
| IO13 | 21 | `KSL_3V` | Machine KSL (point cam) via U8 |
| IO14 | 22 | `DOB_3V` | Output: solenoid data, to the DIN via U4 (5 V) |
| IO16 | 9 | `BTN_B` | S1 rolled toward the USB-C edge (away from the DIN) |
| IO17 | 10 | `BTN_D` | S1 rolled toward the DIN |
| IO38 | 31 | `SOL_EN` | Output: enable of the solenoid buck U6 (high = on) |
| IO39 | 32 | `PG` | CH224A power-good (open drain, 10k pull-up) |
| IO19/IO20 | 13/14 | USB D−/D+ | Native USB on J2 (through U2 ESD) |
| TXD0/RXD0 | 37/36 | J4 | UART header, not populated by default |

Firmware notes:

- Machine inputs: U8 (74LVC125, powered from 3.3 V, 5 V-tolerant inputs)
  translates the 5 V DIN signals; R15–R18 pull them up to 5 V on the DIN side,
  so `INPUT` is enough on the ESP32 side (no internal pull-up needed).
- `DOB`: U4 (74AHCT1G125 on 5 V) drives the DIN from the 3.3 V GPIO.
- Buttons: S1 common is GND → `INPUT_PULLUP`, active low.
- Avoided on purpose: IO3, IO45, IO46 (straps), IO35–IO37 (PSRAM on some
  module variants).
- CH224A over I²C (address 0x22/0x23): it can request up to 28 V (register
  0x0A), above the 25 V rating of C1/C7 and at the TPS54202's limit. Do not
  request more than 20 V.

## Connectors

| Ref | Function |
|---|---|
| J1 | USB-C, power input (USB-PD 15 V) |
| J2 | USB-C, ESP32 native USB (programming, serial) |

J1 and J2 are 14.8 mm apart (centre to centre), like the USB-C ports of a
MacBook, so dual-plug MacBook cables and hubs fit both at once.
| J3 | DIN-7 female, to the knitting machine |
| J14 | 1×8 header duplicating the DIN signals (debug / alternative cable) |
| J4 | ESP32 UART0 (TX, RX), not populated |
| S1 | BL-DT 3-way thumb wheel, wheel protrudes past the top edge, under the OLED. Per the datasheet, rolling the rim 24° toward a terminal's side closes it: toward the USB-C edge → B, toward the DIN → D; push → C (common A to GND) |
| U5 | 0.91" 128×32 I²C OLED module, Hansheng HS91L02W2C01 (LCSC C5248081, SSD1306, address 0x3C), on a 2.5 mm header spacer; any 38 × 12 mm 4-pin GND/VCC/SCL/SDA module fits |

DIN J3 and J14 pinout:

| Signal | J3 | J14 |
|---|---|---|
| ND1 | 1 | 2 |
| KSL | 2 | 3 |
| DOB | 3 | 4 |
| CCP | 4 | 5 |
| HOK | 5 | 6 |
| Vsol | 6 | 7 |
| +5V | 7 | 8 |
| GND | shield (8) | 1 |

## PCB

- 2 layers, GND pour on both sides, 64.5 × 83.1 mm (width × height), drawn in
  its intended orientation: DIN socket J3 facing up, USB-C sockets on the
  right edge. A 23.9 × 8.7 mm notch above the DIN socket leaves room for bulky
  plugs. S1's wheel sticks out of the top edge, centred on its straight part
  (x 123.9–164.5); the OLED's visible area sits 0.5 mm further from the DIN
  than S1's axis (the HS91L02W2C01 active area is 7.62 mm from the end of
  its board, not the 7.1 mm the board was laid out for).
- Net classes: Power 0.6 mm (`+15V`, U6 switch node, `Vout`, `Vsol`),
  Supply 0.3 mm (`+5V`, `+3.3V`, LDO input, J2 VBUS), Default 0.2 mm.
- Minimum track 0.15 mm (fine-pitch escapes), minimum hole 0.2 mm (ESP32
  footprint thermal vias): within JLCPCB's standard process.
- Antenna: the ESP32 antenna is on the right edge, with a 5.6 × 47.9 mm
  cut-out under it (y 32.7–80.6, from x = 158.9: the keep-out starts at
  158.66, the 0.24 mm strip left keeps the SDA/SCL tracks 0.5 mm from the
  edge). The lower part of the OLED module still hangs over the keep-out.
- Routing was done with Freerouting (power nets first, then signals) plus
  local fixes; it is functional but autorouter-looking — worth a manual
  review pass in KiCad (especially the `+15V` / `Vsol` paths and the USB pair).

3D models: `ayab-library/packages3D/OLED_0.91_128x32_I2C.step` (generated by
`packages3D/generators/oled_0.91_128x32_step.py`) and `SW-SMD_BL-DT.x3d` for S1.

A 3D-printable enclosure is in [`enclosure/`](enclosure/README.md).
Its model follows the board's 90° turn (`board_frame()` in the .scad); the
enclosure renders and sections below still show the case in the old
orientation and will be redone with the planned redesign (ring around the
machine's mast).

## Renders

Board renders come from KiCad (`kicad-cli pcb render`), enclosure renders from
OpenSCAD's preview (`enclosure/tools/quick_render.py`) and the 2D sections
from `enclosure/tools/sections.py`. MP4 versions of the animations:
[board turntable](renders/board_turntable.mp4),
[enclosure turntable](enclosure/renders/turntable.mp4),
[enclosure exploded](enclosure/renders/exploded.mp4).

### Board

<table>
<tr><td align="center"><img src="renders/iso_front.png" alt="Front isometric" width="400"><br><sub>Front isometric</sub></td><td align="center"><img src="renders/iso_back.png" alt="Back isometric" width="400"><br><sub>Back isometric</sub></td></tr>
<tr><td align="center"><img src="renders/top.png" alt="Top" width="400"><br><sub>Top</sub></td><td align="center"><img src="renders/bottom.png" alt="Bottom" width="400"><br><sub>Bottom</sub></td></tr>
<tr><td align="center"><img src="renders/board_turntable.gif" alt="Turntable" width="400"><br><sub>Turntable</sub></td></tr>
</table>

### Enclosure

<table>
<tr><td align="center"><img src="enclosure/renders/01_assembled.png" alt="Assembled" width="400"><br><sub>Assembled</sub></td><td align="center"><img src="enclosure/renders/02_assembled_right.png" alt="Assembled, DIN and wheel side" width="400"><br><sub>Assembled, DIN and wheel side</sub></td></tr>
<tr><td align="center"><img src="enclosure/renders/03_xray.png" alt="X-ray (transparent lid)" width="400"><br><sub>X-ray (transparent lid)</sub></td><td align="center"><img src="enclosure/renders/04_exploded.png" alt="Exploded" width="400"><br><sub>Exploded</sub></td></tr>
<tr><td align="center"><img src="enclosure/renders/05_tray_with_board.png" alt="Tray with the board" width="400"><br><sub>Tray with the board</sub></td><td align="center"><img src="enclosure/renders/06_tray.png" alt="Tray" width="400"><br><sub>Tray</sub></td></tr>
<tr><td align="center"><img src="enclosure/renders/07_lid_top.png" alt="Lid, top" width="400"><br><sub>Lid, top</sub></td><td align="center"><img src="enclosure/renders/08_lid_underside.png" alt="Lid, underside" width="400"><br><sub>Lid, underside</sub></td></tr>
<tr><td align="center"><img src="enclosure/renders/09_openings_usb.png" alt="USB-C side" width="400"><br><sub>USB-C side</sub></td><td align="center"><img src="enclosure/renders/10_openings_din_wheel.png" alt="DIN and wheel side" width="400"><br><sub>DIN and wheel side</sub></td></tr>
<tr><td align="center"><img src="enclosure/renders/turntable.gif" alt="Turntable" width="400"><br><sub>Turntable</sub></td><td align="center"><img src="enclosure/renders/exploded.gif" alt="Exploded, animated" width="400"><br><sub>Exploded, animated</sub></td></tr>
</table>

### Enclosure sections

<table>
<tr><td align="center"><img src="enclosure/renders/11_section_wheel_oled.png" alt="Through the wheel S1 and the OLED" width="400"><br><sub>Through the wheel S1 and the OLED</sub></td><td align="center"><img src="enclosure/renders/12_section_din.png" alt="Through the DIN socket axis" width="400"><br><sub>Through the DIN socket axis</sub></td></tr>
<tr><td align="center"><img src="enclosure/renders/13_section_usb.png" alt="Through the USB-C J1" width="400"><br><sub>Through the USB-C J1</sub></td><td align="center"><img src="enclosure/renders/14_section_columns.png" alt="Through the H2 column" width="400"><br><sub>Through the H2 column</sub></td></tr>
</table>

## Production files

`production/` holds outputs generated with `kicad-cli` 10.0.7 from this
revision: Gerbers and Excellon drill files (`gerbers/`, zipped in
`ayab-sr-esp32-gerbers.zip`), the BOM (`ayab-sr-esp32-bom.csv`, grouped, with
an LCSC number on every placed part), the pick-and-place file
(`ayab-sr-esp32-pos.csv`, plus `ayab-sr-esp32-cpl-jlc.csv` in JLCPCB's CPL format with
the `FT Rotation Offset` corrections applied) and the schematic PDF. Regenerate them after
any change (scripts on the `tooling` branch).

## Tooling

The scripts used to edit, check, route and regenerate this board (and the matching workflow skill)
live on the `tooling` branch.

## Open points

- CH224A (checked in the WCH CH224 manual v2.1): PG is open drain, active low,
  rated 32 V, so R20 is right; a single CFG1 resistor enables I²C on CFG2/CFG3
  (internal 7–15k pull-ups), so R21/R22 do not change the mode.
- Wi-Fi is the main link, so the antenna matters most. The lower part of the
  OLED module (y > 32.7) hangs over the antenna keep-out (above the
  cut-out) and will detune it to some degree. On the first boards, measure
  RSSI and throughput with the board in its enclosure and mounted on the
  machine (a large metal body: the antenna end should face away from it),
  and repeat with the OLED removed to see what the overhang costs. If it
  costs too much: move or turn the OLED off the keep-out, or use the
  ESP32-S3-WROOM-1U (u.FL) with a small external antenna (about $0.5–1 more).
- Also on the first boards: scope the 3.3 V rail during Wi-Fi transmit bursts
  (350–500 mA peaks on the AP2112K) with the solenoids firing, the bucks'
  switching noise, and the Vsense / Vsol_div ADC readings. These measurements
  decide whether the first respin goes to 4 layers (solid GND plane under
  the module and the bucks).
- DRC: one item left on purpose, U5 in the antenna keep-out (see above), kept
  as a reminder until Wi-Fi range is measured. `ayab-sr-esp32.kicad_dru` has
  the JLCPCB 2-layer rules plus two documented exceptions: U5 stands on its
  spacer above U3 and S1 (courtyard overlap), and the silkscreen of parts
  that overhang the board edge (U3, U5, J3) is clipped by the fab.
