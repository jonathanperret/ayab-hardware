# AYAB Interface

The AYAB Interface is a replacement PCB that installs inside the knitting
machine and connects it to the AYAB desktop software through an Adafruit
Metro Mini. It was originally designed and produced by Evil Mad Scientist
Laboratories (EMSL).

The design files are made with gEDA (gschem and pcb):

- `schematic/`: schematic, netlist and schematic PDF
- `layout/`: PCB layout, footprints and Gerbers
- `assembly/`: bill of materials (`ayab_rs_oshw.csv`) and pick-and-place
  file (`ayab_rs.xy`)
- `enclosure/`: enclosure drawings
- `CHANGES.md`: changes between board revisions

## Component sourcing

The BOM lists a manufacturer part number for each line, plus an alternate
where one exists, and DigiKey and Mouser order numbers. Availability was
last checked in October 2026; several parts are obsolete or hard to find,
as described below.

### Obsolete connectors

- **J2C–J6C (Molex 53014 MicroBlade, 2 mm)**: obsolete since 2021. Molex
  names the 53253 Micro-Latch series as the successor, but it does not mate
  with the machine's existing cables. Source new old stock.
- **J2A, J3A, J5A (Hirose HNC2 8- and 10-pin)**: end of life. A plain
  2.54 mm pin header (Sullins PRPC008SAAN-RC / PRPC010SAAN-RC) can be fitted
  instead; the cable then has no latch.
- **J7A (Hirose HNC2 3-pin)**: still available, but marked not recommended
  for new designs. The same plain-header substitute applies.

### DigiKey

DigiKey carries every part in the BOM except the obsolete connectors above:

- **U4, U5 (ULN2803A)**: the DigiKey number is for the UMW ULN2803A; the
  EVVO ULN2803A-EV alternate is also stocked there.
- **U2, U3 (PCF8574DWR)**: TI's stock can run out. The UMW PCF8574DWR
  alternate, also sold by DigiKey, is a drop-in replacement.
- **U1 header (Samtec TSW-114-05-T-S)**: not normally stocked by DigiKey;
  it ships from Samtec's stock, with a lead time of a couple of weeks.

### Mouser

Mouser does not carry every part as listed:

- **U4, U5 (ULN2803A)**: the 18-pin wide SOIC ULN2803A is now only made by
  smaller manufacturers (UMW, EVVO) that Mouser does not stock. The Mouser
  number in the BOM is TI's ULN2803CDWR instead. It is electrically the same
  Darlington array (same 2.7 kΩ input resistors, TTL/5 V CMOS inputs) in a
  20-pin SOIC, and its pins line up with the 18-pin footprint: place pins 1–9
  on pads 1–9 and pins 12–20 land on pads 10–18, leaving the two unconnected
  pins (10 and 11) overhanging. It should be a valid substitute, but it has
  not been tested on a board yet.
- **RN1–RN4 (Yageo YC164)**: the Mouser number points at YC164-JR-131KL,
  the 13" reel version of the listed YC164-JR-071KL. The part is the same.
- **U2, U3 (PCF8574DWR)**: TI is the only maker Mouser stocks, and stock
  can run out. The PCF8574ADWR is pin-compatible and usually available, but
  it answers on a different I2C address range (0x38–0x39 instead of
  0x20–0x21). Recent versions of the AYAB firmware detect either, so it
  can be used instead, though the PCF8574 is preferred.

### Other notes

- **U1 (Metro Mini)**: both the original Metro Mini (micro-USB) and the
  Metro Mini V2 (USB-C, Adafruit 2590, the one listed in the BOM) are
  compatible.
- **S1 (reset button)**: optional. It cannot be reached once the board is
  installed in the machine, and the Metro Mini has its own reset button.
- **U1 header**: the BOM lists a 14-pin header that is short on both sides
  (Samtec TSW-114-05-T-S), to stack the Metro Mini 2.54 mm from the board
  without trimming. The header supplied with the Metro Mini can be used
  instead, with the long pins trimmed after soldering.
- **C3**: the footprint is deliberately larger than the case B tantalum
  capacitor in the BOM, so that larger capacitors can also be fitted.
