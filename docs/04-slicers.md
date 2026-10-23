# 4. Slicers: Orca and PrusaSlicer

A slicer turns a model (STL) into the G-code the printer runs. You need one.
Two work well with this machine: **Orca Slicer** and **PrusaSlicer**. This page sets up both,
with the same numbers. Pick one, not both.

Both must be told the firmware is **Klipper** (a setting called "G-code flavor"). That single
choice also avoids the worst trap in this guide, explained in the warning below.

## Which one

| | Orca Slicer | PrusaSlicer |
|---|---|---|
| Interface | modern, fast preview, built-in calibration prints | plain, older layout |
| Used by | most people now | long-time Slic3r/Prusa users |
| Custom printer | you create one and fill in a form | wizard, then edit the profile |
| Klipper flavor | yes, `klipper` | yes, `klipper` |
| Profile in this repo | `presets/orca-notes.md` (values only, no file to import) | `presets/prusaslicer-um2.ini` (ready to load) |
| What we tested | the same numbers, typed by hand; not printed from Orca yet | sliced and printed on this machine |

- Choose **Orca** if you want the nicer interface and the built-in tests.
- Choose **PrusaSlicer** if you want the least typing. The `.ini` in this repo was produced on
  this printer and has been used for real prints.

Both read the same G-code. A file sliced by either one prints the same.

## The numbers

Measured where chapter 7 says so; sane defaults elsewhere (see [07-results](07-results.md)). Enter them once.

| Setting | Value |
|---|---|
| Bed size | 225 x 225 mm |
| Maximum height | 305 mm |
| Nozzle diameter | 0.4 mm |
| Filament diameter | **2.85 mm** (never 1.75) |
| G-code flavor | Klipper |
| Layer height / first layer | 0.2 / 0.2 mm |
| Line width (all of them) | 0.45 mm |
| Perimeters (wall loops) | 2 |
| Top / bottom solid layers | 4 / 3 |
| Infill | 20 %, grid |
| Nozzle / bed temperature | 220 C / 60 C |
| Retraction length / speed | 5 mm / 45 mm/s |
| Z-hop | 0.4 mm |
| Retract before wipe | 70 % |
| Fan | off on layer 1, 100 % from layer 2 |
| Acceleration | 7000 mm/s² (outer wall 5000, first layer 1000) |
| Speeds: perimeter / infill / travel / first layer | 40 / 50 / 150 / 20 mm/s |
| Max volumetric speed | 12 mm³/s |

A 0.45 mm line with a 0.4 mm nozzle is deliberate: the plastic is pressed slightly wider than the
hole, so neighbouring lines fuse. Temperatures from 195 to 220 C looked the same on this machine;
220 C is the safe middle.

## PrusaSlicer: add the printer

1. Install PrusaSlicer and start the **Configuration Wizard** (menu *Configuration > Configuration
   Wizard*).
2. On the printer page choose **Custom** if your version offers it. If it does not, pick any
   printer (for example *Original Prusa i3 MK3S*) and edit it. The fields are the same.
3. Load the profile from this repo: *File > Import > Import Config* (older versions: *File > Load
   Config*) and select `presets/prusaslicer-um2.ini`. Three presets appear: printer, print, filament.
4. Open *Printer Settings* and check: bed 225 x 225 with origin at the front left, max print height
   305, one extruder with a 0.4 mm nozzle, G-code flavor **Klipper**.
5. Open *Filament Settings* and check the diameter is **2.85 mm**. PrusaSlicer defaults to 1.75 mm.
   Wrong diameter means grossly wrong extrusion, not a small error.
6. Slice a 20 mm cube. Slice and preview should work with no warnings.

You should see: the preview fills the bed area and the G-code file starts with
`PRINT_START BED_TEMP=60 EXTRUDER_TEMP=220`.
If you do not: the profile did not load. Do step 3 again and confirm the preset names changed.

The `.ini` calls the `PRINT_START` and `PRINT_END` macros from `config/macros.cfg`. Load or copy
that file to the printer first, or the print stops at the first line with
`Unknown command: "PRINT_START"`.

## Orca: add the printer

1. Install Orca and open the printer dropdown at the top left, then **Add/Remove printers**.
2. Choose **Custom** (or copy any Marlin printer with a 0.4 mm nozzle) and confirm.
3. *Printer Settings > Basic information*: printable area **Rectangular, 225 x 225**, origin 0, 0.
   Printable height **305**. Nozzle diameter **0.4**.
4. *Printer Settings > Advanced*: G-code flavor **klipper**.
5. *Printer Settings > Motion ability*: maximum acceleration 7000 mm/s², maximum speed 300 mm/s.
   If these are lower, Orca quietly clamps your 7000 back down.
