# Orca Slicer: build the UM2E+ profile by hand

Orca has no importable profile in this repo. Type these in once, about ten minutes, and Orca saves
them as your own presets.

**What is tested and what is not.** The PrusaSlicer profile (`presets/prusaslicer-um2.ini`) was
loaded and sliced on this machine, and its G-code was checked line by line. The values below are the
*same* numbers, entered by hand in Orca; they have not been printed from Orca here. Treat the first
Orca print as a test (slice a cube, run the check at the bottom) before trusting a long print.
Paths are menu > tab > section. Set Orca to `Advanced` mode or half these fields stay hidden.

## 1. Printer settings

| Where | Field | Value |
|---|---|---|
| Basic information | Printable area, shape | Rectangular, 225 x 225, origin 0, 0 |
| Basic information | Printable height | 305 |
| Basic information | Nozzle diameter (extruder) | 0.4 |
| Advanced | G-code flavor | **klipper** |
| Motion ability | Maximum acceleration X / Y / extruder | 7000 / 7000 / 5000 mm/s² |
| Motion ability | Maximum speed X / Y | 300 mm/s |
| Motion ability | Emit limits to G-code | on (ignored when flavor is klipper) |

The motion-ability numbers matter: Orca caps your print acceleration to whatever is here, so a
profile with 7000 in the process tab and 1000 here still prints at 1000.

## 2. Printer settings > Extruder (retraction and Z-hop)

| Field | Value |
|---|---|
| Retraction length | 5 mm |
| Retraction speed | 45 mm/s |
| Deretraction speed | 45 mm/s |
| Travel distance threshold | 2 mm |
| Retract on layer change | on |
| Wipe while retracting | on |
| Wipe distance | 2 mm |
| Retract amount before wipe | 70 % (if your field is in mm: 3.5 mm) |
| Z-hop type | Normal |
| Z-hop height | 0.4 mm |
| Extra length on restart | 0 mm |

A long Bowden tube is why 5 mm is needed and 0.8 mm would not be (see [03-tuning](../docs/03-tuning.md)).

## 3. Filament settings

| Field | Value |
|---|---|
| Filament type | PLA |
| Filament diameter | **2.85 mm** |
| Flow ratio | 1.0 |
| Nozzle temperature (and initial layer) | 220 C |
| Bed temperature (and initial layer) | 60 C |
| Max volumetric speed | 12 mm³/s |
| Fan speed min / max | 100 % / 100 % |
| Disable fan for the first | 1 layer |
| Full fan speed at layer | 2 |
| Slow down if layer print time is below | 5 s |
| Min print speed | 10 mm/s |

The diameter is the one field that must not be missed. Orca defaults to 1.75 mm; leaving it there
over-extrudes by roughly 2.6 times and the nozzle ploughs through the part.

## 4. Process settings

Quality:

| Field | Value |
|---|---|
| Layer height / initial layer height | 0.2 / 0.2 mm |
| Line width: default, outer wall, inner wall | 0.45, 0.45, 0.45 mm |
| Line width: sparse infill, internal solid, top surface, initial layer | 0.45 mm each |
| Wall loops | 2 |
| Top shell layers / bottom shell layers | 4 / 3 |
| Sparse infill density / pattern | 20 % / Grid |
| Seam position | Aligned |
| Wall generator | Classic (any is fine, but use the same in both slicers) |

Speed:

| Field | Value |
|---|---|
| Outer wall / inner wall | 40 / 40 mm/s |
| Sparse infill / internal solid infill | 50 / 50 mm/s |
| Top surface | 40 mm/s |
| Initial layer | 20 mm/s |
| Travel | 150 mm/s |
| Bridge | 25 mm/s |

Acceleration (Print settings > Speed > Acceleration):

| Field | Value |
|---|---|
| Normal printing | 7000 mm/s² |
| Outer wall | 5000 mm/s² |
| Inner wall / sparse infill / internal solid / top surface / travel | 7000 mm/s² |
| Initial layer | 1000 mm/s² |

If every acceleration field is 0, Orca uses the printer's own limits. That also works, as long as
printer.cfg has `max_accel: 7000`.

## 5. Machine G-code

| Field | Value |
|---|---|
| Machine start G-code | `PRINT_START BED_TEMP={bed_temperature_initial_layer_single} EXTRUDER_TEMP={nozzle_temperature_initial_layer}` (one line, braces not brackets) |
| Machine end G-code | `PRINT_END` |

Replace anything Orca pre-filled (M104, M190, G28, purge lines) with that single line: the macro
homes, heats and parks the head. If the print stops with `Unknown command: "PRINT_START"`, the macro
file is not on the printer.

## 6. Save and check

1. Save the three presets under your own names, for example `UM2E+ Klipper`, `0.2 fine`, `PLA 2.85`.
2. Slice a 20 mm cube, export the G-code, then run the checks in
   [04-slicers](../docs/04-slicers.md#check-the-g-code-before-printing): no `G2`/`G3`, no `M201`/`M203`/`M205`,
   no `M204 P1500`, at least one `M106`.
3. Print the cube. Corners crisp, not bulged; walls solid, not see-through. Bulging corners mean the
   acceleration is wrong, not the flow. Fat, rough walls mean the filament diameter is still 1.75 mm.