6. *Printer Settings > Extruder*: retraction length 5 mm, speed 45 mm/s, Z-hop 0.4 mm, wipe while
   retracting on, retract before wipe 70 %.
7. *Filament*: filament diameter **2.85 mm**, flow 1.0, nozzle 220 C, bed 60 C, fan 100 % from
   layer 2.
8. *Process*: the quality and speed numbers from the table above.
9. Machine start G-code, all on **one line** — a line break splits the command in two:
   `PRINT_START BED_TEMP={bed_temperature_initial_layer_single} EXTRUDER_TEMP={nozzle_temperature_initial_layer}`
   Machine end G-code: `PRINT_END`. Orca uses braces; square brackets are PrusaSlicer syntax and
   would be pasted literally.
10. Slice the same 20 mm cube and check the file with the commands below.

The full field-by-field checklist is in `presets/orca-notes.md`.
You should see: the 3D bed in Orca is a square, not the default rounded bed, and the sliced file
contains `PRINT_START`. If the bed still looks round, step 3 did not apply.

## Warning: M204 P1500 ruins corners

> **Do not let the slicer write `M204 P1500`.** Some profiles (Marlin flavor, old pre-sliced files)
> write `M204 P1500 T1500`. Klipper reads that and sets acceleration to the **lower** of the two
> numbers, 1500 mm/s², with no warning at all. The head then crawls into every corner, pauses, and
> plastic bulges there. It looks like an extrusion or pressure-advance problem. It is not.
>
> Fix: use the **Klipper** flavor, or delete every `M204 P1500` / `M204 P1500 T1500` line before
> printing. Values of 5000-7000 mm/s² print visibly cleaner on this machine.
>
> Note for the curious: a bare `M204 P1500` on its own is ignored by Klipper, and `M204 S7000` is
> the correct form (Klipper docs, [G-Codes](https://www.klipper3d.org/G-Codes.html): acceleration
> is set from `S`, or from the minimum of `P` and `T` when `S` is absent). Delete the line anyway;
> you do not want to depend on which form your slicer emitted.

## Check the G-code before printing

Every file, every time. It takes ten seconds. In PrusaSlicer use *File > Export G-code*, then run
these in a terminal (any Linux, macOS, or WSL shell):

```bash
f=my_part.gcode

grep -nE "^G2 |^G3 " $f      # must print nothing
grep -nE "M201|M203|M205" $f # must print nothing
grep -n  "M204" $f | head -5 # only M204 S<number> is allowed
grep -c  "M106" $f           # 1 or more: the fan is switched on
```

| Line found | Meaning | Do this |
|---|---|---|
| `G2` / `G3` | arc moves. `[gcode_arcs]` is not in this config, so the line is skipped with `Unknown command: "G2"` and the print continues with a gap | turn arcs off, or use the Klipper flavor, and re-slice |
| `M201`, `M203`, `M205` | Marlin machine limits. Klipper ignores them (console message, print continues) | delete the lines or re-slice with the Klipper flavor |
| `M204 P1500` or `M204 P1500 T1500` | acceleration pinned to 1500 | delete the lines (see the warning above) |
| `T0` in an old file | tool select, not supported here | delete the line |
| nothing at all | good. Print it | - |

Our own test cube was sliced with the PrusaSlicer profile in this repo. Its file contained 56
`M204` lines, all in the `M204 S7000` / `S1000` / `S5000` form, one `M106 S255`, retractions of
`G1 E-5 F2700` (5 mm at 45 mm/s), and no `M201`, `M203`, `M205`, `G2` or `G3`.

## If something looks wrong

| Symptom | Usual cause | Fix |
|---|---|---|
| Bulging corners, shiny blobs at edges | acceleration at 1500 | check `M204` lines, raise accel to 7000 |
| Console shows `Unknown command: "G2"`, print continues with a gap | arcs in the G-code were skipped | set flavor Klipper, disable arc fitting |
| Console shows `Unknown command: "M201"` / `"T0"`, print continues | old Marlin file; limits ignored | delete those lines |
| Very fat, rough walls, nozzle ploughing | filament diameter set to 1.75 | set 2.85 in the filament profile |
| Thin walls, gaps between lines | line width below 0.4 or flow under 0.95 | line width 0.45, flow 1.0 |
| Strings between parts | retraction off or too short | 5 mm at 45 mm/s, wipe on |
| Blob on the part every time it waits for temperature | the wait happens over the print | see the retract-and-park rule in [06-troubleshooting](06-troubleshooting.md) |

## Links

- PrusaSlicer documentation: <https://help.prusa3d.com/slicer>
- Orca wiki, G-code flavor and printer settings: <https://www.orcaslicer.com/wiki/printer_settings/basic%20information/printer_basic_information_advanced.html>
- Klipper's supported G-codes (the `M204` rule): <https://www.klipper3d.org/G-Codes.html>
